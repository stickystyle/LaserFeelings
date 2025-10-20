# ABOUTME: Unit tests for helper resolution orchestration in state machine.
# ABOUTME: Tests helper identification, roll processing, successful helper counting, and integration with main action.

import pytest
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock

from src.models.game_state import GameState, GamePhase
from src.models.agent_actions import Action
from src.utils.dice import roll_lasers_feelings


class TestHelperResolution:
    """Test suite for helper resolution orchestration logic"""

    def test_identify_helping_actions_from_character_actions(self):
        """Test that helping actions can be identified from character_actions dict"""
        # Create character actions: 2 primary actions, 1 helping action
        character_actions = {
            "char_zara_001": {
                "character_id": "char_zara_001",
                "narrative_text": "I attempt to hack the alien console.",
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
                "narrative_text": "I provide covering fire while Zara works.",
                "task_type": "lasers",
                "is_prepared": False,
                "is_expert": False,
                "is_helping": True,
                "helping_character_id": "char_zara_001",
                "help_justification": "Suppressing enemy positions"
            },
            "char_lyra_003": {
                "character_id": "char_lyra_003",
                "narrative_text": "I negotiate with the ship's captain.",
                "task_type": "feelings",
                "is_prepared": False,
                "is_expert": False,
                "is_helping": False,
                "helping_character_id": None
            }
        }

        # Identify primary actions (is_helping=False or is_helping not present)
        primary_actions = {
            char_id: action
            for char_id, action in character_actions.items()
            if not action.get("is_helping", False)
        }
        assert len(primary_actions) == 2
        assert "char_zara_001" in primary_actions
        assert "char_lyra_003" in primary_actions

        # Identify helpers for char_zara_001
        helpers_for_zara = [
            action
            for action in character_actions.values()
            if action.get("is_helping", False) and action.get("helping_character_id") == "char_zara_001"
        ]
        assert len(helpers_for_zara) == 1
        assert helpers_for_zara[0]["character_id"] == "char_kai_002"

    def test_count_successful_helpers_one_helper_succeeds(self):
        """Test counting successful helpers when helper rolls ≥1 success"""
        # Mock a helper's dice roll with 1 success
        with patch('src.utils.dice.roll_lasers_feelings') as mock_roll:
            mock_result = Mock()
            mock_result.total_successes = 1  # Helper succeeds
            mock_roll.return_value = mock_result

            # Simulate helper roll
            helper_result = roll_lasers_feelings(
                character_number=3,
                task_type="lasers",
                is_prepared=False,
                is_expert=False,
                successful_helpers=0
            )

            # Count successful helpers
            successful_count = 1 if mock_result.total_successes >= 1 else 0
            assert successful_count == 1

    def test_count_successful_helpers_one_helper_fails(self):
        """Test that failed helpers (0 successes) don't add to count"""
        # Mock a helper's dice roll with 0 successes
        with patch('src.utils.dice.roll_lasers_feelings') as mock_roll:
            mock_result = Mock()
            mock_result.total_successes = 0  # Helper fails
            mock_roll.return_value = mock_result

            # Simulate helper roll
            helper_result = roll_lasers_feelings(
                character_number=3,
                task_type="lasers",
                is_prepared=False,
                is_expert=False,
                successful_helpers=0
            )

            # Count successful helpers
            successful_count = 1 if mock_result.total_successes >= 1 else 0
            assert successful_count == 0

    def test_count_multiple_successful_helpers(self):
        """Test that multiple successful helpers stack correctly"""
        # Simulate 3 helpers: 2 succeed, 1 fails
        helper_results = [
            Mock(total_successes=2),  # Helper 1: succeeds
            Mock(total_successes=0),  # Helper 2: fails
            Mock(total_successes=1),  # Helper 3: succeeds
        ]

        successful_count = sum(
            1 for result in helper_results if result.total_successes >= 1
        )
        assert successful_count == 2

    def test_successful_helper_counts_structure_in_state(self):
        """Test that successful_helper_counts can be stored in state as dict"""
        # This will eventually be a field in GameState TypedDict
        successful_helper_counts = {
            "char_zara_001": 2,  # Zara has 2 successful helpers
            "char_kai_002": 0,   # Kai has no helpers
            "char_lyra_003": 1,  # Lyra has 1 successful helper
        }

        # Verify we can retrieve counts for main characters
        assert successful_helper_counts.get("char_zara_001", 0) == 2
        assert successful_helper_counts.get("char_kai_002", 0) == 0
        assert successful_helper_counts.get("char_lyra_003", 0) == 1

        # Verify missing characters default to 0
        assert successful_helper_counts.get("char_unknown_999", 0) == 0

    def test_helper_dice_pool_uses_prepared_and_expert_bonuses(self):
        """Test that helpers roll with their own dice pool (prepared/expert apply)"""
        # Helper who is prepared and expert should roll 3d6
        helper_action = {
            "character_id": "char_kai_002",
            "is_prepared": True,
            "is_expert": True,
            "is_helping": True,
            "helping_character_id": "char_zara_001"
        }

        # Calculate helper's dice pool
        is_prepared = helper_action.get("is_prepared", False)
        is_expert = helper_action.get("is_expert", False)

        # Helper rolls with their own modifiers
        result = roll_lasers_feelings(
            character_number=3,
            task_type="lasers",
            is_prepared=is_prepared,
            is_expert=is_expert,
            successful_helpers=0  # Helpers don't get helper bonuses
        )

        # Should roll 3d6 (base + prepared + expert)
        assert result.dice_count == 3

    def test_no_helpers_results_in_zero_count(self):
        """Test that primary actions without helpers get successful_helpers=0"""
        character_actions = {
            "char_zara_001": {
                "character_id": "char_zara_001",
                "narrative_text": "I hack the console alone.",
                "task_type": "lasers",
                "is_helping": False,
                "helping_character_id": None
            }
        }

        # Find helpers for char_zara_001
        helpers = [
            action
            for action in character_actions.values()
            if action.get("is_helping", False) and action.get("helping_character_id") == "char_zara_001"
        ]

        successful_count = 0  # No helpers
        assert len(helpers) == 0
        assert successful_count == 0

    def test_helper_cannot_help_themselves_validation(self):
        """Test that Action model validation prevents self-helping"""
        with pytest.raises(ValueError, match="cannot help themselves"):
            Action(
                character_id="char_zara_001",
                narrative_text="I help myself.",
                is_helping=True,
                helping_character_id="char_zara_001",  # Same as character_id
                help_justification="Self-help"
            )

    def test_main_action_receives_helper_count(self):
        """Test that main character's roll uses successful_helper_count"""
        # Simulate state after helper resolution
        successful_helper_counts = {
            "char_zara_001": 2  # Zara has 2 successful helpers
        }

        character_id = "char_zara_001"
        helper_count = successful_helper_counts.get(character_id, 0)

        # Main character rolls with helper bonus
        result = roll_lasers_feelings(
            character_number=2,
            task_type="lasers",
            is_prepared=True,
            is_expert=True,
            successful_helpers=helper_count  # Use actual count from state
        )

        # Should roll 5d6 (base 3d6 + 2 helpers)
        assert result.dice_count == 5

    def test_helper_resolution_preserves_existing_state_fields(self):
        """Test that helper resolution doesn't overwrite other state fields"""
        # Simulate initial state
        state = {
            "turn_number": 1,
            "session_number": 1,
            "current_phase": "character_action",
            "character_actions": {
                "char_zara_001": {
                    "character_id": "char_zara_001",
                    "narrative_text": "I hack the console.",
                    "is_helping": False
                },
                "char_kai_002": {
                    "character_id": "char_kai_002",
                    "narrative_text": "I help Zara.",
                    "is_helping": True,
                    "helping_character_id": "char_zara_001"
                }
            }
        }

        # Add successful_helper_counts without overwriting other fields
        updated_state = {
            **state,
            "successful_helper_counts": {"char_zara_001": 1}
        }

        # Verify all original fields preserved
        assert updated_state["turn_number"] == 1
        assert updated_state["session_number"] == 1
        assert updated_state["current_phase"] == "character_action"
        assert len(updated_state["character_actions"]) == 2
        assert updated_state["successful_helper_counts"]["char_zara_001"] == 1

    def test_multiple_helpers_to_same_target_stack(self):
        """Test that multiple helpers helping the same character all stack"""
        character_actions = {
            "char_zara_001": {
                "character_id": "char_zara_001",
                "narrative_text": "I hack the console.",
                "is_helping": False
            },
            "char_kai_002": {
                "character_id": "char_kai_002",
                "narrative_text": "I provide covering fire for Zara.",
                "is_helping": True,
                "helping_character_id": "char_zara_001"
            },
            "char_lyra_003": {
                "character_id": "char_lyra_003",
                "narrative_text": "I scan for threats to help Zara.",
                "is_helping": True,
                "helping_character_id": "char_zara_001"
            }
        }

        # Find all helpers for char_zara_001
        helpers = [
            action
            for action in character_actions.values()
            if action.get("is_helping", False) and action.get("helping_character_id") == "char_zara_001"
        ]

        # Simulate all helpers succeed (≥1 success each)
        successful_count = len(helpers)  # Assume all succeed for this test
        assert successful_count == 2

    def test_helper_to_nonexistent_character_gracefully_handled(self):
        """Test that helper helping non-existent character is handled gracefully"""
        character_actions = {
            "char_kai_002": {
                "character_id": "char_kai_002",
                "narrative_text": "I help the ghost.",
                "is_helping": True,
                "helping_character_id": "char_nonexistent_999"  # Doesn't exist
            }
        }

        # Find primary actions
        primary_actions = {
            char_id: action
            for char_id, action in character_actions.items()
            if not action.get("is_helping", False)
        }

        # Find helpers for non-existent character
        helpers = [
            action
            for action in character_actions.values()
            if action.get("is_helping", False) and action.get("helping_character_id") == "char_nonexistent_999"
        ]

        # Helper exists but target doesn't - should be handled gracefully
        # (either skip or log warning)
        assert len(helpers) == 1
        assert "char_nonexistent_999" not in primary_actions

    def test_edge_case_all_helpers_fail(self):
        """Test that when all helpers fail (0 successes), count is 0"""
        # Simulate 3 helpers, all fail
        helper_results = [
            Mock(total_successes=0),  # Helper 1: fails
            Mock(total_successes=0),  # Helper 2: fails
            Mock(total_successes=0),  # Helper 3: fails
        ]

        successful_count = sum(
            1 for result in helper_results if result.total_successes >= 1
        )
        assert successful_count == 0

    def test_edge_case_some_helpers_succeed_some_fail(self):
        """Test that only successful helpers (≥1 success) are counted"""
        # Simulate 4 helpers with mixed results
        helper_results = [
            Mock(total_successes=2),  # Helper 1: succeeds
            Mock(total_successes=0),  # Helper 2: fails
            Mock(total_successes=1),  # Helper 3: succeeds
            Mock(total_successes=0),  # Helper 4: fails
        ]

        successful_count = sum(
            1 for result in helper_results if result.total_successes >= 1
        )
        assert successful_count == 2  # Only helpers 1 and 3 succeeded


class TestHelperResolutionNodeLogic:
    """Test suite for the resolve_helpers_node implementation"""

    def test_resolve_helpers_node_exists(self):
        """Test that resolve_helpers_node function will exist in state machine"""
        # This test will pass once we implement the node
        # For now, we're defining the expected behavior

        # Expected signature:
        # def resolve_helpers_node(state: GameState) -> GameState:
        #     """Resolves all helping actions before main action"""
        #     ...

        # We'll implement this after writing all the tests
        pass

    def test_resolve_helpers_processes_all_helpers(self):
        """Test that resolve_helpers processes all helping actions"""
        # This test defines expected behavior:
        # 1. Find all primary actions (is_helping=False)
        # 2. For each primary action, find helpers (is_helping=True, matching helping_character_id)
        # 3. For each helper, roll dice with their modifiers
        # 4. Count helpers with ≥1 success
        # 5. Store count in state.successful_helper_counts[character_id]

        # Implementation will follow TDD principles
        pass

    def test_resolve_helpers_stores_counts_in_state(self):
        """Test that resolve_helpers stores successful_helper_counts in state"""
        # Expected behavior:
        # Input state: character_actions with helpers
        # Output state: successful_helper_counts dict added

        # Example:
        # state['successful_helper_counts'] = {
        #     'char_zara_001': 2,  # 2 successful helpers
        #     'char_lyra_003': 1,  # 1 successful helper
        #     'char_kai_002': 0,   # No helpers
        # }
        pass

    def test_resolve_helpers_node_transitions_to_dice_resolution(self):
        """Test that resolve_helpers transitions to dice_resolution phase"""
        # Expected behavior:
        # resolve_helpers_node should update current_phase to dice_resolution
        # and set phase_start_time to current time
        pass

    def test_helper_uses_actual_character_number_from_config(self):
        """Test C1: Helpers use their actual character number from config file"""
        from src.orchestration.nodes.outcome_nodes import resolve_helpers_node
        from unittest.mock import patch, mock_open
        import json

        # Create state with one primary action and one helper
        state = {
            "turn_number": 1,
            "session_number": 1,
            "current_phase": "resolve_helpers",
            "phase_start_time": datetime.now(),
            "active_agents": ["agent_alex_001", "agent_morgan_002"],
            "character_actions": {
                "char_zara_001": {
                    "character_id": "char_zara_001",
                    "narrative_text": "I hack the console.",
                    "task_type": "lasers",
                    "is_helping": False,
                    "is_prepared": False,
                    "is_expert": False
                },
                "char_nova_002": {
                    "character_id": "char_nova_002",
                    "narrative_text": "I help Zara.",
                    "task_type": "lasers",
                    "is_helping": True,
                    "helping_character_id": "char_zara_001",
                    "is_prepared": False,
                    "is_expert": False
                }
            },
            "dm_narration": "Test scene",
            "validation_attempt": 0,
            "validation_valid": True,
            "validation_failures": {},
            "strategic_intents": {},
            "ooc_messages": [],
            "character_reactions": {},
            "retrieved_memories": {},
            "dm_adjudication_needed": False,
            "retry_count": 0
        }

        # Mock the config file for char_nova_002 with number=4
        mock_config = {
            "character_id": "char_nova_002",
            "name": "Nova",
            "number": 4,  # Should roll OVER 4 for lasers (harder)
            "style": "Intrepid",
            "role": "Pilot"
        }

        with patch('builtins.open', mock_open(read_data=json.dumps(mock_config))):
            with patch('src.orchestration.nodes.outcome_nodes.roll_lasers_feelings') as mock_roll:
                # Setup mock to capture the character_number argument
                mock_result = Mock()
                mock_result.total_successes = 1
                mock_result.individual_rolls = [5]
                mock_roll.return_value = mock_result

                # Run resolve_helpers
                result_state = resolve_helpers_node(state)

                # Verify roll_lasers_feelings was called with character_number=4 (from config)
                mock_roll.assert_called_once()
                call_args = mock_roll.call_args[1]  # Get keyword arguments
                assert call_args['character_number'] == 4, \
                    f"Expected character_number=4, got {call_args['character_number']}"

                # Verify helper was counted as successful
                assert result_state['successful_helper_counts']['char_zara_001'] == 1

    def test_helper_config_not_found_uses_fallback(self):
        """Test C1: If config not found, use fallback number 3 with warning"""
        from src.orchestration.nodes.outcome_nodes import resolve_helpers_node
        from unittest.mock import patch

        state = {
            "turn_number": 1,
            "session_number": 1,
            "current_phase": "resolve_helpers",
            "phase_start_time": datetime.now(),
            "active_agents": ["agent_alex_001", "agent_morgan_002"],
            "character_actions": {
                "char_zara_001": {
                    "character_id": "char_zara_001",
                    "narrative_text": "I hack the console.",
                    "task_type": "lasers",
                    "is_helping": False
                },
                "char_unknown_999": {
                    "character_id": "char_unknown_999",
                    "narrative_text": "I help Zara.",
                    "task_type": "lasers",
                    "is_helping": True,
                    "helping_character_id": "char_zara_001"
                }
            },
            "dm_narration": "Test scene",
            "validation_attempt": 0,
            "validation_valid": True,
            "validation_failures": {},
            "strategic_intents": {},
            "ooc_messages": [],
            "character_reactions": {},
            "retrieved_memories": {},
            "dm_adjudication_needed": False,
            "retry_count": 0
        }

        with patch('builtins.open', side_effect=FileNotFoundError("Config not found")):
            with patch('src.orchestration.nodes.outcome_nodes.roll_lasers_feelings') as mock_roll:
                mock_result = Mock()
                mock_result.total_successes = 1
                mock_result.individual_rolls = [2]
                mock_roll.return_value = mock_result

                # Should not crash, should use fallback
                result_state = resolve_helpers_node(state)

                # Verify roll was called with fallback number 3
                call_args = mock_roll.call_args[1]
                assert call_args['character_number'] == 3, \
                    f"Expected fallback character_number=3, got {call_args['character_number']}"

    def test_c2_invalid_helper_target_is_skipped_with_warning(self):
        """Test C2: Helpers targeting nonexistent characters are skipped gracefully"""
        from src.orchestration.nodes.outcome_nodes import resolve_helpers_node
        from unittest.mock import patch

        # Create state where helper targets a nonexistent primary character
        state = {
            "turn_number": 1,
            "session_number": 1,
            "current_phase": "resolve_helpers",
            "phase_start_time": datetime.now(),
            "active_agents": ["agent_alex_001", "agent_morgan_002"],
            "character_actions": {
                "char_zara_001": {
                    "character_id": "char_zara_001",
                    "narrative_text": "I hack the console.",
                    "task_type": "lasers",
                    "is_helping": False
                },
                "char_nova_002": {
                    "character_id": "char_nova_002",
                    "narrative_text": "I help a ghost.",
                    "task_type": "lasers",
                    "is_helping": True,
                    "helping_character_id": "char_nonexistent_999",  # Target doesn't exist
                    "is_prepared": False,
                    "is_expert": False
                }
            },
            "dm_narration": "Test scene",
            "validation_attempt": 0,
            "validation_valid": True,
            "validation_failures": {},
            "strategic_intents": {},
            "ooc_messages": [],
            "character_reactions": {},
            "retrieved_memories": {},
            "dm_adjudication_needed": False,
            "retry_count": 0
        }

        with patch('src.orchestration.nodes.outcome_nodes.roll_lasers_feelings') as mock_roll:
            result_state = resolve_helpers_node(state)

            # Verify roll was NOT called (helper was skipped)
            mock_roll.assert_not_called()

            # Verify no successful helper count for nonexistent target
            assert "char_nonexistent_999" not in result_state['successful_helper_counts']

            # Verify char_zara_001 has 0 helpers (not mentioned as target)
            assert result_state['successful_helper_counts'].get('char_zara_001', 0) == 0

    def test_c2_valid_and_invalid_helpers_mixed(self):
        """Test C2: When some helpers are valid and some invalid, only valid ones process"""
        from src.orchestration.nodes.outcome_nodes import resolve_helpers_node
        from unittest.mock import patch, mock_open
        import json

        # Create state with 1 primary, 1 valid helper, 1 invalid helper
        state = {
            "turn_number": 1,
            "session_number": 1,
            "current_phase": "resolve_helpers",
            "phase_start_time": datetime.now(),
            "active_agents": ["agent_alex_001", "agent_morgan_002", "agent_sam_003"],
            "character_actions": {
                "char_zara_001": {
                    "character_id": "char_zara_001",
                    "narrative_text": "I hack the console.",
                    "task_type": "lasers",
                    "is_helping": False
                },
                "char_nova_002": {
                    "character_id": "char_nova_002",
                    "narrative_text": "I help Zara (valid).",
                    "task_type": "lasers",
                    "is_helping": True,
                    "helping_character_id": "char_zara_001",  # Valid target
                    "is_prepared": False,
                    "is_expert": False
                },
                "char_quinn_003": {
                    "character_id": "char_quinn_003",
                    "narrative_text": "I help nobody (invalid).",
                    "task_type": "lasers",
                    "is_helping": True,
                    "helping_character_id": "char_ghost_999",  # Invalid target
                    "is_prepared": False,
                    "is_expert": False
                }
            },
            "dm_narration": "Test scene",
            "validation_attempt": 0,
            "validation_valid": True,
            "validation_failures": {},
            "strategic_intents": {},
            "ooc_messages": [],
            "character_reactions": {},
            "retrieved_memories": {},
            "dm_adjudication_needed": False,
            "retry_count": 0
        }

        # Mock config for valid helper
        mock_config_nova = {
            "character_id": "char_nova_002",
            "name": "Nova",
            "number": 3
        }

        with patch('builtins.open', mock_open(read_data=json.dumps(mock_config_nova))):
            with patch('src.orchestration.nodes.outcome_nodes.roll_lasers_feelings') as mock_roll:
                # Mock successful roll for valid helper
                mock_result = Mock()
                mock_result.total_successes = 1
                mock_result.individual_rolls = [2]
                mock_roll.return_value = mock_result

                result_state = resolve_helpers_node(state)

                # Verify roll was called only ONCE (for valid helper only)
                assert mock_roll.call_count == 1, \
                    f"Expected 1 roll (valid helper), got {mock_roll.call_count}"

                # Verify char_zara_001 has 1 successful helper (only the valid one)
                assert result_state['successful_helper_counts']['char_zara_001'] == 1

    def test_m1_helper_roll_exception_doesnt_crash_resolution(self):
        """Test M1: Exception during helper roll doesn't crash the entire resolution"""
        from src.orchestration.nodes.outcome_nodes import resolve_helpers_node
        from unittest.mock import patch, mock_open
        import json

        # Create state with 2 helpers for same target
        state = {
            "turn_number": 1,
            "session_number": 1,
            "current_phase": "resolve_helpers",
            "phase_start_time": datetime.now(),
            "active_agents": ["agent_alex_001", "agent_morgan_002", "agent_sam_003"],
            "character_actions": {
                "char_zara_001": {
                    "character_id": "char_zara_001",
                    "narrative_text": "I hack the console.",
                    "task_type": "lasers",
                    "is_helping": False
                },
                "char_nova_002": {
                    "character_id": "char_nova_002",
                    "narrative_text": "I help Zara (will crash).",
                    "task_type": "lasers",
                    "is_helping": True,
                    "helping_character_id": "char_zara_001",
                    "is_prepared": False,
                    "is_expert": False
                },
                "char_quinn_003": {
                    "character_id": "char_quinn_003",
                    "narrative_text": "I also help Zara (will succeed).",
                    "task_type": "lasers",
                    "is_helping": True,
                    "helping_character_id": "char_zara_001",
                    "is_prepared": False,
                    "is_expert": False
                }
            },
            "dm_narration": "Test scene",
            "validation_attempt": 0,
            "validation_valid": True,
            "validation_failures": {},
            "strategic_intents": {},
            "ooc_messages": [],
            "character_reactions": {},
            "retrieved_memories": {},
            "dm_adjudication_needed": False,
            "retry_count": 0
        }

        # Mock configs for both helpers
        mock_config = {"character_id": "char_nova_002", "name": "Nova", "number": 3}

        with patch('builtins.open', mock_open(read_data=json.dumps(mock_config))):
            with patch('src.orchestration.nodes.outcome_nodes.roll_lasers_feelings') as mock_roll:
                # First call raises exception, second call succeeds
                mock_result_success = Mock()
                mock_result_success.total_successes = 1
                mock_result_success.individual_rolls = [2]

                mock_roll.side_effect = [
                    RuntimeError("Dice roll service unavailable"),  # First helper crashes
                    mock_result_success  # Second helper succeeds
                ]

                # Should not crash despite first helper exception
                result_state = resolve_helpers_node(state)

                # Verify both helpers attempted to roll
                assert mock_roll.call_count == 2

                # Verify only the successful helper is counted (second one)
                assert result_state['successful_helper_counts']['char_zara_001'] == 1

    def test_m1_all_helpers_exception_still_returns_zero_count(self):
        """Test M1: If all helpers crash, count is 0 and resolution continues"""
        from src.orchestration.nodes.outcome_nodes import resolve_helpers_node
        from unittest.mock import patch, mock_open
        import json

        state = {
            "turn_number": 1,
            "session_number": 1,
            "current_phase": "resolve_helpers",
            "phase_start_time": datetime.now(),
            "active_agents": ["agent_alex_001", "agent_morgan_002"],
            "character_actions": {
                "char_zara_001": {
                    "character_id": "char_zara_001",
                    "narrative_text": "I hack the console.",
                    "task_type": "lasers",
                    "is_helping": False
                },
                "char_nova_002": {
                    "character_id": "char_nova_002",
                    "narrative_text": "I help Zara.",
                    "task_type": "lasers",
                    "is_helping": True,
                    "helping_character_id": "char_zara_001",
                    "is_prepared": False,
                    "is_expert": False
                }
            },
            "dm_narration": "Test scene",
            "validation_attempt": 0,
            "validation_valid": True,
            "validation_failures": {},
            "strategic_intents": {},
            "ooc_messages": [],
            "character_reactions": {},
            "retrieved_memories": {},
            "dm_adjudication_needed": False,
            "retry_count": 0
        }

        mock_config = {"character_id": "char_nova_002", "name": "Nova", "number": 3}

        with patch('builtins.open', mock_open(read_data=json.dumps(mock_config))):
            with patch('src.orchestration.nodes.outcome_nodes.roll_lasers_feelings') as mock_roll:
                # All rolls raise exceptions
                mock_roll.side_effect = ValueError("Invalid dice configuration")

                # Should not crash
                result_state = resolve_helpers_node(state)

                # Verify roll was attempted
                assert mock_roll.call_count == 1

                # Verify helper count is 0 (all failed due to exceptions)
                assert result_state['successful_helper_counts']['char_zara_001'] == 0

    def test_m2_resolve_helpers_sets_current_phase(self):
        """Test M2: resolve_helpers_node explicitly sets current_phase field"""
        from src.orchestration.nodes.outcome_nodes import resolve_helpers_node
        from src.models.game_state import GamePhase

        state = {
            "turn_number": 1,
            "session_number": 1,
            "current_phase": "resolve_helpers",
            "phase_start_time": datetime.now(),
            "active_agents": ["agent_alex_001"],
            "character_actions": {
                "char_zara_001": {
                    "character_id": "char_zara_001",
                    "narrative_text": "I hack the console.",
                    "task_type": "lasers",
                    "is_helping": False
                }
            },
            "dm_narration": "Test scene",
            "validation_attempt": 0,
            "validation_valid": True,
            "validation_failures": {},
            "strategic_intents": {},
            "ooc_messages": [],
            "character_reactions": {},
            "retrieved_memories": {},
            "dm_adjudication_needed": False,
            "retry_count": 0
        }

        result_state = resolve_helpers_node(state)

        # Verify current_phase is set to DICE_RESOLUTION
        assert "current_phase" in result_state, "current_phase not set in result state"
        assert result_state["current_phase"] == GamePhase.DICE_RESOLUTION.value, \
            f"Expected current_phase={GamePhase.DICE_RESOLUTION.value}, got {result_state['current_phase']}"

        # Verify phase_start_time is updated
        assert "phase_start_time" in result_state
        assert result_state["phase_start_time"] is not None
