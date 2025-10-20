# ABOUTME: Integration tests for OOC monitoring system with real Redis.
# ABOUTME: Tests end-to-end message flow from MessageRouter to OOC monitor display.

import json
from datetime import datetime

import pytest
from redis import Redis

from src.config.settings import get_settings
from src.interface.ooc_monitor import OOCMonitor
from src.models.messages import Message, MessageChannel, MessageType
from src.orchestration.message_router import MessageRouter


@pytest.fixture
def redis_client():
    """Real Redis client for integration testing"""
    settings = get_settings()
    client = Redis.from_url(settings.redis_url, decode_responses=False)

    # Clear OOC channel before test
    client.delete("channel:ooc:messages")

    yield client

    # Cleanup after test
    client.delete("channel:ooc:messages")


@pytest.fixture
def message_router(redis_client):
    """MessageRouter instance with real Redis"""
    return MessageRouter(redis_client)


@pytest.mark.integration
class TestOOCMonitoringEndToEnd:
    """Test complete OOC monitoring workflow with real Redis"""

    def test_monitor_detects_new_messages(self, redis_client, message_router):
        """Test that monitor detects messages added via MessageRouter"""
        # Create OOC monitor
        monitor = OOCMonitor(
            output_mode="console",
            redis_url=get_settings().redis_url,
            poll_interval=0.1
        )

        # Add OOC message via MessageRouter
        message = message_router.add_message(
            channel=MessageChannel.OOC,
            from_agent="agent_alex_001",
            content="We should investigate the fuel readings",
            message_type=MessageType.DISCUSSION,
            phase="strategic_intent",
            turn_number=1,
            session_number=1
        )

        # Fetch messages via monitor
        messages = monitor.fetch_ooc_messages()

        # Verify message was detected
        assert len(messages) == 1
        assert messages[0].message_id == message.message_id
        assert messages[0].content == "We should investigate the fuel readings"
        assert messages[0].from_agent == "agent_alex_001"

    def test_monitor_handles_multiple_messages(self, redis_client, message_router):
        """Test monitor handles multiple OOC messages correctly"""
        monitor = OOCMonitor(
            output_mode="console",
            redis_url=get_settings().redis_url
        )

        # Add multiple messages
        message_router.add_message(
            channel=MessageChannel.OOC,
            from_agent="agent_alex_001",
            content="First message",
            message_type=MessageType.DISCUSSION,
            phase="strategic_intent",
            turn_number=1,
            session_number=1
        )

        message_router.add_message(
            channel=MessageChannel.OOC,
            from_agent="agent_jordan_002",
            content="Second message",
            message_type=MessageType.DISCUSSION,
            phase="strategic_intent",
            turn_number=1,
            session_number=1
        )

        # Fetch messages
        messages = monitor.fetch_ooc_messages()

        assert len(messages) == 2
        assert messages[0].content == "First message"
        assert messages[1].content == "Second message"

    def test_monitor_duplicate_filtering_with_real_data(self, redis_client, message_router):
        """Test duplicate filtering works with real Redis data"""
        monitor = OOCMonitor(
            output_mode="console",
            redis_url=get_settings().redis_url
        )

        # Add message
        message_router.add_message(
            channel=MessageChannel.OOC,
            from_agent="agent_alex_001",
            content="Test message",
            message_type=MessageType.DISCUSSION,
            phase="strategic_intent",
            turn_number=1,
            session_number=1
        )

        # First fetch - should be new
        messages = monitor.fetch_ooc_messages()
        assert len(messages) == 1
        assert monitor.is_new_message(messages[0]) is True

        # Second fetch - same message should be duplicate
        messages = monitor.fetch_ooc_messages()
        assert len(messages) == 1
        assert monitor.is_new_message(messages[0]) is False

    def test_monitor_file_output_creates_jsonl(self, redis_client, message_router, tmp_path):
        """Test file output mode creates valid JSONL"""
        log_path = tmp_path / "test_ooc.jsonl"

        monitor = OOCMonitor(
            output_mode="file",
            log_path=str(log_path),
            redis_url=get_settings().redis_url
        )

        # Add message
        message_router.add_message(
            channel=MessageChannel.OOC,
            from_agent="agent_alex_001",
            content="Test file output",
            message_type=MessageType.DISCUSSION,
            phase="strategic_intent",
            turn_number=1,
            session_number=1
        )

        # Fetch and write
        messages = monitor.fetch_ooc_messages()
        for msg in messages:
            if monitor.is_new_message(msg):
                monitor.write_message(msg, agent_name="Alex")

        # Verify file was created
        assert log_path.exists()

        # Verify content is valid JSON
        with open(log_path) as f:
            line = f.readline().strip()
            data = json.loads(line)

            assert data["agent_id"] == "agent_alex_001"
            assert data["agent_name"] == "Alex"
            assert data["content"] == "Test file output"
            assert data["turn_number"] == 1
            assert data["session_number"] == 1

    def test_monitor_filters_by_turn_number(self, redis_client, message_router):
        """Test that messages can be filtered by turn number"""
        monitor = OOCMonitor(
            output_mode="console",
            redis_url=get_settings().redis_url
        )

        # Add messages from different turns
        message_router.add_message(
            channel=MessageChannel.OOC,
            from_agent="agent_alex_001",
            content="Turn 1 message",
            message_type=MessageType.DISCUSSION,
            phase="strategic_intent",
            turn_number=1,
            session_number=1
        )

        message_router.add_message(
            channel=MessageChannel.OOC,
            from_agent="agent_alex_001",
            content="Turn 2 message",
            message_type=MessageType.DISCUSSION,
            phase="strategic_intent",
            turn_number=2,
            session_number=1
        )

        # Fetch all messages
        all_messages = monitor.fetch_ooc_messages()
        assert len(all_messages) == 2

        # Filter by turn
        turn_1_messages = [m for m in all_messages if m.turn_number == 1]
        turn_2_messages = [m for m in all_messages if m.turn_number == 2]

        assert len(turn_1_messages) == 1
        assert turn_1_messages[0].content == "Turn 1 message"

        assert len(turn_2_messages) == 1
        assert turn_2_messages[0].content == "Turn 2 message"

    def test_message_router_to_monitor_flow(self, redis_client):
        """Test complete flow from MessageRouter.add_message to OOCMonitor.fetch"""
        # Create independent instances
        router = MessageRouter(redis_client)
        monitor = OOCMonitor(
            output_mode="console",
            redis_url=get_settings().redis_url
        )

        # Add message via router
        msg = Message(
            message_id="msg_test_001",
            channel=MessageChannel.OOC,
            from_agent="agent_test",
            content="Integration test message",
            timestamp=datetime.now(),
            message_type=MessageType.DISCUSSION,
            phase="strategic_intent",
            turn_number=5,
            session_number=1
        )

        router.route_message(msg)

        # Fetch via monitor
        messages = monitor.fetch_ooc_messages()

        # Verify message made it through
        assert len(messages) >= 1
        found = any(m.message_id == "msg_test_001" for m in messages)
        assert found, "Message not found after routing"

        matching_msg = next(m for m in messages if m.message_id == "msg_test_001")
        assert matching_msg.content == "Integration test message"
        assert matching_msg.turn_number == 5


@pytest.mark.integration
class TestOOCMonitorPerformance:
    """Test OOC monitor performance with larger datasets"""

    def test_monitor_handles_large_message_volume(self, redis_client, message_router):
        """Test monitor can handle large number of messages"""
        monitor = OOCMonitor(
            output_mode="console",
            redis_url=get_settings().redis_url
        )

        # Add 100 messages
        for i in range(100):
            message_router.add_message(
                channel=MessageChannel.OOC,
                from_agent=f"agent_{i % 5:03d}",
                content=f"Message {i}",
                message_type=MessageType.DISCUSSION,
                phase="strategic_intent",
                turn_number=i // 10,
                session_number=1
            )

        # Fetch all messages
        messages = monitor.fetch_ooc_messages()

        assert len(messages) == 100

        # Verify all messages are parseable
        for msg in messages:
            assert msg.content.startswith("Message")
            assert msg.turn_number >= 0
