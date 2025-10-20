# ABOUTME: Unit tests verifying is_helping parameter flows correctly through dice resolution.
# ABOUTME: Tests that character actions with is_helping=True receive bonus dice in state machine.

import pytest
from datetime import datetime

from src.utils.dice import roll_lasers_feelings
from src.models.agent_actions import Action


class TestDiceResolutionHelpingParameter:
    """Test suite verifying is_helping parameter is properly extracted and used"""

    def test_roll_lasers_feelings_accepts_is_helping_parameter(self):
        """Test that roll_lasers_feelings function accepts is_helping parameter"""
        # This verifies the function signature supports is_helping
        result = roll_lasers_feelings(
            character_number=3,
            task_type="lasers",
            is_prepared=False,
            is_expert=False,
            is_helping=True  # Should be accepted
        )

        # Should roll with bonus die (2d6 instead of 1d6)
        assert result.is_helping is True
        assert result.dice_count == 2  # Base (1) + helping (1)

    def test_roll_lasers_feelings_without_is_helping_defaults_false(self):
        """Test that is_helping defaults to False when not provided"""
        result = roll_lasers_feelings(
            character_number=3,
            task_type="lasers"
            # is_helping not provided, should default to False
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

    def test_is_helping_bonus_stacks_with_prepared_and_expert(self):
        """Test that is_helping bonus stacks with other bonuses (max 3d6)"""
        result = roll_lasers_feelings(
            character_number=3,
            task_type="lasers",
            is_prepared=True,
            is_expert=True,
            is_helping=True
        )

        # All three bonuses should stack to max of 3d6
        assert result.is_helping is True
        assert result.is_prepared is True
        assert result.is_expert is True
        assert result.dice_count == 3  # Capped at 3 dice

    def test_character_action_dict_extraction_pattern(self):
        """Test the pattern used in dice_resolution_node to extract is_helping"""
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
        is_helping = character_action_dict.get("is_helping", False)

        # Verify extraction works correctly
        assert task_type == "lasers"
        assert is_prepared is True
        assert is_expert is False
        assert is_helping is True

        # Verify these can be passed to roll function
        result = roll_lasers_feelings(
            character_number=2,
            task_type=task_type,
            is_prepared=is_prepared,
            is_expert=is_expert,
            is_helping=is_helping
        )

        assert result.dice_count == 3  # prepared (1) + helping (1) + base (1)

    def test_is_helping_false_does_not_add_bonus_die(self):
        """Test that is_helping=False does not add bonus die"""
        result = roll_lasers_feelings(
            character_number=3,
            task_type="lasers",
            is_helping=False
        )

        assert result.is_helping is False
        assert result.dice_count == 1  # Base only, no bonus

    def test_dice_result_includes_is_helping_in_result_model(self):
        """Test that LasersFeelingRollResult includes is_helping field"""
        result = roll_lasers_feelings(
            character_number=4,
            task_type="feelings",
            is_helping=True
        )

        # Verify result model has is_helping field
        assert hasattr(result, "is_helping")
        assert result.is_helping is True

        # Verify it can be converted to dict for state storage
        result_dict = {
            "character_number": result.character_number,
            "task_type": result.task_type,
            "is_prepared": result.is_prepared,
            "is_expert": result.is_expert,
            "is_helping": result.is_helping,  # Should be present
            "individual_rolls": result.individual_rolls,
            "die_successes": result.die_successes,
            "laser_feelings_indices": result.laser_feelings_indices,
            "total_successes": result.total_successes,
            "outcome": result.outcome.value,
            "timestamp": result.timestamp
        }

        assert result_dict["is_helping"] is True
