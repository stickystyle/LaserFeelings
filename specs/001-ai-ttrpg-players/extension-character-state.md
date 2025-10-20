# Specification Extension: Memory-Based Equipment with Research Tools

**Version:** 1.0
**Date:** 2025-01-19
**Status:** Proposal
**Related:** spec.md, data-model.md, quickstart.md

---

## Research Insight

Real TTRPG players frequently forget items in their inventory, leading to emergent storytelling moments:
- Players forget they have rope until facing a cliff
- Detail-oriented players remember items better than impulsive players
- The "Wait, I have the thing!" realization creates exciting story beats
- Long sessions cause inventory amnesia

**Design Goal**: Agents should exhibit **human-like fallible memory** for equipment, not perfect recall. This creates emergent behavior driven by personality traits (analytical_score, detail_oriented) and memory corruption mechanics.

## Current State (Intentional, Not a Bug)

When the DM narrates "You pick up the plasma rifle":

1. ✅ Stored as narrative episode in Neo4j memory
2. ✅ Subject to memory corruption based on personality traits
3. ✅ Agent may or may not remember item when needed
4. ✅ Creates emergent "remembering at critical moment" gameplay

**This is the desired behavior.** Perfect inventory recall would break human-like realism.

## The Actual Problem

The only gap is **DM visibility**: How does the DM track ground truth for session management without giving agents perfect memory?

**Design Constraint**: The spec explicitly states (line 92): *"Unlike D&D, there are no complex stats, skills, or inventory systems - just NUMBER, STYLE, ROLE, and GOALS. This simplicity is intentional and should be preserved."*

---

## Proposed Solution

### Philosophy: Memory-Only with DM Research Tools

**Core Principle**: Agents rely on fallible memory for equipment (human-like). DM gets research tools to inspect memory state and track ground truth for session management.

### Approach

1. **Tag Equipment Events**: Add metadata to memory episodes for equipment acquisition/loss
2. **DM Research Commands**: Tools to query what agents remember (without giving agents perfect recall)
3. **DM Session Notes**: Optional lightweight tracking for DM's own notes (never seen by agents)
4. **Research Instrumentation**: Metrics on memory accuracy, retrieval success, emergent "aha!" moments

**Key Insight**: Separation between "what exists" (DM ground truth) and "what agent remembers" (corrupted memory)

### No Changes to Agent Behavior

- Agents continue using base CharacterSheet.equipment + memory retrieval
- No perfect inventory list available to agents
- Equipment recall depends on memory system (corruption, personality traits, recency)
- Emergent forgetting/remembering creates realistic gameplay

---

## New Functional Requirements

### FR-026: Equipment Memory Tagging

**Priority**: P2 (Enhancement, not MVP blocking)

**Requirement**: System MUST tag equipment-related memory episodes with metadata to enable research queries and DM visibility.

**Details**:
- DM narrations mentioning equipment create episodes with `event_type: "equipment"` metadata
- Tag acquisition events: `equipment_action: "acquired"`, `item_name: str`, `turn: int`
- Tag loss events: `equipment_action: "lost"`, `item_name: str`, `turn: int`
- Agents query memory normally (no special equipment access)
- Memory corruption applies equally to equipment memories (human-like forgetting)

### FR-027: DM Equipment Research Commands

**Priority**: P2

**Requirement**: System MUST provide DM research tools to inspect what agents remember about equipment without affecting agent memory.

**Commands**:
- `/mem:equipment [character_name]` - Query all equipment memories for character
- `/mem:test [character_name] [item]` - Test if agent would remember specific item
- `/mem:track [character_name] +[item]` - DM-only note (not visible to agents)
- `/mem:list [character_name]` - Show DM notes for ground truth

**Behavior**:
- Research queries run separately from agent memory queries
- Results show: memory content, confidence score, corruption level, retrieval likelihood
- DM tracking is session notes only (not canonical state, not seen by agents)

### FR-028: Memory Retrieval Metrics

**Priority**: P3 (Research instrumentation)

**Requirement**: System SHOULD track metrics on equipment memory accuracy for research analysis.

**Metrics**:
- Memory retrieval success rate (per agent, per trait profile)
- Correlation between personality traits and equipment recall
- "Aha moment" detection (agent successfully recalls forgotten item at critical time)
- Memory accuracy decay over turn count
- Impact of emotional_memory and detail_oriented traits on equipment recall

### FR-029: Equipment Context in Prompts

**Priority**: P2

**Requirement**: System MUST provide equipment context in agent prompts via memory query, not perfect state list.

**Details**:
- CharacterAgent prompts include base equipment from CharacterSheet
- Agents can query memory for "what equipment do I have?" (memory-based retrieval)
- No guaranteed accurate equipment list (intentional human-like fallibility)
- Recent acquisitions more likely remembered (recency effect)
- High-detail_oriented agents remember equipment better (personality-driven)

---

## Data Model Additions

### 6.4 DM Session Notes (Optional)

**Location**: `src/interface/dm_notes.py` (new file)

```python
from redis import Redis
from pydantic import BaseModel, Field
from loguru import logger

class DMEquipmentNote(BaseModel):
    """
    DM's personal session notes for tracking ground truth.

    NOT visible to agents. NOT canonical state. Just DM bookkeeping
    like physical DM notes during a real game session.
    """

    character_id: str = Field(
        pattern=r'^char_[a-z0-9_]+$',
        description="Character identifier"
    )

    item: str = Field(
        description="Item description"
    )

    acquired_turn: int = Field(
        description="Turn when DM noted acquisition"
    )

    notes: str | None = Field(
        default=None,
        description="Optional DM notes about this item"
    )


class DMNotesManager:
    """
    Manages DM's personal session notes (not agent-visible state).

    This is equivalent to a DM's notebook during a real game.
    Agents NEVER see this data. It's purely for DM session management.
    """

    def __init__(self, redis_client: Redis):
        self.redis = redis_client

    def add_note(self, character_id: str, item: str, turn: int, notes: str | None = None) -> None:
        """Add DM note about equipment (DM bookkeeping only)."""
        pass

    def remove_note(self, character_id: str, item: str) -> None:
        """Remove DM note (DM changed their mind or item lost)."""
        pass

    def get_notes(self, character_id: str) -> list[DMEquipmentNote]:
        """Get all DM notes for a character (DM reference only)."""
        pass

    def clear_all_notes(self) -> int:
        """Clear all DM notes (session restart)."""
        pass
```

**Redis Storage Pattern**:
```
Key: dm:notes:{character_id}:equipment
Type: Set of JSON-serialized DMEquipmentNote
Purpose: DM session bookkeeping, never visible to agents
```

### 6.5 Memory Research Query Results

**Location**: `src/memory/equipment_research.py` (new file)

```python
class EquipmentMemoryQuery(BaseModel):
    """
    Result of DM research query about equipment memories.

    Shows what an agent would retrieve if they queried memory,
    without actually triggering agent memory access.
    """

    character_id: str
    item_name: str

    # Memory retrieval simulation
    would_remember: bool = Field(
        description="Would agent retrieve this memory?"
    )

    confidence: float = Field(
        ge=0.0, le=1.0,
        description="Memory confidence score after corruption"
    )

    corruption_level: float = Field(
        ge=0.0, le=1.0,
        description="How corrupted is this memory? (0=pristine, 1=fully decayed)"
    )

    source_turn: int | None = Field(
        default=None,
        description="Turn when memory was created"
    )

    turns_ago: int | None = Field(
        default=None,
        description="How many turns ago (affects recency decay)"
    )

    memory_text: str | None = Field(
        default=None,
        description="Actual memory content (if would_remember=True)"
    )

    # Personality factor analysis
    detail_oriented_bonus: float = Field(
        description="Boost from detail_oriented trait"
    )

    recency_bonus: float = Field(
        description="Boost from recent acquisition"
    )
```

---

## DM Command Extensions

### Updated Command Reference Table

Add to `quickstart.md` DM Commands Reference section:

| Command | Description | Example |
|---------|-------------|---------|
| `/mem:equipment [char]` | Show all equipment memories | `/mem:equipment Zara-7` |
| `/mem:test [char] [item]` | Test if agent would remember item | `/mem:test Zara-7 plasma rifle` |
| `/mem:track [char] +[item]` | Add DM session note | `/mem:track Zara-7 +plasma rifle` |
| `/mem:track [char] -[item]` | Remove DM session note | `/mem:track Zara-7 -plasma rifle` |
| `/mem:list [char]` | Show DM notes for character | `/mem:list Zara-7` |

### Command Parsing

**Location**: `src/interface/dm_cli.py` (extend DMCommandParser)

Add patterns:
```python
class DMCommandType(str, Enum):
    # ... existing commands ...
    MEMORY_EQUIPMENT = "mem:equipment"
    MEMORY_TEST = "mem:test"
    MEMORY_TRACK = "mem:track"
    MEMORY_LIST = "mem:list"

COMMAND_PATTERNS = {
    # ... existing patterns ...
    DMCommandType.MEMORY_EQUIPMENT: r'^/mem:equipment\s+(\S+)$',
    DMCommandType.MEMORY_TEST: r'^/mem:test\s+(\S+)\s+(.+)$',
    DMCommandType.MEMORY_TRACK: r'^/mem:track\s+(\S+)\s+([+-])(.+)$',
    DMCommandType.MEMORY_LIST: r'^/mem:list\s+(\S+)$',
}
```

### Command Output Examples

**`/mem:equipment Zara-7`** - Show all equipment memories:
```
=== Equipment Memories: Zara-7 ===

Turn 1: Advanced toolkit (base equipment, pristine)
Turn 1: Repair drone (base equipment, pristine)
Turn 5: Plasma rifle (acquired, confidence: 0.85, mild corruption)
Turn 12: Ancient data pad (acquired, confidence: 0.60, moderate corruption)
Turn 18: Broken toolkit (lost/discarded, confidence: 0.40, heavy corruption)

Memory Retrieval Likelihood:
  ✓ Advanced toolkit (100% - base equipment)
  ✓ Repair drone (100% - base equipment)
  ✓ Plasma rifle (85% - recent, detail_oriented bonus)
  ~ Ancient data pad (60% - older, decaying)
  ✗ Broken toolkit (40% - lost item, heavily corrupted)
```

**`/mem:test Zara-7 plasma rifle`** - Test specific item recall:
```
=== Memory Test: Zara-7 / "plasma rifle" ===

Would Remember: YES (85% confidence)

Memory Details:
  Source: Turn 5 DM narration
  Content: "Zara-7 picks up the plasma rifle from the crate"
  Turns Ago: 15 turns
  Corruption: 0.15 (mild - recent memory, high detail_oriented)

Personality Factors:
  detail_oriented: 0.8 → +20% retention
  recency: 15 turns → -10% decay
  emotional_memory: 0.3 → +0% (non-emotional event)

Final Confidence: 0.85 → Would retrieve in memory query
```

**`/mem:track Zara-7 +plasma rifle`** - Add DM note:
```
✓ DM note added: Zara-7 has "plasma rifle"

Note: This is your personal session note, NOT visible to agents.
Agents rely on their own corrupted memory for equipment recall.
```

**`/mem:list Zara-7`** - Show DM notes:
```
=== DM Session Notes: Zara-7 ===

Equipment (DM tracking only):
  + Plasma rifle (noted turn 5)
  + Ancient data pad (noted turn 12, note: "contains star charts")

Reminder: Agents DON'T see this list. They rely on memory.
Use /mem:test to check if agent would actually remember items.
```

---

## Integration Points

### Memory Episode Storage (No Special Handling Needed)

**Location**: `src/memory/graphiti_client.py`

**No modifications required.** Graphiti already handles equipment detection via semantic understanding:

```python
def add_episode(
    self,
    episode_text: str,
    agent_id: str,
    turn_number: int,
    session_number: int,
    **kwargs
) -> str:
    """
    Add memory episode. Graphiti automatically extracts entities and relationships.

    When DM narrates "Zara picks up the plasma rifle", Graphiti's LLM-based
    extraction automatically creates:
    - Entity: "plasma rifle" (object type)
    - Relationship: "Zara-7" -> "has" -> "plasma rifle"
    - Fact: acquisition event with temporal context

    No manual regex detection needed - Graphiti understands semantic meaning.
    """

    episode_id = await self.graphiti_client.add_episode(
        name=f"turn_{turn_number}",
        episode_body=episode_text,
        source_description=f"Session {session_number}, Turn {turn_number}",
        reference_time=datetime.now(),
        custom_metadata={
            "agent_id": agent_id,
            "turn_number": turn_number,
            "session_number": session_number,
            **kwargs.get("custom_metadata", {})
        }
    )

    return episode_id
```

**Key Insight**: Graphiti's entity extraction already understands:
- "picks up", "finds", "acquires", "takes" → possession relationship
- "drops", "loses", "discards" → loss relationship
- Item entities (weapons, tools, objects)
- Temporal context (when acquisition happened)

No regex patterns needed - the LLM handles semantic variations naturally.

### CharacterAgent Prompt Building (No Change)

**Location**: `src/agents/character.py`

**No modifications needed.** Agents continue using base equipment from CharacterSheet:

```python
def _build_character_system_prompt(self) -> str:
    """Build system prompt with base equipment (agents use memory for changes)."""

    # Use base equipment from frozen CharacterSheet
    equipment_str = ', '.join(self.character_sheet.equipment) if self.character_sheet.equipment else 'None'

    # ... rest of prompt building ...

    return f"""You are roleplaying as {self.character_sheet.name}, a {style_str} {role_str}.

Character traits:
- Goal: {self.character_sheet.character_goal}
- Approach: {approach_desc} (number: {self.character_sheet.number})
- Equipment (starting): {equipment_str}

Note: You may have acquired or lost items during this session. Query your memory if you need to recall recent equipment changes.

Speech patterns:
{speech_patterns}

...
"""
```

**Key**: Agents rely on memory queries to remember session equipment changes, not a perfect state list.

### Redis Cleanup

**Location**: `src/utils/redis_cleanup.py`

Update `cleanup_redis_for_new_session()` to clear DM notes:

```python
def cleanup_redis_for_new_session(redis_client: Redis) -> dict:
    """Clear all session state for fresh start."""

    # ... existing cleanup (messages, queues, turn state) ...

    # Clear DM session notes (optional feature)
    dm_notes_keys = redis_client.keys("dm:notes:*")
    if dm_notes_keys:
        deleted_dm_notes = redis_client.delete(*dm_notes_keys)
        logger.info(f"Cleared {deleted_dm_notes} DM note entries")
    else:
        deleted_dm_notes = 0

    return {
        # ... existing counts ...
        "dm_notes": deleted_dm_notes,
    }
```

### DM CLI Command Handlers

**Location**: `src/interface/dm_cli.py`

Add memory research command handlers:

```python
from src.memory.equipment_research import EquipmentMemoryResearcher
from src.interface.dm_notes import DMNotesManager

def _handle_mem_equipment_command(self, character_name: str) -> dict:
    """Handle /mem:equipment command to show all equipment memories."""

    char_id = self._resolve_character_name(character_name)
    if not char_id:
        return {"success": False, "error": f"Character '{character_name}' not found"}

    # Query Graphiti for equipment-related entities and relationships
    # Graphiti's semantic search understands "equipment", "items", "belongings"
    researcher = EquipmentMemoryResearcher(self.graphiti_client)
    memories = researcher.query_equipment_memories(
        agent_id=self._get_agent_id(char_id),
        query="equipment items belongings tools weapons",
        session_number=self.session_number
    )

    # Format output (see Command Output Examples section)
    return {
        "success": True,
        "memories": memories,
        "character_name": character_name
    }


def _handle_mem_test_command(self, character_name: str, item: str) -> dict:
    """Handle /mem:test command to test if agent would remember item."""

    char_id = self._resolve_character_name(character_name)
    if not char_id:
        return {"success": False, "error": f"Character '{character_name}' not found"}

    researcher = EquipmentMemoryResearcher(self.graphiti_client)
    result = researcher.test_item_recall(
        character_id=char_id,
        item_name=item,
        current_turn=self.current_turn,
        personality=self._get_character_personality(char_id)
    )

    # Format output (see Command Output Examples section)
    return {
        "success": True,
        "result": result,
        "character_name": character_name,
        "item": item
    }


def _handle_mem_track_command(self, character_name: str, action: str, item: str) -> dict:
    """Handle /mem:track command for DM session notes."""

    char_id = self._resolve_character_name(character_name)
    if not char_id:
        return {"success": False, "error": f"Character '{character_name}' not found"}

    notes_manager = DMNotesManager(self.redis)

    if action == "+":
        notes_manager.add_note(char_id, item, self.current_turn)
        return {
            "success": True,
            "message": f"DM note added: {character_name} has '{item}'"
        }
    elif action == "-":
        notes_manager.remove_note(char_id, item)
        return {
            "success": True,
            "message": f"DM note removed: {character_name} / '{item}'"
        }


def _handle_mem_list_command(self, character_name: str) -> dict:
    """Handle /mem:list command to show DM session notes."""

    char_id = self._resolve_character_name(character_name)
    if not char_id:
        return {"success": False, "error": f"Character '{character_name}' not found"}

    notes_manager = DMNotesManager(self.redis)
    notes = notes_manager.get_notes(char_id)

    return {
        "success": True,
        "notes": notes,
        "character_name": character_name
    }
```

---

## Testing Requirements

### Unit Tests

**Location**: `tests/unit/interface/test_dm_notes.py`

```python
def test_add_dm_note_creates_entry(redis_client):
    """Test adding DM note stores in Redis."""
    from src.interface.dm_notes import DMNotesManager

    manager = DMNotesManager(redis_client)
    manager.add_note("char_zara_001", "plasma rifle", turn=5)

    notes = manager.get_notes("char_zara_001")
    assert len(notes) == 1
    assert notes[0].item == "plasma rifle"
    assert notes[0].acquired_turn == 5


def test_remove_dm_note_deletes_entry(redis_client):
    """Test removing DM note deletes from Redis."""
    manager = DMNotesManager(redis_client)
    manager.add_note("char_zara_001", "plasma rifle", turn=5)
    manager.remove_note("char_zara_001", "plasma rifle")

    notes = manager.get_notes("char_zara_001")
    assert len(notes) == 0


def test_clear_all_dm_notes(redis_client):
    """Test clearing all DM notes."""
    manager = DMNotesManager(redis_client)
    manager.add_note("char_zara_001", "plasma rifle", turn=5)
    manager.add_note("char_rex_002", "sword", turn=7)

    count = manager.clear_all_notes()
    assert count == 2
```

### Contract Tests

**Location**: `tests/contract/test_equipment_memory_contracts.py`

```python
def test_dm_notes_manager_interface():
    """Verify DMNotesManager has all required methods."""
    from src.interface.dm_notes import DMNotesManager

    assert hasattr(DMNotesManager, 'add_note')
    assert hasattr(DMNotesManager, 'remove_note')
    assert hasattr(DMNotesManager, 'get_notes')
    assert hasattr(DMNotesManager, 'clear_all_notes')


def test_equipment_researcher_interface():
    """Verify EquipmentMemoryResearcher has all required methods."""
    from src.memory.equipment_research import EquipmentMemoryResearcher

    assert hasattr(EquipmentMemoryResearcher, 'query_all_equipment_memories')
    assert hasattr(EquipmentMemoryResearcher, 'test_item_recall')
```

### Integration Tests

**Location**: `tests/integration/test_equipment_memory.py`

```python
def test_equipment_memory_extraction_via_graphiti(graphiti_client):
    """Test Graphiti extracts equipment entities from DM narration."""
    episode_id = graphiti_client.add_episode(
        episode_text="Zara picks up the plasma rifle",
        agent_id="agent_alex_001",
        turn_number=5,
        session_number=1
    )

    # Graphiti's LLM should have extracted:
    # - Entity: "plasma rifle"
    # - Relationship: Zara-7 -> has -> plasma rifle

    # Query for equipment-related entities
    results = graphiti_client.search(
        query="plasma rifle equipment",
        agent_id="agent_alex_001"
    )

    assert len(results) > 0
    assert any("plasma rifle" in str(r).lower() for r in results)


def test_mem_test_command_queries_memory(cli, graphiti_client):
    """Test /mem:test command simulates memory retrieval."""
    # Create equipment memory
    graphiti_client.add_episode(
        episode_text="Zara picks up the plasma rifle",
        agent_id="agent_alex_001",
        turn_number=5,
        session_number=1
    )

    # Test if agent would remember (turn 20, 15 turns later)
    result = cli.execute("/mem:test Zara-7 plasma rifle", turn=20)

    assert result["success"] is True
    assert result["result"].would_remember is True
    assert result["result"].confidence > 0.7  # Recent memory, should be strong


def test_mem_equipment_lists_all_memories(cli, graphiti_client):
    """Test /mem:equipment shows all equipment memories."""
    # Create multiple equipment events
    graphiti_client.add_episode("Zara picks up plasma rifle", ...)
    graphiti_client.add_episode("Zara finds ancient data pad", ...)

    result = cli.execute("/mem:equipment Zara-7")

    assert result["success"] is True
    assert len(result["memories"]) >= 2


def test_dm_notes_independent_of_agent_memory(cli, redis_client, graphiti_client):
    """Test DM notes don't affect agent memory queries."""
    # Add DM note (not a memory)
    cli.execute("/mem:track Zara-7 +plasma rifle")

    # Agent queries memory (should NOT find anything)
    memories = graphiti_client.search(
        query="plasma rifle",
        agent_id="agent_alex_001"
    )

    assert len(memories) == 0  # DM note doesn't create agent memory


def test_cleanup_clears_dm_notes(redis_client):
    """Test cleanup removes DM notes."""
    from src.utils.redis_cleanup import cleanup_redis_for_new_session
    from src.interface.dm_notes import DMNotesManager

    notes_manager = DMNotesManager(redis_client)
    notes_manager.add_note("char_zara_001", "plasma rifle", turn=5)

    result = cleanup_redis_for_new_session(redis_client)

    assert result["dm_notes"] == 1
    notes = notes_manager.get_notes("char_zara_001")
    assert len(notes) == 0
```

---

## Implementation Tasks

### New Tasks (extend tasks.md)

**Phase 4: Memory-Based Equipment Tracking (Extension)**

- [ ] **T220** [P] Implement DMEquipmentNote and DMNotesManager in `src/interface/dm_notes.py`
  - **Reference**: extension-character-state.md §6.4 (DM Session Notes specification)
  - **Tests**: `tests/unit/interface/test_dm_notes.py` (all methods)

- [ ] **T221** Implement EquipmentMemoryQuery model and EquipmentMemoryResearcher in `src/memory/equipment_research.py`
  - **Reference**: extension-character-state.md §6.5 (Memory Research Query Results)
  - **Tests**: `tests/contract/test_equipment_memory_contracts.py::test_equipment_researcher_interface`

- [ ] **T222** [P] Add /mem:equipment, /mem:test, /mem:track, /mem:list commands to DMCommandParser in `src/interface/dm_cli.py`
  - **Reference**: extension-character-state.md §DM Command Extensions (Command Parsing)
  - **Tests**: `tests/unit/interface/test_dm_cli.py::test_parse_mem_equipment_command`, etc.

- [ ] **T223** [P] Implement memory research command handlers in DMCLI class in `src/interface/dm_cli.py`
  - **Reference**: extension-character-state.md §Integration Points (DM CLI Command Handlers)
  - **Tests**: `tests/integration/test_equipment_memory.py::test_mem_test_command_queries_memory`

- [ ] **T224** Implement EquipmentMemoryResearcher.query_equipment_memories() using Graphiti semantic search
  - **Reference**: extension-character-state.md §Integration Points (DM CLI Command Handlers)
  - **Tests**: `tests/integration/test_equipment_memory.py::test_equipment_memory_extraction_via_graphiti`

- [ ] **T225** Implement EquipmentMemoryResearcher.test_item_recall() to simulate memory retrieval
  - **Reference**: extension-character-state.md §6.5 (EquipmentMemoryQuery model)
  - **Tests**: `tests/integration/test_equipment_memory.py::test_mem_test_command_queries_memory`

- [ ] **T226** Update redis cleanup to clear DM notes in `src/utils/redis_cleanup.py`
  - **Reference**: extension-character-state.md §Integration Points (Redis Cleanup)
  - **Tests**: `tests/integration/test_equipment_memory.py::test_cleanup_clears_dm_notes`

- [ ] **T227** Update CharacterAgent prompt to mention memory-based equipment tracking in `src/agents/character.py`
  - **Reference**: extension-character-state.md §Integration Points (CharacterAgent Prompt Building)
  - **Tests**: `tests/integration/test_equipment_memory.py` (verify prompt includes note about querying memory)

- [ ] **T228** Update quickstart.md DM Commands Reference table with memory research commands
  - **Reference**: extension-character-state.md §DM Command Extensions (Command table)
  - **Tests**: Manual verification

---

## Non-Goals (Out of Scope)

1. **Perfect equipment recall for agents**: Agents SHOULD forget items (human-like behavior)
2. **Manual equipment tagging**: Graphiti's LLM extraction handles this automatically
3. **Cross-session persistence**: Equipment memories cleared on session restart (like all memories)
4. **Agent access to DM notes**: DM tracking is session bookkeeping only, never visible to agents
5. **Equipment quantification**: No stack counts, just acquisition/loss events
6. **Nested items**: No containers, no equipped vs carried distinction
7. **Equipment effects on dice**: No mechanical bonuses (purely narrative)
8. **Status effects**: No wounded, inspired, exhausted tracking (separate feature if needed)
9. **Historical "time travel"**: No "what did agent remember at turn X?" queries (current turn only)
10. **Guaranteed memory accuracy**: Memory corruption IS THE FEATURE, not a bug

---

## Migration Path

### For Existing Sessions

Since this is an additive, research-focused feature:
- Existing code continues to work without modification
- Memory tagging happens automatically when equipment keywords detected
- DM research commands are optional tools
- DM notes are optional (DMs can use external notes if preferred)
- No breaking changes to existing models or APIs

### Rollout Plan

1. **Phase 1**: Implement metadata models and DM notes (T220-T221)
2. **Phase 2**: Add memory research query infrastructure (T222)
3. **Phase 3**: Implement equipment detection and tagging (T223-T224)
4. **Phase 4**: Add DM research commands to CLI (T225-T226)
5. **Phase 5**: Update cleanup and documentation (T227-T229)

Each phase can be tested independently.

---

## Rationale & Benefits

### Why Memory-Only?

1. **Research Alignment**: Studying emergent behavior requires fallible memory, not perfect state
2. **Human-Like Agents**: Real players forget items, creating "aha!" moments
3. **Personality-Driven**: detail_oriented, analytical_score affect equipment recall
4. **Simplicity**: No new state layer, just metadata on existing memory system
5. **DM Tools**: Research commands give DM visibility without breaking agent realism

### Benefits Over Perfect State Approach

| Aspect | Perfect State | Memory-Only (Proposed) |
|--------|---------------|------------------------|
| **Realism** | Robotic perfect recall | Human-like forgetting |
| **Emergence** | Predictable | Surprising "I have the thing!" moments |
| **Personality** | No trait impact | detail_oriented, analytical traits matter |
| **Research Value** | Low (expected behavior) | High (emergent coordination) |
| **DM Control** | Agents know everything | DM tracks ground truth separately |
| **Simplicity** | New state layer | Uses existing memory system |

### Example Emergent Behavior

```
Turn 5: DM: "You find a grappling hook in the crate"
        Memory created (tagged: equipment_action=acquired, item=grappling hook)

Turn 25: [Party facing cliff]
         Agent (low detail_oriented): Doesn't remember grappling hook
         Agent: "Maybe we can climb down carefully?"

Turn 27: [Agent queries memory for "cliff" or "climbing gear"]
         Memory retrieval succeeds! (20 turns ago, moderate corruption)
         Agent: "Wait... didn't we find a grappling hook earlier?!"
         DM: "Yes! Great memory!"

Turn 27: [Party uses grappling hook]
         **EMERGENT STORY MOMENT** - realistic player forgetfulness + recall
```

This creates **realistic drama** that perfect inventory would eliminate.

---

## Research Metrics & Instrumentation

### Metrics to Track

1. **Equipment Recall Rate**: % of equipment memories successfully retrieved when queried
2. **Personality Correlation**: Correlation between detail_oriented trait and recall success
3. **Recency Effect**: Memory accuracy vs turns elapsed since acquisition
4. **Aha Moments**: Detected instances of late recall (agent remembers after >10 turns)
5. **Coordination Patterns**: Do players remind each other about forgotten equipment?

### Data Collection

- Log all `/mem:test` queries with results (would_remember, confidence, corruption_level)
- Tag memories when agents successfully query for equipment
- Flag "late recall" events (memory >10 turns old successfully retrieved)
- Track DM note creation (indicates items DM wants to track)

### Analysis Questions

- Do high-analytical agents remember equipment better?
- Does emotional_memory trait affect item recall?
- What decay curve emerges for equipment memories?
- Do parties develop "inventory manager" social roles?

---

## Open Questions

1. **Memory Confidence Threshold**: At what confidence should `/mem:test` report "would remember"? (Proposal: >0.6)
2. **DM Notification**: Should system notify DM when agent forgets important item? (Proposal: No, let it emerge naturally)
3. **Historical Queries**: Should we support "what did agent remember at turn X"? (Proposal: P3, not MVP)
4. **Query Tuning**: Should we provide DM controls for equipment query specificity? (Proposal: Start with broad semantic search, tune based on results)

---

## Conclusion

This extension transforms the "equipment persistence gap" from a **bug to a feature**. By embracing fallible memory, we create opportunities for emergent storytelling that mirrors real TTRPG gameplay: players forget items, remember them at critical moments, and coordinate to compensate for each other's memory gaps.

**Key Insight**: The "Wait, I have the thing!" moment is **more valuable for research** than perfect inventory tracking.

**DM Tools**: Memory research commands give DMs visibility and session management tools without compromising agent realism.

**Recommendation**: Implement as P2 research enhancement after core Phase 3 completion. Estimated effort: 2-3 days for full implementation + testing + research instrumentation.

**Future Research**: Track emergence of "inventory manager" social roles, memory-based party coordination strategies, and personality-driven recall patterns.
