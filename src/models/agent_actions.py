# ABOUTME: Pydantic models for agent strategic intent, directives, actions, and reactions.
# ABOUTME: Defines the contract between BasePersona (player) and Character (roleplay) layers.

from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field, model_validator


class Intent(BaseModel):
    """Strategic intent formulated by BasePersona agent (player layer)"""

    agent_id: str = Field(
        description="Agent ID of the player formulating this intent"
    )
    strategic_goal: str = Field(
        description="High-level objective the player wants to achieve"
    )
    reasoning: str = Field(
        description="Why this approach was chosen"
    )
    risk_assessment: str | None = Field(
        default=None,
        description="Identified risks and mitigation strategies"
    )
    fallback_plan: str | None = Field(
        default=None,
        description="Alternative approach if primary goal fails"
    )


class Directive(BaseModel):
    """High-level instruction from player to character (P2C channel)"""

    from_player: str = Field(
        description="Base persona agent ID issuing the directive"
    )
    to_character: str = Field(
        description="Character ID receiving the directive"
    )
    instruction: str = Field(
        description="High-level action to perform (what, not how)"
    )
    tactical_guidance: str | None = Field(
        default=None,
        description="Optional tactical approach suggestions"
    )
    emotional_tone: str | None = Field(
        default=None,
        description="How character should feel/approach the situation"
    )


class Action(BaseModel):
    """In-character action performed by Character agent as cohesive narrative prose"""

    character_id: str = Field(
        description="Character ID performing the action"
    )
    narrative_text: str = Field(
        description="Complete action as flowing narrative combining intent, dialogue, and mannerisms"
    )

    # Dice roll suggestion fields
    task_type: Literal["lasers", "feelings"] | None = Field(
        default=None,
        description="Suggested task classification: 'lasers' (logic/tech) or 'feelings' (social/emotion)"
    )
    is_prepared: bool = Field(
        default=False,
        description="Whether character is prepared for this task (requests +1d6 bonus dice from DM)"
    )
    prepared_justification: str | None = Field(
        default=None,
        description="Explanation of why character is prepared (e.g., gathered intel, brought tools)"
    )
    is_expert: bool = Field(
        default=False,
        description="Whether character is expert at this task (requests +1d6 bonus dice from DM)"
    )
    expert_justification: str | None = Field(
        default=None,
        description="Explanation of why character is expert (e.g., extensive training, natural talent)"
    )
    is_helping: bool = Field(
        default=False,
        description="Whether character is helping another character (requests +1d6 bonus dice from DM for helped character)"
    )
    helping_character_id: str | None = Field(
        default=None,
        pattern=r"^char_[a-z0-9_]+$",
        description="Character ID of the character being helped (if is_helping=True)"
    )
    help_justification: str | None = Field(
        default=None,
        description="Explanation of how character is helping (e.g., providing cover fire, technical assistance)"
    )

    @model_validator(mode="after")
    def validate_justification_consistency(self) -> "Action":
        """Ensure justifications are provided when corresponding flags are True"""
        if self.is_prepared and not self.prepared_justification:
            raise ValueError("prepared_justification is required when is_prepared=True")

        if self.is_expert and not self.expert_justification:
            raise ValueError("expert_justification is required when is_expert=True")

        if self.is_helping:
            if not self.helping_character_id:
                raise ValueError("helping_character_id is required when is_helping=True")
            if not self.help_justification:
                raise ValueError("help_justification is required when is_helping=True")
            # Prevent characters from helping themselves
            if self.helping_character_id == self.character_id:
                raise ValueError("Characters cannot help themselves (helping_character_id cannot equal character_id)")

        return self


class Reaction(BaseModel):
    """In-character emotional response to DM's outcome narration as cohesive narrative prose"""

    character_id: str = Field(
        description="Character ID reacting"
    )
    narrative_text: str = Field(
        description="Complete reaction as flowing narrative combining emotional response, dialogue, and next intent"
    )


class CharacterState(BaseModel):
    """Current state of a character for context-aware decision making"""

    character_id: str
    current_location: str | None = None
    health_status: str | None = None
    emotional_state: str | None = None
    active_effects: list[str] = Field(
        default_factory=list,
        description="Active status effects, buffs, debuffs"
    )


class PrimaryEmotion(str, Enum):
    """Primary emotional states for character reactions"""
    JOY = "joy"
    ANGER = "anger"
    FEAR = "fear"
    SADNESS = "sadness"
    DISGUST = "disgust"
    SURPRISE = "surprise"
    NEUTRAL = "neutral"


class EmotionalState(BaseModel):
    """Emotional state model for character reactions"""

    primary_emotion: PrimaryEmotion = Field(
        description="The dominant emotion the character is feeling"
    )
    intensity: float = Field(
        ge=0.0,
        le=1.0,
        description="Intensity of the primary emotion (0=none, 1=extreme)"
    )
    secondary_emotions: list[str] = Field(
        default_factory=list,
        description="Additional emotions present (e.g., 'hopeful', 'frustrated')"
    )

    model_config = {"use_enum_values": True}
