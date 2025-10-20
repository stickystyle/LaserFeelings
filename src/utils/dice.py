# ABOUTME: D&D 5e dice roller with notation parsing and DiceRoll model generation.
# ABOUTME: Supports standard notation: "2d6+3", "1d20", "d6" (implicit 1d6), "3d8-2", etc.

import random
import re
from datetime import UTC, datetime

from src.models.dice_models import LasersFeelingRollResult, RollOutcome
from src.models.messages import DiceRoll

# Standard D&D dice types
VALID_DICE_SIDES = {4, 6, 8, 10, 12, 20, 100}


def parse_dice_notation(notation: str) -> tuple[int, int, int]:
    """
    Parse D&D 5e dice notation into components.

    Supports patterns:
    - "2d6+3" -> (2, 6, 3)
    - "1d20" -> (1, 20, 0)
    - "d6" -> (1, 6, 0) (implicit 1 die)
    - "3d8-2" -> (3, 8, -2)
    - "4d10" -> (4, 10, 0)

    Args:
        notation: Dice notation string (e.g., "2d6+3")

    Returns:
        Tuple of (num_dice, die_size, modifier)

    Raises:
        ValueError: If notation is invalid or uses unsupported dice
    """
    notation = notation.strip().lower()

    # Regex pattern for dice notation:
    # Optional number of dice, 'd', die size, optional +/- modifier
    pattern = r'^(\d*)d(\d+)([+-]\d+)?$'
    match = re.match(pattern, notation)

    if not match:
        raise ValueError(
            f"Invalid dice notation: '{notation}'. "
            f"Expected format: 'XdY' or 'XdY+Z' (e.g., '2d6', '1d20+5', 'd6')"
        )

    num_dice_str, die_size_str, modifier_str = match.groups()

    # Parse number of dice (default to 1 if omitted, e.g., "d6")
    num_dice = int(num_dice_str) if num_dice_str else 1

    # Parse die size
    die_size = int(die_size_str)

    # Parse modifier (default to 0 if omitted)
    modifier = int(modifier_str) if modifier_str else 0

    # Validate number of dice
    if num_dice < 1:
        raise ValueError(
            f"Number of dice must be at least 1, got {num_dice}"
        )

    if num_dice > 100:
        raise ValueError(
            f"Number of dice cannot exceed 100, got {num_dice}"
        )

    # Validate die size
    if die_size not in VALID_DICE_SIDES:
        raise ValueError(
            f"Invalid die size: d{die_size}. "
            f"Supported dice: {', '.join(f'd{d}' for d in sorted(VALID_DICE_SIDES))}"
        )

    return num_dice, die_size, modifier


def roll_dice(notation: str) -> DiceRoll:
    """
    Roll dice using D&D 5e notation and return DiceRoll model.

    Examples:
        >>> roll = roll_dice("2d6+3")
        >>> roll.notation
        '2d6+3'
        >>> roll.dice_count
        2
        >>> roll.dice_sides
        6
        >>> roll.modifier
        3
        >>> len(roll.individual_rolls)
        2
        >>> roll.total  # sum of rolls + 3

    Args:
        notation: Dice notation string (e.g., "2d6+3")

    Returns:
        DiceRoll model instance with roll results

    Raises:
        ValueError: If notation is invalid
    """
    # Parse notation
    num_dice, die_size, modifier = parse_dice_notation(notation)

    # Roll dice
    individual_rolls = [
        random.randint(1, die_size)
        for _ in range(num_dice)
    ]

    # Calculate total
    total = sum(individual_rolls) + modifier

    # Create DiceRoll model
    return DiceRoll(
        notation=notation.strip(),
        dice_count=num_dice,
        dice_sides=die_size,
        modifier=modifier,
        individual_rolls=individual_rolls,
        total=total,
        timestamp=datetime.now()
    )


def roll_d6() -> int:
    """
    Convenience function to roll a single d6.

    This is commonly used for Lasers & Feelings game mechanics.

    Returns:
        Integer between 1 and 6 (inclusive)
    """
    return random.randint(1, 6)


def _evaluate_single_die(
    character_number: int,
    roll_result: int,
    task_type: str
) -> tuple[bool, str]:
    """
    Private helper: Evaluate a single d6 against character number.

    NOTE: This is a low-level helper for evaluating individual dice.
    For full Lasers & Feelings rolls, use roll_lasers_feelings() instead.

    Rules:
    - Lasers task: Roll UNDER character number to succeed
    - Feelings task: Roll OVER character number to succeed
    - Roll EXACTLY number: Success with complication (LASER FEELINGS)

    Args:
        character_number: Character's Lasers/Feelings number (2-5)
        roll_result: Single d6 result (1-6)
        task_type: "lasers" or "feelings"

    Returns:
        Tuple of (success: bool, outcome: str)
        outcome is "success", "failure", or "complication"

    Raises:
        ValueError: If parameters are out of valid range
    """
    if not 2 <= character_number <= 5:
        raise ValueError(
            f"Character number must be 2-5, got {character_number}"
        )

    if not 1 <= roll_result <= 6:
        raise ValueError(
            f"Roll result must be 1-6, got {roll_result}"
        )

    task_type = task_type.lower()
    if task_type not in ("lasers", "feelings"):
        raise ValueError(
            f"Task type must be 'lasers' or 'feelings', got '{task_type}'"
        )

    # Exact match = success with complication
    if roll_result == character_number:
        return True, "complication"

    # Lasers task: roll under number
    if task_type == "lasers":
        success = roll_result < character_number
    # Feelings task: roll over number
    else:  # feelings
        success = roll_result > character_number

    outcome = "success" if success else "failure"
    return success, outcome


def roll_lasers_feelings(
    character_number: int,
    task_type: str,
    is_prepared: bool = False,
    is_expert: bool = False,
    is_helping: bool = False,
    gm_question: str | None = None
) -> LasersFeelingRollResult:
    """
    Perform a complete Lasers & Feelings roll with multi-die success counting.

    Rules:
    - Base: 1d6
    - Prepared: +1d6 (2d6 total)
    - Expert: +1d6 (3d6 total if also prepared, 2d6 if not prepared)
    - Helping: +1d6 (max 3d6 total from all modifiers)
    - Each die compared individually to character_number
    - LASERS task: die < number = success, die == number = LASER FEELINGS
    - FEELINGS task: die > number = success, die == number = LASER FEELINGS
    - LASER FEELINGS counts as success + grants special insight
    - Total successes determine outcome:
      * 0 successes = failure
      * 1 success = barely manage (complication)
      * 2 successes = clean success
      * 3 successes = critical success

    Args:
        character_number: Character's Lasers/Feelings number (2-5)
        task_type: "lasers" or "feelings"
        is_prepared: Whether character was prepared (+1d6)
        is_expert: Whether character is expert (+1d6)
        is_helping: Whether character is being helped by another (+1d6)
        gm_question: Optional question to ask GM if LASER FEELINGS occurs

    Returns:
        LasersFeelingRollResult with complete roll details

    Raises:
        ValueError: If parameters are invalid

    Examples:
        >>> # Base roll for number 3 character attempting lasers task
        >>> result = roll_lasers_feelings(3, "lasers")
        >>> result.dice_count
        1
        >>> # Prepared and expert roll
        >>> result = roll_lasers_feelings(4, "feelings", is_prepared=True, is_expert=True)
        >>> result.dice_count
        3
    """
    # Validate inputs
    if not 2 <= character_number <= 5:
        raise ValueError(
            f"Character number must be 2-5, got {character_number}"
        )

    task_type = task_type.lower()
    if task_type not in ("lasers", "feelings"):
        raise ValueError(
            f"Task type must be 'lasers' or 'feelings', got '{task_type}'"
        )

    # Determine number of dice (max 3d6)
    dice_count = 1  # Base
    if is_prepared:
        dice_count += 1
    if is_expert:
        dice_count += 1
    if is_helping:
        dice_count += 1
    dice_count = min(dice_count, 3)  # Cap at 3 dice

    # Roll all dice
    individual_rolls = [roll_d6() for _ in range(dice_count)]

    # Evaluate each die
    die_successes: list[bool] = []
    laser_feelings_indices: list[int] = []

    for idx, roll in enumerate(individual_rolls):
        # Check for exact match (LASER FEELINGS)
        if roll == character_number:
            laser_feelings_indices.append(idx)
            die_successes.append(True)  # LASER FEELINGS counts as success
        # Check for success based on task type
        elif task_type == "lasers":
            # Lasers task: roll under number
            die_successes.append(roll < character_number)
        else:  # feelings
            # Feelings task: roll over number
            die_successes.append(roll > character_number)

    # Count total successes
    total_successes = sum(die_successes)

    # Determine outcome
    if total_successes == 0:
        outcome = RollOutcome.FAILURE
    elif total_successes == 1:
        outcome = RollOutcome.BARELY
    elif total_successes == 2:
        outcome = RollOutcome.SUCCESS
    else:  # 3 successes
        outcome = RollOutcome.CRITICAL

    # Create result
    return LasersFeelingRollResult(
        character_number=character_number,
        task_type=task_type,
        is_prepared=is_prepared,
        is_expert=is_expert,
        is_helping=is_helping,
        individual_rolls=individual_rolls,
        die_successes=die_successes,
        laser_feelings_indices=laser_feelings_indices,
        total_successes=total_successes,
        outcome=outcome,
        gm_question=gm_question,
        timestamp=datetime.now(UTC)
    )


# Backward compatibility alias (deprecated - use roll_lasers_feelings instead)
def validate_lasers_feelings_roll(
    character_number: int,
    roll_result: int,
    task_type: str
) -> tuple[bool, str]:
    """
    DEPRECATED: Use roll_lasers_feelings() for complete rolls.

    This function evaluates a single die, but Lasers & Feelings uses
    multiple dice with success counting. Kept for backward compatibility.
    """
    return _evaluate_single_die(character_number, roll_result, task_type)
