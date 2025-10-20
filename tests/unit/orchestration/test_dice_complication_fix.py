# ABOUTME: Unit test to verify dice_complication field correctly represents LASER FEELINGS only.
# ABOUTME: Tests that dice_complication is True only when exact match occurs, not for "barely" outcomes.

import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime, timezone

from src.orchestration.nodes.outcome_nodes import dice_resolution_node
from src.models.game_state import GameState
from src.utils.dice import LasersFeelingRollResult, RollOutcome


@pytest.fixture
def base_game_state() -> GameState:
    """Base game state for dice resolution tests."""
    return {
        "current_phase": "dice_resolution",
        "phase_start_time": datetime.now(),
        "turn_number": 1,
        "session_number": 1,
        "dm_narration": "Test narration",
        "dm_adjudication_needed": True,
        "active_agents": ["agent_alex_001"],
        "strategic_intents": {"agent_alex_001": {"strategic_goal": "Test"}},
        "ooc_messages": [],
        "character_actions": {
            "char_zara_001": {
                "task_type": "lasers",
                "is_prepared": False,
                "is_expert": False,
                "is_helping": False,
                "narrative_text": "Test action"
            }
        },
        "character_reactions": {},
        "validation_attempt": 0,
        "validation_valid": True,
        "validation_failures": {},
        "retrieved_memories": {},
        "retry_count": 0,
    }


def test_dice_complication_true_only_for_laser_feelings(base_game_state):
    """
    Test that dice_complication is True ONLY when LASER FEELINGS occurs.

    LASER FEELINGS = rolling exact match to character number.
    This should NOT include "barely" outcomes (1 success).
    """
    # Mock roll_lasers_feelings to return LASER FEELINGS result
    with patch("src.orchestration.nodes.outcome_nodes.roll_lasers_feelings") as mock_roll:
        # Character number 2, rolls exact 2 on one die → LASER FEELINGS + success
        mock_roll.return_value = LasersFeelingRollResult(
            character_number=2,
            task_type="lasers",
            is_prepared=False,
            is_expert=False,
            is_helping=False,
            individual_rolls=[2],
            die_successes=[True],
            laser_feelings_indices=[0],  # First die rolled exact match
            total_successes=1,
            outcome=RollOutcome.SUCCESS,
            timestamp=datetime.now(timezone.utc).isoformat()
        )

        result = dice_resolution_node(base_game_state)

        # Verify deprecated field dice_complication is True for LASER FEELINGS
        assert result["dice_complication"] is True
        assert result["dice_success"] is True


def test_dice_complication_false_for_barely_outcome_without_laser_feelings(base_game_state):
    """
    Test that dice_complication is False for "barely" outcome (1 success) WITHOUT LASER FEELINGS.

    This is the critical bug fix: "barely" outcome should NOT set dice_complication=True.
    Only actual LASER FEELINGS (exact match) should trigger it.
    """
    # Mock roll_lasers_feelings to return "barely" outcome (1 success) without LASER FEELINGS
    with patch("src.orchestration.nodes.outcome_nodes.roll_lasers_feelings") as mock_roll:
        # Character number 2, rolls [1] → 1 success (barely) but NO exact match
        mock_roll.return_value = LasersFeelingRollResult(
            character_number=2,
            task_type="lasers",
            is_prepared=False,
            is_expert=False,
            is_helping=False,
            individual_rolls=[1],
            die_successes=[True],
            laser_feelings_indices=[],  # NO LASER FEELINGS (no exact match)
            total_successes=1,
            outcome=RollOutcome.BARELY,
            timestamp=datetime.now(timezone.utc).isoformat()
        )

        result = dice_resolution_node(base_game_state)

        # CRITICAL FIX: dice_complication should be False despite "barely" outcome
        assert result["dice_complication"] is False
        assert result["dice_success"] is True
        assert result["dice_roll_result"]["outcome"] == "barely"


def test_dice_complication_false_for_failure(base_game_state):
    """
    Test that dice_complication is False for failure outcomes without LASER FEELINGS.
    """
    with patch("src.orchestration.nodes.outcome_nodes.roll_lasers_feelings") as mock_roll:
        # Character number 2, rolls [5] → failure, no LASER FEELINGS
        mock_roll.return_value = LasersFeelingRollResult(
            character_number=2,
            task_type="lasers",
            is_prepared=False,
            is_expert=False,
            is_helping=False,
            individual_rolls=[5],
            die_successes=[False],
            laser_feelings_indices=[],
            total_successes=0,
            outcome=RollOutcome.FAILURE,
            timestamp=datetime.now(timezone.utc).isoformat()
        )

        result = dice_resolution_node(base_game_state)

        assert result["dice_complication"] is False
        assert result["dice_success"] is False


def test_dice_complication_true_for_laser_feelings_with_barely_outcome(base_game_state):
    """
    Test that dice_complication is True when LASER FEELINGS occurs on a "barely" outcome.

    Edge case: Rolling exact match on 1 die while having multiple dice total = 1 success.
    """
    with patch("src.orchestration.nodes.outcome_nodes.roll_lasers_feelings") as mock_roll:
        # Character number 2, rolls [2, 5] → 1 success (barely) BUT first die is LASER FEELINGS
        mock_roll.return_value = LasersFeelingRollResult(
            character_number=2,
            task_type="lasers",
            is_prepared=True,  # Prepared = 2 dice
            is_expert=False,
            is_helping=False,
            individual_rolls=[2, 5],
            die_successes=[True, False],
            laser_feelings_indices=[0],  # First die is LASER FEELINGS
            total_successes=1,
            outcome=RollOutcome.BARELY,
            timestamp=datetime.now(timezone.utc).isoformat()
        )

        result = dice_resolution_node(base_game_state)

        # dice_complication should be True because LASER FEELINGS occurred
        assert result["dice_complication"] is True
        assert result["dice_success"] is True
        assert result["dice_roll_result"]["outcome"] == "barely"
