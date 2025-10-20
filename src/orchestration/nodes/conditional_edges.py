# ABOUTME: Conditional edge predicates for LangGraph state machine routing decisions.
# ABOUTME: Contains all conditional logic that determines state transitions in the turn cycle.

from typing import Literal

from loguru import logger

from src.models.game_state import GamePhase, GameState

# ============================================================================
# Constants
# ============================================================================

MAX_CLARIFICATION_ROUNDS = 3


# ============================================================================
# Conditional Edge Predicates
# ============================================================================


def should_retry_validation(state: GameState) -> Literal["valid", "retry", "escalate"]:
    """
    Conditional edge for validation retry logic.

    Args:
        state: Current game state

    Returns:
        Route key: "valid", "retry", or "escalate"
    """
    if state["validation_valid"]:
        return "valid"
    elif state["validation_attempt"] < 3:
        return "retry"
    else:
        return "escalate"


def should_skip_ooc_discussion(state: GameState) -> Literal["discuss", "skip"]:
    """
    Conditional edge for skipping OOC phase in single-agent games.

    Args:
        state: Current game state

    Returns:
        Route key: "discuss" or "skip"
    """
    if len(state["active_agents"]) == 1:
        return "skip"
    else:
        return "discuss"


def check_error_state(state: GameState) -> Literal["continue", "rollback"]:
    """
    Conditional edge for error recovery.

    Args:
        state: Current game state

    Returns:
        Route key: "continue" or "rollback"
    """
    if state.get("error_state"):
        return "rollback"
    else:
        return "continue"


def check_laser_feelings(state: GameState) -> Literal["question", "outcome"]:
    """
    Conditional edge for LASER FEELINGS detection.

    Phase 2 Issue #3: Routes to laser_feelings_question if exact match detected,
    otherwise proceeds to dm_outcome.

    Args:
        state: Current game state

    Returns:
        Route key: "question" if LASER FEELINGS detected, "outcome" otherwise
    """
    if state["current_phase"] == GamePhase.LASER_FEELINGS_QUESTION.value:
        return "question"
    else:
        return "outcome"


def check_clarification_after_collect(state: GameState) -> Literal["wait", "skip"]:
    """
    Conditional edge after dm_clarification_collect.

    Routes to:
    - "wait": If questions exist (current_phase still DM_CLARIFICATION)
    - "skip": If no questions (current_phase changed to MEMORY_QUERY)

    Args:
        state: Current game state

    Returns:
        Route key
    """
    # Check if collect node set phase to MEMORY_QUERY (no questions)
    if state["current_phase"] == GamePhase.MEMORY_QUERY.value:
        return "skip"
    else:
        # Phase is still DM_CLARIFICATION, meaning questions exist
        return "wait"


def check_clarification_after_wait(state: GameState) -> Literal["loop", "proceed"]:
    """
    Conditional edge after dm_clarification_wait (after DM answers).

    Routes to:
    - "loop": Back to collect node to check for follow-up questions
    - "proceed": To second_memory_query if max rounds reached

    Args:
        state: Current game state

    Returns:
        Route key
    """
    current_round = state.get("clarification_round", 1)

    # Check if max rounds reached
    if current_round >= MAX_CLARIFICATION_ROUNDS:
        logger.info(f"Max clarification rounds ({MAX_CLARIFICATION_ROUNDS}) reached")
        return "proceed"
    else:
        # Loop back to collect node for potential follow-ups
        return "loop"
