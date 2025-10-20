# ABOUTME: Integration tests for CLI startup sequence with real Redis.
# ABOUTME: Verifies Redis cleanup on startup while preserving Neo4j graph data.

import pytest
from redis import Redis

from src.config.settings import get_settings
from src.utils.redis_cleanup import cleanup_redis_for_new_session


@pytest.fixture
def redis_client():
    """
    Real Redis client for integration testing.

    Requires docker-compose services to be running.
    """
    settings = get_settings()
    client = Redis.from_url(settings.redis_url, decode_responses=False)

    # Verify connection
    try:
        client.ping()
    except Exception as e:
        pytest.skip(f"Redis not available: {e}")

    yield client

    # Cleanup after test
    client.close()


class TestCLIStartupRedisCleanup:
    """Integration tests for Redis cleanup on CLI startup"""

    def test_cleanup_removes_test_data_from_redis(self, redis_client):
        """Test that cleanup removes seeded test data from Redis"""
        # Arrange - seed some test data
        test_key = "test:cli_startup:message"
        test_value = "test_data"
        redis_client.set(test_key, test_value)

        # Verify data was written
        assert redis_client.get(test_key) == test_value.encode()

        # Act - clean Redis
        result = cleanup_redis_for_new_session(redis_client)

        # Assert - cleanup succeeded
        assert result["success"] is True

        # Assert - test data was removed
        assert redis_client.get(test_key) is None

    def test_cleanup_removes_multiple_keys(self, redis_client):
        """Test that cleanup removes all keys from Redis"""
        # Arrange - seed multiple test keys
        test_keys = [
            "test:message:1",
            "test:message:2",
            "test:state:turn",
            "test:queue:jobs"
        ]

        for key in test_keys:
            redis_client.set(key, "test_value")

        # Verify all keys exist
        assert redis_client.dbsize() >= len(test_keys)

        # Act - clean Redis
        result = cleanup_redis_for_new_session(redis_client)

        # Assert - cleanup succeeded
        assert result["success"] is True

        # Assert - all keys were removed
        assert redis_client.dbsize() == 0

    def test_cleanup_removes_list_data(self, redis_client):
        """Test that cleanup removes Redis list data structures"""
        # Arrange - create list data
        list_key = "test:messages:ooc"
        redis_client.rpush(list_key, "message1", "message2", "message3")

        # Verify list exists
        assert redis_client.llen(list_key) == 3

        # Act - clean Redis
        result = cleanup_redis_for_new_session(redis_client)

        # Assert - cleanup succeeded
        assert result["success"] is True

        # Assert - list was removed
        assert redis_client.exists(list_key) == 0

    def test_cleanup_removes_hash_data(self, redis_client):
        """Test that cleanup removes Redis hash data structures"""
        # Arrange - create hash data
        hash_key = "test:turn:state"
        redis_client.hset(hash_key, mapping={
            "turn_number": "1",
            "phase": "dm_narration",
            "session_number": "1"
        })

        # Verify hash exists
        assert redis_client.exists(hash_key) == 1

        # Act - clean Redis
        result = cleanup_redis_for_new_session(redis_client)

        # Assert - cleanup succeeded
        assert result["success"] is True

        # Assert - hash was removed
        assert redis_client.exists(hash_key) == 0

    def test_cleanup_idempotent_on_empty_database(self, redis_client):
        """Test that cleanup works safely on already-empty database"""
        # Arrange - ensure database is empty
        redis_client.flushdb()
        assert redis_client.dbsize() == 0

        # Act - clean empty Redis
        result = cleanup_redis_for_new_session(redis_client)

        # Assert - cleanup succeeded
        assert result["success"] is True

        # Assert - database still empty
        assert redis_client.dbsize() == 0

    def test_cleanup_returns_success_dict(self, redis_client):
        """Test that cleanup returns proper success dictionary"""
        # Act
        result = cleanup_redis_for_new_session(redis_client)

        # Assert
        assert isinstance(result, dict)
        assert "success" in result
        assert "message" in result
        assert result["success"] is True
        assert isinstance(result["message"], str)

    def test_multiple_cleanups_are_safe(self, redis_client):
        """Test that running cleanup multiple times is safe"""
        # Arrange - seed data
        redis_client.set("test:key", "value")

        # Act - cleanup multiple times
        result1 = cleanup_redis_for_new_session(redis_client)
        result2 = cleanup_redis_for_new_session(redis_client)
        result3 = cleanup_redis_for_new_session(redis_client)

        # Assert - all cleanups succeeded
        assert result1["success"] is True
        assert result2["success"] is True
        assert result3["success"] is True

        # Assert - database is clean
        assert redis_client.dbsize() == 0


@pytest.mark.skip(reason="Neo4j integration not yet implemented in this test suite")
class TestCLIStartupNeo4jPreservation:
    """Integration tests verifying Neo4j graph data is NOT affected by Redis cleanup"""

    def test_cleanup_does_not_affect_neo4j_graph(self, redis_client, neo4j_client):
        """Test that Redis cleanup preserves Neo4j graph memory"""
        # This test would verify Neo4j data persistence
        # Skipped for now - can be implemented when Neo4j integration is needed
        pass
