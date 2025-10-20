# ABOUTME: Unit tests for OOC (Out-of-Character) monitoring system.
# ABOUTME: Tests message formatting, duplicate filtering, and Redis interaction for OOC monitor.

import json
from datetime import datetime
from unittest.mock import MagicMock, patch

from src.models.messages import Message, MessageChannel, MessageType

# The OOC monitor module will be imported after implementation
# For now, we'll use mock imports that will be replaced


class TestOOCMonitorFormatting:
    """Test message formatting for console and JSONL output"""

    def test_format_message_for_console_basic(self):
        """Test formatting a basic OOC message for console display"""
        # Import will work after implementation
        from src.interface.ooc_monitor import OOCMonitor

        monitor = OOCMonitor(output_mode="console")

        message = Message(
            message_id="msg_001",
            channel=MessageChannel.OOC,
            from_agent="agent_alex_001",
            content="I think we should check the fuel readings",
            timestamp=datetime(2025, 10, 19, 14, 32, 15),
            message_type=MessageType.DISCUSSION,
            phase="strategic_intent",
            turn_number=3,
            session_number=1
        )

        formatted = monitor.format_message_console(message, agent_name="Alex")

        assert "[2025-10-19 14:32:15]" in formatted
        assert "Alex (Player):" in formatted
        assert "I think we should check the fuel readings" in formatted

    def test_format_message_for_console_no_agent_name(self):
        """Test console formatting falls back to agent_id when name unavailable"""
        from src.interface.ooc_monitor import OOCMonitor

        monitor = OOCMonitor(output_mode="console")

        message = Message(
            message_id="msg_002",
            channel=MessageChannel.OOC,
            from_agent="agent_jordan_002",
            content="Agreed, let's run diagnostics",
            timestamp=datetime(2025, 10, 19, 14, 32, 18),
            message_type=MessageType.DISCUSSION,
            phase="strategic_intent",
            turn_number=3,
            session_number=1
        )

        formatted = monitor.format_message_console(message)

        assert "agent_jordan_002 (Player):" in formatted

    def test_format_message_for_jsonl(self):
        """Test formatting message as JSONL (JSON Lines)"""
        from src.interface.ooc_monitor import OOCMonitor

        monitor = OOCMonitor(output_mode="file", log_path="/tmp/test.jsonl")

        message = Message(
            message_id="msg_003",
            channel=MessageChannel.OOC,
            from_agent="agent_alex_001",
            content="Test message content",
            timestamp=datetime(2025, 10, 19, 14, 32, 15),
            message_type=MessageType.DISCUSSION,
            phase="strategic_intent",
            turn_number=3,
            session_number=1
        )

        jsonl_line = monitor.format_message_jsonl(message, agent_name="Alex")

        # Parse the JSON to verify structure
        parsed = json.loads(jsonl_line)

        assert parsed["timestamp"] == "2025-10-19T14:32:15"
        assert parsed["agent_id"] == "agent_alex_001"
        assert parsed["agent_name"] == "Alex"
        assert parsed["content"] == "Test message content"
        assert parsed["turn_number"] == 3
        assert parsed["session_number"] == 1

    def test_format_message_jsonl_no_agent_name(self):
        """Test JSONL formatting without agent name"""
        from src.interface.ooc_monitor import OOCMonitor

        monitor = OOCMonitor(output_mode="file", log_path="/tmp/test2.jsonl")

        message = Message(
            message_id="msg_004",
            channel=MessageChannel.OOC,
            from_agent="agent_test_001",
            content="Another message",
            timestamp=datetime(2025, 10, 19, 14, 35, 00),
            message_type=MessageType.DISCUSSION,
            phase="ooc_discussion",
            turn_number=5,
            session_number=1
        )

        jsonl_line = monitor.format_message_jsonl(message)
        parsed = json.loads(jsonl_line)

        # Should fall back to agent_id
        assert parsed["agent_name"] == "agent_test_001"


class TestOOCMonitorDuplicateFiltering:
    """Test duplicate message detection and filtering"""

    def test_is_new_message_first_message(self):
        """Test that first message is always considered new"""
        from src.interface.ooc_monitor import OOCMonitor

        monitor = OOCMonitor(output_mode="console")

        message = Message(
            message_id="msg_001",
            channel=MessageChannel.OOC,
            from_agent="agent_alex_001",
            content="First message",
            timestamp=datetime(2025, 10, 19, 14, 30, 00),
            message_type=MessageType.DISCUSSION,
            phase="strategic_intent",
            turn_number=1,
            session_number=1
        )

        assert monitor.is_new_message(message) is True

    def test_is_new_message_duplicate_detection(self):
        """Test that duplicate messages are detected"""
        from src.interface.ooc_monitor import OOCMonitor

        monitor = OOCMonitor(output_mode="console")

        message1 = Message(
            message_id="msg_001",
            channel=MessageChannel.OOC,
            from_agent="agent_alex_001",
            content="Message 1",
            timestamp=datetime(2025, 10, 19, 14, 30, 00),
            message_type=MessageType.DISCUSSION,
            phase="strategic_intent",
            turn_number=1,
            session_number=1
        )

        message2 = Message(
            message_id="msg_001",  # Same ID
            channel=MessageChannel.OOC,
            from_agent="agent_alex_001",
            content="Message 1",
            timestamp=datetime(2025, 10, 19, 14, 30, 00),
            message_type=MessageType.DISCUSSION,
            phase="strategic_intent",
            turn_number=1,
            session_number=1
        )

        # First time - new
        assert monitor.is_new_message(message1) is True

        # Second time with same message_id - duplicate
        assert monitor.is_new_message(message2) is False

    def test_is_new_message_newer_messages(self):
        """Test that newer messages are detected as new"""
        from src.interface.ooc_monitor import OOCMonitor

        monitor = OOCMonitor(output_mode="console")

        message1 = Message(
            message_id="msg_001",
            channel=MessageChannel.OOC,
            from_agent="agent_alex_001",
            content="First",
            timestamp=datetime(2025, 10, 19, 14, 30, 00),
            message_type=MessageType.DISCUSSION,
            phase="strategic_intent",
            turn_number=1,
            session_number=1
        )

        message2 = Message(
            message_id="msg_002",
            channel=MessageChannel.OOC,
            from_agent="agent_jordan_002",
            content="Second",
            timestamp=datetime(2025, 10, 19, 14, 30, 15),
            message_type=MessageType.DISCUSSION,
            phase="strategic_intent",
            turn_number=1,
            session_number=1
        )

        assert monitor.is_new_message(message1) is True
        assert monitor.is_new_message(message2) is True


class TestOOCMonitorRedisInteraction:
    """Test Redis polling and message retrieval"""

    @patch('src.interface.ooc_monitor.Redis')
    def test_fetch_messages_from_redis(self, mock_redis_class):
        """Test fetching messages from Redis channel:ooc:messages"""
        from src.interface.ooc_monitor import OOCMonitor

        # Mock Redis client
        mock_redis = MagicMock()
        mock_redis_class.from_url.return_value = mock_redis

        # Mock Redis lrange to return OOC messages
        message_data = {
            "message_id": "msg_001",
            "channel": "out_of_character",
            "from_agent": "agent_alex_001",
            "to_agents": None,
            "content": "Should we investigate?",
            "timestamp": "2025-10-19T14:30:00",
            "message_type": "discussion",
            "phase": "strategic_intent",
            "turn_number": 1,
            "session_number": 1
        }

        mock_redis.lrange.return_value = [
            json.dumps(message_data).encode('utf-8')
        ]

        monitor = OOCMonitor(output_mode="console", redis_url="redis://localhost:6379")

        messages = monitor.fetch_ooc_messages()

        # Verify Redis was called correctly
        mock_redis.lrange.assert_called_once_with("channel:ooc:messages", 0, -1)

        # Verify message was parsed
        assert len(messages) == 1
        assert messages[0].message_id == "msg_001"
        assert messages[0].content == "Should we investigate?"

    @patch('src.interface.ooc_monitor.Redis')
    def test_fetch_messages_empty_channel(self, mock_redis_class):
        """Test fetching from empty OOC channel"""
        from src.interface.ooc_monitor import OOCMonitor

        mock_redis = MagicMock()
        mock_redis_class.from_url.return_value = mock_redis
        mock_redis.lrange.return_value = []

        monitor = OOCMonitor(output_mode="console", redis_url="redis://localhost:6379")
        messages = monitor.fetch_ooc_messages()

        assert len(messages) == 0

    @patch('src.interface.ooc_monitor.Redis')
    def test_redis_connection_error_handling(self, mock_redis_class):
        """Test graceful handling of Redis connection errors"""
        from redis.exceptions import ConnectionError

        from src.interface.ooc_monitor import OOCMonitor

        mock_redis = MagicMock()
        mock_redis_class.from_url.return_value = mock_redis
        mock_redis.lrange.side_effect = ConnectionError("Connection refused")

        monitor = OOCMonitor(output_mode="console", redis_url="redis://localhost:6379")

        # Should handle error gracefully and return empty list
        messages = monitor.fetch_ooc_messages()
        assert messages == []


class TestOOCMonitorCLI:
    """Test CLI argument parsing and mode selection"""

    @patch('sys.argv', ['ooc_monitor.py', '--output', 'console'])
    def test_cli_args_console_mode(self):
        """Test CLI argument parsing for console mode"""
        from src.interface.ooc_monitor import parse_args

        args = parse_args()
        assert args.output == "console"
        assert args.poll_interval == 0.5  # Default

    @patch('sys.argv', ['ooc_monitor.py', '--output', 'file', '--log-path', 'logs/ooc.jsonl'])
    def test_cli_args_file_mode(self):
        """Test CLI argument parsing for file mode"""
        from src.interface.ooc_monitor import parse_args

        args = parse_args()
        assert args.output == "file"
        assert args.log_path == "logs/ooc.jsonl"

    @patch('sys.argv', ['ooc_monitor.py', '--poll-interval', '1.0'])
    def test_cli_args_poll_interval(self):
        """Test custom poll interval"""
        from src.interface.ooc_monitor import parse_args

        args = parse_args()
        assert args.poll_interval == 1.0


class TestOOCMonitorFileOutput:
    """Test file output mode"""

    @patch('builtins.open', create=True)
    def test_write_to_file(self, mock_open):
        """Test writing JSONL to file"""
        from src.interface.ooc_monitor import OOCMonitor

        mock_file = MagicMock()
        mock_open.return_value = mock_file

        monitor = OOCMonitor(output_mode="file", log_path="/tmp/test_ooc.jsonl")

        message = Message(
            message_id="msg_001",
            channel=MessageChannel.OOC,
            from_agent="agent_alex_001",
            content="Test output",
            timestamp=datetime(2025, 10, 19, 14, 30, 00),
            message_type=MessageType.DISCUSSION,
            phase="strategic_intent",
            turn_number=1,
            session_number=1
        )

        monitor.write_message(message, agent_name="Alex")

        # Verify file was opened once in append mode with line buffering (during __init__)
        mock_open.assert_called_once_with("/tmp/test_ooc.jsonl", "a", buffering=1)

        # Verify JSONL was written with newline
        assert mock_file.write.called
        written_content = mock_file.write.call_args[0][0]
        assert written_content.endswith("\n")
        assert "Alex" in written_content
