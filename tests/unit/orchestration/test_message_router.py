# ABOUTME: Unit tests for MessageRouter three-channel message routing.
# ABOUTME: Tests IC/OOC/P2C visibility rules and Redis message storage.

import json
from datetime import datetime

import pytest

from src.models.messages import Message, MessageChannel, MessageType
from src.orchestration.message_router import MessageRouter


class TestMessageRouter:
    """Test suite for MessageRouter"""

    def test_route_ic_message_to_characters(self, mock_redis_client):
        """Test IC messages are routed to character channel"""
        router = MessageRouter(mock_redis_client)

        message = Message(
            message_id="msg_001",
            channel=MessageChannel.IC,
            from_agent="char_zara_001",
            to_agents=None,
            content="I attempt to repair the fuel cell",
            timestamp=datetime.now(),
            message_type=MessageType.ACTION,
            phase="character_action",
            turn_number=1
        )

        result = router.route_message(message)

        assert result["success"] is True
        assert result["recipients_count"] == 1

        # Verify message was stored in IC channel
        mock_redis_client.rpush.assert_called()
        call_args = mock_redis_client.rpush.call_args_list
        assert any("channel:ic:messages" in str(call) for call in call_args)

    def test_route_ic_message_creates_summary(self, mock_redis_client):
        """Test IC messages create summaries for players"""
        router = MessageRouter(mock_redis_client)

        message = Message(
            message_id="msg_002",
            channel=MessageChannel.IC,
            from_agent="char_zara_001",
            to_agents=None,
            content="I carefully examine the alien artifact with my scanner",
            timestamp=datetime.now(),
            message_type=MessageType.ACTION,
            phase="character_action",
            turn_number=2
        )

        router.route_message(message)

        # Verify summary was created
        call_args = mock_redis_client.rpush.call_args_list
        assert any("channel:ic:summaries" in str(call) for call in call_args)

    def test_route_ooc_message_to_players(self, mock_redis_client):
        """Test OOC messages are routed to player channel only"""
        router = MessageRouter(mock_redis_client)

        message = Message(
            message_id="msg_003",
            channel=MessageChannel.OOC,
            from_agent="agent_alex_001",
            to_agents=None,
            content="Should we investigate the artifact or leave it alone?",
            timestamp=datetime.now(),
            message_type=MessageType.DISCUSSION,
            phase="ooc_discussion",
            turn_number=3
        )

        result = router.route_message(message)

        assert result["success"] is True
        assert result["recipients_count"] == 1

        # Verify message was stored in OOC channel
        call_args = mock_redis_client.rpush.call_args_list
        assert any("channel:ooc:messages" in str(call) for call in call_args)

    def test_route_p2c_message_to_specific_character(self, mock_redis_client):
        """Test P2C messages are routed to specific character only"""
        router = MessageRouter(mock_redis_client)

        message = Message(
            message_id="msg_004",
            channel=MessageChannel.P2C,
            from_agent="agent_alex_001",
            to_agents=["char_zara_001"],
            content="Use your engineering expertise to assess the damage",
            timestamp=datetime.now(),
            message_type=MessageType.DIRECTIVE,
            phase="p2c_directive",
            turn_number=4
        )

        result = router.route_message(message)

        assert result["success"] is True
        assert result["recipients_count"] == 1

        # Verify message was stored in character-specific P2C channel
        call_args = mock_redis_client.rpush.call_args_list
        assert any("channel:p2c:char_zara_001" in str(call) for call in call_args)

    def test_route_p2c_message_requires_recipients(self, mock_redis_client):
        """Test P2C messages must specify to_agents"""
        router = MessageRouter(mock_redis_client)

        message = Message(
            message_id="msg_005",
            channel=MessageChannel.P2C,
            from_agent="agent_alex_001",
            to_agents=None,  # Missing recipients
            content="Do something",
            timestamp=datetime.now(),
            message_type=MessageType.DIRECTIVE,
            phase="p2c_directive",
            turn_number=5
        )

        with pytest.raises(ValueError, match="P2C messages must specify to_agents"):
            router.route_message(message)

    def test_get_messages_for_character_returns_ic_and_p2c(self, mock_redis_client):
        """Test characters receive IC messages and their P2C directives"""
        # Setup mock Redis to return messages
        ic_message = Message(
            message_id="msg_ic",
            channel=MessageChannel.IC,
            from_agent="dm",
            to_agents=None,
            content="You enter the engine room",
            timestamp=datetime.now(),
            message_type=MessageType.NARRATION,
            phase="dm_narration",
            turn_number=1
        )

        p2c_message = Message(
            message_id="msg_p2c",
            channel=MessageChannel.P2C,
            from_agent="agent_alex_001",
            to_agents=["char_zara_001"],
            content="Check the fuel systems",
            timestamp=datetime.now(),
            message_type=MessageType.DIRECTIVE,
            phase="p2c_directive",
            turn_number=1
        )

        mock_redis_client.lrange.side_effect = [
            [json.dumps(ic_message.model_dump(), default=str)],
            [json.dumps(p2c_message.model_dump(), default=str)]
        ]

        router = MessageRouter(mock_redis_client)
        messages = router.get_messages_for_agent("char_zara_001", "character", limit=50)

        assert len(messages) == 2
        assert any(m.channel == MessageChannel.IC for m in messages)
        assert any(m.channel == MessageChannel.P2C for m in messages)

    def test_get_messages_for_player_returns_ooc_only(self, mock_redis_client):
        """Test players receive only OOC messages, not IC"""
        ooc_message = Message(
            message_id="msg_ooc",
            channel=MessageChannel.OOC,
            from_agent="agent_alex_001",
            to_agents=None,
            content="I think we should be cautious",
            timestamp=datetime.now(),
            message_type=MessageType.DISCUSSION,
            phase="ooc_discussion",
            turn_number=1
        )

        mock_redis_client.lrange.return_value = [
            json.dumps(ooc_message.model_dump(), default=str)
        ]

        router = MessageRouter(mock_redis_client)
        messages = router.get_messages_for_agent("agent_alex_001", "base_persona", limit=50)

        assert len(messages) == 1
        assert messages[0].channel == MessageChannel.OOC

    def test_get_ic_summaries_for_player(self, mock_redis_client):
        """Test players can retrieve IC summaries"""
        from src.models.messages import ICMessageSummary

        summary = ICMessageSummary(
            character_id="char_zara_001",
            action_summary="Zara attempts to repair the fuel cell",
            outcome_summary="The repair is successful",
            turn_number=1,
            timestamp=datetime.now()
        )

        mock_redis_client.lrange.return_value = [
            json.dumps(summary.model_dump(), default=str)
        ]

        router = MessageRouter(mock_redis_client)
        summaries = router.get_ic_summaries_for_player(limit=50)

        assert len(summaries) == 1
        assert summaries[0].character_id == "char_zara_001"
        assert summaries[0].action_summary == "Zara attempts to repair the fuel cell"

    def test_add_message_convenience_method(self, mock_redis_client):
        """Test add_message creates and routes message in one call"""
        router = MessageRouter(mock_redis_client)

        message = router.add_message(
            channel=MessageChannel.IC,
            from_agent="char_zara_001",
            content="I scan the area",
            message_type=MessageType.ACTION,
            phase="character_action",
            turn_number=5
        )

        assert message.message_id.startswith("msg_")
        assert message.channel == MessageChannel.IC
        assert message.content == "I scan the area"

        # Verify routing occurred
        mock_redis_client.rpush.assert_called()

    def test_clear_ic_channel(self, mock_redis_client):
        """Test clearing IC channel deletes messages and summaries"""
        router = MessageRouter(mock_redis_client)

        router.clear_channel(MessageChannel.IC)

        # Verify both IC messages and summaries were deleted
        assert mock_redis_client.delete.call_count >= 2
        call_args = [str(call) for call in mock_redis_client.delete.call_args_list]
        assert any("channel:ic:messages" in arg for arg in call_args)
        assert any("channel:ic:summaries" in arg for arg in call_args)

    def test_clear_ooc_channel(self, mock_redis_client):
        """Test clearing OOC channel"""
        router = MessageRouter(mock_redis_client)

        router.clear_channel(MessageChannel.OOC)

        mock_redis_client.delete.assert_called_with("channel:ooc:messages")

    def test_clear_p2c_channel_pattern_delete(self, mock_redis_client):
        """Test clearing P2C channel deletes all character-specific channels"""
        # Mock sscan_iter to return channel keys
        mock_redis_client.sscan_iter.return_value = iter([
            "channel:p2c:char_001",
            "channel:p2c:char_002"
        ])

        router = MessageRouter(mock_redis_client)
        router.clear_channel(MessageChannel.P2C)

        # Verify sscan_iter was called on active_p2c_channels set
        mock_redis_client.sscan_iter.assert_called_with("active_p2c_channels")
        # Verify delete was called with the channel keys and the set itself
        assert mock_redis_client.delete.call_count == 2
        call_args_list = [str(call) for call in mock_redis_client.delete.call_args_list]
        # First call should delete the channel keys
        assert "channel:p2c:char_001" in call_args_list[0]
        assert "channel:p2c:char_002" in call_args_list[0]
        # Second call should delete the tracking set
        assert "active_p2c_channels" in call_args_list[1]

    def test_message_ttl_applied(self, mock_redis_client):
        """Test TTL is applied to message channels"""
        router = MessageRouter(mock_redis_client)

        message = Message(
            message_id="msg_ttl",
            channel=MessageChannel.IC,
            from_agent="char_zara_001",
            to_agents=None,
            content="Test message",
            timestamp=datetime.now(),
            message_type=MessageType.ACTION,
            phase="character_action",
            turn_number=1
        )

        router.route_message(message)

        # Verify TTL was set (24 hours = 86400 seconds)
        mock_redis_client.expire.assert_called()
        assert any(
            86400 in call.args
            for call in mock_redis_client.expire.call_args_list
        )

    def test_invalid_agent_type_raises_error(self, mock_redis_client):
        """Test invalid agent_type raises ValueError"""
        router = MessageRouter(mock_redis_client)

        with pytest.raises(ValueError, match="Invalid agent_type"):
            router.get_messages_for_agent("agent_001", "invalid_type", limit=50)

    def test_messages_sorted_by_timestamp(self, mock_redis_client):
        """Test messages are sorted by timestamp"""
        now = datetime.now()

        messages = [
            Message(
                message_id=f"msg_{i}",
                channel=MessageChannel.IC,
                from_agent="dm",
                to_agents=None,
                content=f"Message {i}",
                timestamp=datetime(2025, 1, 1, 12, i),
                message_type=MessageType.NARRATION,
                phase="dm_narration",
                turn_number=i
            )
            for i in [3, 1, 2]  # Out of order
        ]

        mock_redis_client.lrange.side_effect = [
            [json.dumps(msg.model_dump(), default=str) for msg in messages],
            []  # Empty P2C messages
        ]

        router = MessageRouter(mock_redis_client)
        result = router.get_messages_for_agent("char_001", "character", limit=50)

        # Should be sorted by timestamp
        assert result[0].turn_number == 1
        assert result[1].turn_number == 2
        assert result[2].turn_number == 3

    def test_summarize_action_truncates_long_content(self, mock_redis_client):
        """Test action summary truncates long content"""
        router = MessageRouter(mock_redis_client)

        long_content = "A" * 150  # 150 characters
        summary = router._summarize_action(long_content)

        assert len(summary) <= 100
        assert summary.endswith("...")

    def test_summarize_action_preserves_short_content(self, mock_redis_client):
        """Test action summary preserves short content"""
        router = MessageRouter(mock_redis_client)

        short_content = "I scan the area"
        summary = router._summarize_action(short_content)

        assert summary == short_content
