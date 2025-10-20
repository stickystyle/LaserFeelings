# ABOUTME: Pydantic model for the crew's starship configuration in Lasers & Feelings.
# ABOUTME: Ship attributes are purely narrative and provide NO mechanical dice bonuses.

from typing import Literal

from pydantic import BaseModel, Field, field_validator


# Valid ship strengths from Lasers & Feelings rules (line 85-88)
ShipStrength = Literal[
    "Fast",
    "Nimble",
    "Well-Armed",
    "Powerful Shields",
    "Superior Sensors",
    "Cloaking Device",
    "Fightercraft"
]

# Valid ship problems from Lasers & Feelings rules (line 94-97)
ShipProblem = Literal[
    "Fuel Hog",
    "Only One Medical Pod",
    "Horrible Circuit Breakers",
    "Grim Reputation"
]


class ShipConfig(BaseModel):
    """
    Configuration for the crew's starship.

    In Lasers & Feelings, the ship is collectively defined by the crew with:
    - Two strengths (capabilities)
    - One problem (ongoing complication)

    **IMPORTANT**: Ship attributes are PURELY NARRATIVE. They do not provide
    dice bonuses or penalties. They create fictional situations and complications
    for the GM to use in storytelling.

    From the Lasers & Feelings rules (lines 101-102):
    "Ship strengths and problems are purely narrative. They don't provide dice
    bonuses or penalties. They create fictional situations and complications for
    the GM to use in storytelling."

    Example:
        ship = ShipConfig(
            name="The Raptor",
            strengths=["Fast", "Nimble"],
            problem="Fuel Hog"
        )
    """

    name: str = Field(
        description="Ship name (e.g., 'The Raptor', 'Starlight Runner')",
        min_length=1
    )

    strengths: list[ShipStrength] = Field(
        description="Two ship strengths (narrative capabilities, not mechanical bonuses)",
        min_length=2,
        max_length=2
    )

    problem: ShipProblem = Field(
        description="One ship problem (narrative complication, not mechanical penalty)"
    )

    @field_validator('name')
    @classmethod
    def validate_name_not_whitespace(cls, v: str) -> str:
        """Ensure ship name is not just whitespace"""
        if v.strip() == "":
            raise ValueError("Ship name cannot be only whitespace")
        return v

    def to_narrative_description(self) -> str:
        """
        Returns a human-readable description of the ship for scene context.

        This description should be included in scene context so that AI agents
        are aware of the ship's narrative capabilities and complications when
        making decisions or roleplaying.

        Returns:
            Formatted string describing the ship
        """
        strengths_str = ", ".join(self.strengths)
        return (
            f"Ship: {self.name} "
            f"(Strengths: {strengths_str}; Problem: {self.problem})"
        )

    model_config = {"frozen": True}  # Immutable configuration
