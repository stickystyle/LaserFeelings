# ABOUTME: Unit tests for dice rolling utilities
# ABOUTME: Validates D&D 5e notation parsing and Lasers & Feelings mechanics

import pytest
from datetime import datetime

from src.utils.dice import (
    parse_dice_notation,
    roll_dice,
    roll_d6,
    validate_lasers_feelings_roll,
    VALID_DICE_SIDES
)
from src.models.messages import DiceRoll


class TestParseDiceNotation:
    """Test suite for parse_dice_notation function"""

    def test_standard_notation_with_modifier(self):
        """Test standard dice notation with positive modifier"""
        assert parse_dice_notation("2d6+3") == (2, 6, 3)
        assert parse_dice_notation("3d8+5") == (3, 8, 5)
        assert parse_dice_notation("1d20+10") == (1, 20, 10)

    def test_standard_notation_without_modifier(self):
        """Test standard dice notation without modifier"""
        assert parse_dice_notation("1d20") == (1, 20, 0)
        assert parse_dice_notation("2d6") == (2, 6, 0)
        assert parse_dice_notation("4d10") == (4, 10, 0)

    def test_implicit_single_die(self):
        """Test notation with implicit 1 die (e.g., 'd6')"""
        assert parse_dice_notation("d6") == (1, 6, 0)
        assert parse_dice_notation("d20") == (1, 20, 0)
        assert parse_dice_notation("d100") == (1, 100, 0)

    def test_negative_modifier(self):
        """Test notation with negative modifier"""
        assert parse_dice_notation("3d8-2") == (3, 8, -2)
        assert parse_dice_notation("2d6-1") == (2, 6, -1)
        assert parse_dice_notation("1d20-5") == (1, 20, -5)

    def test_zero_modifier(self):
        """Test notation with explicit zero modifier"""
        assert parse_dice_notation("2d6+0") == (2, 6, 0)

    def test_case_insensitivity(self):
        """Test that notation is case-insensitive"""
        assert parse_dice_notation("2D6+3") == (2, 6, 3)
        assert parse_dice_notation("D20") == (1, 20, 0)
        assert parse_dice_notation("3D8-2") == (3, 8, -2)

    def test_whitespace_handling(self):
        """Test that leading/trailing whitespace is handled"""
        assert parse_dice_notation("  2d6+3  ") == (2, 6, 3)
        assert parse_dice_notation("\t1d20\n") == (1, 20, 0)

    def test_all_valid_dice_sizes(self):
        """Test parsing with all valid D&D dice sizes"""
        for sides in VALID_DICE_SIDES:
            assert parse_dice_notation(f"1d{sides}") == (1, sides, 0)

    def test_max_dice_count(self):
        """Test maximum allowed dice count (100)"""
        assert parse_dice_notation("100d6") == (100, 6, 0)

    def test_invalid_separator_raises_error(self):
        """Test that invalid separator (not 'd') raises ValueError"""
        with pytest.raises(ValueError, match="Invalid dice notation"):
            parse_dice_notation("2x6")
        with pytest.raises(ValueError, match="Invalid dice notation"):
            parse_dice_notation("2*6")
        with pytest.raises(ValueError, match="Invalid dice notation"):
            parse_dice_notation("2/6")

    def test_invalid_die_size_raises_error(self):
        """Test that unsupported die sizes raise ValueError"""
        with pytest.raises(ValueError, match="Invalid die size"):
            parse_dice_notation("2d7")  # Not a standard D&D die
        with pytest.raises(ValueError, match="Invalid die size"):
            parse_dice_notation("1d3")
        with pytest.raises(ValueError, match="Invalid die size"):
            parse_dice_notation("2d15")

    def test_zero_dice_raises_error(self):
        """Test that zero dice count raises ValueError"""
        with pytest.raises(ValueError, match="Number of dice must be at least 1"):
            parse_dice_notation("0d6")

    def test_negative_dice_raises_error(self):
        """Test that negative dice count raises ValueError"""
        with pytest.raises(ValueError, match="Invalid dice notation"):
            parse_dice_notation("-1d6")

    def test_too_many_dice_raises_error(self):
        """Test that more than 100 dice raises ValueError"""
        with pytest.raises(ValueError, match="Number of dice cannot exceed 100"):
            parse_dice_notation("101d6")
        with pytest.raises(ValueError, match="Number of dice cannot exceed 100"):
            parse_dice_notation("1000d6")

    def test_malformed_notation_raises_error(self):
        """Test that malformed notation raises ValueError"""
        with pytest.raises(ValueError, match="Invalid dice notation"):
            parse_dice_notation("2d")  # Missing die size
        with pytest.raises(ValueError, match="Invalid dice notation"):
            parse_dice_notation("d")  # Missing die size
        with pytest.raises(ValueError, match="Invalid dice notation"):
            parse_dice_notation("2")  # No 'd'
        with pytest.raises(ValueError, match="Invalid dice notation"):
            parse_dice_notation("")  # Empty string
        with pytest.raises(ValueError, match="Invalid dice notation"):
            parse_dice_notation("hello")  # Not a notation

    def test_invalid_modifier_format_raises_error(self):
        """Test that invalid modifier formats raise ValueError"""
        with pytest.raises(ValueError, match="Invalid dice notation"):
            parse_dice_notation("2d6+")  # Missing modifier value
        with pytest.raises(ValueError, match="Invalid dice notation"):
            parse_dice_notation("2d6++3")  # Double operator


class TestRollDice:
    """Test suite for roll_dice function"""

    def test_returns_dice_roll_model(self):
        """Test that roll_dice returns DiceRoll instance"""
        result = roll_dice("2d6+3")
        assert isinstance(result, DiceRoll)

    def test_notation_field_populated(self):
        """Test that notation field is correctly populated"""
        result = roll_dice("2d6+3")
        assert result.notation == "2d6+3"

        result = roll_dice("  1d20  ")
        assert result.notation == "1d20"  # Should strip whitespace

    def test_dice_count_field_populated(self):
        """Test that dice_count field is correctly populated"""
        result = roll_dice("2d6+3")
        assert result.dice_count == 2

        result = roll_dice("d20")
        assert result.dice_count == 1

    def test_dice_sides_field_populated(self):
        """Test that dice_sides field is correctly populated"""
        result = roll_dice("2d6+3")
        assert result.dice_sides == 6

        result = roll_dice("3d8")
        assert result.dice_sides == 8

    def test_modifier_field_populated(self):
        """Test that modifier field is correctly populated"""
        result = roll_dice("2d6+3")
        assert result.modifier == 3

        result = roll_dice("3d8-2")
        assert result.modifier == -2

        result = roll_dice("1d20")
        assert result.modifier == 0

    def test_individual_rolls_correct_length(self):
        """Test that individual_rolls has correct number of elements"""
        result = roll_dice("2d6+3")
        assert len(result.individual_rolls) == 2

        result = roll_dice("5d8")
        assert len(result.individual_rolls) == 5

    def test_individual_rolls_within_range(self):
        """Test that individual rolls are within valid range"""
        # Test multiple rolls to ensure consistency
        for _ in range(10):
            result = roll_dice("3d6")
            for roll in result.individual_rolls:
                assert 1 <= roll <= 6, f"Roll {roll} outside range 1-6"

        for _ in range(10):
            result = roll_dice("2d20")
            for roll in result.individual_rolls:
                assert 1 <= roll <= 20, f"Roll {roll} outside range 1-20"

    def test_total_calculation_correct(self):
        """Test that total is correctly calculated as sum(rolls) + modifier"""
        # Since rolls are random, we verify the calculation is correct
        result = roll_dice("2d6+3")
        expected_total = sum(result.individual_rolls) + 3
        assert result.total == expected_total

        result = roll_dice("3d8-2")
        expected_total = sum(result.individual_rolls) - 2
        assert result.total == expected_total

        result = roll_dice("1d20")
        expected_total = sum(result.individual_rolls)
        assert result.total == expected_total

    def test_rolls_sum_property(self):
        """Test the rolls_sum property returns sum before modifier"""
        result = roll_dice("2d6+3")
        assert result.rolls_sum == sum(result.individual_rolls)
        assert result.rolls_sum == result.total - result.modifier

    def test_timestamp_populated(self):
        """Test that timestamp is present and recent"""
        before = datetime.now()
        result = roll_dice("2d6+3")
        after = datetime.now()

        assert result.timestamp is not None
        assert before <= result.timestamp <= after

    def test_dice_rolls_are_random(self):
        """Test that rolls produce different results (statistical test)"""
        # Roll 20 times and check we get at least some variation
        results = [roll_dice("1d20").total for _ in range(20)]
        unique_results = set(results)

        # With 20 rolls of d20, we should get at least 5 different values
        # (probability of getting 4 or fewer unique values is astronomically low)
        assert len(unique_results) >= 5, "Dice rolls appear non-random"

    def test_invalid_notation_raises_error(self):
        """Test that invalid notation raises ValueError"""
        with pytest.raises(ValueError):
            roll_dice("2x6")
        with pytest.raises(ValueError):
            roll_dice("invalid")
        with pytest.raises(ValueError):
            roll_dice("")

    def test_multiple_dice_types(self):
        """Test rolling different dice types"""
        for sides in [4, 6, 8, 10, 12, 20, 100]:
            result = roll_dice(f"1d{sides}")
            assert result.dice_sides == sides
            assert 1 <= result.individual_rolls[0] <= sides

    def test_edge_case_max_dice(self):
        """Test rolling maximum allowed dice (100d6)"""
        result = roll_dice("100d6")
        assert result.dice_count == 100
        assert len(result.individual_rolls) == 100
        # Total should be between 100 (all 1s) and 600 (all 6s)
        assert 100 <= result.total <= 600


class TestRollD6:
    """Test suite for roll_d6 convenience function"""

    def test_returns_integer(self):
        """Test that roll_d6 returns an integer"""
        result = roll_d6()
        assert isinstance(result, int)

    def test_result_in_valid_range(self):
        """Test that result is between 1 and 6 inclusive"""
        for _ in range(20):
            result = roll_d6()
            assert 1 <= result <= 6, f"Roll {result} outside range 1-6"

    def test_no_rolls_outside_range(self):
        """Test that no rolls are outside valid range (comprehensive)"""
        results = [roll_d6() for _ in range(100)]
        assert all(1 <= r <= 6 for r in results), "Found rolls outside valid range"

    def test_statistical_distribution(self):
        """Test that rolls produce varied results (statistical test)"""
        # Roll 60 times - with fair d6, we should get all 6 values
        results = [roll_d6() for _ in range(60)]
        unique_results = set(results)

        # With 60 rolls, probability of missing a value is low
        # We check for at least 4 different values (very conservative)
        assert len(unique_results) >= 4, "Dice rolls appear non-random"

    def test_min_and_max_possible(self):
        """Test that both minimum (1) and maximum (6) can occur"""
        # Roll many times and verify we see both extremes
        results = [roll_d6() for _ in range(100)]
        assert 1 in results, "Never rolled minimum value (1)"
        assert 6 in results, "Never rolled maximum value (6)"


class TestValidateLasersFeelings:
    """Test suite for Lasers & Feelings roll validation"""

    # Lasers task tests (roll UNDER character number to succeed)

    def test_lasers_roll_under_is_success(self):
        """Test lasers task: rolling under character number succeeds"""
        success, outcome = validate_lasers_feelings_roll(
            character_number=4,
            roll_result=2,
            task_type="lasers"
        )
        assert success is True
        assert outcome == "success"

        success, outcome = validate_lasers_feelings_roll(
            character_number=5,
            roll_result=1,
            task_type="lasers"
        )
        assert success is True
        assert outcome == "success"

    def test_lasers_roll_over_is_failure(self):
        """Test lasers task: rolling over character number fails"""
        success, outcome = validate_lasers_feelings_roll(
            character_number=3,
            roll_result=5,
            task_type="lasers"
        )
        assert success is False
        assert outcome == "failure"

        success, outcome = validate_lasers_feelings_roll(
            character_number=2,
            roll_result=6,
            task_type="lasers"
        )
        assert success is False
        assert outcome == "failure"

    def test_lasers_roll_exact_is_complication(self):
        """Test lasers task: rolling exact number is success with complication"""
        success, outcome = validate_lasers_feelings_roll(
            character_number=4,
            roll_result=4,
            task_type="lasers"
        )
        assert success is True
        assert outcome == "complication"

        success, outcome = validate_lasers_feelings_roll(
            character_number=2,
            roll_result=2,
            task_type="lasers"
        )
        assert success is True
        assert outcome == "complication"

    # Feelings task tests (roll OVER character number to succeed)

    def test_feelings_roll_over_is_success(self):
        """Test feelings task: rolling over character number succeeds"""
        success, outcome = validate_lasers_feelings_roll(
            character_number=3,
            roll_result=5,
            task_type="feelings"
        )
        assert success is True
        assert outcome == "success"

        success, outcome = validate_lasers_feelings_roll(
            character_number=2,
            roll_result=6,
            task_type="feelings"
        )
        assert success is True
        assert outcome == "success"

    def test_feelings_roll_under_is_failure(self):
        """Test feelings task: rolling under character number fails"""
        success, outcome = validate_lasers_feelings_roll(
            character_number=4,
            roll_result=2,
            task_type="feelings"
        )
        assert success is False
        assert outcome == "failure"

        success, outcome = validate_lasers_feelings_roll(
            character_number=5,
            roll_result=1,
            task_type="feelings"
        )
        assert success is False
        assert outcome == "failure"

    def test_feelings_roll_exact_is_complication(self):
        """Test feelings task: rolling exact number is success with complication"""
        success, outcome = validate_lasers_feelings_roll(
            character_number=3,
            roll_result=3,
            task_type="feelings"
        )
        assert success is True
        assert outcome == "complication"

        success, outcome = validate_lasers_feelings_roll(
            character_number=5,
            roll_result=5,
            task_type="feelings"
        )
        assert success is True
        assert outcome == "complication"

    # Case insensitivity tests

    def test_task_type_case_insensitive(self):
        """Test that task_type is case-insensitive"""
        success1, outcome1 = validate_lasers_feelings_roll(
            character_number=3,
            roll_result=2,
            task_type="LASERS"
        )
        success2, outcome2 = validate_lasers_feelings_roll(
            character_number=3,
            roll_result=2,
            task_type="lasers"
        )
        assert success1 == success2
        assert outcome1 == outcome2

        success1, outcome1 = validate_lasers_feelings_roll(
            character_number=3,
            roll_result=5,
            task_type="Feelings"
        )
        success2, outcome2 = validate_lasers_feelings_roll(
            character_number=3,
            roll_result=5,
            task_type="feelings"
        )
        assert success1 == success2
        assert outcome1 == outcome2

    # Edge case tests for all valid character numbers

    def test_all_valid_character_numbers(self):
        """Test validation works for all valid character numbers (2-5)"""
        for char_num in [2, 3, 4, 5]:
            # Should not raise error
            success, outcome = validate_lasers_feelings_roll(
                character_number=char_num,
                roll_result=3,
                task_type="lasers"
            )
            assert isinstance(success, bool)
            assert outcome in ["success", "failure", "complication"]

    # Comprehensive outcome matrix test

    def test_comprehensive_lasers_outcomes(self):
        """Test all possible outcomes for lasers task"""
        # Character number 3: success on 1-2, complication on 3, failure on 4-6
        assert validate_lasers_feelings_roll(3, 1, "lasers") == (True, "success")
        assert validate_lasers_feelings_roll(3, 2, "lasers") == (True, "success")
        assert validate_lasers_feelings_roll(3, 3, "lasers") == (True, "complication")
        assert validate_lasers_feelings_roll(3, 4, "lasers") == (False, "failure")
        assert validate_lasers_feelings_roll(3, 5, "lasers") == (False, "failure")
        assert validate_lasers_feelings_roll(3, 6, "lasers") == (False, "failure")

    def test_comprehensive_feelings_outcomes(self):
        """Test all possible outcomes for feelings task"""
        # Character number 4: failure on 1-3, complication on 4, success on 5-6
        assert validate_lasers_feelings_roll(4, 1, "feelings") == (False, "failure")
        assert validate_lasers_feelings_roll(4, 2, "feelings") == (False, "failure")
        assert validate_lasers_feelings_roll(4, 3, "feelings") == (False, "failure")
        assert validate_lasers_feelings_roll(4, 4, "feelings") == (True, "complication")
        assert validate_lasers_feelings_roll(4, 5, "feelings") == (True, "success")
        assert validate_lasers_feelings_roll(4, 6, "feelings") == (True, "success")

    # Error cases - invalid character_number

    def test_character_number_too_low_raises_error(self):
        """Test that character_number < 2 raises ValueError"""
        with pytest.raises(ValueError, match="Character number must be 2-5"):
            validate_lasers_feelings_roll(1, 3, "lasers")
        with pytest.raises(ValueError, match="Character number must be 2-5"):
            validate_lasers_feelings_roll(0, 3, "lasers")
        with pytest.raises(ValueError, match="Character number must be 2-5"):
            validate_lasers_feelings_roll(-1, 3, "lasers")

    def test_character_number_too_high_raises_error(self):
        """Test that character_number > 5 raises ValueError"""
        with pytest.raises(ValueError, match="Character number must be 2-5"):
            validate_lasers_feelings_roll(6, 3, "lasers")
        with pytest.raises(ValueError, match="Character number must be 2-5"):
            validate_lasers_feelings_roll(10, 3, "lasers")

    # Error cases - invalid roll_result

    def test_roll_result_too_low_raises_error(self):
        """Test that roll_result < 1 raises ValueError"""
        with pytest.raises(ValueError, match="Roll result must be 1-6"):
            validate_lasers_feelings_roll(3, 0, "lasers")
        with pytest.raises(ValueError, match="Roll result must be 1-6"):
            validate_lasers_feelings_roll(3, -1, "lasers")

    def test_roll_result_too_high_raises_error(self):
        """Test that roll_result > 6 raises ValueError"""
        with pytest.raises(ValueError, match="Roll result must be 1-6"):
            validate_lasers_feelings_roll(3, 7, "lasers")
        with pytest.raises(ValueError, match="Roll result must be 1-6"):
            validate_lasers_feelings_roll(3, 20, "lasers")

    # Error cases - invalid task_type

    def test_invalid_task_type_raises_error(self):
        """Test that invalid task_type raises ValueError"""
        with pytest.raises(ValueError, match="Task type must be 'lasers' or 'feelings'"):
            validate_lasers_feelings_roll(3, 3, "invalid")
        with pytest.raises(ValueError, match="Task type must be 'lasers' or 'feelings'"):
            validate_lasers_feelings_roll(3, 3, "")
        with pytest.raises(ValueError, match="Task type must be 'lasers' or 'feelings'"):
            validate_lasers_feelings_roll(3, 3, "combat")
