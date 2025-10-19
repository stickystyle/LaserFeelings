# ABOUTME: Pydantic models for Graphiti memory edges with temporal validation and corruption tracking.
# ABOUTME: Extends Graphiti's base edge schema with TTRPG-specific metadata and memory quality tracking.

from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field, field_validator


class MemoryType(str, Enum):
    """Types of memory stored"""
    EPISODIC = "episodic"  # Session-based events
    SEMANTIC = "semantic"  # Facts about world, NPCs
    PROCEDURAL = "procedural"  # Strategies, patterns


class CorruptionType(str, Enum):
    """Types of memory corruption"""
    DETAIL_DRIFT = "detail_drift"  # Small details change
    EMOTIONAL_COLORING = "emotional_coloring"  # Mood affects recall
    CONFLATION = "conflation"  # Memories blend
    SIMPLIFICATION = "simplification"  # Nuance lost
    FALSE_CONFIDENCE = "false_confidence"  # Add invented details


class MemoryEdge(BaseModel):
    """Extended Graphiti Edge with custom properties"""

    # Core Graphiti fields
    uuid: str
    fact: str
    valid_at: datetime
    invalid_at: datetime | None = None
    episode_ids: list[str]
    source_node_uuid: str
    target_node_uuid: str

    # Custom TTRPG fields
    agent_id: str = Field(
        description="Which agent owns this memory (group_id in Graphiti)"
    )
    memory_type: MemoryType
    session_number: int = Field(ge=1)
    days_elapsed: int = Field(ge=0, description="In-game time when memory formed")

    # Memory quality metadata
    confidence: float = Field(
        default=1.0, ge=0.0, le=1.0,
        description="Certainty score (1.0=fresh, decreases with corruption)"
    )
    importance: float = Field(
        default=0.5, ge=0.0, le=1.0,
        description="Event significance (affects decay rate)"
    )
    rehearsal_count: int = Field(
        default=0, ge=0,
        description="How often memory has been accessed (resists decay)"
    )

    # Corruption tracking
    corruption_type: CorruptionType | None = None
    original_uuid: str | None = Field(
        default=None,
        description="Reference to uncorrupted edge (if this is corrupted)"
    )
    corruption_probability: float | None = Field(
        default=None, ge=0.0, le=1.0,
        description="Calculated probability this memory is corrupted"
    )

    @field_validator('invalid_at')
    @classmethod
    def validate_temporal_consistency(cls, v, info):
        """Ensure invalid_at is after valid_at if both are set"""
        if v is not None and 'valid_at' in info.data:
            valid_at = info.data['valid_at']
            if v <= valid_at:
                raise ValueError(
                    f"invalid_at ({v}) must be after valid_at ({valid_at})"
                )
        return v

    model_config = {"use_enum_values": True}


class CorruptionConfig(BaseModel):
    """Configuration for memory corruption behavior"""

    enabled: bool = Field(
        default=False,
        description="Whether memory corruption is active"
    )
    global_strength: float = Field(
        default=0.5, ge=0.0, le=1.0,
        description="Global corruption rate multiplier (0=none, 1=maximum)"
    )
    corruption_types_enabled: list[CorruptionType] = Field(
        default_factory=lambda: list(CorruptionType),
        description="Which corruption types can occur"
    )
    min_days_before_corruption: int = Field(
        default=7, ge=0,
        description="Minimum in-game days before corruption can occur"
    )
    important_memory_threshold: float = Field(
        default=0.8, ge=0.0, le=1.0,
        description="Importance level that makes memories more resistant"
    )
    rehearsal_immunity_threshold: int = Field(
        default=20, ge=0,
        description="Rehearsal count above which memories become immune"
    )

    model_config = {"use_enum_values": True}


class MemoryNode(BaseModel):
    """Extended Graphiti Node for entities"""

    # Core Graphiti fields
    uuid: str
    name: str
    labels: list[str]  # e.g., ["NPC", "Person"], ["Location", "Tavern"]

    # Custom TTRPG fields
    entity_type: str = Field(
        description="Type of entity: npc, location, item, quest, faction"
    )
    first_seen_session: int
    last_seen_session: int
    relationship_strength: dict[str, float] = Field(
        default_factory=dict,
        description="agent_id -> relationship score (-1 to 1)"
    )


class EpisodeMetadata(BaseModel):
    """Metadata for game session episodes"""

    episode_id: str
    session_number: int
    name: str = Field(
        description="Session name (e.g., 'Session 5: The Merchant's Gambit')"
    )
    reference_time: datetime = Field(
        description="When session occurred in real life"
    )
    in_game_days_elapsed: int = Field(
        description="In-game time at session start"
    )
    turn_count: int
    group_id: str = Field(
        description="Campaign identifier (e.g., 'campaign_main')"
    )

    # Session summary
    key_events: list[str] = Field(default_factory=list)
    npcs_introduced: list[str] = Field(default_factory=list)
    locations_visited: list[str] = Field(default_factory=list)
