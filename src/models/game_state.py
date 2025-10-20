# ABOUTME: Pydantic models for LangGraph game state, validation results, and consensus detection.
# ABOUTME: Defines the turn cycle phases, state transitions, and validation structures.

from datetime import datetime
from enum import Enum
from typing import Literal, NotRequired, TypedDict

from pydantic import BaseModel, Field


class ActionDict(TypedDict):
    """TypedDict representation of Action model for GameState character_actions"""
    character_id: str
    narrative_text: str
    task_type: NotRequired[Literal["lasers", "feelings"] | None]
    is_prepared: NotRequired[bool]
    prepared_justification: NotRequired[str | None]
    is_expert: NotRequired[bool]
    expert_justification: NotRequired[str | None]
    is_helping: NotRequired[bool]
    helping_character_id: NotRequired[str | None]
    help_justification: NotRequired[str | None]


class GamePhase(str, Enum):
    """Turn cycle phases in LangGraph state machine"""
    DM_NARRATION = "dm_narration"
    MEMORY_QUERY = "memory_query"
    STRATEGIC_INTENT = "strategic_intent"
    OOC_DISCUSSION = "ooc_discussion"
    CONSENSUS_DETECTION = "consensus_detection"
    CHARACTER_ACTION = "character_action"
    VALIDATION = "validation"
    DM_ADJUDICATION = "dm_adjudication"
    DICE_RESOLUTION = "dice_resolution"
    DM_OUTCOME = "dm_outcome"
    CHARACTER_REACTION = "character_reaction"
    MEMORY_STORAGE = "memory_storage"


class GameState(TypedDict):
    """Root state for LangGraph turn cycle"""

    # Phase tracking
    current_phase: Literal[
        "dm_narration",
        "memory_query",
        "strategic_intent",
        "ooc_discussion",
        "consensus_detection",
        "character_action",
        "validation",
        "dm_adjudication",
        "dice_resolution",
        "dm_outcome",
        "character_reaction",
        "memory_storage"
    ]
    phase_start_time: datetime
    turn_number: int

    # DM input
    dm_narration: str
    dm_adjudication_needed: bool
    dice_override: NotRequired[int | None]  # Optional DM override for dice
    dm_outcome: NotRequired[str]

    # Active agents
    active_agents: list[str]  # List of agent_ids participating

    # Strategic layer (player level)
    strategic_intents: dict[str, str]  # agent_id -> intent
    ooc_messages: list[dict]  # Strategic discussion messages
    consensus_state: NotRequired[Literal["unanimous", "majority", "conflicted", "timeout"]]

    # Character layer (roleplay level)
    character_actions: dict[str, ActionDict]  # character_id -> Action model dict
    character_reactions: dict[str, str]  # character_id -> reaction

    # Validation state
    validation_attempt: int
    validation_valid: bool
    validation_failures: dict[str, list[str]]  # character_id -> violations

    # Memory retrieval
    retrieved_memories: dict[str, list[dict]]  # agent_id -> memory list

    # Dice resolution - Uses multi-die success counting system
    # Lasers & Feelings rules: Roll 1d6 per die, each die succeeds independently
    # - Lasers task: die succeeds if roll < character's number
    # - Feelings task: die succeeds if roll > character's number
    # - LASER FEELINGS: exact match on any die (prompts DM question)
    dice_action_character: NotRequired[str]  # Which character is rolling
    dice_task_type: NotRequired[Literal["lasers", "feelings"]]  # Task classification
    dice_count: NotRequired[int]  # Number of dice rolled (1-3: base + prepared + expert)
    individual_rolls: NotRequired[list[int]]  # Each individual die result (1-6)
    die_successes: NotRequired[list[bool]]  # Which individual dice succeeded (per-die success)
    total_successes: NotRequired[int]  # Total count of successful dice
    laser_feelings_indices: NotRequired[list[int]]  # Indices with exact match (LASER FEELINGS)
    outcome: NotRequired[Literal["failure", "barely", "success", "critical"]]  # Semantic outcome
    is_prepared: NotRequired[bool]  # Character was prepared (bonus die granted)
    is_expert: NotRequired[bool]  # Character is expert (bonus die granted)
    gm_question: NotRequired[str | None]  # Question for DM when LASER FEELINGS occurs
    laser_feelings_answer: NotRequired[str | None]  # DM's answer to LASER FEELINGS question

    # DEPRECATED fields (kept for backward compatibility)
    dice_result: NotRequired[int]  # DEPRECATED: Use individual_rolls[0] instead
    dice_success: NotRequired[bool]  # DEPRECATED: Use die_successes or total_successes
    dice_complication: NotRequired[bool]  # DEPRECATED: "complication" is old terminology for LASER FEELINGS. Use len(laser_feelings_indices) > 0
    laser_feelings_occurred: NotRequired[bool]  # DEPRECATED: Use len(laser_feelings_indices) > 0

    # Session tracking
    session_number: int  # Current game session number

    # Error handling
    error_state: NotRequired[str | None]
    retry_count: int
    rollback_phase: NotRequired[str | None]
    dm_review_required: NotRequired[bool]  # Flag for DM manual review after validation failures


class MemoryQueryState(TypedDict):
    """State specific to memory query phase"""

    agent_id: str
    query_text: str
    temporal_constraint: NotRequired[dict]  # {session_start, session_end}
    limit: int
    results: NotRequired[list[dict]]


class ValidationState(TypedDict):
    """State specific to validation phase"""

    character_id: str
    narrative_text: str
    attempt: int
    valid: bool
    violations: list[str]
    forbidden_patterns: list[str]
    suggestion: str | None
    previous_violation: str | None


class ValidationResult(BaseModel):
    """Result from action validation"""

    valid: bool
    violations: list[str] = Field(default_factory=list)
    forbidden_patterns: list[str] = Field(default_factory=list)
    suggestion: str | None = None

    # Validation metadata
    method: Literal["pattern", "llm", "hybrid"] = "pattern"
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)


class Stance(str, Enum):
    """Stance classification for consensus detection"""
    AGREE = "agree"
    DISAGREE = "disagree"
    NEUTRAL = "neutral"
    SILENT = "silent"


class Position(BaseModel):
    """Agent's position in consensus discussion"""

    agent_id: str
    stance: Stance
    confidence: float = Field(
        ge=0.0, le=1.0,
        description="Confidence in stance classification"
    )
    supporting_text: str | None = Field(
        default=None,
        description="Text excerpt supporting this classification"
    )

    model_config = {"use_enum_values": True}


class ConsensusState(TypedDict):
    """State specific to consensus detection"""

    messages: list[dict]
    agents: list[str]
    positions: dict[str, dict]  # agent_id -> {stance, confidence}
    result: Literal["unanimous", "majority", "conflicted", "timeout"]
    round_count: int
    start_time: datetime


class ConsensusResult(BaseModel):
    """Result from consensus detection"""

    result: Literal["unanimous", "majority", "conflicted", "timeout"]
    positions: dict[str, Position]
    round_count: int
    duration_seconds: float
    agreed_agents: list[str] = Field(default_factory=list)
    disagreed_agents: list[str] = Field(default_factory=list)
    neutral_agents: list[str] = Field(default_factory=list)

    @property
    def agreement_percentage(self) -> float:
        """Calculate percentage of agents in agreement"""
        total = len(self.positions)
        if total == 0:
            return 0.0
        return len(self.agreed_agents) / total
