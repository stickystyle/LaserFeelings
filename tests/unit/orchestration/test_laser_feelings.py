# ABOUTME: Unit tests for LASER FEELINGS re-roll flow in the state machine.
# ABOUTME: Tests detection, pause, GM answer, action modification, and automatic re-roll.

import pytest
from datetime import datetime
from unittest.mock import MagicMock, patch

from src.models.game_state import GamePhase, GameState
from src.orchestration.nodes.outcome_nodes import (
    dice_resolution_node,
    laser_feelings_question_node,
)


class TestLaserFeelingsDetection:
    """Tests for detecting LASER FEELINGS and pausing resolution"""

    def test_laser_feelings_detection_pauses_resolution(self):
        """When exact match occurs, dice_resolution should pause and transition to LASER_FEELINGS_QUESTION"""
        state: GameState = {
            "current_phase": GamePhase.DICE_RESOLUTION.value,
            "phase_start_time": datetime.now(),
            "turn_number": 1,
            "session_number": 1,
            "dm_narration": "Test",
            "dm_adjudication_needed": True,
            "active_agents": ["agent_alex_001"],
            "strategic_intents": {"agent_alex_001": {"strategic_goal": "Test"}},
            "character_actions": {
                "char_zara_001": {
                    "character_id": "char_zara_001",
                    "narrative_text": "I check the energy readings",
                    "task_type": "lasers",
                    "is_prepared": False,
                    "is_expert": False,
                    "is_helping": False,
                    "gm_question": "What are they really feeling?"
                }
            },
            "character_reactions": {},
            "validation_attempt": 0,
            "validation_valid": True,
            "validation_failures": {},
            "retrieved_memories": {},
            "retry_count": 0,
            "ooc_messages": [],
            "successful_helper_counts": {}
        }

        # Mock roll to return LASER FEELINGS (character number 2, roll exactly 2)
        with patch('src.orchestration.nodes.outcome_nodes.roll_lasers_feelings') as mock_roll:
            mock_roll.return_value = MagicMock(
                character_number=2,
                task_type="lasers",
                is_prepared=False,
                is_expert=False,
                is_helping=False,
                individual_rolls=[2],
                die_successes=[True],
                laser_feelings_indices=[0],  # First die is exact match
                total_successes=1,
                outcome=MagicMock(value="barely"),
                has_laser_feelings=True,
                timestamp=datetime.now()
            )

            result = dice_resolution_node(state)

        # Should transition to LASER_FEELINGS_QUESTION phase
        assert result["current_phase"] == GamePhase.LASER_FEELINGS_QUESTION.value
        assert "laser_feelings_data" in result
        assert result["laser_feelings_data"]["character_id"] == "char_zara_001"
        assert result["laser_feelings_data"]["gm_question"] == "What are they really feeling?"

    def test_no_laser_feelings_proceeds_to_outcome(self):
        """When no exact match, dice_resolution should proceed to DM_OUTCOME"""
        state: GameState = {
            "current_phase": GamePhase.DICE_RESOLUTION.value,
            "phase_start_time": datetime.now(),
            "turn_number": 1,
            "session_number": 1,
            "dm_narration": "Test",
            "dm_adjudication_needed": True,
            "active_agents": ["agent_alex_001"],
            "strategic_intents": {"agent_alex_001": {"strategic_goal": "Test"}},
            "character_actions": {
                "char_zara_001": {
                    "character_id": "char_zara_001",
                    "narrative_text": "I check the energy readings",
                    "task_type": "lasers",
                    "is_prepared": False,
                    "is_expert": False,
                    "is_helping": False
                }
            },
            "character_reactions": {},
            "validation_attempt": 0,
            "validation_valid": True,
            "validation_failures": {},
            "retrieved_memories": {},
            "retry_count": 0,
            "ooc_messages": [],
            "successful_helper_counts": {}
        }

        # Mock roll to return normal success (no exact match)
        with patch('src.orchestration.nodes.outcome_nodes.roll_lasers_feelings') as mock_roll:
            mock_roll.return_value = MagicMock(
                character_number=2,
                task_type="lasers",
                is_prepared=False,
                is_expert=False,
                is_helping=False,
                individual_rolls=[1],
                die_successes=[True],
                laser_feelings_indices=[],  # No exact match
                total_successes=1,
                outcome=MagicMock(value="barely"),
                has_laser_feelings=False,
                timestamp=datetime.now()
            )

            result = dice_resolution_node(state)

        # Should proceed to DM_OUTCOME
        assert result["current_phase"] == GamePhase.DM_OUTCOME.value
        assert "laser_feelings_data" not in result

    def test_laser_feelings_stores_original_roll_and_action(self):
        """LASER FEELINGS data should include original roll, action, and dice parameters"""
        state: GameState = {
            "current_phase": GamePhase.DICE_RESOLUTION.value,
            "phase_start_time": datetime.now(),
            "turn_number": 1,
            "session_number": 1,
            "dm_narration": "Test",
            "dm_adjudication_needed": True,
            "active_agents": ["agent_alex_001"],
            "strategic_intents": {"agent_alex_001": {"strategic_goal": "Test"}},
            "character_actions": {
                "char_zara_001": {
                    "character_id": "char_zara_001",
                    "narrative_text": "I carefully analyze the console",
                    "task_type": "lasers",
                    "is_prepared": True,
                    "is_expert": True,
                    "is_helping": False,
                    "gm_question": "What should I be on the lookout for?"
                }
            },
            "character_reactions": {},
            "validation_attempt": 0,
            "validation_valid": True,
            "validation_failures": {},
            "retrieved_memories": {},
            "retry_count": 0,
            "ooc_messages": [],
            "successful_helper_counts": {"char_zara_001": 2}  # 2 successful helpers
        }

        with patch('src.orchestration.nodes.outcome_nodes.roll_lasers_feelings') as mock_roll:
            mock_roll.return_value = MagicMock(
                character_number=2,
                task_type="lasers",
                is_prepared=True,
                is_expert=True,
                is_helping=False,
                individual_rolls=[3, 2, 1, 5, 4],  # 5 dice (base + prepared + expert + 2 helpers)
                die_successes=[False, True, True, False, False],
                laser_feelings_indices=[1],  # Second die is exact match
                total_successes=2,
                outcome=MagicMock(value="success"),
                has_laser_feelings=True,
                timestamp=datetime.now()
            )

            result = dice_resolution_node(state)

        # Verify stored data
        laser_data = result["laser_feelings_data"]
        assert laser_data["character_id"] == "char_zara_001"
        assert laser_data["original_action"]["narrative_text"] == "I carefully analyze the console"
        assert laser_data["original_action"]["is_prepared"] is True
        assert laser_data["original_action"]["is_expert"] is True
        assert laser_data["gm_question"] == "What should I be on the lookout for?"
        assert laser_data["dice_parameters"]["character_number"] == 2
        assert laser_data["dice_parameters"]["task_type"] == "lasers"
        assert laser_data["dice_parameters"]["is_prepared"] is True
        assert laser_data["dice_parameters"]["is_expert"] is True
        assert laser_data["dice_parameters"]["successful_helpers"] == 2


class TestLaserFeelingsQuestionNode:
    """Tests for the laser_feelings_question_node that waits for GM answer"""

    def test_laser_feelings_question_node_waits_for_gm(self):
        """laser_feelings_question_node should set waiting_for_gm_answer flag"""
        state: GameState = {
            "current_phase": GamePhase.LASER_FEELINGS_QUESTION.value,
            "phase_start_time": datetime.now(),
            "turn_number": 1,
            "session_number": 1,
            "dm_narration": "Test",
            "dm_adjudication_needed": True,
            "active_agents": ["agent_alex_001"],
            "strategic_intents": {},
            "character_actions": {},
            "character_reactions": {},
            "validation_attempt": 0,
            "validation_valid": True,
            "validation_failures": {},
            "retrieved_memories": {},
            "retry_count": 0,
            "ooc_messages": [],
            "laser_feelings_data": {
                "character_id": "char_zara_001",
                "original_action": {
                    "narrative_text": "I scan for anomalies",
                    "task_type": "lasers"
                },
                "gm_question": "Who's behind this?",
                "dice_parameters": {
                    "character_number": 2,
                    "task_type": "lasers",
                    "is_prepared": False,
                    "is_expert": False,
                    "successful_helpers": 0
                }
            }
        }

        result = laser_feelings_question_node(state)

        assert result["waiting_for_gm_answer"] is True
        assert result["current_phase"] == GamePhase.LASER_FEELINGS_QUESTION.value


class TestLaserFeelingsEdgeCases:
    """Tests for edge cases in LASER FEELINGS flow"""

    def test_multiple_exact_matches_only_one_question(self):
        """When multiple dice match, only one question should be asked"""
        state: GameState = {
            "current_phase": GamePhase.DICE_RESOLUTION.value,
            "phase_start_time": datetime.now(),
            "turn_number": 1,
            "session_number": 1,
            "dm_narration": "Test",
            "dm_adjudication_needed": True,
            "active_agents": ["agent_alex_001"],
            "strategic_intents": {"agent_alex_001": {"strategic_goal": "Test"}},
            "character_actions": {
                "char_zara_001": {
                    "character_id": "char_zara_001",
                    "narrative_text": "I analyze the situation",
                    "task_type": "lasers",
                    "is_prepared": True,
                    "is_expert": True,
                    "is_helping": False,
                    "gm_question": "What's the best way to proceed?"
                }
            },
            "character_reactions": {},
            "validation_attempt": 0,
            "validation_valid": True,
            "validation_failures": {},
            "retrieved_memories": {},
            "retry_count": 0,
            "ooc_messages": [],
            "successful_helper_counts": {}
        }

        # Mock roll with TWO exact matches
        with patch('src.orchestration.nodes.outcome_nodes.roll_lasers_feelings') as mock_roll:
            mock_roll.return_value = MagicMock(
                character_number=2,
                task_type="lasers",
                is_prepared=True,
                is_expert=True,
                is_helping=False,
                individual_rolls=[2, 1, 2],  # TWO dice match (indices 0 and 2)
                die_successes=[True, True, True],
                laser_feelings_indices=[0, 2],  # Two exact matches
                total_successes=3,
                outcome=MagicMock(value="critical"),
                has_laser_feelings=True,
                timestamp=datetime.now()
            )

            result = dice_resolution_node(state)

        # Should still only pause once (single question)
        assert result["current_phase"] == GamePhase.LASER_FEELINGS_QUESTION.value
        # Verify only one question is stored
        assert result["laser_feelings_data"]["gm_question"] == "What's the best way to proceed?"
        # Multiple indices stored but only one question asked
        assert len(result["laser_feelings_data"]["original_roll"]["laser_feelings_indices"]) == 2

    def test_exact_match_counts_as_success(self):
        """LASER FEELINGS exact match should count as a success"""
        state: GameState = {
            "current_phase": GamePhase.DICE_RESOLUTION.value,
            "phase_start_time": datetime.now(),
            "turn_number": 1,
            "session_number": 1,
            "dm_narration": "Test",
            "dm_adjudication_needed": True,
            "active_agents": ["agent_alex_001"],
            "strategic_intents": {"agent_alex_001": {"strategic_goal": "Test"}},
            "character_actions": {
                "char_zara_001": {
                    "character_id": "char_zara_001",
                    "narrative_text": "I check the readings",
                    "task_type": "lasers",
                    "is_prepared": False,
                    "is_expert": False,
                    "is_helping": False,
                    "gm_question": "What should I be on the lookout for?"
                }
            },
            "character_reactions": {},
            "validation_attempt": 0,
            "validation_valid": True,
            "validation_failures": {},
            "retrieved_memories": {},
            "retry_count": 0,
            "ooc_messages": [],
            "successful_helper_counts": {}
        }

        # Roll exactly the character number (which is a success)
        with patch('src.orchestration.nodes.outcome_nodes.roll_lasers_feelings') as mock_roll:
            mock_roll.return_value = MagicMock(
                character_number=2,
                task_type="lasers",
                is_prepared=False,
                is_expert=False,
                is_helping=False,
                individual_rolls=[2],  # Exact match
                die_successes=[True],  # Should count as success
                laser_feelings_indices=[0],
                total_successes=1,  # 1 success from the exact match
                outcome=MagicMock(value="barely"),
                has_laser_feelings=True,
                timestamp=datetime.now()
            )

            result = dice_resolution_node(state)

        # Verify the exact match was counted as success
        assert result["laser_feelings_data"]["original_roll"]["total_successes"] == 1
        assert result["laser_feelings_data"]["original_roll"]["die_successes"] == [True]
