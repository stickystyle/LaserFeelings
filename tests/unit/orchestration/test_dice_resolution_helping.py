# ABOUTME: Unit tests verifying successful_helpers parameter flows correctly through dice resolution.
# ABOUTME: Tests that character actions with successful helpers receive bonus dice in state machine.

import pytest
from datetime import datetime

from src.utils.dice import roll_lasers_feelings
from src.models.agent_actions import Action


class TestDiceResolutionHelpingParameter:
    """Test suite verifying successful_helpers parameter is properly used"""

    def test_roll_lasers_feelings_accepts_successful_helpers_parameter(self):
        """Test that roll_lasers_feelings function accepts successful_helpers parameter"""
        # This verifies the function signature supports successful_helpers
        result = roll_lasers_feelings(
            character_number=3,
            task_type="lasers",
            is_prepared=False,
            is_expert=False,
            successful_helpers=1  # One successful helper
        )

        # Should roll with bonus die (2d6 instead of 1d6)
        assert result.is_helping is False  # Deprecated field kept for model compatibility
        assert result.dice_count == 2  # Base (1) + 1 helper (1)

    def test_roll_lasers_feelings_without_successful_helpers_defaults_zero(self):
        """Test that successful_helpers defaults to 0 when not provided"""
        result = roll_lasers_feelings(
            character_number=3,
            task_type="lasers"
            # successful_helpers not provided, should default to 0
        )

        assert result.is_helping is False
        assert result.dice_count == 1  # Base only

    def test_action_model_contains_is_helping_field(self):
        """Test that Action model has is_helping field that can be extracted"""
        action = Action(
            character_id="char_helper_001",
            narrative_text="I provide covering fire for Kai.",
            task_type="lasers",
            is_helping=True,
            helping_character_id="char_kai_002",
            help_justification="I'm suppressing enemy positions"
        )

        # Verify field exists and can be accessed via dict conversion
        action_dict = action.model_dump()
        assert "is_helping" in action_dict
        assert action_dict["is_helping"] is True
        assert action_dict.get("is_helping", False) is True

    def test_successful_helpers_stack_with_prepared_and_expert(self):
        """Test that successful_helpers add dice beyond prepared and expert cap"""
        result = roll_lasers_feelings(
            character_number=3,
            task_type="lasers",
            is_prepared=True,
            is_expert=True,
            successful_helpers=1
        )

        # Base modifiers cap at 3d6, then helpers add beyond that
        assert result.is_helping is False  # Deprecated field
        assert result.is_prepared is True
        assert result.is_expert is True
        assert result.dice_count == 4  # Base 3d6 + 1 helper = 4d6

    def test_character_action_dict_extraction_pattern(self):
        """Test the pattern used in dice_resolution_node with successful_helpers"""
        # Simulate what happens in state_machine.py's dice_resolution_node
        action = Action(
            character_id="char_zara_001",
            narrative_text="I assist Lyra with the alien console.",
            task_type="lasers",
            is_prepared=True,
            prepared_justification="I brought my advanced toolkit",
            is_helping=True,
            helping_character_id="char_lyra_003",
            help_justification="I'm pointing out the correct symbols"
        )

        # Convert to dict (simulating character_actions storage)
        character_action_dict = action.model_dump()

        # Extract using the same pattern as dice_resolution_node
        task_type = character_action_dict.get("task_type", "lasers")
        is_prepared = character_action_dict.get("is_prepared", False)
        is_expert = character_action_dict.get("is_expert", False)

        # Verify extraction works correctly
        assert task_type == "lasers"
        assert is_prepared is True
        assert is_expert is False

        # Verify these can be passed to roll function with successful_helpers
        # For now, pass 0 helpers until Phase 1 Issue #2 implements helper resolution
        result = roll_lasers_feelings(
            character_number=2,
            task_type=task_type,
            is_prepared=is_prepared,
            is_expert=is_expert,
            successful_helpers=0  # Will be populated by helper resolution in Phase 1 Issue #2
        )

        assert result.dice_count == 2  # prepared (1) + base (1), no helpers yet

    def test_successful_helpers_zero_does_not_add_bonus_dice(self):
        """Test that successful_helpers=0 does not add bonus dice"""
        result = roll_lasers_feelings(
            character_number=3,
            task_type="lasers",
            successful_helpers=0
        )

        assert result.is_helping is False
        assert result.dice_count == 1  # Base only, no bonus

    def test_dice_result_includes_is_helping_in_result_model(self):
        """Test that LasersFeelingRollResult includes is_helping field (deprecated)"""
        result = roll_lasers_feelings(
            character_number=4,
            task_type="feelings",
            successful_helpers=1
        )

        # Verify result model has is_helping field (kept for backward compatibility)
        assert hasattr(result, "is_helping")
        assert result.is_helping is False  # Always False now, deprecated

        # Verify it can be converted to dict for state storage
        result_dict = {
            "character_number": result.character_number,
            "task_type": result.task_type,
            "is_prepared": result.is_prepared,
            "is_expert": result.is_expert,
            "is_helping": result.is_helping,  # Deprecated but still present
            "individual_rolls": result.individual_rolls,
            "die_successes": result.die_successes,
            "laser_feelings_indices": result.laser_feelings_indices,
            "total_successes": result.total_successes,
            "outcome": result.outcome.value,
            "timestamp": result.timestamp
        }

        assert result_dict["is_helping"] is False  # Deprecated field
