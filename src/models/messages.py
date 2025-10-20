# ABOUTME: Pydantic models for three-channel message routing and DM commands.
# ABOUTME: Defines IC/OOC/P2C channels with visibility rules, plus DM command structures.

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class MessageChannel(str, Enum):
    """Communication channels with different visibility rules"""
    IC = "in_character"  # Characters see, players get summary
    OOC = "out_of_character"  # Only players see
    P2C = "player_to_character"  # Private directive


class MessageType(str, Enum):
    """Types of messages in the system"""
    NARRATION = "narration"  # DM narration
    DIALOGUE = "dialogue"  # Character dialogue
    ACTION = "action"  # Character action
    REACTION = "reaction"  # Character reaction
    DISCUSSION = "discussion"  # Player OOC discussion
    DIRECTIVE = "directive"  # Player -> Character directive
    SYSTEM = "system"  # System messages


class Message(BaseModel):
    """Base message structure for all communications"""

    message_id: str = Field(
        description="Unique message identifier"
    )
    channel: MessageChannel
    from_agent: str = Field(
        description="Sender agent_id or 'dm'"
    )
    to_agents: list[str] | None = Field(
        default=None,
        description="Recipient agent_ids (None = broadcast)"
    )
    content: str
    timestamp: datetime
    message_type: MessageType = Field(
        description="Type of message being sent"
    )
    phase: str = Field(
        description="Game phase when message was created"
    )

    # Metadata
    turn_number: int
    session_number: int | None = None

    model_config = {"use_enum_values": True}


class DirectiveMessage(BaseModel):
    """Player-to-character directive (one-way communication)"""

    from_player: str = Field(description="Player agent_id")
    to_character: str = Field(description="Character character_id")
    strategic_directive: str = Field(
        description="High-level instruction to character"
    )
    scene_context: str = Field(
        description="Relevant scene information for interpretation"
    )
    timestamp: datetime

    # Interpretation tracking
    interpreted_as: str | None = Field(
        default=None,
        description="How character interpreted directive (filled after action)"
    )


class ICMessageSummary(BaseModel):
    """Summary of IC action for player layer visibility"""

    character_id: str
    action_summary: str = Field(
        description="High-level summary of what character did"
    )
    outcome_summary: str | None = Field(
        default=None,
        description="DM-narrated result (if available)"
    )
    turn_number: int
    timestamp: datetime


class DMCommandType(str, Enum):
    """Types of DM commands"""
    NARRATE = "narrate"  # Begin turn with narration
    ROLL = "roll"  # Override dice result
    SUCCESS = "success"  # Force success
    FAILURE = "failure"  # Force failure
    PAUSE = "pause"  # Pause game
    RESUME = "resume"  # Resume game
    SAVE = "save"  # Save game state
    LOAD = "load"  # Load game state
    STATUS = "status"  # Show current status
    HELP = "help"  # Show help


class DMCommand(BaseModel):
    """DM command structure"""

    command_type: DMCommandType
    args: dict[str, str | int | bool] = Field(
        default_factory=dict,
        description="Command arguments"
    )
    timestamp: datetime

    model_config = {"use_enum_values": True}


class DiceRoll(BaseModel):
    """Dice roll result structure"""

    notation: str = Field(
        description="Dice notation (e.g., '2d6', '1d20+5')"
    )
    dice_count: int = Field(
        ge=1,
        description="Number of dice rolled"
    )
    dice_sides: int = Field(
        ge=2,
        description="Number of sides per die"
    )
    modifier: int = Field(
        default=0,
        description="Static modifier to add"
    )
    individual_rolls: list[int] = Field(
        description="Individual die results"
    )
    total: int = Field(
        description="Sum of rolls + modifier"
    )
    timestamp: datetime

    @property
    def rolls_sum(self) -> int:
        """Sum of individual rolls before modifier"""
        return sum(self.individual_rolls)


# Visibility matrix enforced at routing layer
VISIBILITY_RULES = {
    MessageChannel.IC: {
        "characters": True,  # Full access
        "base_personas": "summary_only"  # Filtered view via ICMessageSummary
    },
    MessageChannel.OOC: {
        "characters": False,  # No access
        "base_personas": True  # Full access
    },
    MessageChannel.P2C: {
        "characters": "recipient_only",  # Only target character
        "base_personas": False  # No access (one-way)
    }
}
