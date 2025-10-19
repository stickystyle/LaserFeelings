# ABOUTME: Exception definitions for agent layer contract violations.
# ABOUTME: Defines error types raised by BasePersonaAgent and CharacterAgent.


class LLMCallFailed(Exception):
    """Raised when OpenAI API call fails after retries"""
    pass


class ValidationFailed(Exception):
    """Raised when action contains narrative overreach"""
    pass


class MaxRetriesExceeded(Exception):
    """Raised after 3 validation failures"""
    pass


class NoConsensusReached(Exception):
    """Raised when discussion lacks clear direction"""
    pass


class InvalidMessageFormat(Exception):
    """Raised when message doesn't match expected schema"""
    pass


class CharacterNotFound(Exception):
    """Raised when specified character doesn't exist"""
    pass


class InvalidCharacterState(Exception):
    """Raised when character state prevents action or is corrupted"""
    pass
