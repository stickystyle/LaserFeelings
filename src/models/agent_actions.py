# ABOUTME: Pydantic models for agent strategic intent, directives, actions, and reactions.
# ABOUTME: Defines the contract between BasePersona (player) and Character (roleplay) layers.

from enum import Enum

from pydantic import BaseModel, Field


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
