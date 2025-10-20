# ABOUTME: Unit tests for Redis cleanup utility used at CLI startup.
# ABOUTME: Validates cleanup function with mocked Redis client to ensure proper database flushing.

from unittest.mock import MagicMock, Mock

import pytest
from redis import Redis, RedisError

from src.utils.redis_cleanup import cleanup_redis_for_new_session


class TestCleanupRedisForNewSession:
    """Test suite for cleanup_redis_for_new_session function"""

    def test_successful_cleanup_returns_success_dict(self):
        """Test that successful cleanup returns success=True with message"""
        # Arrange
        mock_redis = Mock(spec=Redis)
        mock_redis.flushdb.return_value = True

        # Act
        result = cleanup_redis_for_new_session(mock_redis)

        # Assert
        assert result["success"] is True
        assert "message" in result
        assert "cleaned" in result["message"].lower() or "success" in result["message"].lower()

    def test_flushdb_is_called_once(self):
        """Test that flushdb is called exactly once"""
        # Arrange
        mock_redis = Mock(spec=Redis)
        mock_redis.flushdb.return_value = True

        # Act
        cleanup_redis_for_new_session(mock_redis)

        # Assert
        mock_redis.flushdb.assert_called_once()

    def test_connection_error_returns_failure_dict(self):
        """Test that Redis connection errors are handled gracefully"""
        # Arrange
        mock_redis = Mock(spec=Redis)
        mock_redis.flushdb.side_effect = RedisError("Connection refused")

        # Act
        result = cleanup_redis_for_new_session(mock_redis)

        # Assert
        assert result["success"] is False
        assert "message" in result
        assert "error" in result["message"].lower() or "failed" in result["message"].lower()

    def test_connection_error_includes_error_details(self):
        """Test that connection error message includes error details"""
        # Arrange
        mock_redis = Mock(spec=Redis)
        error_msg = "Connection refused"
        mock_redis.flushdb.side_effect = RedisError(error_msg)

        # Act
        result = cleanup_redis_for_new_session(mock_redis)

        # Assert
        assert result["success"] is False
        assert error_msg in result["message"]

    def test_generic_exception_returns_failure_dict(self):
        """Test that non-Redis exceptions are handled gracefully"""
        # Arrange
        mock_redis = Mock(spec=Redis)
        mock_redis.flushdb.side_effect = Exception("Unexpected error")

        # Act
        result = cleanup_redis_for_new_session(mock_redis)

        # Assert
        assert result["success"] is False
        assert "message" in result

    def test_return_type_is_dict(self):
        """Test that function always returns a dictionary"""
        # Arrange
        mock_redis = Mock(spec=Redis)
        mock_redis.flushdb.return_value = True

        # Act
        result = cleanup_redis_for_new_session(mock_redis)

        # Assert
        assert isinstance(result, dict)

    def test_return_dict_has_required_keys(self):
        """Test that return dict always has success and message keys"""
        # Arrange
        mock_redis = Mock(spec=Redis)
        mock_redis.flushdb.return_value = True

        # Act
        result = cleanup_redis_for_new_session(mock_redis)

        # Assert
        assert "success" in result
        assert "message" in result

    def test_success_value_is_boolean(self):
        """Test that success value is always a boolean"""
        # Arrange - success case
        mock_redis = Mock(spec=Redis)
        mock_redis.flushdb.return_value = True

        # Act
        result = cleanup_redis_for_new_session(mock_redis)

        # Assert
        assert isinstance(result["success"], bool)

        # Arrange - error case
        mock_redis.flushdb.side_effect = RedisError("Error")

        # Act
        result = cleanup_redis_for_new_session(mock_redis)

        # Assert
        assert isinstance(result["success"], bool)

    def test_message_value_is_string(self):
        """Test that message value is always a string"""
        # Arrange
        mock_redis = Mock(spec=Redis)
        mock_redis.flushdb.return_value = True

        # Act
        result = cleanup_redis_for_new_session(mock_redis)

        # Assert
        assert isinstance(result["message"], str)

    def test_none_redis_client_returns_failure_dict(self):
        """Test that passing None as redis_client returns failure dict"""
        # Arrange
        none_client = None

        # Act
        result = cleanup_redis_for_new_session(none_client)

        # Assert
        assert result["success"] is False
        assert "message" in result

    def test_timeout_error_returns_failure_dict(self):
        """Test that Redis timeout errors are handled gracefully"""
        # Arrange
        mock_redis = Mock(spec=Redis)
        mock_redis.flushdb.side_effect = RedisError("Timeout while reading from socket")

        # Act
        result = cleanup_redis_for_new_session(mock_redis)

        # Assert
        assert result["success"] is False
        assert "message" in result
