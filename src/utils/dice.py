# ABOUTME: D&D 5e dice roller with notation parsing and DiceRoll model generation.
# ABOUTME: Supports standard notation: "2d6+3", "1d20", "d6" (implicit 1d6), "3d8-2", etc.

import random
import re
from datetime import datetime

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


def validate_lasers_feelings_roll(
    character_number: int,
    roll_result: int,
    task_type: str
) -> tuple[bool, str]:
    """
    Validate a Lasers & Feelings roll outcome.

    Rules:
    - Lasers task: Roll UNDER character number to succeed
    - Feelings task: Roll OVER character number to succeed
    - Roll EXACTLY number: Success with complication

    Args:
        character_number: Character's Lasers/Feelings number (2-5)
        roll_result: 1d6 roll result
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
