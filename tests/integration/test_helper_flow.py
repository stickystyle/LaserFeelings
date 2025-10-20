# ABOUTME: Integration tests for helper resolution flow with successful helpers adding bonus dice.
# ABOUTME: Tests end-to-end helper scenarios including multiple helpers, failed helpers, and stacking bonuses.

import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime

from redis import Redis

from src.orchestration.state_machine import resolve_helpers_node, dice_resolution_node
from src.models.game_state import GameState


@pytest.fixture
def mock_redis_integration():
    """Mock Redis client for integration tests"""
    redis = MagicMock(spec=Redis)
    redis.ping = MagicMock(return_value=True)
    return redis


class TestHelperFlowIntegration:
    """Integration tests for full helper resolution flow"""

    def test_full_helper_flow_two_helpers_both_succeed(self):
        """
        Test complete helper flow:
        - Character A attempts to hack console (primary action)
        - Character B helps by providing covering fire
        - Character C helps by scanning for threats
        - Both helpers succeed (≥1 success)
        - Character A's roll uses successful_helpers=2
        """
        # Setup initial state with character actions
        initial_state: GameState = {
            "current_phase": "resolve_helpers",
            "phase_start_time": datetime.now(),
            "turn_number": 1,
            "session_number": 1,
            "dm_narration": "The alien console beeps ominously.",
            "dm_adjudication_needed": True,
            "active_agents": ["agent_zara_001", "agent_kai_002", "agent_lyra_003"],
            "strategic_intents": {},
            "ooc_messages": [],
            "character_actions": {
                "char_zara_001": {
                    "character_id": "char_zara_001",
                    "narrative_text": "I attempt to hack the alien console using my omnitool.",
                    "task_type": "lasers",
                    "is_prepared": True,
                    "prepared_justification": "I studied the alien tech beforehand",
                    "is_expert": True,
                    "expert_justification": "I'm an expert engineer",
                    "is_helping": False,
                    "helping_character_id": None
                },
                "char_kai_002": {
                    "character_id": "char_kai_002",
                    "narrative_text": "I provide covering fire to protect Zara while she works.",
                    "task_type": "lasers",
                    "is_prepared": False,
                    "is_expert": False,
                    "is_helping": True,
                    "helping_character_id": "char_zara_001",
                    "help_justification": "Suppressing enemy positions"
                },
                "char_lyra_003": {
                    "character_id": "char_lyra_003",
                    "narrative_text": "I scan for incoming threats to help Zara focus.",
                    "task_type": "lasers",
                    "is_prepared": False,
                    "is_expert": False,
                    "is_helping": True,
                    "helping_character_id": "char_zara_001",
                    "help_justification": "Using sensors to watch perimeter"
                }
            },
            "character_reactions": {},
            "validation_attempt": 0,
            "validation_valid": True,
            "validation_failures": {},
            "retrieved_memories": {},
            "retry_count": 0,
        }

        # Mock roll_lasers_feelings to control helper rolls
        with patch('src.orchestration.state_machine.roll_lasers_feelings') as mock_roll:
            # First call: Helper Kai succeeds (2 successes)
            # Second call: Helper Lyra succeeds (1 success)
            mock_roll.side_effect = [
                MagicMock(total_successes=2, individual_rolls=[2, 3]),  # Kai succeeds
                MagicMock(total_successes=1, individual_rolls=[2]),     # Lyra succeeds
            ]

            # Step 1: Resolve helpers
            state_after_helpers = resolve_helpers_node(initial_state)

            # Verify successful_helper_counts was added
            assert "successful_helper_counts" in state_after_helpers
            assert state_after_helpers["successful_helper_counts"]["char_zara_001"] == 2

            # Verify both helpers were rolled
            assert mock_roll.call_count == 2

        # Step 2: Dice resolution uses helper count
        dice_state = {
            **state_after_helpers,
            "current_phase": "dice_resolution",
            "active_agents": ["agent_alex_001"]  # Use real agent from config
        }

        # Mock the agent-to-character mapping
        with patch('src.orchestration.state_machine._get_character_id_for_agent') as mock_mapping:
            mock_mapping.return_value = "char_zara_001"

            with patch('src.orchestration.state_machine.roll_lasers_feelings') as mock_main_roll:
                # Main character rolls with 5d6 (base 3d6 + 2 helpers)
                mock_main_roll.return_value = MagicMock(
                    dice_count=5,
                    total_successes=3,
                    individual_rolls=[1, 2, 3, 4, 5],
                    die_successes=[True, True, False, False, False],
                    laser_feelings_indices=[],
                    outcome=MagicMock(value="success"),
                    has_laser_feelings=False,
                    character_number=2,
                    task_type="lasers",
                    is_prepared=True,
                    is_expert=True,
                    is_helping=False,
                    timestamp=datetime.now()
                )

                final_state = dice_resolution_node(dice_state)

                # Verify main roll was called with successful_helpers=2
                mock_main_roll.assert_called_once()
                call_args = mock_main_roll.call_args
                assert call_args.kwargs["successful_helpers"] == 2
                assert call_args.kwargs["is_prepared"] is True
                assert call_args.kwargs["is_expert"] is True

    def test_helper_flow_one_helper_fails(self):
        """
        Test helper flow where one helper fails (0 successes):
        - Character A attempts action
        - Character B helps but fails (0 successes)
        - Character A's roll uses successful_helpers=0
        """
        initial_state: GameState = {
            "current_phase": "resolve_helpers",
            "phase_start_time": datetime.now(),
            "turn_number": 1,
            "session_number": 1,
            "dm_narration": "Test narration",
            "dm_adjudication_needed": True,
            "active_agents": ["agent_zara_001", "agent_kai_002"],
            "strategic_intents": {},
            "ooc_messages": [],
            "character_actions": {
                "char_zara_001": {
                    "character_id": "char_zara_001",
                    "narrative_text": "I hack the console.",
                    "task_type": "lasers",
                    "is_prepared": False,
                    "is_expert": False,
                    "is_helping": False,
                    "helping_character_id": None
                },
                "char_kai_002": {
                    "character_id": "char_kai_002",
                    "narrative_text": "I try to help Zara but fail.",
                    "task_type": "lasers",
                    "is_prepared": False,
                    "is_expert": False,
                    "is_helping": True,
                    "helping_character_id": "char_zara_001",
                    "help_justification": "Attempting to cover"
                }
            },
            "character_reactions": {},
            "validation_attempt": 0,
            "validation_valid": True,
            "validation_failures": {},
            "retrieved_memories": {},
            "retry_count": 0,
        }

        with patch('src.orchestration.state_machine.roll_lasers_feelings') as mock_roll:
            # Helper fails (0 successes)
            mock_roll.return_value = MagicMock(total_successes=0, individual_rolls=[6])

            state_after_helpers = resolve_helpers_node(initial_state)

            # Verify helper count is 0 (failed helper doesn't count)
            assert state_after_helpers["successful_helper_counts"]["char_zara_001"] == 0

    def test_helper_flow_no_helpers(self):
        """
        Test helper flow with no helpers:
        - Character A attempts action alone
        - No helpers present
        - Character A's roll uses successful_helpers=0
        """
        initial_state: GameState = {
            "current_phase": "resolve_helpers",
            "phase_start_time": datetime.now(),
            "turn_number": 1,
            "session_number": 1,
            "dm_narration": "Test narration",
            "dm_adjudication_needed": True,
            "active_agents": ["agent_zara_001"],
            "strategic_intents": {},
            "ooc_messages": [],
            "character_actions": {
                "char_zara_001": {
                    "character_id": "char_zara_001",
                    "narrative_text": "I hack the console alone.",
                    "task_type": "lasers",
                    "is_prepared": False,
                    "is_expert": False,
                    "is_helping": False,
                    "helping_character_id": None
                }
            },
            "character_reactions": {},
            "validation_attempt": 0,
            "validation_valid": True,
            "validation_failures": {},
            "retrieved_memories": {},
            "retry_count": 0,
        }

        state_after_helpers = resolve_helpers_node(initial_state)

        # Verify helper count is 0 (no helpers)
        assert state_after_helpers["successful_helper_counts"]["char_zara_001"] == 0

    def test_helper_flow_multiple_primary_actions_with_different_helper_counts(self):
        """
        Test helper flow with multiple primary actions:
        - Character A has 2 successful helpers
        - Character B has 0 helpers
        - Character C has 1 successful helper
        """
        initial_state: GameState = {
            "current_phase": "resolve_helpers",
            "phase_start_time": datetime.now(),
            "turn_number": 1,
            "session_number": 1,
            "dm_narration": "Test narration",
            "dm_adjudication_needed": True,
            "active_agents": ["agent_a", "agent_b", "agent_c", "agent_helper1", "agent_helper2", "agent_helper3"],
            "strategic_intents": {},
            "ooc_messages": [],
            "character_actions": {
                # Primary actions
                "char_a_001": {
                    "character_id": "char_a_001",
                    "narrative_text": "Character A action",
                    "is_helping": False
                },
                "char_b_002": {
                    "character_id": "char_b_002",
                    "narrative_text": "Character B action",
                    "is_helping": False
                },
                "char_c_003": {
                    "character_id": "char_c_003",
                    "narrative_text": "Character C action",
                    "is_helping": False
                },
                # Helpers
                "char_helper1_004": {
                    "character_id": "char_helper1_004",
                    "narrative_text": "Helper 1 helps A",
                    "is_helping": True,
                    "helping_character_id": "char_a_001",
                    "help_justification": "Help A"
                },
                "char_helper2_005": {
                    "character_id": "char_helper2_005",
                    "narrative_text": "Helper 2 helps A",
                    "is_helping": True,
                    "helping_character_id": "char_a_001",
                    "help_justification": "Help A"
                },
                "char_helper3_006": {
                    "character_id": "char_helper3_006",
                    "narrative_text": "Helper 3 helps C",
                    "is_helping": True,
                    "helping_character_id": "char_c_003",
                    "help_justification": "Help C"
                }
            },
            "character_reactions": {},
            "validation_attempt": 0,
            "validation_valid": True,
            "validation_failures": {},
            "retrieved_memories": {},
            "retry_count": 0,
        }

        with patch('src.orchestration.state_machine.roll_lasers_feelings') as mock_roll:
            # All helpers succeed
            mock_roll.return_value = MagicMock(total_successes=1, individual_rolls=[2])

            state_after_helpers = resolve_helpers_node(initial_state)

            # Verify helper counts
            assert state_after_helpers["successful_helper_counts"]["char_a_001"] == 2
            assert state_after_helpers["successful_helper_counts"]["char_b_002"] == 0
            assert state_after_helpers["successful_helper_counts"]["char_c_003"] == 1

    def test_helper_flow_mixed_success_rates(self):
        """
        Test helper flow with mixed success rates:
        - Character A has 3 helpers: 2 succeed, 1 fails
        - Only the 2 successful helpers count
        """
        initial_state: GameState = {
            "current_phase": "resolve_helpers",
            "phase_start_time": datetime.now(),
            "turn_number": 1,
            "session_number": 1,
            "dm_narration": "Test narration",
            "dm_adjudication_needed": True,
            "active_agents": ["agent_a", "agent_h1", "agent_h2", "agent_h3"],
            "strategic_intents": {},
            "ooc_messages": [],
            "character_actions": {
                "char_a_001": {
                    "character_id": "char_a_001",
                    "narrative_text": "Character A action",
                    "is_helping": False
                },
                "char_h1_002": {
                    "character_id": "char_h1_002",
                    "narrative_text": "Helper 1",
                    "is_helping": True,
                    "helping_character_id": "char_a_001",
                    "help_justification": "Help"
                },
                "char_h2_003": {
                    "character_id": "char_h2_003",
                    "narrative_text": "Helper 2",
                    "is_helping": True,
                    "helping_character_id": "char_a_001",
                    "help_justification": "Help"
                },
                "char_h3_004": {
                    "character_id": "char_h3_004",
                    "narrative_text": "Helper 3",
                    "is_helping": True,
                    "helping_character_id": "char_a_001",
                    "help_justification": "Help"
                }
            },
            "character_reactions": {},
            "validation_attempt": 0,
            "validation_valid": True,
            "validation_failures": {},
            "retrieved_memories": {},
            "retry_count": 0,
        }

        with patch('src.orchestration.state_machine.roll_lasers_feelings') as mock_roll:
            # Helper 1: succeeds (2 successes)
            # Helper 2: fails (0 successes)
            # Helper 3: succeeds (1 success)
            mock_roll.side_effect = [
                MagicMock(total_successes=2, individual_rolls=[1, 2]),
                MagicMock(total_successes=0, individual_rolls=[6]),
                MagicMock(total_successes=1, individual_rolls=[1]),
            ]

            state_after_helpers = resolve_helpers_node(initial_state)

            # Verify only 2 successful helpers count (helper 2 failed)
            assert state_after_helpers["successful_helper_counts"]["char_a_001"] == 2

    def test_helper_prepared_and_expert_bonuses_apply(self):
        """
        Test that helper's prepared and expert bonuses are used in their roll:
        - Helper is prepared and expert
        - Helper should roll 3d6 (base + prepared + expert)
        """
        initial_state: GameState = {
            "current_phase": "resolve_helpers",
            "phase_start_time": datetime.now(),
            "turn_number": 1,
            "session_number": 1,
            "dm_narration": "Test narration",
            "dm_adjudication_needed": True,
            "active_agents": ["agent_zara_001", "agent_kai_002"],
            "strategic_intents": {},
            "ooc_messages": [],
            "character_actions": {
                "char_zara_001": {
                    "character_id": "char_zara_001",
                    "narrative_text": "I hack the console.",
                    "is_helping": False
                },
                "char_kai_002": {
                    "character_id": "char_kai_002",
                    "narrative_text": "I help Zara.",
                    "task_type": "lasers",
                    "is_prepared": True,
                    "prepared_justification": "I prepared my gear",
                    "is_expert": True,
                    "expert_justification": "I'm an expert soldier",
                    "is_helping": True,
                    "helping_character_id": "char_zara_001",
                    "help_justification": "Providing cover"
                }
            },
            "character_reactions": {},
            "validation_attempt": 0,
            "validation_valid": True,
            "validation_failures": {},
            "retrieved_memories": {},
            "retry_count": 0,
        }

        with patch('src.orchestration.state_machine.roll_lasers_feelings') as mock_roll:
            mock_roll.return_value = MagicMock(total_successes=2, individual_rolls=[1, 2, 3])

            state_after_helpers = resolve_helpers_node(initial_state)

            # Verify roll was called with prepared and expert bonuses
            mock_roll.assert_called_once()
            call_args = mock_roll.call_args
            assert call_args.kwargs["is_prepared"] is True
            assert call_args.kwargs["is_expert"] is True
            assert call_args.kwargs["successful_helpers"] == 0  # Helpers don't get helper bonuses
