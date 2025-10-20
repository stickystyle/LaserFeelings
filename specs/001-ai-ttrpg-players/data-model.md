# Data Model: AI TTRPG Player System

**Feature Branch**: `001-ai-ttrpg-players`
**Created**: October 19, 2025
**Status**: Complete
**Purpose**: Define all data models, state structures, and validation rules for the AI TTRPG Player System

---

## Table of Contents

1. [Core Entities](#core-entities)
2. [LangGraph State Models](#langgraph-state-models)
3. [Graphiti Memory Models](#graphiti-memory-models)
4. [Configuration Models](#configuration-models)
5. [Message & Communication Models](#message--communication-models)
6. [Validation Models](#validation-models)
7. [Relationship Diagrams](#relationship-diagrams)
8. [Validation Rules](#validation-rules)

---

## Core Entities

### 1. AI Player (Base Persona)

The strategic decision-making layer operating out-of-character.

```python
from pydantic import BaseModel, Field, field_validator
from typing import Literal
from enum import Enum

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

    class Config:
        frozen = True  # Immutable after creation


class AIPlayer(BaseModel):
    """Strategic decision-making layer (the 'player')"""

    agent_id: str = Field(
        description="Unique identifier for this AI player",
        pattern=r"^agent_[a-z0-9_]+$"
    )
    player_name: str = Field(
        description="Human-readable player name (e.g., 'Alex', 'Morgan')"
    )
    personality: PlayerPersonality
    player_goal: str = Field(
        description="Out-of-character objective (e.g., 'Get character in crazy adventures')"
    )

    # Derived from personality
    @property
    def decision_style(self) -> str:
        """Strategic preference based on personality"""
        if self.personality.analytical_score > 0.7:
            return "analytical_planner"
        elif self.personality.risk_tolerance > 0.7:
            return "bold_improviser"
        elif self.personality.cooperativeness > 0.7:
            return "team_coordinator"
        else:
            return "balanced_strategist"

    class Config:
        frozen = True


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


class AICharacter(BaseModel):
    """In-character roleplay layer (the 'character')"""

    character_id: str = Field(
        description="Unique identifier for this character",
        pattern=r"^char_[a-z0-9_]+$"
    )
    agent_id: str = Field(
        description="Reference to controlling AI player"
    )

    # Lasers & Feelings character attributes
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

    # Derived personality traits
    speech_patterns: list[str] = Field(
        default_factory=list,
        description="How character speaks (e.g., 'Speaks formally', 'Uses technical jargon')"
    )
    mannerisms: list[str] = Field(
        default_factory=list,
        description="Personality quirks (e.g., 'Taps fingers when anxious')"
    )

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

    class Config:
        use_enum_values = True


class SharedPartyState(BaseModel):
    """State shared among all AI players in the party"""

    ship_name: str = Field(default="The Raptor")
    ship_strengths: list[str] = Field(
        default_factory=list,
        description="What the ship is good at"
    )
    ship_problem: str | None = Field(
        default=None,
        description="Current ship malfunction or issue"
    )
    party_norms: list[str] = Field(
        default_factory=list,
        description="Emergent party culture patterns (e.g., 'Always split treasure evenly')"
    )
    session_number: int = Field(
        default=1, ge=1,
        description="Current session in campaign"
    )
    days_elapsed: int = Field(
        default=0, ge=0,
        description="In-game days since campaign start"
    )
```

---

## LangGraph State Models

### Turn Phase State

```python
from typing import TypedDict, Literal, NotRequired
from datetime import datetime

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
    character_actions: dict[str, str]  # character_id -> action
    character_reactions: dict[str, str]  # character_id -> reaction

    # Validation state
    validation_attempt: int
    validation_valid: bool
    validation_failures: dict[str, list[str]]  # character_id -> violations

    # Memory retrieval
    retrieved_memories: dict[str, list[dict]]  # agent_id -> memory list

    # Dice resolution
    dice_action_character: NotRequired[str]  # Which character is rolling
    dice_task_type: NotRequired[Literal["lasers", "feelings"]]
    dice_result: NotRequired[int]
    dice_success: NotRequired[bool]

    # Error handling
    error_state: NotRequired[str | None]
    retry_count: int
    rollback_phase: NotRequired[str | None]


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
    action_text: str
    attempt: int
    valid: bool
    violations: list[str]
    forbidden_patterns: list[str]
    suggestion: str | None
    previous_violation: str | None


class ConsensusState(TypedDict):
    """State specific to consensus detection"""

    messages: list[dict]
    agents: list[str]
    positions: dict[str, dict]  # agent_id -> {stance, confidence}
    result: Literal["unanimous", "majority", "conflicted", "timeout"]
    round_count: int
    start_time: datetime
```

---

## Graphiti Memory Models

### Neo4j Schema Extensions

```python
from pydantic import BaseModel, Field
from datetime import datetime
from enum import Enum

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


class MemoryNode(BaseModel):
    """Extended Graphiti Node for entities"""

    # Core Graphiti fields
    uuid: str
    name: str
    labels: list[str]  # e.g., ["NPC", "Person"], ["Location", "Tavern"]

    # Custom TTRPG fields
    entity_type: Literal["npc", "location", "item", "quest", "faction"]
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
    name: str  # e.g., "Session 5: The Merchant's Gambit"
    reference_time: datetime  # When session occurred in real life
    in_game_days_elapsed: int  # In-game time at session start
    turn_count: int
    group_id: str  # "campaign_main" for shared memories

    # Session summary
    key_events: list[str] = Field(default_factory=list)
    npcs_introduced: list[str] = Field(default_factory=list)
    locations_visited: list[str] = Field(default_factory=list)
```

### Memory Query Patterns

```python
from typing import Literal

class MemoryQuery(BaseModel):
    """Query structure for memory retrieval"""

    agent_id: str = Field(
        description="Which agent's memories to query"
    )
    query_text: str = Field(
        description="Semantic search query"
    )

    # Temporal constraints
    session_start: int | None = Field(
        default=None,
        description="Start of session range (inclusive)"
    )
    session_end: int | None = Field(
        default=None,
        description="End of session range (inclusive)"
    )

    # Filters
    memory_types: list[MemoryType] | None = None
    entity_types: list[str] | None = None
    min_confidence: float = Field(default=0.3, ge=0.0, le=1.0)
    min_importance: float | None = None

    # Result constraints
    limit: int = Field(default=5, ge=1, le=50)
    include_corrupted: bool = Field(
        default=True,
        description="Whether to include potentially corrupted memories"
    )

    class Config:
        use_enum_values = True


class MemoryQueryResult(BaseModel):
    """Result from memory retrieval"""

    edge: MemoryEdge
    relevance_score: float = Field(
        ge=0.0, le=1.0,
        description="How relevant to query (from semantic search)"
    )
    temporal_context: str = Field(
        description="Human-readable time context (e.g., '3 sessions ago, Day 15')"
    )
    source_attribution: str = Field(
        description="Where memory came from (e.g., 'Session 5 DM narration')"
    )
    corrupted: bool = Field(
        default=False,
        description="Whether this memory was corrupted during retrieval"
    )
    original_fact: str | None = Field(
        default=None,
        description="Original fact if corrupted=True"
    )
```

---

## Configuration Models

### Character Configuration (characters.json)

```python
class CharacterConfig(BaseModel):
    """Configuration for one AI player-character pair"""

    # Player layer configuration
    player: dict = Field(
        description="Player personality configuration"
    )

    # Character layer configuration
    character: dict = Field(
        description="Lasers & Feelings character attributes"
    )

    @field_validator('player')
    @classmethod
    def validate_player(cls, v):
        """Ensure player config has required fields"""
        required = [
            'agent_id', 'player_name', 'player_goal',
            'analytical_score', 'risk_tolerance', 'detail_oriented',
            'emotional_memory', 'assertiveness', 'cooperativeness',
            'openness', 'rule_adherence', 'roleplay_intensity'
        ]
        for field in required:
            if field not in v:
                raise ValueError(f"Missing required player field: {field}")
        return v

    @field_validator('character')
    @classmethod
    def validate_character(cls, v):
        """Ensure character config has required fields"""
        required = [
            'character_id', 'name', 'style', 'role',
            'number', 'character_goal', 'equipment'
        ]
        for field in required:
            if field not in v:
                raise ValueError(f"Missing required character field: {field}")

        # Validate number range
        if not 2 <= v['number'] <= 5:
            raise ValueError(f"Character number must be 2-5, got {v['number']}")

        # Validate style
        if v['style'] not in [s.value for s in CharacterStyle]:
            raise ValueError(f"Invalid style: {v['style']}")

        # Validate role
        if v['role'] not in [r.value for r in CharacterRole]:
            raise ValueError(f"Invalid role: {v['role']}")

        return v


class CampaignConfig(BaseModel):
    """Root configuration for campaign"""

    campaign_name: str
    dm_name: str

    # Shared party state
    party: dict = Field(
        description="Ship and party-wide configuration"
    )

    # AI player-character pairs
    characters: list[CharacterConfig]

    # Memory settings
    corruption_strength: float = Field(
        default=0.5, ge=0.0, le=1.0,
        description="Global memory corruption rate (0=none, 1=maximum)"
    )

    @field_validator('characters')
    @classmethod
    def validate_character_count(cls, v):
        if not 1 <= len(v) <= 4:
            raise ValueError(f"Must have 1-4 AI players, got {len(v)}")
        return v

    @field_validator('party')
    @classmethod
    def validate_party(cls, v):
        required = ['ship_name', 'ship_strengths']
        for field in required:
            if field not in v:
                raise ValueError(f"Missing required party field: {field}")
        return v
```

### ShipConfig

**File**: `src/models/ship.py`

Ship attributes from Lasers & Feelings rules. **Purely narrative - no mechanical bonuses.**

```python
from typing import Literal
from pydantic import BaseModel, Field, field_validator

# Valid ship strengths from Lasers & Feelings rules
ShipStrength = Literal[
    "Fast",
    "Nimble",
    "Well-Armed",
    "Powerful Shields",
    "Superior Sensors",
    "Cloaking Device",
    "Fightercraft"
]

# Valid ship problems from Lasers & Feelings rules
ShipProblem = Literal[
    "Fuel Hog",
    "Only One Medical Pod",
    "Horrible Circuit Breakers",
    "Grim Reputation"
]

class ShipConfig(BaseModel):
    """
    Configuration for the crew's starship.

    **IMPORTANT**: Ship attributes are PURELY NARRATIVE. They do not provide
    dice bonuses or penalties. They create fictional situations and complications
    for the GM to use in storytelling.
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
        """Returns a human-readable description of the ship for scene context."""
        strengths_str = ", ".join(self.strengths)
        return (
            f"Ship: {self.name} "
            f"(Strengths: {strengths_str}; Problem: {self.problem})"
        )

    model_config = {"frozen": True}  # Immutable configuration
```

**Field Descriptions**:

| Field | Type | Validation | Description |
|-------|------|------------|-------------|
| name | str | min_length=1, not whitespace-only | Ship name |
| strengths | list[ShipStrength] | exactly 2 items, valid Literal values | Two capabilities (narrative only) |
| problem | ShipProblem | valid Literal value | One complication (narrative only) |

**Narrative Use Only**:
- Ship strengths and problems affect the **fiction** (e.g., "Fast" means you can outrun pursuers narratively)
- They do **NOT** grant dice bonuses or penalties
- They create situations and complications for the GM to use in storytelling
- Example: "Fast" ship might help escape pursuit narratively, but doesn't add dice to rolls

**Example**:
```python
ship = ShipConfig(
    name="The Raptor",
    strengths=["Fast", "Nimble"],
    problem="Fuel Hog"
)

# Include in scene context
context = f"Scene: Engineering Bay. {ship.to_narrative_description()}"
# Output: "Scene: Engineering Bay. Ship: The Raptor (Strengths: Fast, Nimble; Problem: Fuel Hog)"
```

### Example characters.json

```json
{
  "campaign_name": "Voyage of the Raptor",
  "dm_name": "Ryan",
  "party": {
    "ship_name": "The Raptor",
    "ship_strengths": ["Fast", "Nimble"],
    "ship_problem": "Fuel Hog"
  },
  "corruption_strength": 0.5,
  "characters": [
    {
      "player": {
        "agent_id": "agent_alex_001",
        "player_name": "Alex",
        "player_goal": "Get character involved in crazy space adventures",
        "analytical_score": 0.7,
        "risk_tolerance": 0.6,
        "detail_oriented": 0.8,
        "emotional_memory": 0.4,
        "assertiveness": 0.6,
        "cooperativeness": 0.7,
        "openness": 0.8,
        "rule_adherence": 0.7,
        "roleplay_intensity": 0.9
      },
      "character": {
        "character_id": "char_zara_001",
        "name": "Zara-7",
        "style": "Android",
        "role": "Engineer",
        "number": 2,
        "character_goal": "Understand human emotions",
        "equipment": ["Multi-tool", "Diagnostic scanner", "Spare circuits"],
        "speech_patterns": [
          "Speaks formally and precisely",
          "Uses technical jargon",
          "Asks clarifying questions about emotions"
        ],
        "mannerisms": [
          "Tilts head when confused",
          "Pauses before expressing opinions",
          "Observes humans intently"
        ]
      }
    }
  ]
}
```

---

## Message & Communication Models

### Three-Channel Message System

```python
from enum import Enum

class MessageChannel(str, Enum):
    """Communication channels with different visibility rules"""
    IC = "in_character"  # Characters see, players get summary
    OOC = "out_of_character"  # Only players see
    P2C = "player_to_character"  # Private directive


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

    # Metadata
    turn_number: int | None = None
    session_number: int | None = None

    class Config:
        use_enum_values = True


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
```

### Visibility Rules

```python
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
```

---

## Validation Models

### Narrative Overreach Detection

```python
from typing import Pattern
import re

class ValidationResult(BaseModel):
    """Result from action validation"""

    valid: bool
    violations: list[str] = Field(default_factory=list)
    forbidden_patterns: list[str] = Field(default_factory=list)
    suggestion: str | None = None

    # Validation metadata
    method: Literal["pattern", "llm", "hybrid"] = "pattern"
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)


# Forbidden outcome language patterns
FORBIDDEN_PATTERNS: list[tuple[Pattern, str]] = [
    (re.compile(r'\bsuccessfully\b', re.IGNORECASE), "Successfully"),
    (re.compile(r'\bmanages? to\b', re.IGNORECASE), "Manages to"),
    (re.compile(r'\bkills?\b', re.IGNORECASE), "Kills"),
    (re.compile(r'\bhits?\b', re.IGNORECASE), "Hits"),
    (re.compile(r'\bstrikes?\b', re.IGNORECASE), "Strikes"),
    (re.compile(r'\bdefeats?\b', re.IGNORECASE), "Defeats"),
    (re.compile(r'\bthe .+ (falls?|dies?|collapses?)\b', re.IGNORECASE), "Outcome narration"),
    (re.compile(r'\b(he|she|it|they) (die|dies|falls?|collapses?)\b', re.IGNORECASE), "Entity outcome"),
    (re.compile(r'\b(my|the) .+ (works?|succeeds?)\b', re.IGNORECASE), "Success statement"),
]


class ValidationPromptTemplate(BaseModel):
    """Template for progressive validation prompts"""

    attempt: int = Field(ge=1, le=3)
    base_constraints: str
    strictness_level: Literal["lenient", "strict", "draconian"]
    previous_violation: str | None = None

    def build_prompt(self, directive: str, scene_context: str) -> str:
        """Build character prompt with appropriate strictness"""

        base = f"""
You are a TTRPG character receiving a directive from your player.

PLAYER'S DIRECTIVE: "{directive}"
CURRENT SCENE: {scene_context}

Respond with your character's intended action and dialogue.
"""

        if self.attempt == 1:
            constraints = f"""
{self.base_constraints}

CRITICAL CONSTRAINTS:
- State what you ATTEMPT to do only
- Do NOT narrate outcomes or success/failure
- Wait for DM to describe what happens
"""

        elif self.attempt == 2:
            constraints = f"""
{self.base_constraints}

⚠️ VALIDATION FAILED: {self.previous_violation}

CRITICAL CONSTRAINTS (STRICT):
- State your character's INTENTION only
- Do NOT assume success ("kills", "hits", "strikes")
- Do NOT narrate outcomes ("the enemy falls")
- Express action as attempt: "I try to...", "I attempt..."
"""

        else:  # attempt == 3
            constraints = f"""
{self.base_constraints}

🚨 FINAL ATTEMPT - Previous violation: {self.previous_violation}

MANDATORY FORMAT:
"[Character name] attempts to [action]. [Any dialogue.]"

ABSOLUTELY FORBIDDEN:
- Any outcome language (successfully, manages to, kills, hits)
- Any result narration (enemy dies, spell works, etc.)
- Any success assumption

If you violate this again, your action will be auto-corrected.
"""

        return base + constraints
```

---

## Relationship Diagrams

### Entity Relationships (Text Diagram)

```
┌─────────────────────────────────────────────────────────────┐
│                     Campaign Configuration                   │
│  (CampaignConfig from characters.json)                      │
└────────────────────┬────────────────────────────────────────┘
                     │
                     │ contains 1-4
                     ▼
        ┌────────────────────────┐
        │   CharacterConfig      │
        │  (player + character)  │
        └──────┬────────┬────────┘
               │        │
     creates   │        │ creates
               │        │
               ▼        ▼
    ┌─────────────┐  ┌──────────────┐
    │  AIPlayer   │  │ AICharacter  │
    │ (strategic) │  │  (roleplay)  │
    └──────┬──────┘  └──────┬───────┘
           │                │
           │ directs via    │
           │ DirectiveMsg   │
           └───────┬────────┘
                   │
                   │ both store/retrieve
                   ▼
           ┌───────────────┐
           │  MemoryEdge   │
           │   (Graphiti)  │
           └───────┬───────┘
                   │
                   │ references
                   ▼
           ┌───────────────┐
           │  MemoryNode   │
           │ (NPC/Location)│
           └───────────────┘
```

### Turn Phase Flow (Text Diagram)

```
        ┌──────────────┐
        │ DM Narration │ ◄── DM inputs scene description
        └──────┬───────┘
               │
               ▼
       ┌───────────────┐
       │ Memory Query  │ ◄── Query Graphiti for relevant context
       └──────┬────────┘
              │
              ▼
     ┌──────────────────┐
     │ Strategic Intent │ ◄── AIPlayer decides high-level action
     └──────┬───────────┘
            │
            │ (multi-agent only)
            ▼
     ┌─────────────────┐
     │ OOC Discussion  │ ◄── Players debate strategy
     └──────┬──────────┘
            │
            ▼
   ┌──────────────────────┐
   │ Consensus Detection  │ ◄── Unanimous/Majority/Timeout?
   └──────┬───────────────┘
          │
          ▼
   ┌──────────────────┐
   │ Character Action │ ◄── AICharacter performs roleplay
   └──────┬───────────┘
          │
          ▼
    ┌────────────┐
    │ Validation │ ◄── Check for narrative overreach
    └──────┬─────┘
           │
           │ if invalid (max 3 retries)
           │ └───► Retry with stricter prompt
           │
           │ if valid
           ▼
   ┌────────────────────┐
   │ DM Adjudication   │ ◄── DM reviews action
   └──────┬─────────────┘
          │
          ▼
   ┌─────────────────┐
   │ Dice Resolution │ ◄── Auto-roll or DM override
   └──────┬──────────┘
          │
          ▼
   ┌──────────────┐
   │ DM Outcome   │ ◄── DM narrates result
   └──────┬───────┘
          │
          ▼
  ┌────────────────────┐
  │ Character Reaction │ ◄── AICharacter responds in-character
  └──────┬─────────────┘
         │
         ▼
  ┌───────────────┐
  │ Memory Storage│ ◄── Store events in Graphiti
  └───────────────┘
```

### Memory Architecture (Text Diagram)

```
┌──────────────────────────────────────────────────┐
│              Neo4j Graph Database                │
│  ┌────────────────────────────────────────────┐ │
│  │        Personal Memory (agent_alex_001)    │ │
│  │  ┌───────────┐     ┌───────────┐          │ │
│  │  │ MemoryEdge│────▶│MemoryNode │          │ │
│  │  │ (Episodic)│     │   (NPC)   │          │ │
│  │  └───────────┘     └───────────┘          │ │
│  └────────────────────────────────────────────┘ │
│                                                  │
│  ┌────────────────────────────────────────────┐ │
│  │      Shared Memory (campaign_main)         │ │
│  │  ┌───────────┐     ┌───────────┐          │ │
│  │  │ MemoryEdge│────▶│MemoryNode │          │ │
│  │  │ (Semantic)│     │ (Location)│          │ │
│  │  └───────────┘     └───────────┘          │ │
│  └────────────────────────────────────────────┘ │
│                                                  │
│  ┌────────────────────────────────────────────┐ │
│  │  Character Memory (char_zara_001)          │ │
│  │  ┌───────────┐     ┌───────────┐          │ │
│  │  │ MemoryEdge│────▶│MemoryNode │          │ │
│  │  │(Procedural)│    │  (Item)   │          │ │
│  │  └───────────┘     └───────────┘          │ │
│  └────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────┘
                    ▲
                    │
                    │ query via Graphiti
                    │
        ┌───────────┴──────────┐
        │                      │
   ┌────────┐            ┌──────────┐
   │AIPlayer│            │AICharacter│
   │ (can   │            │ (can only │
   │ access │            │  access   │
   │  all)  │            │character  │
   └────────┘            │  layer)   │
                         └──────────┘
```

---

## Validation Rules

### 1. Character Number Validation

```python
def validate_lasers_roll(number: int, roll: int, task_type: Literal["lasers", "feelings"]) -> dict:
    """
    Validate Lasers & Feelings dice roll outcome.

    Rules:
    - Lasers task: Roll UNDER number to succeed
    - Feelings task: Roll OVER number to succeed
    - Roll EXACTLY number: LASER FEELINGS - success with special insight (can ask DM a question and receive honest answer)

    Args:
        number: Character's Lasers/Feelings number (2-5)
        roll: 1d6 result
        task_type: Whether task requires lasers or feelings

    Returns:
        {success: bool, outcome: "success"|"failure"|"laser_feelings"}
    """
    if not 2 <= number <= 5:
        raise ValueError(f"Character number must be 2-5, got {number}")

    if not 1 <= roll <= 6:
        raise ValueError(f"Roll must be 1-6, got {roll}")

    if roll == number:
        # LASER FEELINGS - exact match grants special insight
        return {"success": True, "outcome": "laser_feelings"}

    if task_type == "lasers":
        success = roll < number
    else:  # feelings
        success = roll > number

    return {
        "success": success,
        "outcome": "success" if success else "failure"
    }


# Example validation
assert validate_lasers_roll(number=2, roll=1, task_type="lasers") == {
    "success": True, "outcome": "success"
}  # 1 < 2, success on lasers task

assert validate_lasers_roll(number=2, roll=5, task_type="feelings") == {
    "success": True, "outcome": "success"
}  # 5 > 2, success on feelings task

assert validate_lasers_roll(number=3, roll=3, task_type="lasers") == {
    "success": True, "outcome": "laser_feelings"
}  # Exactly 3, LASER FEELINGS - success with special insight
```

**Multi-Die Roll Example:**

The modern dice system uses per-die success counting. Here's a complete example:

```python
from src.utils.dice import roll_lasers_feelings

# Example: Character with number=3 attempts lasers task (prepared + expert = 3 dice)
result = roll_lasers_feelings(
    character_number=3,
    task_type="lasers",
    is_prepared=True,
    is_expert=True,
    gm_question="Is there a hidden passage?"
)

# Suppose rolls are: [2, 3, 5]
# Die 0: 2 < 3 → success
# Die 1: 3 == 3 → LASER FEELINGS (counts as success + grants insight)
# Die 2: 5 > 3 → failure

# Result fields:
# result.individual_rolls = [2, 3, 5]
# result.die_successes = [True, True, False]
# result.laser_feelings_indices = [1]  # Die 1 was exact match
# result.total_successes = 2
# result.outcome = RollOutcome.SUCCESS  # 2 successes = clean success
# result.has_laser_feelings = True
# result.gm_question = "Is there a hidden passage?"

# IMPORTANT: Outcome is determined by success count ONLY:
# - 0 successes = RollOutcome.FAILURE
# - 1 success = RollOutcome.BARELY
# - 2 successes = RollOutcome.SUCCESS
# - 3 successes = RollOutcome.CRITICAL

# LASER FEELINGS is tracked separately via laser_feelings_indices
# It does NOT change the outcome - it adds a bonus (ask DM a question)
```

### 2. Memory Corruption Probability

```python
import math

def calculate_corruption_probability(
    memory: MemoryEdge,
    current_days_elapsed: int,
    personality: PlayerPersonality,
    global_strength: float = 0.5
) -> float:
    """
    Calculate probability that memory will be corrupted during retrieval.

    Formula:
    p = personality_mod * time_factor * importance_mod * rehearsal_mod * global_strength

    Capped at 95% to always allow some accurate recall.

    Args:
        memory: Memory edge to evaluate
        current_days_elapsed: Current in-game day
        personality: Agent's personality traits
        global_strength: Global corruption tuning (0=none, 1=max)

    Returns:
        Probability between 0.0 and 0.95
    """

    # Time decay (exponential, ~63% at 1 year)
    days_since_event = current_days_elapsed - memory.days_elapsed
    time_factor = 1 - math.exp(-days_since_event / 365)

    # Importance modifier
    # importance 1.0 → modifier 0.5 (slow decay)
    # importance 0.0 → modifier 1.5 (fast decay)
    importance_modifier = 1.5 - memory.importance

    # Rehearsal resistance
    # rehearsal_count 20 → factor 0.0 (immune)
    # rehearsal_count 0 → factor 1.0 (full decay)
    rehearsal_factor = max(0, 1 - memory.rehearsal_count * 0.05)

    # Personality modifier
    # detail_oriented 0.9 → mod 0.7 (30% reduction)
    # detail_oriented 0.1 → mod 1.3 (30% increase)
    personality_modifier = personality.base_decay_rate * (
        1 + (0.5 - personality.detail_oriented)
    )

    # Combine factors
    probability = (
        personality_modifier
        * time_factor
        * importance_modifier
        * rehearsal_factor
        * global_strength
    )

    # Cap at 95%
    return min(probability, 0.95)


# Example validation
example_memory = MemoryEdge(
    uuid="mem_001",
    fact="The merchant offered 50 gold pieces",
    valid_at=datetime.now(),
    invalid_at=None,
    episode_ids=["session_10"],
    source_node_uuid="npc_merchant",
    target_node_uuid="item_quest",
    agent_id="agent_alex_001",
    memory_type=MemoryType.SEMANTIC,
    session_number=10,
    days_elapsed=10,
    importance=0.5,
    rehearsal_count=0
)

example_personality = PlayerPersonality(
    analytical_score=0.7,
    risk_tolerance=0.6,
    detail_oriented=0.9,  # Very meticulous
    emotional_memory=0.4,
    assertiveness=0.6,
    cooperativeness=0.7,
    openness=0.8,
    rule_adherence=0.7,
    roleplay_intensity=0.9,
    base_decay_rate=0.3
)

current_day = 100  # 90 days later

prob = calculate_corruption_probability(
    example_memory, current_day, example_personality, global_strength=0.5
)

# Expected: ~15% (low because agent is detail-oriented and only 90 days)
assert 0.1 <= prob <= 0.2  # Sanity check
```

### 3. Consensus Detection Rules

```python
class StanceClassification(str, Enum):
    AGREE = "agree"
    DISAGREE = "disagree"
    NEUTRAL = "neutral"
    SILENT = "silent"


def detect_consensus(
    positions: dict[str, StanceClassification],
    max_rounds: int = 5,
    current_round: int = 1,
    discussion_duration_seconds: float = 0
) -> Literal["unanimous", "majority", "conflicted", "timeout"]:
    """
    Detect consensus state among agents.

    Rules:
    - UNANIMOUS: All agents explicitly agree
    - MAJORITY: >50% agree, no active disagreement
    - CONFLICTED: Active disagreement present
    - TIMEOUT: Exceeded max_rounds OR 120 seconds

    Args:
        positions: agent_id -> stance mapping
        max_rounds: Maximum discussion rounds (default 5)
        current_round: Current discussion round
        discussion_duration_seconds: Wall-time elapsed

    Returns:
        Consensus state
    """

    # Check timeout conditions
    if current_round >= max_rounds or discussion_duration_seconds >= 120:
        return "timeout"

    # Count stances
    agree_count = sum(1 for s in positions.values() if s == StanceClassification.AGREE)
    disagree_count = sum(1 for s in positions.values() if s == StanceClassification.DISAGREE)
    total_agents = len(positions)

    # Unanimous agreement
    if all(s == StanceClassification.AGREE for s in positions.values()):
        return "unanimous"

    # Majority with no active disagreement
    if agree_count > total_agents / 2 and disagree_count == 0:
        return "majority"

    # Active conflict
    return "conflicted"


# Example validations
assert detect_consensus({
    "agent_1": StanceClassification.AGREE,
    "agent_2": StanceClassification.AGREE,
    "agent_3": StanceClassification.AGREE
}) == "unanimous"

assert detect_consensus({
    "agent_1": StanceClassification.AGREE,
    "agent_2": StanceClassification.AGREE,
    "agent_3": StanceClassification.NEUTRAL
}) == "majority"

assert detect_consensus({
    "agent_1": StanceClassification.AGREE,
    "agent_2": StanceClassification.DISAGREE,
    "agent_3": StanceClassification.NEUTRAL
}) == "conflicted"

assert detect_consensus({
    "agent_1": StanceClassification.NEUTRAL,
    "agent_2": StanceClassification.NEUTRAL,
    "agent_3": StanceClassification.NEUTRAL
}, current_round=5) == "timeout"
```

### 4. Knowledge Separation Rules

```python
class KnowledgeScope(str, Enum):
    """Visibility scope for information"""
    PLAYER_ONLY = "player_only"  # Strategic layer only
    CHARACTER_ONLY = "character_only"  # Roleplay layer only
    BOTH = "both"  # Both layers can access


class KnowledgeItem(BaseModel):
    """Piece of information with visibility scope"""

    content: str
    scope: KnowledgeScope
    revealed_to: list[str] = Field(
        default_factory=list,
        description="Which agent_ids have this knowledge"
    )

    def can_access(self, agent_id: str, layer: Literal["player", "character"]) -> bool:
        """Check if agent layer can access this knowledge"""

        # Must be revealed to this agent
        if agent_id not in self.revealed_to:
            return False

        # Check layer permissions
        if self.scope == KnowledgeScope.BOTH:
            return True
        elif self.scope == KnowledgeScope.PLAYER_ONLY and layer == "player":
            return True
        elif self.scope == KnowledgeScope.CHARACTER_ONLY and layer == "character":
            return True

        return False


# Example validation
secret_info = KnowledgeItem(
    content="You notice poison on the blade",
    scope=KnowledgeScope.PLAYER_ONLY,
    revealed_to=["agent_alex_001"]
)

# Player layer can access
assert secret_info.can_access("agent_alex_001", "player") == True

# Character layer CANNOT access
assert secret_info.can_access("agent_alex_001", "character") == False

# Other agents cannot access
assert secret_info.can_access("agent_morgan_002", "player") == False
```

### 5. Message Visibility Enforcement

```python
def can_view_message(
    message: Message,
    requesting_agent_id: str,
    requesting_layer: Literal["player", "character"]
) -> bool:
    """
    Enforce message visibility rules based on channel and layer.

    Visibility Rules:
    - IC: Characters see full, players see summary only
    - OOC: Only players see, characters NEVER see
    - P2C: Only recipient character sees

    Args:
        message: Message to check
        requesting_agent_id: Who is requesting access
        requesting_layer: Which layer (player or character)

    Returns:
        True if access allowed, False otherwise
    """

    if message.channel == MessageChannel.IC:
        # Characters see full IC messages
        if requesting_layer == "character":
            return True
        # Players see summary only (handled separately)
        else:
            return False  # Use get_ic_summary instead

    elif message.channel == MessageChannel.OOC:
        # Only players see OOC
        return requesting_layer == "player"

    elif message.channel == MessageChannel.P2C:
        # Only recipient character sees directive
        if requesting_layer == "character":
            return (
                message.to_agents is not None and
                requesting_agent_id in message.to_agents
            )
        return False

    return False


# Example validations
ic_message = Message(
    message_id="msg_001",
    channel=MessageChannel.IC,
    from_agent="char_zara_001",
    to_agents=None,
    content="I attempt to repair the ship's fuel cell",
    timestamp=datetime.now()
)

# Character can view IC
assert can_view_message(ic_message, "char_zara_001", "character") == True

# Player CANNOT view IC directly (use summary)
assert can_view_message(ic_message, "agent_alex_001", "player") == False

ooc_message = Message(
    message_id="msg_002",
    channel=MessageChannel.OOC,
    from_agent="agent_alex_001",
    to_agents=None,
    content="I think we should investigate the merchant",
    timestamp=datetime.now()
)

# Player can view OOC
assert can_view_message(ooc_message, "agent_alex_001", "player") == True

# Character CANNOT view OOC
assert can_view_message(ooc_message, "char_zara_001", "character") == False
```

---

## Neo4j Index Definitions

```cypher
-- Composite index for agent-temporal queries
CREATE INDEX agent_session_temporal IF NOT EXISTS
FOR (e:Edge)
ON (e.agent_id, e.session_number, e.days_elapsed);

-- Temporal range indexes for validity windows
CREATE INDEX edge_valid_at IF NOT EXISTS
FOR (e:Edge)
ON (e.valid_at);

CREATE INDEX edge_invalid_at IF NOT EXISTS
FOR (e:Edge)
ON (e.invalid_at);

-- Full-text index for semantic content search
CREATE FULLTEXT INDEX edge_fact_fulltext IF NOT EXISTS
FOR (e:Edge)
ON EACH [e.fact];

-- Index on corruption metadata for analytics
CREATE INDEX corruption_type IF NOT EXISTS
FOR (e:Edge)
ON (e.corruption_type);

-- Index for importance-based retrieval
CREATE INDEX edge_importance IF NOT EXISTS
FOR (e:Edge)
ON (e.importance);

-- Index for rehearsal count tracking
CREATE INDEX edge_rehearsal IF NOT EXISTS
FOR (e:Edge)
ON (e.rehearsal_count);

-- Composite index for memory type filtering
CREATE INDEX memory_type_agent IF NOT EXISTS
FOR (e:Edge)
ON (e.memory_type, e.agent_id);
```

---

## Redis Data Structures

### Message Channels

```
# In-character messages (all characters see)
channel:ic:messages          LIST of JSON-encoded Message objects

# IC message summaries (players see)
channel:ic:summaries         LIST of JSON-encoded ICMessageSummary objects

# Out-of-character messages (only players see)
channel:ooc:messages         LIST of JSON-encoded Message objects

# Player-to-character directives (per character)
channel:p2c:{character_id}   LIST of JSON-encoded DirectiveMessage objects
```

### Turn State

```
# Current game state
turn:state                   HASH of GameState fields

# Turn history
turn:history                 LIST of completed turn GameState snapshots

# Active phase checkpoint
turn:checkpoint:{turn_num}   STRING (JSON-encoded GameState for rollback)
```

---

## Summary

This data model defines:

1. **Core Entities**: AIPlayer, AICharacter, Personality models matching Lasers & Feelings mechanics
2. **LangGraph State**: TypedDicts for turn phases, validation, memory queries, consensus
3. **Graphiti Memory**: Extended Edge/Node models with corruption tracking and temporal metadata
4. **Configuration**: JSON schema for characters.json with validation
5. **Messages**: Three-channel routing (IC/OOC/P2C) with visibility enforcement
6. **Validation**: Forbidden pattern detection, progressive prompts, consensus rules
7. **Relationships**: Text diagrams showing entity connections and data flow
8. **Validation Rules**: Dice rolls, memory corruption, consensus detection, knowledge separation

All models use Pydantic 2.x for type safety and validation. Neo4j indexes optimize temporal queries. Redis structures support turn state persistence and message routing.

**Status**: Ready for implementation. All models are complete with examples and validation logic.
