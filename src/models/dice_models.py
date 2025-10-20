# ABOUTME: Pydantic models for dice roll results in Lasers & Feelings game system.
# ABOUTME: Includes RollOutcome enum and LasersFeelingRollResult with multi-die validation.

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field, field_validator, model_validator


class RollOutcome(str, Enum):
    """Outcome classification for Lasers & Feelings rolls based on success count"""
    FAILURE = "failure"   # 0 successes
    BARELY = "barely"     # 1 success
    SUCCESS = "success"   # 2 successes
    CRITICAL = "critical" # 3 successes


class LasersFeelingRollResult(BaseModel):
    """Lasers & Feelings roll result with multi-die success counting

    Each die is evaluated individually against the character number:
    - Lasers task: roll < character_number to succeed
    - Feelings task: roll > character_number to succeed
    - Exact match: LASER FEELINGS (success + special insight)

    Base roll is 1d6; +1d6 if prepared; +1d6 if expert; +1d6 if helping (max 3d6)
    Total successes determine outcome: 0=failure, 1=barely, 2=success, 3=critical
    """

    character_number: int = Field(
        ge=2,
        le=5,
        description="Character's Lasers/Feelings number (2-5)"
    )
    task_type: str = Field(
        pattern="^(lasers|feelings)$",
        description="Task type: 'lasers' or 'feelings'"
    )
    is_prepared: bool = Field(
        default=False,
        description="Whether character was prepared (+1d6)"
    )
    is_expert: bool = Field(
        default=False,
        description="Whether character is expert (+1d6)"
    )
    is_helping: bool = Field(
        default=False,
        description="Whether character is being helped by another (+1d6)"
    )
    individual_rolls: list[int] = Field(
        description="Individual d6 results (1-3 dice)"
    )
    die_successes: list[bool] = Field(
        description="Whether each die succeeded (parallel to individual_rolls)"
    )
    laser_feelings_indices: list[int] = Field(
        default_factory=list,
        description="Indices of dice that rolled exact match (LASER FEELINGS)"
    )
    total_successes: int = Field(
        ge=0,
        le=3,
        description="Total number of successful dice (0-3)"
    )
    outcome: RollOutcome = Field(
        description="Roll outcome based on success count"
    )
    gm_question: str | None = Field(
        default=None,
        description="Optional question to ask GM if LASER FEELINGS occurred"
    )
    timestamp: datetime

    @field_validator('timestamp')
    @classmethod
    def validate_timezone_aware(cls, v: datetime) -> datetime:
        """Ensure timestamp is timezone-aware"""
        if v.tzinfo is None:
            raise ValueError("timestamp must be timezone-aware")
        return v

    @model_validator(mode='after')
    def validate_list_consistency(self):
        """Validate that all list fields are consistent with each other"""
        # Validate die_successes length matches individual_rolls
        if len(self.individual_rolls) != len(self.die_successes):
            raise ValueError(
                f"individual_rolls length ({len(self.individual_rolls)}) "
                f"must match die_successes length ({len(self.die_successes)})"
            )

        # Validate laser_feelings_indices are valid
        for idx in self.laser_feelings_indices:
            if idx < 0 or idx >= len(self.individual_rolls):
                raise ValueError(
                    f"laser_feelings_indices contains invalid index {idx} "
                    f"(valid range: 0-{len(self.individual_rolls)-1})"
                )

        # Validate total_successes matches actual count
        actual_successes = sum(self.die_successes)
        if self.total_successes != actual_successes:
            raise ValueError(
                f"total_successes ({self.total_successes}) doesn't match "
                f"count of successful dice ({actual_successes})"
            )

        return self

    @property
    def has_laser_feelings(self) -> bool:
        """Whether any die rolled exactly the character number"""
        return len(self.laser_feelings_indices) > 0

    @property
    def dice_count(self) -> int:
        """Total number of dice rolled"""
        return len(self.individual_rolls)
