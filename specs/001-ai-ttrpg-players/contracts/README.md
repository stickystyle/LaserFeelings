# LangGraph Node Contracts

This directory contains formal contract specifications for each LangGraph node in the AI TTRPG Player System turn cycle state machine.

## Purpose

Node contracts define the input/output schemas, validation rules, and behavioral expectations for each phase of the turn-based gameplay loop. They serve as:

1. **Implementation Blueprints**: Clear specifications for developers implementing LangGraph nodes
2. **Testing Specifications**: Expected inputs, outputs, and edge cases for unit/integration tests
3. **Documentation**: Comprehensive reference for system behavior and data flow
4. **Validation Targets**: Success criteria and performance benchmarks

## Contract Files

### Implementation Status Legend

- ✅ **Production**: Wired into graph and actively used in Phase 3
- ⚠️ **MVP Stub**: Wired into graph but returns placeholder data (Phase 5+ integration pending)
- 🔧 **Unwired**: Implemented but intentionally bypassed (Phase 4+ integration)
- ❌ **Not Implemented**: Design only, no code yet (Phase 7+ future work)

### Phase 3 Production Nodes

1. **`clarification_contract.yaml`** - DM Clarification Q&A System ✅ **NEW**
   - **Phases**: `dm_clarification_collect`, `dm_clarification_wait`
   - **Purpose**: Allow AI players to ask DM questions after narration before strategy
   - **Key Features**:
     - Two-node conditional interrupt pattern (collect → wait only if questions exist)
     - Multi-round Q&A loop (up to 3 rounds)
     - Auto-generation of questions via LLM based on narration
     - DM can force finish to skip remaining rounds
     - All Q&A visible on OOC channel
   - **Status**: ✅ Production (added Oct 20, 2025, commit d895a93)

2. **`memory_query_contract.yaml`** - Memory Retrieval Node ⚠️
   - **Phase**: `memory_retrieval`, `second_memory_query`
   - **Purpose**: Retrieve relevant memories from Graphiti knowledge graph
   - **Key Features**:
     - Semantic search across personal, character, and shared memories
     - Temporal filtering and memory corruption simulation
     - Rehearsal count tracking for memory strengthening
   - **Status**: ⚠️ MVP Stub - Currently returns empty memories, Phase 5 will add Graphiti integration

3. **`player_agent_contract.yaml`** - Strategic Intent Node ✅
   - **Phase**: `strategic_intent`
   - **Purpose**: Strategic decision-making layer (out-of-character)
   - **Key Features**:
     - Personality-driven strategic planning
     - Memory integration for context-aware decisions
     - Clarifying question generation (Phase 3 addition)
     - Routes to P2C directive phase (not directly to character)
   - **Status**: ✅ Production

4. **`p2c_directive_contract.yaml`** - Player-to-Character Message Routing ✅ **NEW**
   - **Phase**: `p2c_directive`
   - **Purpose**: Route strategic intent to character via MessageRouter P2C channel
   - **Key Features**:
     - Enforces dual-layer architecture boundary
     - Uses Redis message routing for clean separation
     - Enables future interception/filtering features
   - **Status**: ✅ Production

5. **`character_agent_contract.yaml`** - In-Character Action Node ✅
   - **Phase**: `character_action`
   - **Purpose**: Roleplay layer performing character actions
   - **Key Features**:
     - Directive interpretation through personality lens
     - Intent-only action expression (no outcome narration)
     - Helper detection (is_helping, helping_character_id)
     - Prepared/expert detection for dice bonuses
     - Speech pattern and mannerism consistency
   - **Status**: ✅ Production

6. **`helper_resolution_contract.yaml`** - Helper Dice Pre-Roll ✅ **NEW**
   - **Phase**: `resolve_helpers`
   - **Purpose**: Roll dice for all helping characters before main action
   - **Key Features**:
     - Identifies helpers from character actions
     - Pre-rolls dice for each helper
     - Counts successful helpers (≥1 success)
     - Grants +1 die per successful helper to main action
   - **Status**: ✅ Production (implements Lasers & Feelings "+1d6 if you have help" rule)

7. **`laser_feelings_contract.yaml`** - LASER FEELINGS Question System ✅ **NEW**
   - **Phase**: `laser_feelings_question`
   - **Purpose**: Handle exact number roll (LASER FEELINGS game mechanic)
   - **Key Features**:
     - Detects exact match on any die
     - Auto-generates contextual question for DM
     - DM interrupt point
     - Answer influences outcome narration
   - **Status**: ✅ Production (implements core Lasers & Feelings game rule)

### Phase 4+ Future Nodes

8. **`validation_contract.yaml`** - Narrative Overreach Detection Node 🔧
   - **Phase**: `validation`
   - **Purpose**: Prevent AI from narrating action outcomes
   - **Key Features**:
     - Hybrid pattern + semantic validation
     - Up to 3 retry attempts with escalating strictness
     - Auto-correction fallback after max retries
   - **Status**: 🔧 Unwired - Implemented but bypassed, Phase 4 will wire into graph

### Phase 7+ Future Nodes (Not Implemented)

9. **OOC Discussion & Consensus** ❌
   - **Phases**: `ooc_discussion`, `consensus_detection`
   - **Purpose**: Multi-agent strategic coordination
   - **Status**: ❌ Not Implemented - Phase 7 future work

## Contract Structure

Each contract YAML file contains:

### Required Sections

- **`node_name`**: Unique identifier for the LangGraph node
- **`description`**: Purpose and role in turn cycle
- **`input_schema`**: Expected state fields and agent configuration
- **`output_schema`**: Produced state fields and phase transitions
- **`preconditions`**: Required state before node execution
- **`postconditions`**: Guaranteed state after successful execution
- **`error_conditions`**: Error scenarios and handling strategies
- **`retry_logic`**: Progressive retry behavior with attempt-specific prompts
- **`validation_rules`**: Specific validation checks and examples
- **`examples`**: Concrete invocation scenarios with sample data

### Optional Sections

- **`algorithm`**: Step-by-step execution logic (for complex nodes)
- **`integration_notes`**: LangGraph implementation guidance
- **`performance_targets`**: Execution time and resource budgets
- **`related_requirements`**: Cross-references to spec.md requirements

## Usage

### For Implementation

1. Read the contract for your target node
2. Implement the `input_schema` and `output_schema` using TypedDict/Pydantic
3. Follow the `algorithm` or `retry_logic` sections for business logic
4. Ensure all `preconditions` are checked before execution
5. Validate all `postconditions` are met before returning
6. Use `examples` section for unit test fixtures

### For Testing

1. Use `examples` section for test case generation
2. Verify `preconditions` enforcement
3. Validate `postconditions` satisfaction
4. Test all `error_conditions` with appropriate fallbacks
5. Benchmark against `performance_targets`

### For Integration

1. Review `integration_notes` for LangGraph-specific guidance
2. Implement conditional edges using retry_logic decision trees
3. Connect nodes according to `output_schema.current_phase` transitions
4. Use RQ worker patterns from integration_notes for parallelism

## LangGraph Workflow Integration

**Phase 3 Production Architecture** (18 nodes, 4 interrupt points)

Nodes connect in this sequence:

```
dm_narration (INTERRUPT for DM input)
    ↓
memory_retrieval [MVP STUB - returns empty]
    ↓
dm_clarification_collect (auto-asks players for questions)
    ↓
[Conditional] → dm_clarification_wait (INTERRUPT) OR skip to second_memory_query
    ↓ (if questions exist)
dm_clarification_wait (INTERRUPT for DM answers)
    ↓
[Loop back to collect for follow-ups OR proceed after max 3 rounds]
    ↓
second_memory_query [MVP STUB - returns empty]
    ↓
strategic_intent (player decides strategy)
    ↓
p2c_directive (route via MessageRouter P2C channel)
    ↓
character_action (character performs action)
    ↓
[Phase 4 TODO: validation retry loop - currently bypassed]
    ↓
dm_adjudication (INTERRUPT for DM ruling)
    ↓
resolve_helpers (pre-roll dice for all helpers)
    ↓
dice_resolution (roll action dice with bonuses)
    ↓
[Conditional] → laser_feelings_question (INTERRUPT) OR dm_outcome
    ↓ (if exact number rolled)
laser_feelings_question (INTERRUPT for GM question)
    ↓
dm_outcome (INTERRUPT for DM narration)
    ↓
character_reaction (character responds emotionally)
    ↓
memory_consolidation [MVP STUB - logs only, no storage]
    ↓
END
```

### Conditional Edges (Phase 3 Reality)

- **`dm_clarification_collect → dm_clarification_wait`**: If clarifying_questions_this_round not empty
- **`dm_clarification_collect → second_memory_query`**: If no questions asked, skip clarification
- **`dm_clarification_wait → dm_clarification_collect`**: Loop back for follow-ups (max 3 rounds)
- **`dm_clarification_wait → second_memory_query`**: After max rounds or DM types "finish"
- **`dice_resolution → laser_feelings_question`**: If any die == character's number (LASER FEELINGS)
- **`dice_resolution → dm_outcome`**: Normal dice resolution, no exact match

### Interrupt Points (DM Interaction)

The graph pauses at exactly **4 nodes** to wait for DM input:

1. **`dm_clarification_wait`**: DM answers player questions (multi-round Q&A)
2. **`dm_adjudication`**: DM adjudicates action validity
3. **`laser_feelings_question`**: DM answers the LASER FEELINGS question
4. **`dm_outcome`**: DM narrates the outcome of the action

### Phase 4+ Features (Not Yet Wired)

- **`validation_retry`**: Implemented but bypassed - character_action routes directly to dm_adjudication
- **`validation_escalate`**: Implemented but not wired into graph
- **`rollback_handler`**: Implemented but not wired into graph
- **`ooc_discussion`**: Not implemented (Phase 7 - multi-agent coordination)
- **`consensus_detection`**: Not implemented (Phase 7 - multi-agent coordination)

## State Management

All nodes operate on a shared `GameState` TypedDict with **50+ fields**:

```python
class GameState(TypedDict):
    # Phase tracking
    current_phase: Literal["dm_narration", "memory_query", "dm_clarification",
                           "strategic_intent", "p2c_directive", "character_action", ...]
    turn_number: int
    session_number: int

    # DM input
    dm_narration: str
    dm_adjudication_needed: bool
    dm_outcome: NotRequired[str]

    # Strategic layer
    strategic_intents: dict[str, str]  # agent_id -> intent

    # Character layer (NOTE: ActionDict not simple string!)
    character_actions: dict[str, ActionDict]  # character_id -> full action object
    character_reactions: dict[str, str]

    # Memory retrieval
    retrieved_memories: dict[str, list[dict]]
    retrieved_memories_post_clarification: NotRequired[dict[str, list[dict]]]

    # Clarification system (Phase 3 addition)
    clarification_round: NotRequired[int]
    awaiting_dm_clarifications: NotRequired[bool]
    clarifying_questions_this_round: NotRequired[dict[str, dict]]
    all_clarification_questions: NotRequired[list[dict]]

    # Dice resolution (multi-die system)
    dice_count: NotRequired[int]
    individual_rolls: NotRequired[list[int]]
    die_successes: NotRequired[list[bool]]
    total_successes: NotRequired[int]
    successful_helper_counts: NotRequired[dict[str, int]]  # Phase 3 addition

    # LASER FEELINGS (Phase 3 addition)
    laser_feelings_indices: NotRequired[list[int]]
    gm_question: NotRequired[str | None]
    laser_feelings_answer: NotRequired[str | None]

    # Validation (Phase 4 - not yet active)
    validation_attempt: int
    validation_valid: bool
    validation_failures: dict[str, list[str]]

    # ... (see data-model.md and src/models/game_state.py for complete 50+ field schema)
```

**Note**: `character_actions` is a `dict[str, ActionDict]` with structured data including task_type, is_prepared, is_expert, is_helping, helping_character_id, and justification fields - NOT a simple `dict[str, str]` as early contracts showed.

## Example Workflow

```python
from langgraph.graph import StateGraph, END

workflow = StateGraph(GameState)

# Add nodes
workflow.add_node("memory_query", memory_query_node)
workflow.add_node("player_agent", player_agent_strategic_intent)
workflow.add_node("character_action", character_agent_action)
workflow.add_node("validation", validation_node)

# Add edges
workflow.set_entry_point("memory_query")
workflow.add_edge("memory_query", "player_agent")
workflow.add_edge("player_agent", "character_action")
workflow.add_edge("character_action", "validation")

# Conditional edge for retry logic
workflow.add_conditional_edges(
    "validation",
    should_retry_validation,  # See validation_contract.yaml
    {
        "valid": "dm_adjudication",
        "retry": "character_action",
        "max_retries": "dm_adjudication"
    }
)
```

## Performance Targets Summary

| Node | P50 (ms) | P95 (ms) | Notes |
|------|----------|----------|-------|
| memory_query | 500 | 1500 | Graphiti search + corruption simulation |
| player_agent | 1500 | 3000 | LLM strategic reasoning |
| character_action | 2000 | 4000 | LLM roleplay generation |
| validation | 500 | 2000 | Pattern + optional LLM semantic check |

## Related Documents

- **`../data-model.md`**: Complete data model and TypedDict schemas
- **`../spec.md`**: Functional requirements and user stories
- **`../research.md`**: Technology choices and implementation patterns
- **`../plan.md`**: Implementation roadmap and phases

## Revision History

- **2025-10-21**: Major update to reflect Phase 3 implementation reality
  - Updated README with actual 18-node architecture (was 8 nodes)
  - Added clarification_contract.yaml (two-node Q&A system)
  - Added helper_resolution_contract.yaml (Lasers & Feelings helper mechanics)
  - Added laser_feelings_contract.yaml (exact number roll question system)
  - Added p2c_directive_contract.yaml (MessageRouter integration)
  - Updated memory_query_contract.yaml (marked as MVP stub, Phase 5 pending)
  - Updated player_agent_contract.yaml (added clarification, P2C routing)
  - Updated character_agent_contract.yaml (ActionDict structure, helper fields)
  - Updated validation_contract.yaml (marked as unwired, Phase 4 pending)
  - Documented 4 interrupt points for DM interaction
  - Added implementation status legend (Production/MVP Stub/Unwired/Not Implemented)
  - Updated GameState schema to show 50+ fields including Phase 3 additions
  - Fixed GamePhase enum to include P2C_DIRECTIVE phase

- **2025-10-19**: Initial contract generation for MVP nodes
  - memory_query_contract.yaml
  - player_agent_contract.yaml
  - character_agent_contract.yaml
  - validation_contract.yaml

---

**Note**: Contracts now accurately reflect Phase 3 production reality. Contracts marked as "MVP Stub", "Unwired", or "Not Implemented" represent future phase work (Phases 4-7). All Phase 3 production features are fully documented.
