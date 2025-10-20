# ABOUTME: Exception definitions for orchestration layer errors.
# ABOUTME: Defines error types raised by TtrpgOrchestrator, MessageRouter, and ConsensusDetector.


class InvalidCommand(Exception):
    """Raised when DM command is malformed"""

    pass


class PhaseTransitionFailed(Exception):
    """Raised when state machine can't transition phases"""

    pass


class AgentExecutionFailed(Exception):
    """Raised when agent worker job fails"""

    pass


class JobFailedError(Exception):
    """Raised when RQ job fails or times out"""

    pass


class MaxRetriesExceeded(Exception):
    """Raised when retry limit exceeded"""

    pass


class InvalidPhaseTransition(Exception):
    """Raised when attempting invalid phase transition"""

    pass


class CheckpointNotFound(Exception):
    """Raised when checkpoint doesn't exist for rollback"""

    pass


class InvalidChannel(Exception):
    """Raised when message channel is invalid"""

    pass


class RecipientNotFound(Exception):
    """Raised when message recipient doesn't exist"""

    pass


class AgentNotFound(Exception):
    """Raised when agent_id doesn't exist"""

    pass


class InvalidAgentList(Exception):
    """Raised when agents list is empty or invalid"""

    pass


class PhaseTransitionError(Exception):
    """Raised when state machine encounters an error during phase transition"""

    pass
