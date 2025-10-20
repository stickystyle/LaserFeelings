# ABOUTME: Validation retry and escalation node handlers for character action validation.
# ABOUTME: Manages validation retry attempts and escalates to DM review when max retries exceeded.

from datetime import datetime

from loguru import logger

from src.models.game_state import GamePhase, GameState


def validation_retry_node(state: GameState) -> GameState:
    """
    Retry character action with stricter validation prompt.

    Args:
        state: Current game state

    Returns:
        Updated state with retry attempt incremented
    """
    logger.warning(f"[VALIDATION RETRY] Attempt {state['validation_attempt'] + 1}/3")

    # TODO: In full implementation, re-dispatch character jobs with stricter prompts
    # For MVP, we increment attempt and proceed
    # validation_failures = state["validation_failures"]  # Available for future use

    return {
        **state,
        "validation_attempt": state["validation_attempt"] + 1,
        "current_phase": GamePhase.CHARACTER_ACTION.value,
        "phase_start_time": datetime.now(),
    }


def validation_escalate_node(state: GameState) -> GameState:
    """
    Escalate validation failures to DM review.

    Args:
        state: Current game state

    Returns:
        Updated state with DM review flag set
    """
    logger.error("[VALIDATION ESCALATE] Max retries exceeded, flagging for DM review")

    return {
        **state,
        "dm_review_required": True,
        "current_phase": GamePhase.DM_ADJUDICATION.value,
        "phase_start_time": datetime.now(),
    }
