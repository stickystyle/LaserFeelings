# Enhanced Tasks Examples: AI TTRPG Player System

**Purpose**: This file demonstrates enhanced task format with explicit implementation steps, line references, and clear success criteria.

**Note**: These are examples showing the improved format. The full tasks.md should be updated with this pattern.

---

## How to Read Enhanced Tasks

Each enhanced task includes:

1. **Prerequisites** - What must be complete before starting
2. **Implementation Steps** - Numbered steps with exact file/line references
3. **Copy-and-Adapt Instructions** - Explicit "copy this code from line X"
4. **Success Criteria** - How to verify completion
5. **Common Pitfalls** - What to watch out for

---

## Enhanced Format Examples

### Example 1: Foundation Task (Settings Model)

**Original Format:**
```
T007 Implement Settings model with Pydantic settings in src/config/settings.py
  - **Reference**: data-model.md §6.1 (Settings), research.md §1-8 for config values
```

**Enhanced Format:**

---

### T007 Implement Settings model with Pydantic settings in src/config/settings.py

**Prerequisites**:
- T002 complete (pyproject.toml exists)
- T003 complete (pydantic and pydantic-settings installed)

**Implementation Steps**:

1. **Create the file structure**:
   ```bash
   mkdir -p src/config
   touch src/config/settings.py
   touch src/config/__init__.py
   ```

2. **Add ABOUTME comment** (2 lines at top of file):
   ```python
   # ABOUTME: Application configuration management using Pydantic Settings
   # ABOUTME: Loads environment variables for OpenAI, Neo4j, Redis, and system parameters
   ```

3. **Copy base Settings model from data-model.md §6.1**:
   - Open data-model.md, scroll to Section 6.1 (search for "### 6.1 Settings")
   - Copy the complete `Settings` class definition
   - Paste into src/config/settings.py

4. **Add configuration values from research findings**:
   - OpenAI config: See research.md §4, lines 450-460 (model names, max_tokens)
   - Neo4j config: See research.md §2, lines 138-140 (URI, credentials)
   - Redis config: See research.md §3, lines 280-285 (host, port, db number)
   - RQ config: See research.md §3, lines 310-315 (queue names, timeouts)
   - LangSmith config: See plan.md line 20 (observability setup)

5. **Add field validators**:
   ```python
   from pydantic import field_validator

   @field_validator('openai_max_tokens')
   def validate_token_limit(cls, v):
       if v > 5000:
           raise ValueError('Token limit exceeds per-turn budget (5000)')
       return v
   ```

6. **Create settings instance**:
   ```python
   # At bottom of file
   settings = Settings()
   ```

7. **Write unit test FIRST** (TDD):
   - Create tests/unit/config/test_settings.py
   - Test that environment variables load correctly
   - Test field validation (e.g., negative port number should fail)
   - **Verify test FAILS** before implementation complete

**Success Criteria**:
- [ ] File has ABOUTME comment
- [ ] Settings class inherits from BaseSettings
- [ ] All config fields from plan.md Technical Context present
- [ ] Field validators enforce constraints (token budget, valid URIs)
- [ ] Can load from .env file: `settings = Settings(_env_file='.env')`
- [ ] Unit tests pass

**Common Pitfalls**:
- Forgetting `model_config = SettingsConfigDict(env_file='.env')` for auto-loading
- Not using `Field(default=...)` for optional configs
- Missing type hints (Pydantic needs them)

**Reference Files**:
- Primary: data-model.md §6.1
- Config values: research.md §2 (Neo4j), §3 (Redis/RQ), §4 (OpenAI)
- Pattern: plan.md lines 619-623 (Settings usage in constitution check)

---

### Example 2: Memory Layer Task (Graphiti Client)

**Original Format:**
```
T034 [P] [US1] Implement Graphiti client wrapper in src/memory/graphiti_client.py
  - **Reference**: research.md §2 (Graphiti Memory Integration - complete code examples), contracts/memory_interface.yaml
```

**Enhanced Format:**

---

### T034 [P] [US1] Implement Graphiti client wrapper in src/memory/graphiti_client.py

**Prerequisites**:
- T007 complete (Settings model exists)
- T024 complete (Docker infrastructure running)
- T009-T011 complete (MemoryEdge, MemoryType, CorruptionType enums exist)

**Implementation Steps**:

1. **Create file with ABOUTME comment**:
   ```python
   # ABOUTME: Graphiti client wrapper for temporal knowledge graph memory
   # ABOUTME: Handles episode creation, temporal queries, and Neo4j connection management
   ```

2. **Copy Graphiti initialization code**:
   - Open research.md, navigate to §2 "Graphiti Memory Integration"
   - Copy lines 137-143 (Graphiti client initialization)
   - Paste as `__init__` method of GraphitiClient class

3. **Copy session episode creation**:
   - Copy the `create_session_episode` function from research.md lines 146-158
   - Adapt to method: `async def add_episode(self, session_number: int, messages: List[str], reference_time: datetime) -> str`
   - Update to use `self.graphiti` instead of global `graphiti`

4. **Copy temporal query method**:
   - Copy `query_memories_at_time` function from research.md lines 161-183
   - Rename to match contract: `async def search(self, query: str, agent_id: str, valid_at: datetime, limit: int = 5) -> List[MemoryEdge]`
   - Update group_ids to use agent_id parameter
   - Convert Graphiti Edge results to our MemoryEdge model (see data-model.md §2.1)

5. **Implement contract interface**:
   - Open contracts/memory_interface.yaml
   - Read CorruptedTemporalMemory.search method spec (lines 5-10)
   - Ensure method signature matches: `search(query: str, agent_id: str, limit: int, apply_corruption: bool)`
   - Read add_episode method spec (lines 11-15)
   - Ensure return type matches: `episode_id: str`

6. **Add error handling**:
   - Wrap Graphiti calls in try/except
   - Handle connection errors (Neo4j down)
   - Handle query timeout errors
   - See contracts/memory_interface.yaml "errors" section for expected exceptions

7. **Write contract test FIRST** (TDD):
   - Open tests/contract/test_memory_contracts.py
   - Implement test from T030 task
   - Test `search()` method returns correct types
   - Test `add_episode()` creates episode in Neo4j
   - **Verify tests FAIL** before implementation

**Implementation Sequence for search() method**:
```python
# a. Define method signature from contract
async def search(
    self,
    query: str,
    agent_id: str,
    limit: int = 5,
    apply_corruption: bool = False
) -> List[MemoryEdge]:

# b. Call Graphiti search (research.md lines 168-173)
    results = await self.graphiti.search(
        query=query,
        group_ids=[agent_id],
        num_results=limit
    )

# c. Convert to MemoryEdge objects (data-model.md §2.1)
    edges = []
    for result in results:
        edge = MemoryEdge(
            uuid=result.uuid,
            fact=result.fact,
            valid_at=result.valid_at,
            # ... other fields from MemoryEdge model
        )
        edges.append(edge)

# d. Apply corruption if requested (will implement in T180+)
    if apply_corruption:
        # TODO: Implement in Phase 9
        pass

    return edges
```

**Success Criteria**:
- [ ] GraphitiClient class initialized with Settings
- [ ] `add_episode()` creates episode in Neo4j (verify at http://localhost:7474)
- [ ] `search()` returns List[MemoryEdge] matching contract
- [ ] Contract tests from T030 pass
- [ ] Error handling for connection failures works
- [ ] ABOUTME comment present

**Common Pitfalls**:
- Forgetting `async`/`await` (Graphiti is fully async)
- Not converting Graphiti's Edge type to our MemoryEdge model
- Hardcoding group_ids instead of using parameter
- Missing temporal filtering (valid_at/invalid_at checks)

**Reference Files**:
- Primary: research.md §2 (lines 112-230)
- Contract: contracts/memory_interface.yaml (entire CorruptedTemporalMemory section)
- Model: data-model.md §2.1 (MemoryEdge fields)
- Setup: research.md §5 (Neo4j indexes needed for queries)

---

### Example 3: Agent Layer Task (BasePersonaAgent)

**Original Format:**
```
T038 [P] [US1] Implement BasePersonaAgent with strategic decision-making in src/agents/base_persona.py
  - **Reference**: contracts/agent_interface.yaml (BasePersonaAgent interface), data-model.md §1.1 (AgentPersonality)
```

**Enhanced Format:**

---

### T038 [P] [US1] Implement BasePersonaAgent with strategic decision-making in src/agents/base_persona.py

**Prerequisites**:
- T013 complete (AgentPersonality model exists)
- T017 complete (Message model exists)
- T034 complete (GraphitiClient wrapper exists)
- T007 complete (Settings exists)

**Implementation Steps**:

1. **Create file with ABOUTME comment**:
   ```python
   # ABOUTME: Strategic decision-making agent (player layer) for TTRPG gameplay
   # ABOUTME: Handles out-of-character discussion, intent formulation, and character directive creation
   ```

2. **Read the contract specification completely**:
   - Open contracts/agent_interface.yaml
   - Read BasePersonaAgent section (lines 143-198)
   - Note the 3 methods required:
     - `participate_in_ooc_discussion` (lines 146-155)
     - `formulate_strategic_intent` (lines 156-165)
     - `create_character_directive` (lines 166-175)
   - Read "behavior" requirements section (lines 176-185)
   - Read "errors" section (lines 186-198)

3. **Create class structure**:
   ```python
   from pydantic import BaseModel
   from src.models.personality import AgentPersonality
   from src.models.messages import Message
   from src.config.settings import settings
   from openai import AsyncOpenAI

   class BasePersonaAgent:
       def __init__(
           self,
           personality: AgentPersonality,
           memory_client,  # GraphitiClient
           openai_client: AsyncOpenAI
       ):
           self.personality = personality
           self.memory = memory_client
           self.openai = openai_client
   ```

4. **Implement participate_in_ooc_discussion method**:
   - **Signature** from contract (agent_interface.yaml lines 147-155):
     ```python
     async def participate_in_ooc_discussion(
         self,
         dm_narration: str,
         other_messages: List[Message]
     ) -> Message:
     ```

   - **Implementation pattern** from research.md §4 (LLM call with structured output):
     - Build prompt incorporating personality traits (data-model.md §1.1)
     - Query memory for relevant context (use self.memory.search())
     - Call OpenAI with personality-influenced prompt
     - Return Message object with channel=OUT_OF_CHARACTER

   - **Copy LLM call pattern** from research.md §4, lines 450-480:
     ```python
     response = await self.openai.chat.completions.create(
         model=settings.openai_model,
         messages=[
             {"role": "system", "content": system_prompt},
             {"role": "user", "content": user_prompt}
         ],
         max_tokens=settings.openai_max_tokens,
         temperature=0.7
     )
     ```

5. **Implement formulate_strategic_intent method**:
   - Signature from contract (lines 156-165)
   - Takes discussion_summary (string of OOC messages)
   - Returns Intent object (see contracts/agent_interface.yaml Intent schema)
   - Should reflect personality.play_style (cautious vs aggressive)
   - Include risk_assessment based on personality.risk_tolerance

6. **Implement create_character_directive method**:
   - Signature from contract (lines 166-175)
   - Translates Intent (strategic) → Directive (tactical)
   - This is the "player-to-character" communication
   - Should be high-level, not prescriptive (allow interpretation gap)

7. **Add personality influence logic**:
   ```python
   def _adjust_for_personality(self, base_prompt: str) -> str:
       """Modify prompts based on personality traits"""
       if self.personality.play_style == PlayStyle.CAUTIOUS:
           return base_prompt + "\nEmphasize caution and risk mitigation."
       elif self.personality.play_style == PlayStyle.AGGRESSIVE:
           return base_prompt + "\nFavor bold, decisive action."
       # ... other play styles
   ```

8. **Write contract tests FIRST** (from T028):
   - Create tests/contract/test_agent_contracts.py
   - Test BasePersonaAgent interface compliance
   - Test method signatures match contract
   - Test return types are correct
   - **Verify tests FAIL** before methods implemented

**Detailed Implementation Example: participate_in_ooc_discussion**

```python
async def participate_in_ooc_discussion(
    self,
    dm_narration: str,
    other_messages: List[Message]
) -> Message:
    """Strategic discussion contribution (OOC layer)"""

    # Step 1: Query memory for relevant context
    relevant_memories = await self.memory.search(
        query=dm_narration,
        agent_id=self.personality.agent_id,
        limit=5
    )

    # Step 2: Build context-aware prompt
    memory_context = "\n".join([m.fact for m in relevant_memories])
    discussion_context = "\n".join([m.content for m in other_messages])

    system_prompt = f"""You are {self.personality.name}, a {self.personality.play_style.value} player.

Your personality traits:
- Risk tolerance: {self.personality.risk_tolerance}
- Analytical score: {self.personality.analytical_score}
- Preferred tactics: {', '.join(self.personality.preferred_tactics)}

Relevant memories from past sessions:
{memory_context}

DM's narration: {dm_narration}

Other players' discussion:
{discussion_context}

Respond with your strategic thoughts on how to approach this situation.
Stay in character as a player (not your character). This is out-of-character discussion.
"""

    # Step 3: Call LLM (research.md §4 pattern)
    response = await self.openai.chat.completions.create(
        model=settings.openai_model,
        messages=[{"role": "system", "content": system_prompt}],
        max_tokens=settings.openai_max_tokens,
        temperature=0.7
    )

    # Step 4: Package as Message
    from datetime import datetime
    import uuid

    return Message(
        message_id=str(uuid.uuid4()),
        timestamp=datetime.now(),
        channel=Channel.OUT_OF_CHARACTER,
        from_agent=self.personality.agent_id,
        to_agents=[],  # Broadcast to all
        content=response.choices[0].message.content,
        message_type=MessageType.DISCUSSION,
        turn_number=0,  # Will be set by orchestrator
        phase="OOC_DISCUSSION"
    )
```

**Success Criteria**:
- [ ] All 3 methods implemented with correct signatures
- [ ] Methods use personality traits to influence decisions
- [ ] LLM calls follow research.md §4 pattern with error handling
- [ ] Memory queries work (integration with T034)
- [ ] Returns Message/Intent/Directive objects matching contract schemas
- [ ] Contract tests from T028 pass
- [ ] ABOUTME comment present
- [ ] Error handling for LLM failures (see contract errors section)

**Common Pitfalls**:
- Not making personality traits actually influence decisions (just decorative)
- Forgetting to query memory before making decisions (agents should remember!)
- Returning raw LLM string instead of proper Message object
- Missing async/await keywords
- Not handling OpenAI API errors (rate limits, timeouts)
- Hardcoding agent_id instead of using self.personality.agent_id

**Reference Files**:
- Primary contract: contracts/agent_interface.yaml (lines 143-198)
- Personality model: data-model.md §1.1 (lines 16-82)
- LLM call pattern: research.md §4 (lines 450-480)
- Message model: data-model.md §4.1 (for return types)
- Settings: src/config/settings.py (T007 output)

---

### Example 4: Orchestration Task (State Machine)

**Original Format:**
```
T046 [US1] Implement LangGraph state machine with GamePhase transitions in src/orchestration/state_machine.py
  - **Reference**: research.md §1 (LangGraph State Machine - workflow build example), data-model.md §3.1 (GameState + GamePhase)
```

**Enhanced Format:**

---

### T046 [US1] Implement LangGraph state machine with GamePhase transitions in src/orchestration/state_machine.py

**Prerequisites**:
- T018 complete (GameState model exists in src/models/game_state.py)
- T009 complete (GamePhase enum exists)
- T038-T044 complete (Agent methods exist to call from nodes)

**This is a FOUNDATIONAL task** - all phase handler tasks (T047-T056) depend on this skeleton

**Implementation Steps**:

1. **Create file with ABOUTME comment**:
   ```python
   # ABOUTME: LangGraph state machine orchestrating turn-based TTRPG gameplay phases
   # ABOUTME: Handles phase transitions, validation retry loops, and DM intervention checkpoints
   ```

2. **Copy LangGraph imports and setup** from research.md §1 (lines 27-29):
   ```python
   from langgraph.graph import StateGraph, END
   from langgraph.checkpoint.memory import MemorySaver
   from typing import TypedDict, Literal
   ```

3. **Define GameState TypedDict** based on data-model.md §3.1:
   - Open data-model.md, navigate to §3.1 "GameState"
   - Copy the field list (lines 180-200)
   - Convert Pydantic model to TypedDict for LangGraph:
   ```python
   from typing import TypedDict, List, Optional

   class GameState(TypedDict):
       # Session tracking
       session_number: int
       turn_number: int
       current_phase: str  # GamePhase enum value
       days_elapsed: int
       current_timestamp: str  # ISO format datetime

       # Narrative context
       dm_narration: str
       active_scene: str
       location: str

       # Agent states (per-agent data)
       agent_states: dict  # agent_id -> state dict
       character_states: dict  # character_id -> state dict

       # Communication channels
       ooc_messages: List[dict]  # Message objects as dicts
       strategic_intents: dict  # agent_id -> Intent
       character_actions: dict  # character_id -> Action

       # Validation tracking
       validation_results: dict  # character_id -> ValidationResult
       validation_attempts: dict  # character_id -> int

       # Memory updates (batch)
       memory_updates: List[dict]
   ```

4. **Create placeholder node functions** (will be implemented in T047-T056):
   ```python
   def dm_narration_node(state: GameState) -> GameState:
       """Phase: DM_NARRATION - Wait for DM input"""
       # TODO: Implement in T047
       return state

   def memory_retrieval_node(state: GameState) -> GameState:
       """Phase: MEMORY_RETRIEVAL - Load relevant memories"""
       # TODO: Implement in T048
       return state

   # ... create placeholders for all 12 phases from GamePhase enum
   ```

5. **Build StateGraph workflow** (research.md §1, lines 68-95):
   ```python
   def build_ttrpg_workflow() -> StateGraph:
       """Construct the turn-based state machine"""

       # Initialize graph
       workflow = StateGraph(GameState)

       # Add all phase nodes
       workflow.add_node("dm_narration", dm_narration_node)
       workflow.add_node("memory_retrieval", memory_retrieval_node)
       workflow.add_node("strategic_intent", strategic_intent_node)
       workflow.add_node("character_action", character_action_node)
       workflow.add_node("validation_check", validation_check_node)
       workflow.add_node("dm_adjudication", dm_adjudication_node)
       # ... add remaining nodes

       # Set entry point
       workflow.set_entry_point("dm_narration")

       # Add linear edges (basic flow, will add conditionals later)
       workflow.add_edge("dm_narration", "memory_retrieval")
       workflow.add_edge("memory_retrieval", "strategic_intent")
       workflow.add_edge("strategic_intent", "character_action")
       workflow.add_edge("character_action", "validation_check")
       # ... add remaining edges

       return workflow
   ```

6. **Add checkpointing** (research.md §1, lines 94-95):
   ```python
   # Compile workflow with persistence
   app = build_ttrpg_workflow().compile(
       checkpointer=MemorySaver()  # Use SQLiteSaver in production
   )
   ```

7. **Create workflow execution interface**:
   ```python
   async def execute_turn_cycle(
       dm_input: str,
       session_id: str,
       existing_state: Optional[GameState] = None
   ) -> GameState:
       """Execute one complete turn cycle"""

       # Initialize or load state
       if existing_state is None:
           state = GameState(
               session_number=1,
               turn_number=1,
               current_phase="DM_NARRATION",
               # ... initialize all fields
           )
       else:
           state = existing_state

       # Update with DM input
       state["dm_narration"] = dm_input

       # Run workflow
       config = {"configurable": {"thread_id": session_id}}
       result = await app.ainvoke(state, config=config)

       return result
   ```

8. **Write integration test FIRST** (from T032):
   - Create tests/integration/test_turn_cycle.py
   - Test that workflow can execute through all phases
   - Test that state persists via checkpointing
   - **Verify test FAILS** (nodes are placeholders)

**Phase Implementation Order** (for T047-T056):

After this task, implement phase handlers in this order:
1. T047: DM_NARRATION (simplest - just stores input)
2. T048: MEMORY_RETRIEVAL (calls GraphitiClient)
3. T052: DM_ADJUDICATION (simple - waits for DM command)
4. T056: MEMORY_CONSOLIDATION (calls GraphitiClient.add_episode)
5. Then remaining phases in task order

**Success Criteria**:
- [ ] StateGraph created with all phase nodes as placeholders
- [ ] GameState TypedDict matches data-model.md §3.1
- [ ] Workflow compiles without errors
- [ ] Checkpointing configured (MemorySaver)
- [ ] Basic linear edges connect all phases
- [ ] execute_turn_cycle() function exists and accepts dm_input
- [ ] Can invoke workflow: `app.invoke(state)` succeeds
- [ ] Integration test from T032 created (will fail until phases implemented)
- [ ] ABOUTME comment present

**Common Pitfalls**:
- Using Pydantic BaseModel instead of TypedDict (LangGraph needs TypedDict)
- Forgetting to return new state dict from nodes (mutations don't work)
- Not compiling with checkpointer (loses state between turns)
- Adding conditional edges before predicates are defined
- Mixing sync/async (LangGraph supports both but be consistent)

**Next Steps After This Task**:
- T047-T056 will fill in the placeholder node functions
- T090 will add conditional edges for validation retry loop
- T146 will add conditional edges for consensus detection

**Reference Files**:
- Primary: research.md §1 (lines 9-109) - complete LangGraph example
- GameState spec: data-model.md §3.1 (lines 180-220)
- GamePhase enum: data-model.md §3.1 (phase sequence)
- Checkpointing: research.md §1 (lines 98-102)
- Contract: contracts/orchestrator_interface.yaml

---

### Example 5: Phase Handler with Dependencies (Validation Phase)

**Original Format:**
```
T090 [US2] Add VALIDATION_CHECK phase handler to state machine in src/orchestration/state_machine.py
  - **Reference**: research.md §1 (conditional edge example with should_retry_validation), data-model.md §3.1 (GamePhase)
```

**Enhanced Format:**

---

### T090 [US2] Add VALIDATION_CHECK phase handler to state machine in src/orchestration/state_machine.py

**Prerequisites**:
- T046 complete (state machine skeleton exists)
- T051 complete (CHARACTER_ACTION phase fills state["character_actions"])
- T084 complete (ValidationAgent exists)
- T089 complete (ValidationAgent RQ worker exists)

**This task adds both a NODE and CONDITIONAL EDGES**

**Implementation Steps**:

1. **Locate the placeholder node** in src/orchestration/state_machine.py:
   - Find `def validation_check_node(state: GameState) -> GameState:`
   - This was created as placeholder in T046

2. **Implement the validation node** using RQ worker pattern from research.md §3:

```python
from redis import Redis
from rq import Queue
from src.workers.validation_worker import validate_character_action

def validation_check_node(state: GameState) -> GameState:
    """Phase: VALIDATION_CHECK - Validate actions for narrative overreach"""

    # Get Redis connection
    redis_conn = Redis(
        host=settings.redis_host,
        port=settings.redis_port,
        db=settings.redis_db
    )
    queue = Queue('validation', connection=redis_conn)

    # Validate each character's action
    validation_results = {}

    for character_id, action in state["character_actions"].items():
        # Get current attempt number (for progressive strictness)
        attempt = state["validation_attempts"].get(character_id, 1)

        # Dispatch validation job (research.md §3, lines 295-305)
        job = queue.enqueue(
            validate_character_action,
            action=action,
            attempt=attempt,
            job_timeout=30,
            result_ttl=300
        )

        # Block until validation completes
        result = job.result  # Blocks until worker returns
        validation_results[character_id] = result

    # Update state with validation results
    return {
        **state,
        "validation_results": validation_results,
        "current_phase": "VALIDATION_CHECK"  # Stay in phase for conditional routing
    }
```

3. **Create conditional edge predicate** (research.md §1, lines 48-55):

```python
def should_retry_validation(state: GameState) -> Literal["valid", "retry", "fail"]:
    """Decide next phase based on validation results

    Returns:
        "valid" - All actions valid, proceed to DM_ADJUDICATION
        "retry" - Some actions invalid but retries remaining, go to CHARACTER_ACTION
        "fail" - Max retries exceeded, proceed to DM_ADJUDICATION with warning
    """

    # Check all validation results
    all_valid = all(
        result.valid
        for result in state["validation_results"].values()
    )

    if all_valid:
        return "valid"

    # Check if any character has retries remaining
    for character_id, result in state["validation_results"].items():
        if not result.valid:
            attempt = state["validation_attempts"].get(character_id, 1)
            if attempt < 3:
                return "retry"  # At least one can retry

    # All failed characters exhausted retries
    return "fail"
```

4. **Add retry node** for attempt increment:

```python
def retry_with_correction(state: GameState) -> GameState:
    """Increment attempt counter and prepare for retry

    Called when validation fails but retries remain.
    Updates validation_attempts counter for progressive strictness.
    """

    updated_attempts = state["validation_attempts"].copy()

    # Increment attempt for each failed character
    for character_id, result in state["validation_results"].items():
        if not result.valid:
            current = updated_attempts.get(character_id, 1)
            updated_attempts[character_id] = current + 1

    return {
        **state,
        "validation_attempts": updated_attempts,
        "current_phase": "CHARACTER_ACTION"  # Route back to retry
    }
```

5. **Update workflow graph** (modify build_ttrpg_workflow() function):

   **Remove** this line (from T046):
   ```python
   workflow.add_edge("validation_check", "dm_adjudication")  # OLD: unconditional
   ```

   **Add** these lines:
   ```python
   # Add retry node
   workflow.add_node("retry_correction", retry_with_correction)

   # Replace unconditional edge with conditional routing
   workflow.add_conditional_edges(
       "validation_check",
       should_retry_validation,  # Predicate function
       {
           "valid": "dm_adjudication",      # All valid → proceed
           "retry": "retry_correction",     # Retry available → correction node
           "fail": "dm_adjudication"        # Max retries → proceed with warning
       }
   )

   # Route retry_correction back to character action
   workflow.add_edge("retry_correction", "character_action")
   ```

6. **Update CHARACTER_ACTION phase** to use attempt number (edit T051 implementation):

```python
# In character_action_node, add:
def character_action_node(state: GameState) -> GameState:
    # ... existing code ...

    for character_id, directive in state["character_directives"].items():
        attempt = state["validation_attempts"].get(character_id, 1)  # NEW

        job = queue.enqueue(
            character_agent_perform_action,
            directive=directive,
            scene_context=state["active_scene"],
            attempt=attempt,  # NEW: Pass to worker for progressive prompts
            # ... rest of params
        )
```

7. **Update integration tests**:
   - Edit tests/integration/test_turn_cycle.py
   - Add test for validation retry loop
   - Test that invalid action triggers retry
   - Test that 3rd failure proceeds with warning flag
   - Test progressive strictness (attempt 1 vs 2 vs 3 prompts)

**Validation Flow Diagram**:
```
CHARACTER_ACTION
  ↓
VALIDATION_CHECK (this task)
  ↓
[should_retry_validation predicate]
  ├─ "valid" → DM_ADJUDICATION (proceed)
  ├─ "retry" → retry_correction → CHARACTER_ACTION (loop back)
  └─ "fail" → DM_ADJUDICATION (with warning_flag=True)
```

**Success Criteria**:
- [ ] validation_check_node dispatches RQ jobs for each character
- [ ] should_retry_validation predicate correctly routes based on results
- [ ] retry_correction node increments validation_attempts
- [ ] Conditional edges replace old unconditional edge
- [ ] Integration test confirms retry loop works (invalid action retries up to 3 times)
- [ ] Integration test confirms 3rd failure proceeds with warning
- [ ] ValidationResult.warning_flag set correctly on final failure

**Common Pitfalls**:
- Forgetting to remove old `add_edge("validation_check", "dm_adjudication")` line
- Not incrementing validation_attempts in retry_correction node
- Predicate returning wrong routing key (typo in "valid"/"retry"/"fail")
- Not passing attempt number to character worker (breaks progressive strictness)
- Blocking on wrong RQ job (mixing up character IDs)

**Reference Files**:
- LangGraph conditional edges: research.md §1 (lines 48-92)
- Validation patterns: research.md §4 (lines 450-536)
- RQ worker dispatch: research.md §3 (lines 295-320)
- ValidationResult model: data-model.md §3.2
- Progressive prompts: research.md §4 (lines 475-519)

---

## Task Type Checklists

### Checklist: Implementing Any Pydantic Model

- [ ] Read data-model.md section for the entity
- [ ] Copy model skeleton with all fields
- [ ] Add `model_config` with example
- [ ] Add field validators for constraints
- [ ] Add ABOUTME comment (2 lines at top of file)
- [ ] Import required enums and types
- [ ] Write unit test for validation rules (e.g., score out of range should fail)
- [ ] Test that example in model_config actually validates

### Checklist: Implementing Any Agent Method

- [ ] Read contracts/agent_interface.yaml for method specification
- [ ] Check `input` schema (parameter types)
- [ ] Check `output` schema (return type)
- [ ] Check `behavior` requirements (what method must/must not do)
- [ ] Check `errors` section (what exceptions to handle)
- [ ] Review research.md §4 for LLM call patterns
- [ ] Query memory before making decisions (agents should remember!)
- [ ] Apply personality traits to influence behavior
- [ ] Write contract test FIRST (verify it fails)
- [ ] Implement method
- [ ] Add error handling (API failures, timeouts)
- [ ] Verify contract test passes

### Checklist: Implementing Any LangGraph Node

- [ ] Read research.md §1 for state machine patterns
- [ ] Receive state: `def node_name(state: GameState) -> GameState:`
- [ ] Extract needed data from state dict
- [ ] Perform phase logic (call agents, query memory, etc.)
- [ ] Return NEW state dict (don't mutate): `return {**state, "field": new_value}`
- [ ] Update current_phase field in returned state
- [ ] Add edge to/from this node in workflow graph
- [ ] Test that node returns correct state shape

### Checklist: Adding Conditional Edges

- [ ] Create predicate function: `def predicate(state: GameState) -> Literal["key1", "key2"]:`
- [ ] Return routing key based on state condition
- [ ] Ensure all possible routing keys have corresponding edges
- [ ] Use `workflow.add_conditional_edges()` with predicate and routing dict
- [ ] Test all routing paths (write tests for each branch)
- [ ] Verify predicate keys match exactly (case-sensitive)

### Checklist: Implementing RQ Workers

- [ ] Read research.md §3 for worker patterns
- [ ] Create standalone function (not class method) for worker
- [ ] Function must be importable at module level
- [ ] Add type hints to all parameters
- [ ] Implement exponential backoff for LLM calls (research.md §3, lines 330-350)
- [ ] Return serializable result (Pydantic model.dict() or plain dict)
- [ ] Create queue: `Queue('queue_name', connection=redis_conn)`
- [ ] Enqueue job with timeout: `queue.enqueue(func, arg=val, job_timeout=60)`
- [ ] Block for result: `result = job.result`
- [ ] Handle job failure (job.is_failed, job.exc_info)

---

## General Implementation Patterns

### Pattern: Copy-and-Adapt from Research

1. **Locate** the relevant section in research.md (use section number from task)
2. **Read** the "Code Example" subsection
3. **Copy** the complete code block
4. **Paste** into your file
5. **Adapt** variable names to match our models (e.g., `result` → `memory_edge`)
6. **Replace** placeholders with actual imports and Settings values
7. **Test** that adapted code runs

### Pattern: Implement from Contract

1. **Open** contracts/{name}_interface.yaml
2. **Find** the method/interface you're implementing
3. **Copy** the input/output schemas
4. **Read** the behavior requirements (MUST/MUST NOT)
5. **Note** the errors you must handle
6. **Implement** method matching signature exactly
7. **Write** contract test verifying behavior
8. **Run** test and verify it fails before implementation complete

### Pattern: Add ABOUTME Comments

Every source file needs exactly 2 lines at the top:

```python
# ABOUTME: [What this file does - one sentence]
# ABOUTME: [Key responsibilities or subsystems - one sentence]
```

Examples:
```python
# ABOUTME: LangGraph state machine orchestrating turn-based TTRPG gameplay phases
# ABOUTME: Handles phase transitions, validation retry loops, and DM intervention checkpoints
```

```python
# ABOUTME: Strategic decision-making agent (player layer) for TTRPG gameplay
# ABOUTME: Handles out-of-character discussion, intent formulation, and character directive creation
```

### Pattern: TDD (Test-Driven Development)

All tasks follow TDD:

1. **Write test FIRST** (before any implementation)
2. **Run test** and verify it FAILS
3. **Implement** minimum code to make test pass
4. **Run test** again and verify it PASSES
5. **Refactor** code while keeping test green

For contract tests:
- Test that method signatures match
- Test that return types are correct
- Test that behavior requirements are met

For unit tests:
- Test validation rules (invalid input should fail)
- Test edge cases (empty lists, None values)
- Test calculations (memory corruption probability)

For integration tests:
- Test complete workflows (full turn cycle)
- Test cross-component interaction (agent → memory → state)

---

## Using This Enhanced Format

**When starting any task**:

1. Read the **Prerequisites** - complete them first if needed
2. Follow **Implementation Steps** in exact order
3. Copy code from specified files/lines (don't rewrite from scratch)
4. Use **Success Criteria** as your checklist
5. Watch for **Common Pitfalls** mentioned
6. Reference the **Checklist** for your task type

**When stuck**:

1. Re-read the contract/spec referenced in the task
2. Check research.md for code examples
3. Look at data-model.md for field definitions
4. Review the relevant checklist
5. Ask for help if unclear (don't guess)

---

## Notes on Enhanced Format

This enhanced format reduces ambiguity and makes tasks more "copy-and-execute". Key improvements:

- **Line number references**: "research.md §2, lines 137-143" instead of just "research.md §2"
- **Explicit copy instructions**: "Copy this function" instead of "Reference this"
- **Step-by-step sequences**: Numbered steps with concrete actions
- **Code snippets in tasks**: Show exactly what to implement
- **Success criteria**: Clear definition of "done"
- **Common pitfalls**: Proactive error prevention
- **Prerequisites**: No mystery dependencies
- **Checklists**: Reusable patterns across similar tasks

This format works best when:
- Implementation details are already written (research.md, data-model.md, contracts/)
- Tasks reference specific code to copy/adapt
- Success is objectively verifiable
- Patterns are reusable across multiple tasks
