# ABOUTME: Exception definitions for memory layer errors.
# ABOUTME: Defines error types raised by CorruptedTemporalMemory and Graphiti integration.


class GraphitiConnectionFailed(Exception):
    """Raised when connection to Neo4j/Graphiti fails"""
    pass


class InvalidAgentID(Exception):
    """Raised when agent_id is invalid or not found"""
    pass


class EpisodeCreationFailed(Exception):
    """Raised when Graphiti fails to create episode"""
    pass


class MemoryNotFound(Exception):
    """Raised when memory UUID doesn't exist"""
    pass


class AlreadyInvalidated(Exception):
    """Raised when attempting to invalidate already-invalidated memory"""
    pass


class IndexCreationFailed(Exception):
    """Raised when Neo4j index creation fails"""
    pass


class LLMCallFailed(Exception):
    """Raised when OpenAI API call fails"""
    pass
