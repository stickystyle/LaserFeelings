# LangGraph Agent Orchestration Patterns

## Research Summary: Turn-Based AI TTRPG Player System

**Research Date**: 2025-10-18
**LangGraph Version**: 0.2.x (Note: v1.0 alpha is available; v1.0 release scheduled for October 2025)

---

## Decision: Hierarchical Subgraph Architecture with Supervisor Pattern

For a turn-based AI TTRPG player system with dual-layer (player/character) agents, the recommended approach is:

**Hierarchical Subgraph Architecture** where:
- Each player agent is a compiled subgraph with its own state machine
- Character agents within each player operate as nodes in the player's subgraph
- A top-level supervisor orchestrates turn order and validation
- Each layer maintains independent state with explicit communication channels

---

## Rationale: Why This Approach Fits TTRPG Requirements

### 1. **Natural Domain Mapping**
- **Player Layer**: Each player subgraph manages character selection, strategy, and meta-game decisions
- **Character Layer**: Individual character nodes handle roleplay, actions, and character-specific validation
- This maps perfectly to how TTRPGs work: players control characters with distinct personalities and capabilities

### 2. **Isolated State Management**
- Each subgraph (player) maintains its own state independent of others
- Prevents state pollution between players
- Enables parallel processing during non-conflicting actions (e.g., simultaneous character sheet updates)

### 3. **Turn-Based Control Flow**
- Supervisor pattern provides centralized turn orchestration
- Conditional edges enable strict phase transitions (e.g., "planning" → "action" → "validation" → "resolution")
- Built-in checkpointing supports rollback for invalid actions

### 4. **Validation & Retry Capabilities**
- LangGraph's RetryPolicy enables automatic retry with exponential backoff
- Conditional edges can implement validation loops with attempt counters
- Checkpoint system allows state rollback for failed validations

### 5. **Production-Ready Features**
- Built-in persistence through checkpointers
- Time-travel debugging for complex interactions
- Human-in-the-loop support for DM intervention
- Fault tolerance and recovery from failures

---

## Key Patterns

### 1. Dual-Layer Agent Structure

**Pattern**: Hierarchical Subgraphs with Shared & Private State

```python
from langgraph.graph import StateGraph, END
from typing import TypedDict, Annotated, Literal
from operator import add

# Top-level game state (shared across all players)
class GameState(TypedDict):
    current_turn: int
    phase: Literal["planning", "action", "validation", "resolution"]
    turn_order: list[str]
    validation_errors: Annotated[list[str], add]  # Reducer pattern
    game_log: Annotated[list[str], add]

# Player subgraph state (private to each player)
class PlayerState(TypedDict):
    player_id: str
    active_character: str
    character_states: dict[str, dict]  # character_id -> character data
    pending_action: dict | None
    validation_attempts: int

# Character node state (within player subgraph)
class CharacterState(TypedDict):
    character_id: str
    hp: int
    inventory: list[str]
    status_effects: list[str]
    last_action: dict | None

# Build player subgraph
def create_player_subgraph(player_id: str) -> StateGraph:
    player_graph = StateGraph(PlayerState)

    # Character nodes
    player_graph.add_node("select_character", select_character_node)
    player_graph.add_node("plan_action", plan_action_node)
    player_graph.add_node("execute_action", execute_action_node)
    player_graph.add_node("validate_action", validate_action_node)

    # Conditional edges for validation retry
    player_graph.add_conditional_edges(
        "validate_action",
        route_validation,
        {
            "retry": "plan_action",      # Retry if invalid
            "success": END,              # Success ends turn
            "max_retries": END           # Give up after 3 attempts
        }
    )

    player_graph.set_entry_point("select_character")
    return player_graph.compile()

# Top-level supervisor graph
def create_supervisor_graph():
    supervisor = StateGraph(GameState)

    # Add compiled player subgraphs as nodes
    supervisor.add_node("player_1", create_player_subgraph("player_1"))
    supervisor.add_node("player_2", create_player_subgraph("player_2"))
    supervisor.add_node("turn_manager", turn_manager_node)
    supervisor.add_node("game_validator", game_validator_node)

    # Turn-based routing
    supervisor.add_conditional_edges(
        "turn_manager",
        route_turn,
        {
            "player_1": "player_1",
            "player_2": "player_2",
            "end_round": "game_validator"
        }
    )

    supervisor.set_entry_point("turn_manager")
    return supervisor.compile()
```

**Key Benefits**:
- Each player subgraph is independent and reusable
- State isolation prevents cross-contamination
- Compiled subgraphs can be tested independently

---

### 2. Turn-Based State Machine with Strict Phases

**Pattern**: Conditional Edges with Phase Guards

```python
from typing import Literal

# Routing function for turn phases
def route_turn_phase(state: GameState) -> Literal["planning", "action", "validation", "resolution", "end_turn"]:
    """Route based on current phase and validation status."""

    if state["phase"] == "planning":
        return "action"

    elif state["phase"] == "action":
        return "validation"

    elif state["phase"] == "validation":
        if state["validation_errors"]:
            # Has errors - stay in validation or move to retry
            return "planning" if state.get("retry_count", 0) < 3 else "end_turn"
        else:
            # No errors - proceed to resolution
            return "resolution"

    elif state["phase"] == "resolution":
        return "end_turn"

    return "end_turn"

# Validation node with retry counter
def validate_action_node(state: PlayerState) -> PlayerState:
    """Validate pending action and increment retry counter."""

    action = state["pending_action"]
    errors = []

    # Validation logic (example)
    if not action.get("target"):
        errors.append("Action requires a target")

    if not has_sufficient_resources(state, action):
        errors.append("Insufficient resources for action")

    # Update state with validation results
    return {
        **state,
        "validation_attempts": state.get("validation_attempts", 0) + 1,
        "validation_errors": errors
    }

# Conditional edge with retry limit
def route_validation(state: PlayerState) -> Literal["retry", "success", "max_retries"]:
    """Route validation based on errors and retry count."""

    if not state.get("validation_errors"):
        return "success"

    if state.get("validation_attempts", 0) >= 3:
        return "max_retries"

    return "retry"
```

**Key Benefits**:
- Explicit phase transitions prevent invalid state progressions
- Retry counter prevents infinite loops
- Clear routing logic for debugging

---

### 3. Validation Loops with Retry Limits

**Pattern**: RetryPolicy + State Counter Hybrid

LangGraph provides **two complementary retry mechanisms**:

#### A. **Node-Level RetryPolicy** (for transient failures)

```python
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.constants import RetryPolicy

# Configure retry policy for node execution failures
player_graph.add_node(
    "execute_action",
    execute_action_node,
    retry=RetryPolicy(
        max_attempts=3,
        initial_interval=1.0,          # Start with 1 second
        backoff_factor=2.0,             # Double each time
        max_interval=10.0,              # Cap at 10 seconds
        retry_on=(ValueError, TimeoutError)  # Only retry specific errors
    )
)
```

**Use Case**: Handles transient failures like API timeouts, temporary network errors, or rate limits.

#### B. **State-Based Validation Loops** (for logical validation)

```python
def validate_and_route(state: PlayerState) -> dict:
    """Validate action logic and track attempts."""

    action = state["pending_action"]
    errors = []

    # Logical validation (not transient failures)
    if not is_valid_target(action["target"], state):
        errors.append("Invalid target for this action")

    if violates_game_rules(action, state):
        errors.append("Action violates game rules")

    attempts = state.get("validation_attempts", 0) + 1

    return {
        "validation_errors": errors,
        "validation_attempts": attempts
    }

# Routing with attempt limit
def route_after_validation(state: PlayerState) -> Literal["retry", "success", "failed"]:
    if not state["validation_errors"]:
        return "success"

    if state["validation_attempts"] >= 3:
        return "failed"  # Max retries exceeded

    return "retry"

# Add conditional edge
player_graph.add_conditional_edges(
    "validate_action",
    route_after_validation,
    {
        "retry": "plan_action",      # Loop back to planning
        "success": END,              # Validation passed
        "failed": "report_failure"   # Max attempts reached
    }
)
```

**Use Case**: Handles logical/semantic validation failures that require re-planning, not just retrying the same operation.

**Combined Strategy**:
```python
# Use BOTH for robust error handling
player_graph.add_node(
    "validate_action",
    validate_and_route,
    retry=RetryPolicy(max_attempts=2)  # Retry transient failures
)
# PLUS state-based routing for logical retries (shown above)
```

**Key Benefits**:
- RetryPolicy handles infrastructure failures automatically
- State counter tracks logical validation attempts
- Clear separation between transient vs. semantic errors
- Prevents infinite loops while allowing intelligent retry

---

### 4. Checkpoint-Based Rollback

**Pattern**: Time-Travel for Invalid States

```python
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph import StateGraph

# Initialize with persistent checkpointer
memory = SqliteSaver.from_conn_string("game_state.db")

supervisor = create_supervisor_graph()
app = supervisor.compile(checkpointer=memory)

# Execute with thread tracking
config = {"configurable": {"thread_id": "game_session_1"}}
result = app.invoke(initial_state, config)

# Rollback on critical validation failure
async def handle_validation_failure(thread_id: str):
    """Rollback to last valid checkpoint."""

    # Get state history
    history = app.get_state_history({"configurable": {"thread_id": thread_id}})

    # Find last valid checkpoint (before validation failure)
    for checkpoint in history:
        if checkpoint.values.get("phase") == "resolution":  # Last successful phase
            # Resume from this checkpoint
            app.update_state(
                {"configurable": {"thread_id": thread_id}},
                checkpoint.values,
                as_node="turn_manager"  # Resume from turn manager
            )
            break
```

**Key Benefits**:
- Full state history for debugging
- Ability to rollback invalid game states
- Supports DM intervention and corrections

---

## Alternatives Considered

### Alternative 1: Flat Multi-Agent with Manual Coordination

**What**: All players and characters as peer nodes in a single graph with manual turn management.

**Why Rejected**:
- **State Complexity**: Single shared state becomes unwieldy with multiple players/characters
- **Tight Coupling**: Changes to one player's logic affect others
- **Poor Isolation**: No natural boundaries for testing individual players
- **Scalability**: Adding new players requires modifying core graph structure

### Alternative 2: Send API (Orchestrator-Worker Pattern)

**What**: Use LangGraph's Send API to dynamically create worker nodes for each action.

**Why Rejected**:
- **Overhead**: Creates new nodes dynamically, which is overkill for fixed player count
- **Stateless Workers**: Workers don't maintain state across turns, requiring complex state passing
- **Turn Order**: Designed for parallel execution, but TTRPG requires strict sequential turns
- **Better Fit**: This pattern excels for dynamic task decomposition (e.g., research reports), not turn-based games

**When to Use**: If implementing a "planning phase" where a player agent dynamically breaks down a complex action into parallel sub-actions.

### Alternative 3: Pure LangChain ReAct Agent

**What**: Use standard LangChain ReAct agents without LangGraph's state machine.

**Why Rejected**:
- **No State Persistence**: ReAct agents don't maintain structured state between invocations
- **Limited Control Flow**: No built-in support for turn-based progression
- **No Checkpointing**: Can't rollback or time-travel for validation failures
- **Manual Retry Logic**: Must implement all retry/validation logic manually

---

## Code Examples

### Complete Minimal Example

```python
from langgraph.graph import StateGraph, END, START
from langgraph.checkpoint.sqlite import SqliteSaver
from typing import TypedDict, Annotated, Literal
from operator import add

# ========================================
# State Definitions
# ========================================

class GameState(TypedDict):
    """Top-level game state (supervisor)."""
    current_player: str
    turn_number: int
    game_log: Annotated[list[str], add]

class PlayerState(TypedDict):
    """Player subgraph state."""
    player_id: str
    action: str | None
    validation_attempts: int
    errors: list[str]

# ========================================
# Node Functions
# ========================================

def plan_action(state: PlayerState) -> dict:
    """Character plans an action (LLM call)."""
    # In real implementation: call GPT-4 with character context
    action = "attack goblin"  # Simulated
    return {"action": action}

def validate_action(state: PlayerState) -> dict:
    """Validate action against game rules."""
    errors = []

    if state["action"] == "invalid_action":
        errors.append("Invalid action type")

    attempts = state["validation_attempts"] + 1

    return {
        "validation_attempts": attempts,
        "errors": errors
    }

def route_validation(state: PlayerState) -> Literal["retry", "success", "failed"]:
    """Route based on validation results."""
    if not state["errors"]:
        return "success"
    if state["validation_attempts"] >= 3:
        return "failed"
    return "retry"

def execute_action(state: PlayerState) -> dict:
    """Execute validated action."""
    log_entry = f"{state['player_id']} executes: {state['action']}"
    return {"game_log": [log_entry]}

def turn_manager(state: GameState) -> dict:
    """Manage turn order."""
    players = ["player_1", "player_2"]
    current_idx = players.index(state["current_player"])
    next_player = players[(current_idx + 1) % len(players)]

    return {
        "current_player": next_player,
        "turn_number": state["turn_number"] + 1
    }

def route_turn(state: GameState) -> Literal["player_1", "player_2", "end_game"]:
    """Route to current player or end game."""
    if state["turn_number"] >= 10:
        return "end_game"
    return state["current_player"]

# ========================================
# Graph Construction
# ========================================

def create_player_subgraph(player_id: str):
    """Create a player subgraph."""
    player_graph = StateGraph(PlayerState)

    # Add nodes
    player_graph.add_node("plan_action", plan_action)
    player_graph.add_node("validate_action", validate_action)
    player_graph.add_node("execute_action", execute_action)

    # Add edges
    player_graph.add_edge(START, "plan_action")
    player_graph.add_edge("plan_action", "validate_action")
    player_graph.add_conditional_edges(
        "validate_action",
        route_validation,
        {
            "retry": "plan_action",
            "success": "execute_action",
            "failed": END
        }
    )
    player_graph.add_edge("execute_action", END)

    # Compile with initial state injection
    compiled = player_graph.compile()

    # Wrap to inject player_id
    def wrapped_player(state: GameState):
        player_state = PlayerState(
            player_id=player_id,
            action=None,
            validation_attempts=0,
            errors=[]
        )
        result = compiled.invoke(player_state)
        return {"game_log": result.get("game_log", [])}

    return wrapped_player

def create_game_supervisor():
    """Create top-level supervisor graph."""
    supervisor = StateGraph(GameState)

    # Add player subgraphs as nodes
    supervisor.add_node("player_1", create_player_subgraph("player_1"))
    supervisor.add_node("player_2", create_player_subgraph("player_2"))
    supervisor.add_node("turn_manager", turn_manager)

    # Add routing
    supervisor.add_edge(START, "turn_manager")
    supervisor.add_conditional_edges(
        "turn_manager",
        route_turn,
        {
            "player_1": "player_1",
            "player_2": "player_2",
            "end_game": END
        }
    )
    supervisor.add_edge("player_1", "turn_manager")
    supervisor.add_edge("player_2", "turn_manager")

    return supervisor.compile(checkpointer=SqliteSaver.from_conn_string(":memory:"))

# ========================================
# Execution
# ========================================

if __name__ == "__main__":
    game = create_game_supervisor()

    initial_state = GameState(
        current_player="player_1",
        turn_number=0,
        game_log=[]
    )

    config = {"configurable": {"thread_id": "session_1"}}
    result = game.invoke(initial_state, config)

    print("Game Log:")
    for entry in result["game_log"]:
        print(f"  - {entry}")
```

---

## Implementation Considerations

### 1. State Communication Between Layers

**Challenge**: Player subgraphs need to access game state (e.g., enemy positions) and write back results.

**Solution**: Use state transformers when subgraph state differs from parent state:

```python
def player_node_wrapper(state: GameState):
    """Transform game state -> player state -> game state."""

    # Extract relevant data for player
    player_input = PlayerState(
        player_id=state["current_player"],
        game_context={
            "enemies": state["enemies"],
            "allies": state["allies"]
        },
        action=None,
        validation_attempts=0
    )

    # Invoke player subgraph
    player_result = player_subgraph.invoke(player_input)

    # Transform player results back to game state
    return {
        "game_log": state["game_log"] + [player_result["action_log"]],
        "action_results": player_result["action_outcome"]
    }
```

### 2. Validation Complexity

**Challenge**: Some validations require game-wide context (e.g., "is target in range?").

**Solution**: Pass validation context into subgraph or use a shared validation service:

```python
# Option 1: Pass context into subgraph
def create_player_with_context(player_id: str, game_context: dict):
    player_graph = StateGraph(PlayerState)

    def validate_with_context(state: PlayerState):
        return validate_action(state, game_context)  # Use closure

    player_graph.add_node("validate", validate_with_context)
    # ... rest of graph

# Option 2: Shared validation node at supervisor level
supervisor.add_node("global_validator", validate_game_rules)
supervisor.add_edge("player_1", "global_validator")
supervisor.add_edge("global_validator", "turn_manager")
```

### 3. Retry Strategy

**Best Practice**: Combine both retry mechanisms:

```python
from langgraph.constants import RetryPolicy

# Transient failures (API errors, timeouts)
player_graph.add_node(
    "plan_action",
    plan_action_node,
    retry=RetryPolicy(max_attempts=3, retry_on=(TimeoutError, APIError))
)

# Logical failures (invalid actions)
player_graph.add_conditional_edges(
    "validate_action",
    route_validation,  # State-based routing
    {"retry": "plan_action", "success": END, "failed": "report_error"}
)
```

---

## References

### Official Documentation
- **LangGraph Main Docs**: https://langchain-ai.github.io/langgraph/
- **Multi-Agent Systems**: https://langchain-ai.github.io/langgraph/concepts/multi_agent/
- **Subgraphs How-To**: https://langchain-ai.github.io/langgraph/how-tos/subgraph/
- **Hierarchical Agent Teams Tutorial**: https://langchain-ai.github.io/langgraph/tutorials/multi_agent/hierarchical_agent_teams/
- **Retry Policies**: https://changelog.langchain.com/announcements/enhanced-state-management-retries-in-langgraph-python
- **Time-Travel & Checkpointing**: https://langchain-ai.github.io/langgraph/how-tos/human_in_the_loop/time-travel/

### Code Examples
- **Hierarchical Teams Example**: https://github.com/langchain-ai/langgraph/blob/main/docs/docs/tutorials/multi_agent/hierarchical_agent_teams.ipynb
- **Agent Supervisor**: https://github.com/langchain-ai/langgraph/blob/main/examples/multi_agent/agent_supervisor.ipynb
- **Validation with Retries**: https://langchain-ai.github.io/langgraph/tutorials/extraction/retries/

### Best Practices Articles (2025)
- **"LangGraph State Machines: Managing Complex Agent Task Flows"**: https://dev.to/jamesli/langgraph-state-machines-managing-complex-agent-task-flows-in-production-36f4
- **"Orchestrator-Worker Workflows with LangGraph"**: https://medium.com/@email2argha/delegate-parallelize-synthesize-building-orchestrator-worker-workflows-with-langgraph-d01b767655c4
- **"Mastering Persistence in LangGraph"**: https://medium.com/@vinodkrane/mastering-persistence-in-langgraph-checkpoints-threads-and-beyond-21e412aaed60

### Framework Comparisons
- **LangGraph vs LangChain (2025)**: https://medium.com/@vinodkrane/langchain-vs-langgraph-choosing-the-right-framework-for-your-ai-workflows-in-2025-5aeab94833ce
- **Agent Orchestration Guide**: https://medium.com/@akankshasinha247/agent-orchestration-when-to-use-langchain-langgraph-autogen-or-build-an-agentic-rag-system-cc298f785ea4

---

## Version Note

**Important**: These patterns are based on LangGraph 0.2.x. The official documentation states:

> "These docs will be deprecated and removed with the release of LangGraph v1.0 in October 2025."

LangGraph v1.0 alpha is currently available. For production systems launching after October 2025, review the v1.0 documentation for any API changes, particularly around:
- State schema definitions
- Subgraph compilation
- Retry policy configuration
- Checkpoint serialization

The **core concepts** (hierarchical subgraphs, supervisor pattern, state machines) are expected to remain stable, but syntax may evolve.

---

## Next Steps

1. **Prototype**: Build minimal player subgraph with 1-2 nodes to validate state flow
2. **Test Validation**: Implement retry logic with state counter + conditional edges
3. **Add Checkpointing**: Integrate SqliteSaver for state persistence
4. **Scale**: Add second player subgraph and supervisor orchestration
5. **Monitor v1.0**: Track LangGraph v1.0 release for migration needs

---

**Research conducted by**: Claude (Sonnet 4.5)
**For**: Ryan (ttrpg-ai project)
**Date**: 2025-10-18
