# Data Models: AI TTRPG Player System

**Date**: October 18, 2025
**Status**: Phase 1 Design
**Purpose**: Define core entities, validation rules, state transitions, and relationships

---

## Overview

This document specifies all data models for the AI TTRPG Player System using Pydantic 2.x for validation. Models are organized by domain layer.

---

## 1. Agent Layer Models

### 1.1 AgentPersonality

**Purpose**: Define personality traits affecting strategic decision-making and memory corruption for base persona agents.

```python
from pydantic import BaseModel, Field
from typing import List
from enum import Enum

class PlayStyle(str, Enum):
    CAUTIOUS = "cautious"
    AGGRESSIVE = "aggressive"
    DIPLOMATIC = "diplomatic"
    CHAOTIC = "chaotic"
    ANALYTICAL = "analytical"

class AgentPersonality(BaseModel):
    """Base persona agent personality configuration"""

    # Identity
    agent_id: str = Field(..., description="Unique agent identifier", pattern=r"^agent_[a-z0-9_]+$")
    name: str = Field(..., description="Human-readable agent name", min_length=1, max_length=50)

    # Core personality traits (0.0 to 1.0 scale)
    risk_tolerance: float = Field(..., ge=0.0, le=1.0, description="Willingness to take risks")
    analytical_score: float = Field(..., ge=0.0, le=1.0, description="Logical vs intuitive thinking")
    emotional_memory: float = Field(..., ge=0.0, le=1.0, description="Emotional influence on recall")
    detail_oriented: float = Field(..., ge=0.0, le=1.0, description="Attention to specifics")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Self-assuredness level")

    # Strategic preferences
    play_style: PlayStyle = Field(..., description="Primary gameplay approach")
    preferred_tactics: List[str] = Field(default_factory=list, description="Favorite strategies")

    # Memory corruption parameters
    base_decay_rate: float = Field(default=0.3, ge=0.0, le=1.0, description="Baseline memory degradation")

    model_config = {
        "json_schema_extra": {
            "example": {
                "agent_id": "agent_alex_001",
                "name": "Alex",
                "risk_tolerance": 0.3,
                "analytical_score": 0.8,
                "emotional_memory": 0.4,
                "detail_oriented": 0.9,
                "confidence": 0.7,
                "play_style": "cautious",
                "preferred_tactics": ["stealth", "negotiation", "planning"],
                "base_decay_rate": 0.2
            }
        }
    }
```

**Validation Rules**:
- All scores must be in range [0.0, 1.0]
- `agent_id` must follow pattern `agent_[name]_[number]`
- `name` cannot be empty or exceed 50 characters
- `preferred_tactics` can be empty list

**Relationships**:
- 1:1 with BasePersonaAgent instance
- 1:1 with CharacterSheet (paired player-character)

---

### 1.2 CharacterSheet

**Purpose**: Define in-character personality and attributes for character agents using Lasers & Feelings game system.

**Reference**: See `lasers_and_feelings_rpg.pdf` and `56udLX.png` character sheet template.

```python
from pydantic import BaseModel, Field
from typing import Optional, List
from enum import Enum

class Style(str, Enum):
    """Lasers & Feelings character archetypes"""
    ALIEN = "Alien"
    ANDROID = "Android"
    DANGEROUS = "Dangerous"
    HEROIC = "Heroic"
    HOT_SHOT = "Hot-Shot"
    INTREPID = "Intrepid"
    SAVVY = "Savvy"

class Role(str, Enum):
    """Lasers & Feelings character roles/jobs"""
    DOCTOR = "Doctor"
    ENVOY = "Envoy"
    ENGINEER = "Engineer"
    EXPLORER = "Explorer"
    PILOT = "Pilot"
    SCIENTIST = "Scientist"
    SOLDIER = "Soldier"

class CharacterSheet(BaseModel):
    """Character agent identity and personality (Lasers & Feelings system)"""

    # Identity
    character_id: str = Field(..., description="Unique character identifier", pattern=r"^char_[a-z0-9_]+$")
    character_name: str = Field(..., description="In-game character name", min_length=1, max_length=50)

    # Lasers & Feelings core attributes
    style: Style = Field(..., description="Character archetype from L&F system")
    role: Role = Field(..., description="Character job/function from L&F system")
    number: int = Field(..., ge=2, le=5, description="Lasers (low) vs Feelings (high) balance")

    # Goals (dual layer)
    player_goal: str = Field(..., description="What player wants to do (OOC)", max_length=200)
    character_goal: str = Field(..., description="What character wants (IC)", max_length=200)

    # Equipment
    equipment: List[str] = Field(default_factory=list, description="Items character carries", max_length=10)

    # Derived roleplay attributes (from STYLE + ROLE)
    speech_patterns: str = Field(..., description="How character speaks", max_length=200)
    mannerisms: Optional[str] = Field(default=None, description="Physical mannerisms", max_length=200)

    model_config = {
        "json_schema_extra": {
            "example": {
                "character_id": "char_zara_001",
                "character_name": "Zara-7",
                "style": "Android",
                "role": "Engineer",
                "number": 3,
                "player_goal": "Get involved in crazy space adventures and make best of them",
                "character_goal": "Understand human emotions and prove worth to crew",
                "equipment": ["Repair kit", "Multitool", "Emergency beacon"],
                "speech_patterns": "Precise, formal language. Uses technical jargon. Asks clarifying questions.",
                "mannerisms": "Tilts head when confused. Pauses before emotional responses."
            }
        }
    }
```

**Validation Rules**:
- `character_id` must follow pattern `char_[name]_[number]`
- `style` must be one of canonical L&F styles
- `role` must be one of canonical L&F roles
- `number` must be integer 2-5 (per L&F rules)
- `equipment` list max 10 items
- `player_goal` and `character_goal` max 200 characters

**Game Mechanics Integration**:
- **number = 2**: Better at Lasers (logic/tech). Roll 1d6 under 2 for Lasers tasks, over 2 for Feelings tasks
- **number = 3**: Balanced. Roll under 3 for Lasers, over 3 for Feelings
- **number = 4**: Balanced. Roll under 4 for Lasers, over 4 for Feelings
- **number = 5**: Better at Feelings (emotion/intuition). Roll under 5 for Lasers, over 5 for Feelings
- **Rolling exactly your number**: Success with a twist/complication

**Relationships**:
- 1:1 with CharacterAgent instance
- 1:1 with AgentPersonality (paired player-character)

---

### 1.3 ShipState

**Purpose**: Define shared party ship state from Lasers & Feelings system.

**Reference**: See `56udLX.png` character sheet template - "YOUR SHIP" section.

```python
from pydantic import BaseModel, Field
from typing import List

class ShipState(BaseModel):
    """Shared party ship state (Lasers & Feelings system)"""

    # Ship identity
    ship_name: str = Field(default="The Raptor", description="Ship name", max_length=50)

    # Ship attributes
    strengths: List[str] = Field(default_factory=list, description="What ship is good at", max_length=5)
    problem: str = Field(..., description="Current ship malfunction or issue", max_length=200)

    # Metadata
    last_updated_session: int = Field(..., ge=1, description="Session when ship state last changed")

    model_config = {
        "json_schema_extra": {
            "example": {
                "ship_name": "The Raptor",
                "strengths": ["Fast", "Well-armed", "Cloaking device"],
                "problem": "Life support system failing - 48 hours of air remaining",
                "last_updated_session": 1
            }
        }
    }
```

**Validation Rules**:
- `ship_name` max 50 characters
- `strengths` list max 5 items
- `problem` max 200 characters (should be concise, pressing issue)
- `last_updated_session` must be positive integer

**Design Notes**:
- Ship state is **shared** across all party members and influences strategic decisions
- Ship `problem` creates party-wide pressure and drives adventure hooks
- Strengths provide narrative options for creative solutions
- DM can update ship state during gameplay to introduce new complications

**Relationships**:
- Shared by all CharacterSheet instances in the party
- Referenced during strategic planning (OOC discussion phase)
- May influence memory queries ("Can our ship handle atmospheric entry?")

---

## 2. Memory Layer Models

### 2.1 MemoryEdge

**Purpose**: Represent temporal knowledge graph edges with corruption metadata.

```python
from pydantic import BaseModel, Field, field_validator
from typing import Optional, List
from datetime import datetime
from enum import Enum
import uuid

class MemoryType(str, Enum):
    EPISODIC = "episodic"      # Specific events
    SEMANTIC = "semantic"       # General knowledge
    PROCEDURAL = "procedural"   # How-to knowledge

class CorruptionType(str, Enum):
    DETAIL_DRIFT = "detail_drift"
    EMOTIONAL_COLORING = "emotional_coloring"
    CONFLATION = "conflation"
    SIMPLIFICATION = "simplification"
    FALSE_CONFIDENCE = "false_confidence"

class MemoryEdge(BaseModel):
    """Temporal memory graph edge with corruption tracking"""

    # Identity
    uuid: str = Field(default_factory=lambda: str(uuid.uuid4()), description="Unique edge ID")
    fact: str = Field(..., description="Memory content", min_length=1, max_length=1000)

    # Temporal metadata
    valid_at: datetime = Field(..., description="When memory became valid")
    invalid_at: Optional[datetime] = Field(default=None, description="When memory was invalidated")
    session_number: int = Field(..., ge=1, description="Game session when created")
    days_elapsed: int = Field(..., ge=0, description="In-game days since campaign start")

    # Corruption metadata
    confidence: float = Field(default=1.0, ge=0.0, le=1.0, description="Memory certainty score")
    corruption_type: Optional[CorruptionType] = Field(default=None, description="Type of corruption applied")
    original_uuid: Optional[str] = Field(default=None, description="UUID of uncorrupted original")

    # Memory strength
    importance: float = Field(default=0.5, ge=0.0, le=1.0, description="Event significance")
    rehearsal_count: int = Field(default=0, ge=0, description="Times memory accessed")
    emotional_weight: float = Field(default=0.5, ge=0.0, le=1.0, description="Emotional intensity")

    # Categorization
    memory_type: MemoryType = Field(..., description="Memory category")

    # Graph relationships (stored as references)
    source_episode_id: str = Field(..., description="Episode UUID this memory came from")
    related_entities: List[str] = Field(default_factory=list, description="Related entity UUIDs")

    @field_validator("invalid_at")
    @classmethod
    def validate_temporal_consistency(cls, v: Optional[datetime], info) -> Optional[datetime]:
        """Ensure invalid_at > valid_at if set"""
        if v is not None and "valid_at" in info.data:
            if v <= info.data["valid_at"]:
                raise ValueError("invalid_at must be after valid_at")
        return v

    model_config = {
        "json_schema_extra": {
            "example": {
                "uuid": "550e8400-e29b-41d4-a716-446655440000",
                "fact": "The merchant offered 50 gold pieces for the quest",
                "valid_at": "2025-01-15T10:30:00",
                "invalid_at": None,
                "session_number": 3,
                "days_elapsed": 15,
                "confidence": 1.0,
                "corruption_type": None,
                "original_uuid": None,
                "importance": 0.7,
                "rehearsal_count": 0,
                "emotional_weight": 0.3,
                "memory_type": "episodic",
                "source_episode_id": "episode_003",
                "related_entities": ["merchant_galvin", "quest_dragon_hunt"]
            }
        }
    }
```

**Validation Rules**:
- `invalid_at` must be after `valid_at` if set
- `session_number` must be positive integer
- `days_elapsed` must be non-negative
- All probability scores in range [0.0, 1.0]

**State Transitions**:
- **Created**: `valid_at` set, `invalid_at` None, `confidence` 1.0
- **Corrupted**: New edge created with `corruption_type` set, `original_uuid` points to original
- **Invalidated**: `invalid_at` set to current time
- **Rehearsed**: `rehearsal_count` incremented on each query

**Relationships**:
- Links to Episode nodes in Neo4j
- Links to Entity nodes (NPCs, locations, items)
- References original MemoryEdge if corrupted

---

### 2.2 CorruptionConfig

**Purpose**: Configuration for memory corruption system.

```python
from pydantic import BaseModel, Field

class CorruptionConfig(BaseModel):
    """Memory corruption system configuration"""

    # Global settings
    enabled: bool = Field(default=True, description="Enable/disable corruption")
    global_strength: float = Field(default=0.5, ge=0.0, le=1.0, description="Overall corruption intensity")
    min_days_for_corruption: int = Field(default=7, ge=0, description="Minimum days before corruption applies")

    # Corruption probability modifiers
    importance_weight: float = Field(default=0.2, ge=0.0, le=1.0, description="Importance factor in probability")
    rehearsal_resistance: float = Field(default=0.05, ge=0.0, le=0.2, description="Resistance per rehearsal")

    # LLM settings for corruption generation
    corruption_model: str = Field(default="gpt-4o-mini-2024-07-18", description="LLM model for corruption")
    corruption_temperature: float = Field(default=0.7, ge=0.0, le=2.0, description="LLM temperature")

    model_config = {
        "json_schema_extra": {
            "example": {
                "enabled": True,
                "global_strength": 0.5,
                "min_days_for_corruption": 7,
                "importance_weight": 0.2,
                "rehearsal_resistance": 0.05,
                "corruption_model": "gpt-4o-mini-2024-07-18",
                "corruption_temperature": 0.7
            }
        }
    }
```

---

## 3. Orchestration Layer Models

### 3.1 GameState

**Purpose**: Represent complete game state for LangGraph state machine.

```python
from pydantic import BaseModel, Field
from typing import Dict, List, Optional
from datetime import datetime
from enum import Enum

class GamePhase(str, Enum):
    SESSION_START = "session_start"
    DM_NARRATION = "dm_narration"
    MEMORY_RETRIEVAL = "memory_retrieval"
    OOC_DISCUSSION = "ooc_discussion"
    STRATEGIC_INTENT = "strategic_intent"
    P2C_DIRECTIVE = "p2c_directive"
    CHARACTER_ACTION = "character_action"
    VALIDATION_CHECK = "validation_check"
    DM_ADJUDICATION = "dm_adjudication"
    DICE_RESOLUTION = "dice_resolution"
    DM_OUTCOME = "dm_outcome"
    CHARACTER_REACTION = "character_reaction"
    MEMORY_CONSOLIDATION = "memory_consolidation"
    SESSION_END = "session_end"

class GameState(BaseModel):
    """Complete game state for turn-based orchestration"""

    # Session tracking
    session_number: int = Field(..., ge=1, description="Current session number")
    turn_number: int = Field(..., ge=1, description="Turn within current session")
    current_phase: GamePhase = Field(..., description="Current turn phase")

    # Time tracking
    days_elapsed: int = Field(..., ge=0, description="In-game days since campaign start")
    current_timestamp: datetime = Field(..., description="Real-world time")

    # Active state
    dm_narration: str = Field(default="", description="DM's scene description")
    active_scene: str = Field(default="", description="Current scene name")
    location: str = Field(default="", description="Current location")

    # Agent states (keyed by agent_id)
    agent_states: Dict[str, dict] = Field(default_factory=dict, description="Base persona states")
    character_states: Dict[str, dict] = Field(default_factory=dict, description="Character agent states")

    # Turn accumulation
    ooc_messages: List[dict] = Field(default_factory=list, description="Out-of-character discussion")
    strategic_intents: Dict[str, dict] = Field(default_factory=dict, description="Player strategic decisions")
    character_actions: Dict[str, dict] = Field(default_factory=dict, description="Character actions")
    validation_results: Dict[str, dict] = Field(default_factory=dict, description="Validation outcomes")

    # Memory updates pending
    memory_updates: List[dict] = Field(default_factory=list, description="Memory writes to batch")

    # Consensus state
    consensus_state: Optional[str] = Field(default=None, description="OOC consensus status")

    model_config = {
        "json_schema_extra": {
            "example": {
                "session_number": 1,
                "turn_number": 5,
                "current_phase": "character_action",
                "days_elapsed": 3,
                "current_timestamp": "2025-10-18T14:30:00",
                "dm_narration": "A goblin leaps from behind the tree",
                "active_scene": "Forest Ambush",
                "location": "Darkwood Forest",
                "agent_states": {},
                "character_states": {},
                "ooc_messages": [],
                "strategic_intents": {},
                "character_actions": {},
                "validation_results": {},
                "memory_updates": [],
                "consensus_state": None
            }
        }
    }
```

**Validation Rules**:
- `session_number` and `turn_number` must be positive
- `days_elapsed` must be non-negative
- Phase must be valid enum value

**State Transitions**:
Defined by `GamePhase` enum sequential flow:

```
SESSION_START
↓
DM_NARRATION
↓
MEMORY_RETRIEVAL
↓
OOC_DISCUSSION → (consensus detection)
  ├─ UNANIMOUS → STRATEGIC_INTENT
  ├─ MAJORITY → STRATEGIC_INTENT
  └─ CONFLICTED → continue OOC_DISCUSSION or TIMEOUT
↓
STRATEGIC_INTENT
↓
P2C_DIRECTIVE
↓
CHARACTER_ACTION
↓
VALIDATION_CHECK → (validation retry)
  ├─ VALID → DM_ADJUDICATION
  ├─ RETRY → CHARACTER_ACTION (up to 3 attempts)
  └─ FAIL → DM_ADJUDICATION (with warning)
↓
DM_ADJUDICATION
↓
DICE_RESOLUTION (if needed)
↓
DM_OUTCOME
↓
CHARACTER_REACTION
↓
MEMORY_CONSOLIDATION
↓
[loop to DM_NARRATION or SESSION_END]
```

---

### 3.2 Message

**Purpose**: Represent routed communication between agents with channel-based visibility.

```python
from pydantic import BaseModel, Field
from typing import List
from datetime import datetime
from enum import Enum
import uuid

class Channel(str, Enum):
    IC = "in_character"          # Character roleplay
    OOC = "out_of_character"     # Strategic discussion
    P2C = "player_to_character"  # Private directive

class MessageType(str, Enum):
    NARRATION = "narration"
    DIALOGUE = "dialogue"
    ACTION = "action"
    REACTION = "reaction"
    DISCUSSION = "discussion"
    DIRECTIVE = "directive"

class Message(BaseModel):
    """Routed message with channel-based visibility"""

    # Identity
    message_id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="Unique message ID")
    timestamp: datetime = Field(default_factory=datetime.now, description="When message created")

    # Routing
    channel: Channel = Field(..., description="Communication channel")
    from_agent: str = Field(..., description="Sending agent ID")
    to_agents: List[str] = Field(default_factory=list, description="Recipients (empty = broadcast)")

    # Content
    content: str = Field(..., description="Message content", min_length=1, max_length=2000)
    message_type: MessageType = Field(..., description="Message category")

    # Metadata
    turn_number: int = Field(..., ge=1, description="Turn this message belongs to")
    phase: GamePhase = Field(..., description="Phase when message created")

    model_config = {
        "json_schema_extra": {
            "example": {
                "message_id": "msg_550e8400",
                "timestamp": "2025-10-18T14:30:15",
                "channel": "ic",
                "from_agent": "char_thrain_001",
                "to_agents": [],
                "content": "I charge at the goblin with my sword raised!",
                "message_type": "action",
                "turn_number": 5,
                "phase": "character_action"
            }
        }
    }
```

**Visibility Rules** (enforced by MessageRouter):

| Channel | Characters See | Base Personas See |
|---------|---------------|-------------------|
| IC      | Full access   | Summary only      |
| OOC     | No access     | Full access       |
| P2C     | Recipient only | No access        |

---

### 3.3 ValidationResult

**Purpose**: Represent validation outcome with retry tracking.

```python
from pydantic import BaseModel, Field, field_validator
from typing import Optional

class ValidationResult(BaseModel):
    """Validation outcome with retry escalation"""

    # Result
    valid: bool = Field(..., description="Whether action passed validation")
    attempt: int = Field(..., ge=1, le=3, description="Attempt number (1-3)")

    # If invalid
    violation: Optional[str] = Field(default=None, description="What rule was violated")
    forbidden_pattern: Optional[str] = Field(default=None, description="Regex pattern matched")
    suggestion: Optional[str] = Field(default=None, description="How to fix")

    # Final action
    action: str = Field(..., description="Validated or auto-fixed action text")
    auto_fixed: bool = Field(default=False, description="Whether auto-correction applied")
    warning_flag: bool = Field(default=False, description="Flag for DM review")

    @field_validator("violation", "forbidden_pattern", "suggestion")
    @classmethod
    def validate_invalid_fields(cls, v: Optional[str], info) -> Optional[str]:
        """If invalid, violation should be set"""
        if not info.data.get("valid") and v is None and info.field_name == "violation":
            raise ValueError("violation must be set when valid=False")
        return v

    model_config = {
        "json_schema_extra": {
            "example": {
                "valid": False,
                "attempt": 2,
                "violation": "Contains outcome language",
                "forbidden_pattern": "\\bkills?\\b",
                "suggestion": "State intention only, not outcome",
                "action": "I swing my sword at the goblin, aiming for its shoulder",
                "auto_fixed": False,
                "warning_flag": False
            }
        }
    }
```

**Validation States**:
- **VALID** (attempt 1): Pass validation, proceed
- **INVALID** (attempt 1-2): Retry with correction
- **INVALID** (attempt 3): Auto-fix or flag for DM

---

### 3.4 ConsensusState

**Purpose**: Represent agreement level among multiple agents.

```python
from pydantic import BaseModel, Field
from typing import Dict
from enum import Enum

class Stance(str, Enum):
    AGREE = "agree"
    DISAGREE = "disagree"
    NEUTRAL = "neutral"
    SILENT = "silent"

class Position(BaseModel):
    """Individual agent's position on proposal"""
    agent_id: str
    stance: Stance
    confidence: float = Field(..., ge=0.0, le=1.0)

class ConsensusState(str, Enum):
    UNANIMOUS = "unanimous"    # All explicitly agree
    MAJORITY = "majority"      # >50% agree, no disagree
    CONFLICTED = "conflicted"  # Active disagreement
    TIMEOUT = "timeout"        # Exceeded discussion limit

class ConsensusResult(BaseModel):
    """OOC discussion consensus outcome"""

    # Result
    state: ConsensusState = Field(..., description="Consensus level achieved")
    positions: Dict[str, Position] = Field(..., description="Each agent's position")

    # Metadata
    rounds_elapsed: int = Field(..., ge=0, description="Discussion rounds completed")
    time_elapsed_seconds: float = Field(..., ge=0.0, description="Real-time discussion duration")

    # Decision
    proceed_with_action: bool = Field(..., description="Whether to proceed to action phase")
    dissenting_agents: list[str] = Field(default_factory=list, description="Agents who disagreed")

    model_config = {
        "json_schema_extra": {
            "example": {
                "state": "majority",
                "positions": {
                    "agent_alex": {"agent_id": "agent_alex", "stance": "agree", "confidence": 0.9},
                    "agent_blair": {"agent_id": "agent_blair", "stance": "agree", "confidence": 0.7},
                    "agent_casey": {"agent_id": "agent_casey", "stance": "neutral", "confidence": 0.5}
                },
                "rounds_elapsed": 3,
                "time_elapsed_seconds": 45.2,
                "proceed_with_action": True,
                "dissenting_agents": []
            }
        }
    }
```

---

## 4. DM Interface Models

### 4.1 DMCommand

**Purpose**: Parsed DM input commands with type safety.

```python
from pydantic import BaseModel, Field
from typing import Optional
from enum import Enum

class DMCommandType(str, Enum):
    NARRATE = "narrate"
    ROLL = "roll"
    SUCCESS = "success"
    FAIL = "fail"
    ASK = "ask"
    END_SESSION = "end_session"

class DiceRoll(BaseModel):
    """Parsed dice notation"""
    num_dice: int = Field(..., ge=1, le=100)
    die_size: int = Field(..., ge=2, le=100)
    modifier: int = Field(default=0, ge=-100, le=100)
    advantage: bool = Field(default=False)
    disadvantage: bool = Field(default=False)

    def __str__(self) -> str:
        base = f"{self.num_dice}d{self.die_size}"
        if self.modifier != 0:
            sign = "+" if self.modifier > 0 else ""
            base += f"{sign}{self.modifier}"
        if self.advantage:
            base += " (advantage)"
        if self.disadvantage:
            base += " (disadvantage)"
        return base

class DMCommand(BaseModel):
    """Parsed DM command with validation"""

    command_type: DMCommandType = Field(..., description="Command type")
    text: Optional[str] = Field(default=None, description="Command text (narration, outcome, etc.)")

    # For roll commands
    dice_roll: Optional[DiceRoll] = Field(default=None, description="Parsed dice notation")
    dc: Optional[int] = Field(default=None, ge=1, le=50, description="Difficulty class")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {"command_type": "narrate", "text": "A goblin jumps from behind a tree"},
                {"command_type": "roll", "dice_roll": {"num_dice": 1, "die_size": 20, "modifier": 5}, "dc": 15},
                {"command_type": "success", "text": "Your blade strikes the goblin's shoulder"},
                {"command_type": "fail", "text": "Your swing misses as the goblin dodges"},
                {"command_type": "end_session"}
            ]
        }
    }
```

**Command Grammar**:
```
narrate <text>         → Scene description
roll <dice> dc <num>   → Call for roll (e.g., roll 1d20+5 dc 15)
success <text>         → Auto-success narration
fail <text>            → Auto-failure narration
ask <question>         → Request player clarification
end_session            → End current session
```

---

## 5. Settings & Configuration

### 5.1 Settings

**Purpose**: Application-wide configuration from environment variables.

```python
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional

class Settings(BaseSettings):
    """Application configuration from environment"""

    # LLM Configuration
    openai_api_key: str
    openai_model_base_persona: str = "gpt-4o-2024-08-06"
    openai_model_character: str = "gpt-4o-2024-08-06"
    openai_model_corruption: str = "gpt-4o-mini-2024-07-18"
    openai_model_validation: str = "gpt-4o-mini-2024-07-18"

    # Database Configuration
    neo4j_uri: str = "bolt://localhost:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: str

    # Redis Configuration
    redis_url: str = "redis://localhost:6379"
    rq_queue_base_persona: str = "base_persona"
    rq_queue_character: str = "character"
    rq_queue_validation: str = "validation"

    # Graphiti Configuration
    graphiti_group_id_prefix: str = "ttrpg_campaign_"

    # Memory Corruption Configuration
    corruption_enabled: bool = True
    corruption_strength: float = 0.5
    min_days_for_corruption: int = 7

    # Observability
    langsmith_api_key: Optional[str] = None
    langsmith_project: str = "ttrpg-ai-agents"
    langsmith_tracing_enabled: bool = False

    # Performance Tuning
    max_tokens_base_persona: int = 1000
    max_tokens_character: int = 1000
    temperature_base_persona: float = 0.7
    temperature_character: float = 0.8

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False
    )
```

---

## Summary

### Entity Count
- **11 core models** defined with full Pydantic validation
- **6 enum types** for constrained values
- **15+ validation rules** enforcing data integrity

### Validation Coverage
- Type safety via Pydantic 2.x
- Range constraints (ge/le)
- String patterns (regex)
- Custom validators for temporal consistency
- Field-level defaults and optionality

### Relationships Mapped
- Agent ↔ Personality (1:1)
- Agent ↔ Character (1:1)
- Memory ↔ Episode (N:1)
- Memory ↔ Entities (N:M)
- Message ↔ Channel visibility rules

### State Transitions Defined
- GamePhase: 14-phase turn cycle with conditional branching
- ValidationResult: 3-attempt retry escalation
- ConsensusState: 4-state agreement detection
- MemoryEdge: Created → Corrupted → Invalidated lifecycle

**All models ready for implementation with pytest contract tests.**
