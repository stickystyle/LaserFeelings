# LangGraph Node Contracts

This directory contains formal contract specifications for each LangGraph node in the AI TTRPG Player System turn cycle state machine.

## Purpose

Node contracts define the input/output schemas, validation rules, and behavioral expectations for each phase of the turn-based gameplay loop. They serve as:

1. **Implementation Blueprints**: Clear specifications for developers implementing LangGraph nodes
2. **Testing Specifications**: Expected inputs, outputs, and edge cases for unit/integration tests
3. **Documentation**: Comprehensive reference for system behavior and data flow
4. **Validation Targets**: Success criteria and performance benchmarks

## Contract Files

### Core Turn Cycle Nodes

1. **`memory_query_contract.yaml`** - Memory Retrieval Node
   - **Phase**: `memory_query`
   - **Purpose**: Retrieve relevant memories from Graphiti knowledge graph
   - **Key Features**:
     - Semantic search across personal, character, and shared memories
     - Temporal filtering and memory corruption simulation
     - Rehearsal count tracking for memory strengthening
     - Support for explicit DM queries
   - **Requirements**: FR-005, FR-006, FR-007, FR-019

2. **`player_agent_contract.yaml`** - Strategic Intent Node
   - **Phase**: `strategic_intent`
   - **Purpose**: Strategic decision-making layer (out-of-character)
   - **Key Features**:
     - Personality-driven strategic planning
     - Memory integration for context-aware decisions
     - Multi-agent OOC discussion initiation
     - Progressive retry logic for invalid intents
   - **Requirements**: FR-001, FR-002, FR-006, FR-007, FR-013

3. **`character_agent_contract.yaml`** - In-Character Action Node
   - **Phase**: `character_action`
   - **Purpose**: Roleplay layer performing character actions
   - **Key Features**:
     - Directive interpretation through personality lens
     - Intent-only action expression (no outcome narration)
     - Speech pattern and mannerism consistency
     - Progressive strictness on validation retries
   - **Requirements**: FR-001, FR-002, FR-003, FR-004, FR-009

4. **`validation_contract.yaml`** - Narrative Overreach Detection Node
   - **Phase**: `validation`
   - **Purpose**: Prevent AI from narrating action outcomes
   - **Key Features**:
     - Hybrid pattern + semantic validation
     - Up to 3 retry attempts with escalating strictness
     - Auto-correction fallback after max retries
     - False positive override via LLM semantic check
   - **Requirements**: FR-003, FR-004, FR-011

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

Nodes connect in this sequence:

```
dm_narration
    ↓
memory_query ←─────────────┐ (on error)
    ↓                       │
strategic_intent            │
    ↓                       │
ooc_discussion (multi-agent only)
    ↓                       │
consensus_detection         │
    ↓                       │
character_action ←──────────┤ (retry on validation failure)
    ↓                       │
validation ─────────────────┘
    ↓
dm_adjudication
    ↓
dice_resolution
    ↓
dm_outcome
    ↓
character_reaction
    ↓
memory_storage
```

### Conditional Edges

- **`validation → character_action`**: Retry on validation failure (max 3 attempts)
- **`validation → dm_adjudication`**: Proceed on validation success or max retries
- **`strategic_intent → ooc_discussion`**: Multi-agent coordination
- **`strategic_intent → character_action`**: Single agent skip coordination
- **`any_node → error_handler`**: On critical failure, rollback to last stable phase

## State Management

All nodes operate on a shared `GameState` TypedDict:

```python
class GameState(TypedDict):
    current_phase: Literal["memory_query", "strategic_intent", ...]
    turn_number: int
    dm_narration: str
    strategic_intents: dict[str, str]
    character_actions: dict[str, str]
    retrieved_memories: dict[str, list[dict]]
    validation_attempt: int
    validation_valid: bool
    validation_failures: dict[str, list[str]]
    # ... (see data-model.md for complete schema)
```

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

- **2025-10-19**: Initial contract generation for MVP nodes
  - memory_query_contract.yaml
  - player_agent_contract.yaml
  - character_agent_contract.yaml
  - validation_contract.yaml

---

**Note**: These contracts are living documents. Update them as implementation reveals new requirements or edge cases. All changes should maintain backward compatibility with existing LangGraph workflows.
