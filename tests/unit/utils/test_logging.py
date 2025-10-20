# ABOUTME: Unit tests for structured logging utilities
# ABOUTME: Validates loguru configuration, convenience functions, and context attachment

import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest
from loguru import logger

from src.utils.logging import (
    DEFAULT_FORMAT,
    get_logger,
    log_memory_operation,
    log_phase_transition,
    log_turn_event,
    setup_logging,
)


@pytest.fixture(autouse=True)
def reset_logger():
    """Reset logger state before each test"""
    # Remove all handlers before test
    logger.remove()
    yield
    # Clean up after test
    logger.remove()


@pytest.fixture
def temp_log_dir():
    """Create a temporary directory for log files"""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


class TestSetupLogging:
    """Test suite for setup_logging function"""

    def test_valid_log_levels(self):
        """Test that all valid log levels are accepted"""
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]

        for level in valid_levels:
            logger.remove()  # Clean slate
            # Should not raise error
            setup_logging(log_level=level, console_output=True, file_output=False)

    def test_log_level_case_insensitive(self):
        """Test that log level is case-insensitive"""
        # These should all work
        for level in ["debug", "Debug", "DEBUG", "DeBuG"]:
            logger.remove()
            setup_logging(log_level=level, console_output=True, file_output=False)

    def test_invalid_log_level_raises_error(self):
        """Test that invalid log level raises ValueError"""
        with pytest.raises(ValueError, match="Invalid log level"):
            setup_logging(log_level="INVALID")

        with pytest.raises(ValueError, match="Invalid log level"):
            setup_logging(log_level="TRACE")  # Valid in loguru but not in our API

        with pytest.raises(ValueError, match="Invalid log level"):
            setup_logging(log_level="")

    def test_console_output_enabled(self):
        """Test that console output can be enabled"""
        with patch.object(logger, 'add') as mock_add:
            setup_logging(
                log_level="INFO",
                console_output=True,
                file_output=False
            )

            # Verify logger.add was called with sys.stderr
            assert mock_add.called
            call_args = mock_add.call_args[0]
            assert call_args[0] == sys.stderr

    def test_console_output_disabled(self):
        """Test that console output can be disabled"""
        with patch.object(logger, 'add') as mock_add:
            setup_logging(
                log_level="INFO",
                console_output=False,
                file_output=False
            )

            # Verify logger.add was NOT called (no handlers added)
            assert not mock_add.called

    def test_file_output_enabled(self, temp_log_dir):
        """Test that file output can be enabled"""
        setup_logging(
            log_level="INFO",
            log_dir=temp_log_dir,
            console_output=False,
            file_output=True
        )

        # Verify log directory was created
        assert temp_log_dir.exists()

        # Log a message and verify file is created
        logger.info("test message")

        # Check that at least one log file exists
        log_files = list(temp_log_dir.glob("*.log"))
        assert len(log_files) > 0

    def test_file_output_disabled(self, temp_log_dir):
        """Test that file output can be disabled"""
        setup_logging(
            log_level="INFO",
            log_dir=temp_log_dir,
            console_output=False,
            file_output=False
        )

        # Log a message
        logger.info("test message")

        # Verify no log files were created
        log_files = list(temp_log_dir.glob("*.log"))
        assert len(log_files) == 0

    def test_log_directory_creation(self, temp_log_dir):
        """Test that log directory is created if it doesn't exist"""
        nested_dir = temp_log_dir / "nested" / "logs"
        assert not nested_dir.exists()

        setup_logging(
            log_level="INFO",
            log_dir=nested_dir,
            console_output=False,
            file_output=True
        )

        # Verify nested directory was created
        assert nested_dir.exists()

    def test_default_log_directory(self):
        """Test that default log directory is 'logs' in current directory"""
        with patch('pathlib.Path.mkdir') as mock_mkdir, \
             patch.object(logger, 'add'):
            setup_logging(
                log_level="INFO",
                log_dir=None,  # Use default
                console_output=False,
                file_output=True
            )

            # Verify mkdir was called (directory creation)
            assert mock_mkdir.called

    def test_custom_format_string(self):
        """Test that custom format string is accepted"""
        custom_format = "{time} | {level} | {message}"

        with patch.object(logger, 'add') as mock_add:
            setup_logging(
                log_level="INFO",
                console_output=True,
                file_output=False,
                format_string=custom_format
            )

            # Verify custom format was used
            call_kwargs = mock_add.call_args[1]
            assert call_kwargs['format'] == custom_format

    def test_default_format_string(self):
        """Test that default format string is used when none provided"""
        with patch.object(logger, 'add') as mock_add:
            setup_logging(
                log_level="INFO",
                console_output=True,
                file_output=False,
                format_string=None
            )

            # Verify default format was used
            call_kwargs = mock_add.call_args[1]
            assert call_kwargs['format'] == DEFAULT_FORMAT

    def test_idempotent_calls(self):
        """Test that setup_logging can be called multiple times safely"""
        # Should not raise error
        setup_logging(log_level="INFO", console_output=True, file_output=False)
        setup_logging(log_level="DEBUG", console_output=True, file_output=False)
        setup_logging(log_level="WARNING", console_output=True, file_output=False)

        # Logger should still work
        logger.info("test message")

    def test_rotation_parameter(self, temp_log_dir):
        """Test that rotation parameter is passed to file handler"""
        with patch.object(logger, 'add') as mock_add:
            setup_logging(
                log_level="INFO",
                log_dir=temp_log_dir,
                console_output=False,
                file_output=True,
                rotation="50 MB"
            )

            # Find the call that added file handler (second call)
            file_handler_call = None
            for call_obj in mock_add.call_args_list:
                if call_obj[1].get('rotation'):
                    file_handler_call = call_obj
                    break

            assert file_handler_call is not None
            assert file_handler_call[1]['rotation'] == "50 MB"

    def test_retention_parameter(self, temp_log_dir):
        """Test that retention parameter is passed to file handler"""
        with patch.object(logger, 'add') as mock_add:
            setup_logging(
                log_level="INFO",
                log_dir=temp_log_dir,
                console_output=False,
                file_output=True,
                retention="7 days"
            )

            # Find the call that added file handler
            file_handler_call = None
            for call_obj in mock_add.call_args_list:
                if call_obj[1].get('retention'):
                    file_handler_call = call_obj
                    break

            assert file_handler_call is not None
            assert file_handler_call[1]['retention'] == "7 days"

    def test_compression_parameter(self, temp_log_dir):
        """Test that compression parameter is passed to file handler"""
        with patch.object(logger, 'add') as mock_add:
            setup_logging(
                log_level="INFO",
                log_dir=temp_log_dir,
                console_output=False,
                file_output=True,
                compression="gz"
            )

            # Find the call that added file handler
            file_handler_call = None
            for call_obj in mock_add.call_args_list:
                if call_obj[1].get('compression'):
                    file_handler_call = call_obj
                    break

            assert file_handler_call is not None
            assert file_handler_call[1]['compression'] == "gz"

    def test_both_console_and_file_output(self, temp_log_dir):
        """Test that both console and file output can be enabled simultaneously"""
        with patch.object(logger, 'add') as mock_add:
            setup_logging(
                log_level="INFO",
                log_dir=temp_log_dir,
                console_output=True,
                file_output=True
            )

            # Verify logger.add was called twice (console + file)
            # Third call is for the "Logging configured" message itself
            assert mock_add.call_count >= 2

    def test_log_level_filtering(self, temp_log_dir, capsys):
        """Test that log level filtering works correctly"""
        # Setup with file output to a temp directory to capture logs
        setup_logging(log_level="WARNING", console_output=True, file_output=True, log_dir=temp_log_dir)

        # Log messages at different levels
        logger.debug("debug message")
        logger.info("info message")
        logger.warning("warning message")
        logger.error("error message")

        # Force logger to complete any pending writes
        logger.complete()

        # Read from log file to verify filtering
        log_files = list(temp_log_dir.glob("*.log"))
        assert len(log_files) > 0

        log_content = log_files[0].read_text()

        # Only WARNING and ERROR should be logged
        assert "debug message" not in log_content
        assert "info message" not in log_content
        assert "warning message" in log_content
        assert "error message" in log_content


class TestGetLogger:
    """Test suite for get_logger function"""

    def test_returns_logger_instance(self):
        """Test that get_logger returns logger instance"""
        result = get_logger()
        assert result is not None

    def test_returns_loguru_logger(self):
        """Test that get_logger returns loguru logger"""
        result = get_logger()
        # Check it has loguru logger methods
        assert hasattr(result, 'info')
        assert hasattr(result, 'debug')
        assert hasattr(result, 'warning')
        assert hasattr(result, 'error')
        assert hasattr(result, 'bind')

    def test_logger_info_method_works(self):
        """Test that logger.info() method works"""
        setup_logging(log_level="INFO", console_output=False, file_output=False)
        test_logger = get_logger()

        # Should not raise error
        test_logger.info("test message")

    def test_logger_debug_method_works(self):
        """Test that logger.debug() method works"""
        setup_logging(log_level="DEBUG", console_output=False, file_output=False)
        test_logger = get_logger()

        # Should not raise error
        test_logger.debug("test message")

    def test_logger_warning_method_works(self):
        """Test that logger.warning() method works"""
        setup_logging(log_level="INFO", console_output=False, file_output=False)
        test_logger = get_logger()

        # Should not raise error
        test_logger.warning("test message")

    def test_logger_error_method_works(self):
        """Test that logger.error() method works"""
        setup_logging(log_level="INFO", console_output=False, file_output=False)
        test_logger = get_logger()

        # Should not raise error
        test_logger.error("test message")

    def test_logger_bind_method_works(self):
        """Test that logger.bind() method works for context"""
        setup_logging(log_level="INFO", console_output=False, file_output=False)
        test_logger = get_logger()

        # Should not raise error
        bound_logger = test_logger.bind(phase="test", session=1)
        bound_logger.info("test message")


class TestLogTurnEvent:
    """Test suite for log_turn_event convenience function"""

    def test_attaches_phase_context(self):
        """Test that phase context is attached"""
        setup_logging(log_level="INFO", console_output=False, file_output=False)

        with patch.object(logger, 'bind') as mock_bind:
            mock_bind.return_value = logger  # Return logger for chaining

            log_turn_event(
                message="test message",
                phase="DM_NARRATION",
                session_number=5,
                turn_number=23
            )

            # Verify bind was called with phase
            call_kwargs = mock_bind.call_args[1]
            assert call_kwargs['phase'] == "DM_NARRATION"

    def test_attaches_session_context(self):
        """Test that session context is attached"""
        setup_logging(log_level="INFO", console_output=False, file_output=False)

        with patch.object(logger, 'bind') as mock_bind:
            mock_bind.return_value = logger

            log_turn_event(
                message="test message",
                phase="CHARACTER_ACTION",
                session_number=42,
                turn_number=10
            )

            call_kwargs = mock_bind.call_args[1]
            assert call_kwargs['session'] == 42

    def test_attaches_turn_context(self):
        """Test that turn context is attached"""
        setup_logging(log_level="INFO", console_output=False, file_output=False)

        with patch.object(logger, 'bind') as mock_bind:
            mock_bind.return_value = logger

            log_turn_event(
                message="test message",
                phase="STRATEGIC_INTENT",
                session_number=5,
                turn_number=99
            )

            call_kwargs = mock_bind.call_args[1]
            assert call_kwargs['turn'] == 99

    def test_attaches_agent_id_when_provided(self):
        """Test that agent_id is attached when provided"""
        setup_logging(log_level="INFO", console_output=False, file_output=False)

        with patch.object(logger, 'bind') as mock_bind:
            mock_bind.return_value = logger

            log_turn_event(
                message="test message",
                phase="CHARACTER_ACTION",
                session_number=5,
                turn_number=23,
                agent_id="agent_alex"
            )

            call_kwargs = mock_bind.call_args[1]
            assert call_kwargs['agent_id'] == "agent_alex"

    def test_omits_agent_id_when_not_provided(self):
        """Test that agent_id is omitted when not provided"""
        setup_logging(log_level="INFO", console_output=False, file_output=False)

        with patch.object(logger, 'bind') as mock_bind:
            mock_bind.return_value = logger

            log_turn_event(
                message="test message",
                phase="DM_NARRATION",
                session_number=5,
                turn_number=23
            )

            call_kwargs = mock_bind.call_args[1]
            assert 'agent_id' not in call_kwargs

    def test_accepts_extra_context_kwargs(self):
        """Test that extra keyword arguments are included in context"""
        setup_logging(log_level="INFO", console_output=False, file_output=False)

        with patch.object(logger, 'bind') as mock_bind:
            mock_bind.return_value = logger

            log_turn_event(
                message="test message",
                phase="CHARACTER_ACTION",
                session_number=5,
                turn_number=23,
                action="repair ship",
                target="engine"
            )

            call_kwargs = mock_bind.call_args[1]
            assert call_kwargs['action'] == "repair ship"
            assert call_kwargs['target'] == "engine"

    def test_logs_at_info_level_by_default(self, temp_log_dir):
        """Test that default log level is INFO"""
        setup_logging(log_level="INFO", console_output=False, file_output=True, log_dir=temp_log_dir)

        log_turn_event(
            message="test message",
            phase="DM_NARRATION",
            session_number=5,
            turn_number=23
        )

        # Verify message was logged
        log_files = list(temp_log_dir.glob("*.log"))
        assert len(log_files) > 0
        log_content = log_files[0].read_text()
        assert "test message" in log_content

    def test_logs_at_debug_level(self, temp_log_dir):
        """Test that DEBUG level can be specified"""
        setup_logging(log_level="DEBUG", console_output=False, file_output=True, log_dir=temp_log_dir)

        log_turn_event(
            message="debug test message",
            phase="DM_NARRATION",
            session_number=5,
            turn_number=23,
            level="DEBUG"
        )

        # Verify debug message was logged
        log_files = list(temp_log_dir.glob("*.log"))
        assert len(log_files) > 0
        log_content = log_files[0].read_text()
        assert "debug test message" in log_content
        assert "DEBUG" in log_content

    def test_logs_at_warning_level(self, temp_log_dir):
        """Test that WARNING level can be specified"""
        setup_logging(log_level="INFO", console_output=False, file_output=True, log_dir=temp_log_dir)

        log_turn_event(
            message="warning test message",
            phase="CHARACTER_ACTION",
            session_number=5,
            turn_number=23,
            level="WARNING"
        )

        # Verify warning message was logged
        log_files = list(temp_log_dir.glob("*.log"))
        assert len(log_files) > 0
        log_content = log_files[0].read_text()
        assert "warning test message" in log_content
        assert "WARNING" in log_content

    def test_logs_at_error_level(self, temp_log_dir):
        """Test that ERROR level can be specified"""
        setup_logging(log_level="INFO", console_output=False, file_output=True, log_dir=temp_log_dir)

        log_turn_event(
            message="error test message",
            phase="MEMORY_RETRIEVAL",
            session_number=5,
            turn_number=23,
            level="ERROR"
        )

        # Verify error message was logged
        log_files = list(temp_log_dir.glob("*.log"))
        assert len(log_files) > 0
        log_content = log_files[0].read_text()
        assert "error test message" in log_content
        assert "ERROR" in log_content

    def test_level_parameter_case_insensitive(self):
        """Test that level parameter is case-insensitive"""
        setup_logging(log_level="INFO", console_output=False, file_output=False)

        # Should not raise error
        log_turn_event(
            message="test",
            phase="DM_NARRATION",
            session_number=1,
            turn_number=1,
            level="info"
        )

        log_turn_event(
            message="test",
            phase="DM_NARRATION",
            session_number=1,
            turn_number=1,
            level="Info"
        )


class TestLogPhaseTransition:
    """Test suite for log_phase_transition convenience function"""

    def test_attaches_from_phase_context(self):
        """Test that from_phase context is attached"""
        setup_logging(log_level="INFO", console_output=False, file_output=False)

        with patch.object(logger, 'bind') as mock_bind:
            mock_bind.return_value = logger

            log_phase_transition(
                from_phase="DM_NARRATION",
                to_phase="MEMORY_RETRIEVAL",
                session_number=5,
                turn_number=23
            )

            call_kwargs = mock_bind.call_args[1]
            assert call_kwargs['from_phase'] == "DM_NARRATION"

    def test_attaches_to_phase_context(self):
        """Test that to_phase context is attached"""
        setup_logging(log_level="INFO", console_output=False, file_output=False)

        with patch.object(logger, 'bind') as mock_bind:
            mock_bind.return_value = logger

            log_phase_transition(
                from_phase="MEMORY_RETRIEVAL",
                to_phase="STRATEGIC_INTENT",
                session_number=5,
                turn_number=23
            )

            call_kwargs = mock_bind.call_args[1]
            assert call_kwargs['to_phase'] == "STRATEGIC_INTENT"

    def test_attaches_session_and_turn_context(self):
        """Test that session and turn context are attached"""
        setup_logging(log_level="INFO", console_output=False, file_output=False)

        with patch.object(logger, 'bind') as mock_bind:
            mock_bind.return_value = logger

            log_phase_transition(
                from_phase="STRATEGIC_INTENT",
                to_phase="CHARACTER_ACTION",
                session_number=7,
                turn_number=15
            )

            call_kwargs = mock_bind.call_args[1]
            assert call_kwargs['session'] == 7
            assert call_kwargs['turn'] == 15

    def test_attaches_duration_when_provided(self):
        """Test that duration_ms is attached when provided"""
        setup_logging(log_level="INFO", console_output=False, file_output=False)

        with patch.object(logger, 'bind') as mock_bind:
            mock_bind.return_value = logger

            log_phase_transition(
                from_phase="DM_NARRATION",
                to_phase="MEMORY_RETRIEVAL",
                session_number=5,
                turn_number=23,
                duration_ms=150.5
            )

            call_kwargs = mock_bind.call_args[1]
            assert call_kwargs['duration_ms'] == 150.5

    def test_omits_duration_when_not_provided(self):
        """Test that duration_ms is omitted when not provided"""
        setup_logging(log_level="INFO", console_output=False, file_output=False)

        with patch.object(logger, 'bind') as mock_bind:
            mock_bind.return_value = logger

            log_phase_transition(
                from_phase="MEMORY_RETRIEVAL",
                to_phase="STRATEGIC_INTENT",
                session_number=5,
                turn_number=23
            )

            call_kwargs = mock_bind.call_args[1]
            assert 'duration_ms' not in call_kwargs

    def test_logs_transition_message(self, temp_log_dir):
        """Test that transition message is logged correctly"""
        setup_logging(log_level="INFO", console_output=False, file_output=True, log_dir=temp_log_dir)

        log_phase_transition(
            from_phase="CHARACTER_ACTION",
            to_phase="DM_RESOLUTION",
            session_number=5,
            turn_number=23
        )

        # Verify transition message was logged
        log_files = list(temp_log_dir.glob("*.log"))
        assert len(log_files) > 0
        log_content = log_files[0].read_text()
        assert "CHARACTER_ACTION" in log_content
        assert "DM_RESOLUTION" in log_content
        assert "Phase transition" in log_content


class TestLogMemoryOperation:
    """Test suite for log_memory_operation convenience function"""

    def test_attaches_operation_context(self):
        """Test that operation context is attached"""
        setup_logging(log_level="INFO", console_output=False, file_output=False)

        with patch.object(logger, 'bind') as mock_bind:
            mock_bind.return_value = logger

            log_memory_operation(
                operation="query",
                agent_id="agent_alex",
                session_number=5
            )

            call_kwargs = mock_bind.call_args[1]
            assert call_kwargs['operation'] == "query"

    def test_attaches_agent_id_context(self):
        """Test that agent_id context is attached"""
        setup_logging(log_level="INFO", console_output=False, file_output=False)

        with patch.object(logger, 'bind') as mock_bind:
            mock_bind.return_value = logger

            log_memory_operation(
                operation="store",
                agent_id="agent_jordan",
                session_number=5
            )

            call_kwargs = mock_bind.call_args[1]
            assert call_kwargs['agent_id'] == "agent_jordan"

    def test_attaches_session_context(self):
        """Test that session context is attached"""
        setup_logging(log_level="INFO", console_output=False, file_output=False)

        with patch.object(logger, 'bind') as mock_bind:
            mock_bind.return_value = logger

            log_memory_operation(
                operation="corrupt",
                agent_id="agent_alex",
                session_number=42
            )

            call_kwargs = mock_bind.call_args[1]
            assert call_kwargs['session'] == 42

    def test_attaches_query_when_provided(self):
        """Test that query is attached when provided"""
        setup_logging(log_level="INFO", console_output=False, file_output=False)

        with patch.object(logger, 'bind') as mock_bind:
            mock_bind.return_value = logger

            log_memory_operation(
                operation="query",
                agent_id="agent_alex",
                session_number=5,
                query="merchant negotiations"
            )

            call_kwargs = mock_bind.call_args[1]
            assert call_kwargs['query'] == "merchant negotiations"

    def test_omits_query_when_not_provided(self):
        """Test that query is omitted when not provided"""
        setup_logging(log_level="INFO", console_output=False, file_output=False)

        with patch.object(logger, 'bind') as mock_bind:
            mock_bind.return_value = logger

            log_memory_operation(
                operation="store",
                agent_id="agent_alex",
                session_number=5
            )

            call_kwargs = mock_bind.call_args[1]
            assert 'query' not in call_kwargs

    def test_attaches_result_count_when_provided(self):
        """Test that result_count is attached when provided"""
        setup_logging(log_level="INFO", console_output=False, file_output=False)

        with patch.object(logger, 'bind') as mock_bind:
            mock_bind.return_value = logger

            log_memory_operation(
                operation="query",
                agent_id="agent_alex",
                session_number=5,
                result_count=3
            )

            call_kwargs = mock_bind.call_args[1]
            assert call_kwargs['result_count'] == 3

    def test_omits_result_count_when_not_provided(self):
        """Test that result_count is omitted when not provided"""
        setup_logging(log_level="INFO", console_output=False, file_output=False)

        with patch.object(logger, 'bind') as mock_bind:
            mock_bind.return_value = logger

            log_memory_operation(
                operation="store",
                agent_id="agent_alex",
                session_number=5
            )

            call_kwargs = mock_bind.call_args[1]
            assert 'result_count' not in call_kwargs

    def test_accepts_extra_context_kwargs(self):
        """Test that extra keyword arguments are included in context"""
        setup_logging(log_level="INFO", console_output=False, file_output=False)

        with patch.object(logger, 'bind') as mock_bind:
            mock_bind.return_value = logger

            log_memory_operation(
                operation="query",
                agent_id="agent_alex",
                session_number=5,
                memory_type="episodic",
                time_range="recent"
            )

            call_kwargs = mock_bind.call_args[1]
            assert call_kwargs['memory_type'] == "episodic"
            assert call_kwargs['time_range'] == "recent"

    def test_logs_memory_operation_message(self, temp_log_dir):
        """Test that memory operation message is logged correctly"""
        setup_logging(log_level="INFO", console_output=False, file_output=True, log_dir=temp_log_dir)

        log_memory_operation(
            operation="query",
            agent_id="agent_alex",
            session_number=5
        )

        # Verify memory operation message was logged
        log_files = list(temp_log_dir.glob("*.log"))
        assert len(log_files) > 0
        log_content = log_files[0].read_text()
        assert "Memory operation" in log_content
        assert "query" in log_content
