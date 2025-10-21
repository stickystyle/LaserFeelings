# ABOUTME: Pydantic models for agent personality traits and character sheets.
# ABOUTME: Defines the dual-layer architecture: strategic player persona + in-character roleplay layer.

from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field, field_validator


class PlayStyle(str, Enum):
    """Strategic preferences for gameplay"""
    ANALYTICAL_PLANNER = "analytical_planner"
    BOLD_IMPROVISER = "bold_improviser"
    TEAM_COORDINATOR = "team_coordinator"
    BALANCED_STRATEGIST = "balanced_strategist"


class CharacterStyle(str, Enum):
    """Canonical character archetypes from Lasers & Feelings"""
    ALIEN = "Alien"
    ANDROID = "Android"
    DANGEROUS = "Dangerous"
    HEROIC = "Heroic"
    HOT_SHOT = "Hot-Shot"
    INTREPID = "Intrepid"
    SAVVY = "Savvy"


class CharacterRole(str, Enum):
    """Canonical character roles from Lasers & Feelings"""
    DOCTOR = "Doctor"
    ENVOY = "Envoy"
    ENGINEER = "Engineer"
    EXPLORER = "Explorer"
    PILOT = "Pilot"
    SCIENTIST = "Scientist"
    SOLDIER = "Soldier"


class PlayerPersonality(BaseModel):
    """Personality traits affecting strategic decision-making"""

    analytical_score: float = Field(
        ge=0.0, le=1.0,
        description="How analytical vs intuitive (0=pure gut, 1=pure logic)"
    )
    risk_tolerance: float = Field(
        ge=0.0, le=1.0,
        description="Willingness to take risks (0=cautious, 1=reckless)"
    )
    detail_oriented: float = Field(
        ge=0.0, le=1.0,
        description="Focus on details vs big picture (affects memory decay)"
    )
    emotional_memory: float = Field(
        ge=0.0, le=1.0,
        description="How much emotions color memories (0=factual, 1=mood-driven)"
    )
    assertiveness: float = Field(
        ge=0.0, le=1.0,
        description="Tendency to lead vs follow (0=follower, 1=leader)"
    )
    cooperativeness: float = Field(
        ge=0.0, le=1.0,
        description="Preference for teamwork vs solo action"
    )
    openness: float = Field(
        ge=0.0, le=1.0,
        description="Acceptance of new ideas vs traditional approaches"
    )
    rule_adherence: float = Field(
        ge=0.0, le=1.0,
        description="Respect for game rules vs creative interpretation"
    )
    roleplay_intensity: float = Field(
        ge=0.0, le=1.0,
        description="How much player stays in-character vs metagaming"
    )
    base_decay_rate: float = Field(
        default=0.5, ge=0.0, le=1.0,
        description="Base memory corruption rate before modifiers"
    )

    @property
    def decision_style(self) -> str:
        """Strategic preference based on personality"""
        if self.analytical_score > 0.7:
            return PlayStyle.ANALYTICAL_PLANNER.value
        elif self.risk_tolerance > 0.7:
            return PlayStyle.BOLD_IMPROVISER.value
        elif self.cooperativeness > 0.7:
            return PlayStyle.TEAM_COORDINATOR.value
        else:
            return PlayStyle.BALANCED_STRATEGIST.value

    model_config = {"frozen": True}  # Immutable after creation


class CharacterSheet(BaseModel):
    """Lasers & Feelings character sheet for in-character roleplay layer"""

    # Lasers & Feelings core attributes
    name: str = Field(description="Character name")
    style: CharacterStyle = Field(description="Character archetype")
    role: CharacterRole = Field(description="Character job/function")
    number: int = Field(
        ge=2, le=5,
        description="Lasers (low) vs Feelings (high) balance"
    )
    character_goal: str = Field(
        description="In-character motivation (e.g., 'Become Captain')"
    )
    equipment: list[str] = Field(
        default_factory=list,
        description="Items character carries"
    )

    # Roleplay personality traits
    speech_patterns: list[str] = Field(
        default_factory=list,
        description="How character speaks (e.g., 'Speaks formally', 'Uses technical jargon')"
    )
    mannerisms: list[str] = Field(
        default_factory=list,
        description="Personality quirks (e.g., 'Taps fingers when anxious')"
    )

    @field_validator('name', 'character_goal')
    @classmethod
    def validate_non_empty_string(cls, v: str, info) -> str:
        """Ensure name and character_goal are non-empty strings"""
        if not v or not v.strip():
            raise ValueError(f'{info.field_name} cannot be empty')
        return v

    @field_validator('number', mode='before')
    @classmethod
    def validate_number_type(cls, v):
        """Ensure number is an integer, not a string"""
        if isinstance(v, str):
            raise ValueError('number must be an integer, not a string')
        return v

    @property
    def approach_bias(self) -> Literal["lasers", "feelings", "balanced"]:
        """Determine preferred problem-solving approach from number"""
        if self.number == 2:
            return "lasers"  # Logical, technical
        elif self.number == 5:
            return "feelings"  # Intuitive, emotional
        else:
            return "balanced"

    @field_validator('speech_patterns', 'mannerisms', mode='before')
    @classmethod
    def ensure_list(cls, v):
        if v is None:
            return []
        return v

    model_config = {"use_enum_values": True, "frozen": True}
