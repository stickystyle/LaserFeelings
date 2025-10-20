# ABOUTME: Unit tests for dice rolling utilities
# ABOUTME: Validates D&D 5e notation parsing and Lasers & Feelings mechanics

from datetime import UTC, datetime

import pytest

from src.models.messages import DiceRoll
from src.utils.dice import (
    VALID_DICE_SIDES,
    parse_dice_notation,
    roll_d6,
    roll_dice,
    validate_lasers_feelings_roll,
)


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
    """
    Test suite for validate_lasers_feelings_roll (deprecated).

    NOTE: This tests the backward-compatibility function that evaluates
    a single die. For multi-die Lasers & Feelings rolls, see TestRollLasersFeelings.
    """

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

    def test_lasers_roll_exact_is_laser_feelings(self):
        """Test lasers task: rolling exact number is LASER FEELINGS (deprecated: returns 'complication')"""
        success, outcome = validate_lasers_feelings_roll(
            character_number=4,
            roll_result=4,
            task_type="lasers"
        )
        assert success is True
        # NOTE: This function is deprecated and returns "complication" for backward compatibility
        # Modern code should use roll_lasers_feelings() and check has_laser_feelings
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

    def test_feelings_roll_exact_is_laser_feelings(self):
        """Test feelings task: rolling exact number is LASER FEELINGS (deprecated: returns 'complication')"""
        success, outcome = validate_lasers_feelings_roll(
            character_number=3,
            roll_result=3,
            task_type="feelings"
        )
        assert success is True
        # NOTE: This function is deprecated and returns "complication" for backward compatibility
        # Modern code should use roll_lasers_feelings() and check has_laser_feelings
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
        # Character number 3: success on 1-2, LASER FEELINGS on 3, failure on 4-6
        # NOTE: "complication" is deprecated terminology for LASER FEELINGS
        assert validate_lasers_feelings_roll(3, 1, "lasers") == (True, "success")
        assert validate_lasers_feelings_roll(3, 2, "lasers") == (True, "success")
        assert validate_lasers_feelings_roll(3, 3, "lasers") == (True, "complication")  # LASER FEELINGS
        assert validate_lasers_feelings_roll(3, 4, "lasers") == (False, "failure")
        assert validate_lasers_feelings_roll(3, 5, "lasers") == (False, "failure")
        assert validate_lasers_feelings_roll(3, 6, "lasers") == (False, "failure")

    def test_comprehensive_feelings_outcomes(self):
        """Test all possible outcomes for feelings task"""
        # Character number 4: failure on 1-3, LASER FEELINGS on 4, success on 5-6
        # NOTE: "complication" is deprecated terminology for LASER FEELINGS
        assert validate_lasers_feelings_roll(4, 1, "feelings") == (False, "failure")
        assert validate_lasers_feelings_roll(4, 2, "feelings") == (False, "failure")
        assert validate_lasers_feelings_roll(4, 3, "feelings") == (False, "failure")
        assert validate_lasers_feelings_roll(4, 4, "feelings") == (True, "complication")  # LASER FEELINGS
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


class TestRollLasersFeelings:
    """Test suite for complete Lasers & Feelings multi-die rolling"""

    def test_import_function(self):
        """Test that roll_lasers_feelings can be imported"""
        from src.utils.dice import roll_lasers_feelings
        assert callable(roll_lasers_feelings)

    def test_returns_correct_model(self):
        """Test that function returns LasersFeelingRollResult model"""
        from src.models.dice_models import LasersFeelingRollResult
        from src.utils.dice import roll_lasers_feelings

        result = roll_lasers_feelings(3, "lasers")
        assert isinstance(result, LasersFeelingRollResult)

    # Dice count tests

    def test_base_roll_has_one_die(self):
        """Test base roll (not prepared, not expert) rolls 1d6"""
        from src.utils.dice import roll_lasers_feelings

        result = roll_lasers_feelings(3, "lasers", is_prepared=False, is_expert=False)
        assert result.dice_count == 1
        assert len(result.individual_rolls) == 1
        assert len(result.die_successes) == 1

    def test_prepared_roll_has_two_dice(self):
        """Test prepared roll (not expert) rolls 2d6"""
        from src.utils.dice import roll_lasers_feelings

        result = roll_lasers_feelings(3, "lasers", is_prepared=True, is_expert=False)
        assert result.dice_count == 2
        assert len(result.individual_rolls) == 2
        assert len(result.die_successes) == 2

    def test_expert_roll_has_two_dice(self):
        """Test expert roll (not prepared) rolls 2d6"""
        from src.utils.dice import roll_lasers_feelings

        result = roll_lasers_feelings(3, "lasers", is_prepared=False, is_expert=True)
        assert result.dice_count == 2
        assert len(result.individual_rolls) == 2
        assert len(result.die_successes) == 2

    def test_prepared_and_expert_roll_has_three_dice(self):
        """Test prepared + expert roll rolls 3d6"""
        from src.utils.dice import roll_lasers_feelings

        result = roll_lasers_feelings(3, "lasers", is_prepared=True, is_expert=True)
        assert result.dice_count == 3
        assert len(result.individual_rolls) == 3
        assert len(result.die_successes) == 3

    # Dice value validation

    def test_individual_rolls_within_range(self):
        """Test all dice are valid d6 results (1-6)"""
        from src.utils.dice import roll_lasers_feelings

        # Roll many times to ensure consistency
        for _ in range(20):
            result = roll_lasers_feelings(3, "lasers", is_prepared=True, is_expert=True)
            for roll in result.individual_rolls:
                assert 1 <= roll <= 6, f"Die rolled {roll}, outside valid range"

    # Model field population tests

    def test_character_number_stored(self):
        """Test character_number is correctly stored"""
        from src.utils.dice import roll_lasers_feelings

        for char_num in [2, 3, 4, 5]:
            result = roll_lasers_feelings(char_num, "lasers")
            assert result.character_number == char_num

    def test_task_type_stored(self):
        """Test task_type is correctly stored"""
        from src.utils.dice import roll_lasers_feelings

        result = roll_lasers_feelings(3, "lasers")
        assert result.task_type == "lasers"

        result = roll_lasers_feelings(3, "feelings")
        assert result.task_type == "feelings"

    def test_task_type_case_insensitive(self):
        """Test task_type is normalized to lowercase"""
        from src.utils.dice import roll_lasers_feelings

        result = roll_lasers_feelings(3, "LASERS")
        assert result.task_type == "lasers"

        result = roll_lasers_feelings(3, "Feelings")
        assert result.task_type == "feelings"

    def test_is_prepared_stored(self):
        """Test is_prepared flag is correctly stored"""
        from src.utils.dice import roll_lasers_feelings

        result = roll_lasers_feelings(3, "lasers", is_prepared=True)
        assert result.is_prepared is True

        result = roll_lasers_feelings(3, "lasers", is_prepared=False)
        assert result.is_prepared is False

    def test_is_expert_stored(self):
        """Test is_expert flag is correctly stored"""
        from src.utils.dice import roll_lasers_feelings

        result = roll_lasers_feelings(3, "lasers", is_expert=True)
        assert result.is_expert is True

        result = roll_lasers_feelings(3, "lasers", is_expert=False)
        assert result.is_expert is False

    def test_gm_question_stored(self):
        """Test gm_question is correctly stored"""
        from src.utils.dice import roll_lasers_feelings

        result = roll_lasers_feelings(3, "lasers", gm_question="What's really happening?")
        assert result.gm_question == "What's really happening?"

        result = roll_lasers_feelings(3, "lasers")
        assert result.gm_question is None

    def test_timestamp_populated(self):
        """Test timestamp is present and recent"""

        from src.utils.dice import roll_lasers_feelings

        before = datetime.now(UTC)
        result = roll_lasers_feelings(3, "lasers")
        after = datetime.now(UTC)

        assert result.timestamp is not None
        assert before <= result.timestamp <= after

    # Success counting tests - using statistical approach since rolls are random

    def test_lasers_task_success_counting_logic(self):
        """Test lasers task counts successes correctly (roll < number)"""

        from src.utils.dice import roll_lasers_feelings

        # Mock roll_d6 to control results
        original_roll_d6 = roll_d6

        def mock_roll_d6():
            return mock_results.pop(0)

        # Test with character_number=4, lasers task
        # Rolls: [1, 3, 5] → 1<4 ✓, 3<4 ✓, 5>4 ✗ → 2 successes
        mock_results = [1, 3, 5]
        import src.utils.dice as dice_module
        dice_module.roll_d6 = mock_roll_d6

        try:
            result = roll_lasers_feelings(4, "lasers", is_prepared=True, is_expert=True)
            assert result.individual_rolls == [1, 3, 5]
            assert result.die_successes == [True, True, False]
            assert result.total_successes == 2
            assert result.outcome == "success"
        finally:
            dice_module.roll_d6 = original_roll_d6

    def test_feelings_task_success_counting_logic(self):
        """Test feelings task counts successes correctly (roll > number)"""
        from src.utils.dice import roll_lasers_feelings

        # Mock roll_d6 to control results
        original_roll_d6 = roll_d6

        def mock_roll_d6():
            return mock_results.pop(0)

        # Test with character_number=3, feelings task
        # Rolls: [2, 4, 5] → 2<3 ✗, 4>3 ✓, 5>3 ✓ → 2 successes
        mock_results = [2, 4, 5]
        import src.utils.dice as dice_module
        dice_module.roll_d6 = mock_roll_d6

        try:
            result = roll_lasers_feelings(3, "feelings", is_prepared=True, is_expert=True)
            assert result.individual_rolls == [2, 4, 5]
            assert result.die_successes == [False, True, True]
            assert result.total_successes == 2
            assert result.outcome == "success"
        finally:
            dice_module.roll_d6 = original_roll_d6

    def test_laser_feelings_detection(self):
        """Test LASER FEELINGS (exact match) is detected and counts as success"""
        from src.utils.dice import roll_lasers_feelings

        # Mock roll_d6 to control results
        original_roll_d6 = roll_d6

        def mock_roll_d6():
            return mock_results.pop(0)

        # Test with character_number=3, lasers task
        # Rolls: [3, 5, 1] → 3==3 LASER_FEELINGS ✓, 5>3 ✗, 1<3 ✓ → 2 successes
        mock_results = [3, 5, 1]
        import src.utils.dice as dice_module
        dice_module.roll_d6 = mock_roll_d6

        try:
            result = roll_lasers_feelings(3, "lasers", is_prepared=True, is_expert=True)
            assert result.individual_rolls == [3, 5, 1]
            assert result.die_successes == [True, False, True]  # LASER FEELINGS counts as success
            assert result.laser_feelings_indices == [0]  # First die was exact match
            assert result.total_successes == 2
            assert result.has_laser_feelings is True
        finally:
            dice_module.roll_d6 = original_roll_d6

    def test_multiple_laser_feelings(self):
        """Test multiple LASER FEELINGS in one roll"""
        from src.utils.dice import roll_lasers_feelings

        # Mock roll_d6 to control results
        original_roll_d6 = roll_d6

        def mock_roll_d6():
            return mock_results.pop(0)

        # Test with character_number=4, feelings task
        # Rolls: [4, 4, 5] → 4==4 LF ✓, 4==4 LF ✓, 5>4 ✓ → 3 successes
        mock_results = [4, 4, 5]
        import src.utils.dice as dice_module
        dice_module.roll_d6 = mock_roll_d6

        try:
            result = roll_lasers_feelings(4, "feelings", is_prepared=True, is_expert=True)
            assert result.individual_rolls == [4, 4, 5]
            assert result.die_successes == [True, True, True]
            assert result.laser_feelings_indices == [0, 1]  # First two dice were exact
            assert result.total_successes == 3
            assert result.outcome == "critical"
            assert result.has_laser_feelings is True
        finally:
            dice_module.roll_d6 = original_roll_d6

    def test_no_laser_feelings(self):
        """Test no LASER FEELINGS when no exact matches"""
        from src.utils.dice import roll_lasers_feelings

        # Mock roll_d6 to control results
        original_roll_d6 = roll_d6

        def mock_roll_d6():
            return mock_results.pop(0)

        # Test with character_number=3, lasers task
        # Rolls: [1, 2, 5] → 1<3 ✓, 2<3 ✓, 5>3 ✗ → 2 successes, no exact match
        mock_results = [1, 2, 5]
        import src.utils.dice as dice_module
        dice_module.roll_d6 = mock_roll_d6

        try:
            result = roll_lasers_feelings(3, "lasers", is_prepared=True, is_expert=True)
            assert result.laser_feelings_indices == []
            assert result.has_laser_feelings is False
        finally:
            dice_module.roll_d6 = original_roll_d6

    # Outcome determination tests

    def test_outcome_failure_zero_successes(self):
        """Test 0 successes = failure"""
        from src.utils.dice import roll_lasers_feelings

        # Mock roll_d6 to control results
        original_roll_d6 = roll_d6

        def mock_roll_d6():
            return mock_results.pop(0)

        # Character_number=2, lasers task: only 1 succeeds, so roll [3,4,5] all fail
        mock_results = [3, 4, 5]
        import src.utils.dice as dice_module
        dice_module.roll_d6 = mock_roll_d6

        try:
            result = roll_lasers_feelings(2, "lasers", is_prepared=True, is_expert=True)
            assert result.total_successes == 0
            assert result.outcome == "failure"
        finally:
            dice_module.roll_d6 = original_roll_d6

    def test_outcome_barely_one_success(self):
        """Test 1 success = barely manage"""
        from src.utils.dice import roll_lasers_feelings

        # Mock roll_d6 to control results
        original_roll_d6 = roll_d6

        def mock_roll_d6():
            return mock_results.pop(0)

        # Character_number=3, lasers task: [1, 4, 5] → only 1 succeeds
        mock_results = [1, 4, 5]
        import src.utils.dice as dice_module
        dice_module.roll_d6 = mock_roll_d6

        try:
            result = roll_lasers_feelings(3, "lasers", is_prepared=True, is_expert=True)
            assert result.total_successes == 1
            assert result.outcome == "barely"
        finally:
            dice_module.roll_d6 = original_roll_d6

    def test_outcome_success_two_successes(self):
        """Test 2 successes = clean success"""
        from src.utils.dice import roll_lasers_feelings

        # Mock roll_d6 to control results
        original_roll_d6 = roll_d6

        def mock_roll_d6():
            return mock_results.pop(0)

        # Character_number=4, lasers task: [1, 2, 5] → 2 succeed
        mock_results = [1, 2, 5]
        import src.utils.dice as dice_module
        dice_module.roll_d6 = mock_roll_d6

        try:
            result = roll_lasers_feelings(4, "lasers", is_prepared=True, is_expert=True)
            assert result.total_successes == 2
            assert result.outcome == "success"
        finally:
            dice_module.roll_d6 = original_roll_d6

    def test_outcome_critical_three_successes(self):
        """Test 3 successes = critical success"""
        from src.utils.dice import roll_lasers_feelings

        # Mock roll_d6 to control results
        original_roll_d6 = roll_d6

        def mock_roll_d6():
            return mock_results.pop(0)

        # Character_number=5, lasers task: [1, 2, 3] → all 3 succeed
        mock_results = [1, 2, 3]
        import src.utils.dice as dice_module
        dice_module.roll_d6 = mock_roll_d6

        try:
            result = roll_lasers_feelings(5, "lasers", is_prepared=True, is_expert=True)
            assert result.total_successes == 3
            assert result.outcome == "critical"
        finally:
            dice_module.roll_d6 = original_roll_d6

    # Edge case tests

    def test_character_number_2_lasers_extreme_difficulty(self):
        """Test character_number=2 lasers task (very difficult: only 1 succeeds)"""
        from src.utils.dice import roll_lasers_feelings

        # Character 2 on lasers task: only rolling 1 succeeds, 2 is LASER FEELINGS
        # Over many rolls, we should see very few successes
        success_count = 0
        for _ in range(30):
            result = roll_lasers_feelings(2, "lasers")
            if result.total_successes > 0:
                success_count += 1

        # With 30 rolls, expect success rate around 33% (rolling 1 or 2)
        # Should have at least a few successes but not many
        assert success_count > 0  # Should get some successes
        assert success_count < 25  # But not too many (should be around 10)

    def test_character_number_5_feelings_extreme_difficulty(self):
        """Test character_number=5 feelings task (very difficult: only 6 succeeds)"""
        from src.utils.dice import roll_lasers_feelings

        # Character 5 on feelings task: only rolling 6 succeeds, 5 is LASER FEELINGS
        # Over many rolls, we should see very few successes
        success_count = 0
        for _ in range(30):
            result = roll_lasers_feelings(5, "feelings")
            if result.total_successes > 0:
                success_count += 1

        # With 30 rolls, expect success rate around 33% (rolling 5 or 6)
        # Should have at least a few successes but not many
        assert success_count > 0  # Should get some successes
        assert success_count < 25  # But not too many (should be around 10)

    def test_character_number_3_balanced(self):
        """Test character_number=3 has balanced success rates"""
        from src.utils.dice import roll_lasers_feelings

        # Character 3: lasers succeeds on 1,2,3 (50%), feelings succeeds on 3,4,5,6 (66%)
        # Run many trials and verify rough balance
        lasers_successes = 0
        feelings_successes = 0

        for _ in range(30):
            lasers_result = roll_lasers_feelings(3, "lasers")
            if lasers_result.total_successes > 0:
                lasers_successes += 1

            feelings_result = roll_lasers_feelings(3, "feelings")
            if feelings_result.total_successes > 0:
                feelings_successes += 1

        # Lasers should succeed about 50% of the time
        assert 10 <= lasers_successes <= 25

        # Feelings should succeed more often (66%)
        assert 15 <= feelings_successes <= 30

    # Validation tests

    def test_invalid_character_number_too_low(self):
        """Test character_number < 2 raises ValueError"""
        from src.utils.dice import roll_lasers_feelings

        with pytest.raises(ValueError, match="Character number must be 2-5"):
            roll_lasers_feelings(1, "lasers")
        with pytest.raises(ValueError, match="Character number must be 2-5"):
            roll_lasers_feelings(0, "lasers")
        with pytest.raises(ValueError, match="Character number must be 2-5"):
            roll_lasers_feelings(-1, "lasers")

    def test_invalid_character_number_too_high(self):
        """Test character_number > 5 raises ValueError"""
        from src.utils.dice import roll_lasers_feelings

        with pytest.raises(ValueError, match="Character number must be 2-5"):
            roll_lasers_feelings(6, "lasers")
        with pytest.raises(ValueError, match="Character number must be 2-5"):
            roll_lasers_feelings(10, "lasers")

    def test_invalid_task_type(self):
        """Test invalid task_type raises ValueError"""
        from src.utils.dice import roll_lasers_feelings

        with pytest.raises(ValueError, match="Task type must be 'lasers' or 'feelings'"):
            roll_lasers_feelings(3, "invalid")
        with pytest.raises(ValueError, match="Task type must be 'lasers' or 'feelings'"):
            roll_lasers_feelings(3, "")
        with pytest.raises(ValueError, match="Task type must be 'lasers' or 'feelings'"):
            roll_lasers_feelings(3, "combat")


class TestLasersFeelingsResultValidation:
    """Test suite for LasersFeelingRollResult model validation"""

    # Timezone validation tests

    def test_timestamp_must_be_timezone_aware(self):
        """Test that naive datetime raises validation error"""
        from datetime import datetime

        from pydantic import ValidationError

        from src.models.dice_models import LasersFeelingRollResult, RollOutcome

        with pytest.raises(ValidationError, match="timestamp must be timezone-aware"):
            LasersFeelingRollResult(
                character_number=3,
                task_type="lasers",
                is_prepared=False,
                is_expert=False,
                individual_rolls=[1],
                die_successes=[True],
                laser_feelings_indices=[],
                total_successes=1,
                outcome=RollOutcome.BARELY,
                timestamp=datetime.now()  # Naive datetime
            )

    def test_timestamp_accepts_timezone_aware_datetime(self):
        """Test that timezone-aware datetime is accepted"""
        from datetime import datetime

        from src.models.dice_models import LasersFeelingRollResult, RollOutcome

        result = LasersFeelingRollResult(
            character_number=3,
            task_type="lasers",
            is_prepared=False,
            is_expert=False,
            individual_rolls=[1],
            die_successes=[True],
            laser_feelings_indices=[],
            total_successes=1,
            outcome=RollOutcome.BARELY,
            timestamp=datetime.now(UTC)  # Timezone-aware
        )
        assert result.timestamp.tzinfo is not None

    # List consistency validation tests

    def test_die_successes_length_must_match_individual_rolls(self):
        """Test that die_successes length mismatch raises validation error"""
        from datetime import datetime

        from pydantic import ValidationError

        from src.models.dice_models import LasersFeelingRollResult, RollOutcome

        with pytest.raises(ValidationError, match="individual_rolls length.*must match die_successes length"):
            LasersFeelingRollResult(
                character_number=3,
                task_type="lasers",
                is_prepared=True,
                is_expert=False,
                individual_rolls=[1, 2],  # 2 rolls
                die_successes=[True],      # but only 1 success record
                laser_feelings_indices=[],
                total_successes=1,
                outcome=RollOutcome.BARELY,
                timestamp=datetime.now(UTC)
            )

    def test_laser_feelings_indices_must_be_valid(self):
        """Test that invalid laser_feelings_indices raise validation error"""
        from datetime import datetime

        from pydantic import ValidationError

        from src.models.dice_models import LasersFeelingRollResult, RollOutcome

        # Index too high
        with pytest.raises(ValidationError, match="laser_feelings_indices contains invalid index"):
            LasersFeelingRollResult(
                character_number=3,
                task_type="lasers",
                is_prepared=False,
                is_expert=False,
                individual_rolls=[1],
                die_successes=[True],
                laser_feelings_indices=[5],  # Index 5 when only 1 die exists
                total_successes=1,
                outcome=RollOutcome.BARELY,
                timestamp=datetime.now(UTC)
            )

        # Negative index
        with pytest.raises(ValidationError, match="laser_feelings_indices contains invalid index"):
            LasersFeelingRollResult(
                character_number=3,
                task_type="lasers",
                is_prepared=True,
                is_expert=False,
                individual_rolls=[1, 2],
                die_successes=[True, False],
                laser_feelings_indices=[-1],  # Negative index
                total_successes=1,
                outcome=RollOutcome.BARELY,
                timestamp=datetime.now(UTC)
            )

    def test_total_successes_must_match_actual_count(self):
        """Test that total_successes mismatch raises validation error"""
        from datetime import datetime

        from pydantic import ValidationError

        from src.models.dice_models import LasersFeelingRollResult, RollOutcome

        with pytest.raises(ValidationError, match="total_successes.*doesn't match count of successful dice"):
            LasersFeelingRollResult(
                character_number=3,
                task_type="lasers",
                is_prepared=True,
                is_expert=False,
                individual_rolls=[1, 2],
                die_successes=[True, True],  # 2 successes
                laser_feelings_indices=[],
                total_successes=1,  # But claims only 1 success
                outcome=RollOutcome.BARELY,
                timestamp=datetime.now(UTC)
            )

    def test_valid_model_passes_all_validators(self):
        """Test that a valid model passes all validators"""
        from datetime import datetime

        from src.models.dice_models import LasersFeelingRollResult, RollOutcome

        result = LasersFeelingRollResult(
            character_number=3,
            task_type="lasers",
            is_prepared=True,
            is_expert=True,
            individual_rolls=[1, 2, 3],
            die_successes=[True, True, True],
            laser_feelings_indices=[2],  # Valid index
            total_successes=3,  # Matches actual count
            outcome=RollOutcome.CRITICAL,
            timestamp=datetime.now(UTC)  # Timezone-aware
        )
        assert result.dice_count == 3
        assert result.has_laser_feelings is True

    # RollOutcome enum tests

    def test_roll_outcome_enum_values(self):
        """Test that RollOutcome enum has correct values"""
        from src.models.dice_models import RollOutcome

        assert RollOutcome.FAILURE.value == "failure"
        assert RollOutcome.BARELY.value == "barely"
        assert RollOutcome.SUCCESS.value == "success"
        assert RollOutcome.CRITICAL.value == "critical"

    def test_roll_outcome_enum_in_model(self):
        """Test that RollOutcome enum works in model"""
        from datetime import datetime

        from src.models.dice_models import LasersFeelingRollResult, RollOutcome

        for outcome_enum, expected_value in [
            (RollOutcome.FAILURE, "failure"),
            (RollOutcome.BARELY, "barely"),
            (RollOutcome.SUCCESS, "success"),
            (RollOutcome.CRITICAL, "critical"),
        ]:
            result = LasersFeelingRollResult(
                character_number=3,
                task_type="lasers",
                is_prepared=False,
                is_expert=False,
                individual_rolls=[1],
                die_successes=[True],
                laser_feelings_indices=[],
                total_successes=1,
                outcome=outcome_enum,
                timestamp=datetime.now(UTC)
            )
            assert result.outcome == outcome_enum
            assert result.outcome.value == expected_value

    def test_roll_outcome_invalid_string_raises_error(self):
        """Test that invalid outcome string raises validation error"""
        from datetime import datetime

        from pydantic import ValidationError

        from src.models.dice_models import LasersFeelingRollResult

        with pytest.raises(ValidationError):
            LasersFeelingRollResult(
                character_number=3,
                task_type="lasers",
                is_prepared=False,
                is_expert=False,
                individual_rolls=[1],
                die_successes=[True],
                laser_feelings_indices=[],
                total_successes=1,
                outcome="invalid_outcome",  # Invalid string
                timestamp=datetime.now(UTC)
            )
