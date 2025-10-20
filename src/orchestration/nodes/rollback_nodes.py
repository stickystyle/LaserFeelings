# ABOUTME: Rollback handler node for error recovery and phase restoration.
# ABOUTME: Handles rollback to previous stable phase with retry counting and error clearing.

from datetime import datetime

from loguru import logger

from src.models.game_state import GamePhase, GameState
from src.orchestration.exceptions import MaxRetriesExceeded


def rollback_handler_node(state: GameState) -> GameState:
    """
    Handle rollback to previous stable phase.

    Args:
        state: Current game state

    Returns:
        Restored state from checkpoint

    Raises:
        MaxRetriesExceeded: When retry count reaches 3
    """
    logger.error(
        f"[ROLLBACK] Error in phase {state['current_phase']}: {state.get('error_state', 'Unknown')}"
    )

    # Determine rollback target
    rollback_phase = state.get("rollback_phase", GamePhase.DM_NARRATION.value)

    # Increment retry count
    retry_count = state.get("retry_count", 0) + 1

    if retry_count >= 3:
        logger.critical("[ROLLBACK] Max retries exceeded, halting turn cycle")
        raise MaxRetriesExceeded(
            f"Max retries exceeded after rollback from {state['current_phase']}"
        )

    return {
        **state,
        "current_phase": rollback_phase,
        "retry_count": retry_count,
        "error_state": None,  # Clear error
        "phase_start_time": datetime.now(),
    }
