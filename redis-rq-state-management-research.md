# Redis Queue Management with RQ

## Research Summary: Turn Phase State Persistence for AI TTRPG System

**Research Date**: 2025-10-19
**Target Stack**: RQ 1.x+, Redis 7.x, LangGraph 0.2.x, Python 3.11+
**Research Focus**: Crash recovery, exponential backoff retry, async LLM API worker management

---

## Decision: Hybrid LangGraph Checkpointer + RQ Job Queue Architecture

For turn phase state persistence with crash recovery in the AI TTRPG system, the recommended approach is:

**Hybrid Architecture** where:
- **LangGraph Redis Checkpointer** manages turn phase state machine persistence
- **RQ Job Queue** handles async LLM API calls with retry logic
- **Redis** provides unified storage for both checkpoints and job state
- **Turn phases** are atomic with checkpoint-based rollback on failure

**Critical Integration Pattern**: LangGraph owns the state machine (turn phases), RQ owns the work execution (LLM API calls), and Redis coordinates both through separate namespaces.

---

## Rationale: Why This Approach Fits TTRPG Requirements

### 1. **LangGraph Checkpointer for Turn Phase State**

**Why Not Pure RQ for State Management?**
- RQ is designed for job execution, not state machine orchestration
- RQ doesn't natively support hierarchical state (player layer -> character layer)
- LangGraph provides turn phase rollback and time-travel debugging
- LangGraph Redis Checkpointer is purpose-built for agent state persistence

**LangGraph Redis Checkpointer Benefits**:
- Native support for LangGraph state graphs (player/character subgraphs)
- Thread-level persistence enables session recovery with `thread_id`
- BLPOP-based task orchestration prevents work loss on worker crashes
- Built-in checkpoint history for rollback to any previous turn phase
- Async support via `AsyncRedisSaver` for concurrent API calls

### 2. **RQ for LLM API Call Execution**

**Why RQ for API Calls?**
- Built-in exponential backoff retry mechanism
- Worker isolation via `SpawnWorker` (each job in separate process)
- Failed job registry for crash recovery
- Simple integration with Redis for job state
- Graceful shutdown preserves in-flight jobs

**RQ Solves**:
- LLM API transient failures (rate limits, timeouts, network errors)
- Worker crashes don't lose job state (stored in Redis)
- Concurrent API calls for 3-4 AI agents via multiple workers
- Automatic job retry with configurable intervals (2s, 5s, 10s)

### 3. **Redis 7.x as Unified Backend**

**Single Redis Instance for Both**:
- LangGraph checkpoints stored in Redis (keys: `langgraph:*`)
- RQ job state stored in Redis (keys: `rq:*`)
- Atomic operations via `WATCH`/`MULTI`/`EXEC` for phase transitions
- Redis persistence (`--appendonly yes`) ensures crash recovery
- Pub/Sub for real-time job status updates

### 4. **Crash Recovery Strategy**

**Multi-Layer Recovery**:
1. **Turn Phase Level** (LangGraph): Checkpoint after each phase; rollback to last stable checkpoint on failure
2. **Job Level** (RQ): Retry failed jobs via `FailedJobRegistry`; exponential backoff for transient errors
3. **Data Level** (Redis): AOF persistence ensures no data loss on Redis crash

**Recovery Flow**:
```
Crash Detected
  ↓
LangGraph loads last checkpoint (e.g., "Strategic Intent" phase)
  ↓
RQ reschedules abandoned jobs from FailedJobRegistry
  ↓
System retries turn phase with fresh LLM API calls
  ↓
If retry fails → flag for DM intervention (per FR-002)
```

### 5. **Worker Management for Concurrent API Calls**

**RQ Worker Architecture**:
- Run 4-6 workers (1-2 workers per AI agent for parallelism)
- Each worker handles one job at a time (no internal concurrency)
- Workers use `SpawnWorker` for process isolation (prevents memory leaks)
- Supervisor (systemd/Docker Compose) manages worker lifecycle
- Workers auto-retry jobs from queue on startup after crash

**Concurrency Pattern**:
```
Player 1 Strategic Intent → RQ Job (Worker 1)
Player 2 Strategic Intent → RQ Job (Worker 2)  } Parallel execution
Player 3 Strategic Intent → RQ Job (Worker 3)
Player 4 Strategic Intent → RQ Job (Worker 4)

All jobs write results back to Redis → LangGraph reads results → Next phase
```

---

## Key Patterns

### 1. Turn Phase State Persistence with LangGraph Redis Checkpointer

**Pattern**: Checkpoint After Every Phase Transition

```python
from langgraph.checkpoint.redis import RedisSaver
from langgraph.graph import StateGraph, END, START
from redis import Redis
from typing import TypedDict, Literal

# Turn phase state managed by LangGraph
class TurnState(TypedDict):
    phase: Literal[
        "dm_narration",
        "memory_query",
        "strategic_intent",
        "character_action",
        "validation",
        "dm_adjudication",
        "dice_resolution",
        "dm_outcome",
        "character_reaction",
        "memory_storage"
    ]
    current_player: str
    turn_number: int
    validation_attempts: int
    llm_job_ids: dict[str, str]  # player_id -> RQ job_id
    last_stable_phase: str

# Initialize Redis checkpointer
redis_conn = Redis(host='localhost', port=6379, db=0, decode_responses=False)
checkpointer = RedisSaver(redis_conn)

# Build turn phase state machine
def create_turn_graph():
    graph = StateGraph(TurnState)

    # Define turn phases as nodes
    graph.add_node("dm_narration", dm_narration_node)
    graph.add_node("memory_query", memory_query_node)
    graph.add_node("strategic_intent", strategic_intent_node)
    graph.add_node("character_action", character_action_node)
    graph.add_node("validation", validation_node)
    graph.add_node("dm_adjudication", dm_adjudication_node)

    # Strict phase sequencing (per FR-002)
    graph.add_edge(START, "dm_narration")
    graph.add_edge("dm_narration", "memory_query")
    graph.add_edge("memory_query", "strategic_intent")
    graph.add_edge("strategic_intent", "character_action")
    graph.add_edge("character_action", "validation")

    # Validation with retry/rollback
    graph.add_conditional_edges(
        "validation",
        route_validation,
        {
            "success": "dm_adjudication",
            "retry": "strategic_intent",  # Rollback 2 phases
            "failed": "dm_intervention"    # Max retries exceeded
        }
    )

    graph.add_edge("dm_adjudication", END)

    # Compile with checkpointer
    return graph.compile(checkpointer=checkpointer)

# Execute with session persistence
turn_app = create_turn_graph()

# Session start/resume
config = {
    "configurable": {
        "thread_id": "session_2025-10-19_game1",
        "checkpoint_ns": "turn_phases"
    }
}

# Execute turn (checkpoints automatically saved after each phase)
result = turn_app.invoke(initial_state, config)

# Crash recovery: Resume from last checkpoint
history = turn_app.get_state_history(config)
last_checkpoint = next(history)  # Most recent checkpoint
turn_app.update_state(config, last_checkpoint.values, as_node="memory_query")
```

**Key Benefits**:
- Automatic checkpointing after every phase transition
- Zero-code rollback using `get_state_history()` and `update_state()`
- Thread ID enables session resumption after crash
- Checkpoint namespace isolates turn phase state from other data

---

### 2. Exponential Backoff Integration with RQ Retry

**Pattern**: RQ Job Wrapper for LLM API Calls with Custom Retry Intervals

```python
from rq import Queue, Retry
from rq.job import Job
from redis import Redis
from tenacity import retry, wait_exponential, stop_after_attempt, retry_if_exception_type
import openai

# Redis connection for RQ
redis_conn = Redis(host='localhost', port=6379, db=0)
llm_queue = Queue('llm_calls', connection=redis_conn)

# LLM API call with exponential backoff (2s, 5s, 10s per requirements)
@retry(
    wait=wait_exponential(multiplier=1, min=2, max=10),  # 2s, 4s, 8s, 10s (capped)
    stop=stop_after_attempt(5),  # Max 5 attempts (~35s total per FR-013)
    retry=retry_if_exception_type((openai.RateLimitError, openai.APIConnectionError, openai.Timeout))
)
def call_llm_strategic_intent(player_id: str, context: dict) -> dict:
    """
    Make LLM API call for strategic intent phase.
    Retries transient errors with exponential backoff.
    """
    try:
        response = openai.ChatCompletion.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": f"You are {player_id}'s strategic layer..."},
                {"role": "user", "content": context["dm_narration"]}
            ],
            timeout=30  # 30s timeout per call
        )
        return {
            "player_id": player_id,
            "strategic_intent": response.choices[0].message.content,
            "status": "success"
        }
    except Exception as e:
        # Log error for research analysis (FR-022)
        print(f"LLM API error for {player_id}: {type(e).__name__}: {e}")
        raise  # Re-raise for tenacity retry

# Enqueue LLM API call as RQ job
def enqueue_strategic_intent(player_id: str, context: dict) -> str:
    """
    Enqueue LLM API call with RQ retry policy.
    Returns job_id for status tracking.
    """
    job = llm_queue.enqueue(
        call_llm_strategic_intent,
        args=(player_id, context),
        retry=Retry(max=3, interval=[10, 30, 60]),  # RQ-level retry (fallback)
        job_timeout='2m',  # Hard timeout (max 2 minutes per job)
        result_ttl=3600,  # Keep results for 1 hour
        failure_ttl=86400  # Keep failures for 24 hours (debugging)
    )
    return job.id

# Turn phase node that enqueues jobs for all players
def strategic_intent_node(state: TurnState) -> dict:
    """
    Strategic Intent phase: Enqueue LLM API calls for all players.
    Returns job IDs for result polling.
    """
    job_ids = {}

    for player_id in ["player_1", "player_2", "player_3"]:
        context = {
            "dm_narration": state["dm_narration"],
            "player_memory": state["player_memories"][player_id]
        }
        job_id = enqueue_strategic_intent(player_id, context)
        job_ids[player_id] = job_id

    # Store job IDs in state for result retrieval
    return {
        "llm_job_ids": job_ids,
        "phase": "strategic_intent_pending"
    }

# Result polling node (separate phase)
def await_strategic_intent_results(state: TurnState) -> dict:
    """
    Poll RQ jobs for completion.
    Blocks until all jobs finish or timeout.
    """
    results = {}
    failed_jobs = []

    for player_id, job_id in state["llm_job_ids"].items():
        job = Job.fetch(job_id, connection=redis_conn)

        # Wait for job completion (blocking)
        try:
            job.refresh()  # Update job status

            if job.is_finished:
                results[player_id] = job.result
            elif job.is_failed:
                failed_jobs.append(player_id)
                print(f"Job failed for {player_id}: {job.exc_info}")
            else:
                # Job still running (should not happen with blocking wait)
                raise TimeoutError(f"Job {job_id} did not complete in time")

        except Exception as e:
            failed_jobs.append(player_id)
            print(f"Error fetching job {job_id}: {e}")

    # Handle failures per FR-013 (rollback and flag for DM)
    if failed_jobs:
        return {
            "phase": "strategic_intent_failed",
            "failed_players": failed_jobs,
            "requires_dm_intervention": True
        }

    return {
        "strategic_intents": results,
        "phase": "character_action"  # Advance to next phase
    }
```

**Retry Timeline** (per FR-013 requirements):
```
Attempt 1: Immediate (t=0s)
  ↓ Fail (rate limit)
Attempt 2: Wait 2s (t=2s)
  ↓ Fail (timeout)
Attempt 3: Wait 4s (t=6s)
  ↓ Fail (connection error)
Attempt 4: Wait 8s (t=14s)
  ↓ Fail (rate limit)
Attempt 5: Wait 10s (capped) (t=24s)
  ↓ Success or Final Failure

Total: ~35 seconds maximum (within FR-013 requirement)
```

**Key Benefits**:
- Tenacity handles transient errors at function level (innermost retry)
- RQ provides job-level retry as fallback (outer retry)
- Failed jobs preserved in `FailedJobRegistry` for post-crash recovery
- Job IDs stored in LangGraph state enable result correlation

---

### 3. Worker Management for Concurrent API Calls

**Pattern**: Multi-Worker Pool with Process Isolation

```python
# worker_manager.py
from rq import Worker, Queue
from rq.worker import SpawnWorker
from redis import Redis
import os

# Redis connection
redis_conn = Redis(host='localhost', port=6379, db=0)

# Define queues
llm_queue = Queue('llm_calls', connection=redis_conn)
high_priority_queue = Queue('high_priority', connection=redis_conn)

# Spawn worker with crash isolation
def start_worker(worker_id: int, queues: list[str]):
    """
    Start RQ worker with SpawnWorker for process isolation.
    Each worker handles one job at a time.
    """
    worker = SpawnWorker(
        queues=[Queue(q, connection=redis_conn) for q in queues],
        connection=redis_conn,
        name=f"ttrpg_worker_{worker_id}"
    )

    # Register exception handler
    worker.push_exc_handler(log_job_failure)

    # Start worker (blocking)
    worker.work(
        max_jobs=100,  # Restart worker after 100 jobs (prevent memory leaks)
        with_scheduler=True  # Enable scheduled job support
    )

def log_job_failure(job, exc_type, exc_value, traceback):
    """
    Exception handler for failed jobs.
    Logs to research analysis system (FR-022).
    """
    print(f"Job {job.id} failed: {exc_type.__name__}: {exc_value}")

    # Log to research database
    from research_logger import log_api_failure
    log_api_failure(
        job_id=job.id,
        player_id=job.args[0] if job.args else "unknown",
        error_type=exc_type.__name__,
        error_message=str(exc_value),
        retry_count=job.retries_left
    )

    # Return False to continue processing other jobs
    return False

if __name__ == "__main__":
    worker_id = int(os.environ.get("WORKER_ID", 0))
    start_worker(worker_id, ["llm_calls", "high_priority"])
```

**Docker Compose Configuration** (recommended for production):

```yaml
# docker-compose.yml
services:
  redis:
    image: redis:7-alpine
    command: redis-server --appendonly yes  # Enable AOF persistence
    volumes:
      - redis_data:/data
    ports:
      - "6379:6379"

  # RQ workers (4 workers for 3-4 AI agents)
  worker_1:
    build: .
    command: python worker_manager.py
    environment:
      - WORKER_ID=1
      - REDIS_HOST=redis
    depends_on:
      - redis
    restart: unless-stopped

  worker_2:
    build: .
    command: python worker_manager.py
    environment:
      - WORKER_ID=2
      - REDIS_HOST=redis
    depends_on:
      - redis
    restart: unless-stopped

  worker_3:
    build: .
    command: python worker_manager.py
    environment:
      - WORKER_ID=3
      - REDIS_HOST=redis
    depends_on:
      - redis
    restart: unless-stopped

  worker_4:
    build: .
    command: python worker_manager.py
    environment:
      - WORKER_ID=4
      - REDIS_HOST=redis
    depends_on:
      - redis
    restart: unless-stopped

  # Optional: RQ dashboard for monitoring
  rq_dashboard:
    image: eoranged/rq-dashboard
    ports:
      - "9181:9181"
    environment:
      - RQ_DASHBOARD_REDIS_URL=redis://redis:6379
    depends_on:
      - redis

volumes:
  redis_data:
```

**Worker Concurrency Model**:
```
4 Workers × 1 Job/Worker = 4 Concurrent LLM API Calls

Example during Strategic Intent Phase:
Worker 1: call_llm_strategic_intent(player_1) → 3s
Worker 2: call_llm_strategic_intent(player_2) → 5s  } Parallel
Worker 3: call_llm_strategic_intent(player_3) → 4s
Worker 4: call_llm_strategic_intent(player_4) → 2s

Total Time: max(3s, 5s, 4s, 2s) = 5s (vs. 14s sequential)
```

**Key Benefits**:
- Process isolation via `SpawnWorker` prevents worker crashes from cascading
- Multiple workers enable parallel LLM API calls (critical for 3-4 agents)
- Docker Compose auto-restarts workers on crash
- Redis AOF persistence ensures job state survives Redis restart
- RQ Dashboard provides real-time monitoring (optional)

---

### 4. Crash Recovery Mechanism

**Pattern**: Atomic Phase Transitions with Checkpoint Rollback

```python
from langgraph.checkpoint.redis import RedisSaver
from rq import Queue
from redis import Redis
import redis.exceptions
from typing import Optional

class TurnPhaseManager:
    """
    Manages turn phase execution with crash recovery.
    Coordinates LangGraph checkpoints and RQ job state.
    """

    def __init__(self, redis_conn: Redis):
        self.redis_conn = redis_conn
        self.checkpointer = RedisSaver(redis_conn)
        self.llm_queue = Queue('llm_calls', connection=redis_conn)
        self.turn_graph = create_turn_graph()  # From pattern #1

    def execute_turn_phase(
        self,
        session_id: str,
        phase: str,
        state: dict
    ) -> dict:
        """
        Execute a turn phase with atomic checkpoint and job tracking.
        Automatically rolls back on failure.
        """
        config = {
            "configurable": {
                "thread_id": session_id,
                "checkpoint_ns": "turn_phases"
            }
        }

        # Mark last stable phase before attempting new phase
        state["last_stable_phase"] = state.get("phase", "dm_narration")

        try:
            # Execute phase (LangGraph automatically checkpoints)
            result = self.turn_graph.invoke(state, config)

            # Verify checkpoint was saved
            current_checkpoint = self.turn_graph.get_state(config)
            if current_checkpoint.values["phase"] != result["phase"]:
                raise RuntimeError("Checkpoint mismatch after phase execution")

            return result

        except Exception as e:
            print(f"Phase execution failed: {e}")
            return self._handle_phase_failure(session_id, state, e)

    def _handle_phase_failure(
        self,
        session_id: str,
        state: dict,
        error: Exception
    ) -> dict:
        """
        Rollback to last stable phase and retry once (per FR-002).
        """
        config = {
            "configurable": {
                "thread_id": session_id,
                "checkpoint_ns": "turn_phases"
            }
        }

        # Get checkpoint history
        history = list(self.turn_graph.get_state_history(config))

        # Find last stable checkpoint
        last_stable = None
        for checkpoint in history:
            if checkpoint.values.get("phase") == state.get("last_stable_phase"):
                last_stable = checkpoint
                break

        if not last_stable:
            # No stable checkpoint found - catastrophic failure
            return {
                "phase": "crashed",
                "error": f"No stable checkpoint found. Error: {error}",
                "requires_dm_intervention": True
            }

        # Rollback to last stable checkpoint
        self.turn_graph.update_state(
            config,
            last_stable.values,
            as_node="memory_query"  # Resume from safe phase
        )

        # Check if this is a retry
        retry_count = state.get("retry_count", 0)

        if retry_count >= 1:
            # Already retried once - flag for DM (per FR-002)
            return {
                "phase": "dm_intervention",
                "error": f"Phase failed after retry. Error: {error}",
                "requires_dm_intervention": True,
                "failed_phase": state.get("phase")
            }

        # Attempt retry
        state["retry_count"] = retry_count + 1
        return self.execute_turn_phase(session_id, last_stable.values["phase"], last_stable.values)

    def recover_abandoned_jobs(self, session_id: str) -> list[str]:
        """
        Recover RQ jobs abandoned due to worker crash.
        Called on session resume.
        """
        from rq.registry import FailedJobRegistry, StartedJobRegistry

        failed_registry = FailedJobRegistry(queue=self.llm_queue)
        started_registry = StartedJobRegistry(queue=self.llm_queue)

        recovered_jobs = []

        # Requeue failed jobs
        for job_id in failed_registry.get_job_ids():
            job = Job.fetch(job_id, connection=self.redis_conn)

            # Check if job belongs to this session
            if job.meta.get("session_id") == session_id:
                # Requeue job
                job.requeue()
                recovered_jobs.append(job_id)
                print(f"Requeued failed job: {job_id}")

        # Handle started jobs (worker crashed mid-execution)
        for job_id in started_registry.get_job_ids():
            job = Job.fetch(job_id, connection=self.redis_conn)

            if job.meta.get("session_id") == session_id:
                # Move to FailedJobRegistry with AbandonedJobError
                job.set_status("failed")
                job.exc_info = "Worker crashed during execution"
                failed_registry.add(job, -1)  # Add without TTL

                # Then requeue
                job.requeue()
                recovered_jobs.append(job_id)
                print(f"Recovered abandoned job: {job_id}")

        return recovered_jobs

# Usage example
manager = TurnPhaseManager(redis_conn)

# Execute turn
result = manager.execute_turn_phase(
    session_id="session_2025-10-19_game1",
    phase="strategic_intent",
    state=current_state
)

# On crash/restart: Recover session
if result.get("requires_dm_intervention"):
    print("DM intervention required!")
    # Flag for DM via CLI
else:
    # Continue turn
    pass

# Recover abandoned jobs (run on session resume)
recovered = manager.recover_abandoned_jobs("session_2025-10-19_game1")
print(f"Recovered {len(recovered)} abandoned jobs")
```

**Recovery Flow Diagram**:
```
Worker Crash Detected
  ↓
1. LangGraph loads last checkpoint (e.g., phase="memory_query")
  ↓
2. TurnPhaseManager calls recover_abandoned_jobs()
  ↓
3. Scan FailedJobRegistry + StartedJobRegistry for session jobs
  ↓
4. Requeue jobs → Workers pick up jobs automatically
  ↓
5. Resume turn from last stable phase
  ↓
6. If retry fails → Flag for DM intervention (per FR-002)
```

**Key Benefits**:
- Atomic phase transitions ensure consistent state
- Checkpoint history enables time-travel debugging
- Abandoned job recovery prevents data loss
- Single retry attempt (per FR-002) before DM escalation
- Session ID tagging enables multi-session recovery

---

## Alternatives Considered

### Alternative 1: Pure RQ for State Machine (No LangGraph)

**What**: Use RQ job chaining with `depends_on` to implement turn phase state machine.

**Example**:
```python
from rq import Queue

q = Queue('game', connection=redis_conn)

# Chain turn phases as dependent jobs
dm_narration_job = q.enqueue(dm_narration_phase)
memory_query_job = q.enqueue(memory_query_phase, depends_on=dm_narration_job)
strategic_intent_job = q.enqueue(strategic_intent_phase, depends_on=memory_query_job)
character_action_job = q.enqueue(character_action_phase, depends_on=strategic_intent_job)
```

**Why Rejected**:
- **No State Persistence**: RQ jobs are stateless; each phase would need to reload full game state from Redis manually
- **Limited Rollback**: RQ has no built-in checkpoint system; implementing rollback requires custom logic
- **Dependency Complexity**: Hierarchical player/character subgraphs would require complex job chaining across multiple queues
- **No Conditional Edges**: RQ `depends_on` is linear dependency only; conditional routing (validation retry) requires manual routing logic
- **Research Tooling**: No time-travel debugging or state inspection tools (LangGraph Studio provides visual debugging)

**When to Use**: Simple linear task pipelines without state management needs.

---

### Alternative 2: Celery instead of RQ

**What**: Use Celery task queue instead of RQ for LLM API call orchestration.

**Why Rejected**:
- **Complexity Overhead**: Celery requires message broker (RabbitMQ or Redis) + result backend (separate config); RQ uses Redis for both
- **Steeper Learning Curve**: Celery has more features but higher cognitive load for team unfamiliar with it
- **Over-Engineering**: Celery's advanced features (canvas primitives, task routing, priority routing) not needed for 3-4 concurrent agents
- **RQ Simplicity Wins**: RQ's "simple job queues" philosophy matches TTRPG research project better than Celery's enterprise feature set

**When to Use**: Large-scale production systems with complex task routing, periodic tasks, or multi-broker setups.

---

### Alternative 3: LangGraph Persistence Only (No RQ)

**What**: Use LangGraph's built-in retry policies and async nodes for everything, no separate job queue.

**Example**:
```python
from langgraph.constants import RetryPolicy

# Use LangGraph's RetryPolicy for LLM calls
player_graph.add_node(
    "strategic_intent",
    strategic_intent_llm_call,
    retry=RetryPolicy(
        max_attempts=5,
        initial_interval=2.0,
        backoff_factor=2.0,
        max_interval=10.0
    )
)
```

**Why Rejected**:
- **Worker Isolation**: LangGraph nodes run in-process; a crash kills the entire state machine (RQ workers are isolated processes)
- **No Graceful Shutdown**: LangGraph doesn't handle in-flight work during shutdown; RQ workers finish current jobs before stopping
- **Limited Observability**: RQ provides FailedJobRegistry, job status, and RQ Dashboard; LangGraph retry failures only visible in logs
- **Retry Granularity**: LangGraph RetryPolicy is per-node; RQ jobs can be manually requeued/inspected/modified post-failure
- **Production Maturity**: RQ is battle-tested for background jobs; LangGraph retry is newer feature (added in 0.2.x)

**When to Use**: Prototype/MVP systems where simplicity outweighs production resilience.

---

### Alternative 4: Redis Streams for Job Queue

**What**: Use Redis Streams + consumer groups instead of RQ for job distribution.

**Example**:
```python
# Add job to stream
redis_conn.xadd('llm_jobs', {'player_id': 'player_1', 'context': json.dumps(ctx)})

# Workers consume from stream
messages = redis_conn.xreadgroup('workers', 'worker_1', {'llm_jobs': '>'})
```

**Why Rejected**:
- **No Built-In Retry**: Redis Streams require manual retry logic; RQ provides `Retry` object with intervals
- **Job State Management**: Must manually track job status, failures, results in Redis keys; RQ handles this automatically
- **Worker Coordination**: Consumer groups require manual worker health checks; RQ workers auto-register/deregister
- **Complexity**: Redis Streams are lower-level primitive; RQ provides higher-level job abstraction
- **Tooling Gap**: No equivalent to RQ Dashboard for Redis Streams

**When to Use**: Real-time event streaming (e.g., game event broadcast), not discrete job execution.

---

## Code Examples

### Complete Integration Example: Turn Phase with RQ Jobs

```python
# turn_executor.py
"""
ABOUTME: Integrates LangGraph turn phase state machine with RQ job queue for LLM API calls.
ABOUTME: Provides crash recovery and exponential backoff retry for AI TTRPG system.
"""

from langgraph.graph import StateGraph, END, START
from langgraph.checkpoint.redis import RedisSaver
from rq import Queue, Retry
from rq.job import Job
from redis import Redis
from typing import TypedDict, Literal, Optional
from tenacity import retry, wait_exponential, stop_after_attempt, retry_if_exception_type
import openai
import time

# ========================================
# Configuration
# ========================================

REDIS_HOST = 'localhost'
REDIS_PORT = 6379
REDIS_DB = 0

redis_conn = Redis(host=REDIS_HOST, port=REDIS_PORT, db=REDIS_DB, decode_responses=False)
llm_queue = Queue('llm_calls', connection=redis_conn)
checkpointer = RedisSaver(redis_conn)

# ========================================
# State Definitions
# ========================================

class TurnState(TypedDict):
    """Turn phase state machine state."""
    session_id: str
    turn_number: int
    phase: Literal[
        "dm_narration",
        "memory_query",
        "strategic_intent",
        "strategic_intent_pending",
        "character_action",
        "validation",
        "dm_adjudication",
        "dm_intervention"
    ]
    dm_narration: str
    player_memories: dict[str, list[dict]]
    llm_job_ids: dict[str, str]
    strategic_intents: dict[str, str]
    validation_attempts: int
    last_stable_phase: str
    retry_count: int
    requires_dm_intervention: bool

# ========================================
# LLM API Call Functions (RQ Jobs)
# ========================================

@retry(
    wait=wait_exponential(multiplier=1, min=2, max=10),  # 2s, 4s, 8s, 10s
    stop=stop_after_attempt(5),
    retry=retry_if_exception_type((
        openai.RateLimitError,
        openai.APIConnectionError,
        openai.Timeout
    ))
)
def call_llm_strategic_intent(
    player_id: str,
    dm_narration: str,
    player_memory: list[dict],
    session_id: str
) -> dict:
    """
    LLM API call for strategic intent phase.
    Includes exponential backoff retry (2s, 5s, 10s).
    """
    try:
        response = openai.ChatCompletion.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "system",
                    "content": f"You are {player_id}'s strategic decision-making layer in a TTRPG..."
                },
                {
                    "role": "user",
                    "content": f"DM says: {dm_narration}\n\nRecent memory: {player_memory}"
                }
            ],
            timeout=30
        )

        return {
            "player_id": player_id,
            "strategic_intent": response.choices[0].message.content,
            "status": "success",
            "timestamp": time.time()
        }

    except Exception as e:
        # Log for research analysis
        print(f"[{session_id}] LLM API error for {player_id}: {type(e).__name__}")
        raise

# ========================================
# Turn Phase Nodes
# ========================================

def dm_narration_node(state: TurnState) -> dict:
    """
    DM Narration phase: Prompt DM for narration input.
    """
    narration = input("DM, enter your narration: ")

    return {
        "dm_narration": narration,
        "phase": "memory_query",
        "last_stable_phase": "dm_narration"
    }

def memory_query_node(state: TurnState) -> dict:
    """
    Memory Query phase: Retrieve relevant memories for each player.
    """
    # TODO: Integrate with Neo4j memory retrieval
    memories = {
        "player_1": [{"event": "Met merchant Galvin", "turn": state["turn_number"] - 5}],
        "player_2": [{"event": "Found ancient artifact", "turn": state["turn_number"] - 3}],
        "player_3": [{"event": "Witnessed ship damage", "turn": state["turn_number"] - 1}]
    }

    return {
        "player_memories": memories,
        "phase": "strategic_intent",
        "last_stable_phase": "memory_query"
    }

def strategic_intent_node(state: TurnState) -> dict:
    """
    Strategic Intent phase: Enqueue LLM API calls for all players.
    """
    job_ids = {}

    for player_id in ["player_1", "player_2", "player_3"]:
        job = llm_queue.enqueue(
            call_llm_strategic_intent,
            args=(
                player_id,
                state["dm_narration"],
                state["player_memories"].get(player_id, []),
                state["session_id"]
            ),
            retry=Retry(max=3, interval=[10, 30, 60]),
            job_timeout='2m',
            result_ttl=3600,
            meta={"session_id": state["session_id"], "turn": state["turn_number"]}
        )
        job_ids[player_id] = job.id

    return {
        "llm_job_ids": job_ids,
        "phase": "strategic_intent_pending"
    }

def await_strategic_intent_results_node(state: TurnState) -> dict:
    """
    Poll RQ jobs for completion and collect results.
    """
    results = {}
    failed_players = []
    max_wait = 120  # 2 minutes max wait
    start_time = time.time()

    while time.time() - start_time < max_wait:
        all_complete = True

        for player_id, job_id in state["llm_job_ids"].items():
            if player_id in results or player_id in failed_players:
                continue

            job = Job.fetch(job_id, connection=redis_conn)
            job.refresh()

            if job.is_finished:
                results[player_id] = job.result["strategic_intent"]
            elif job.is_failed:
                failed_players.append(player_id)
                print(f"Job failed for {player_id}: {job.exc_info}")
            else:
                all_complete = False

        if all_complete:
            break

        time.sleep(0.5)  # Poll every 500ms

    # Check for failures
    if failed_players:
        return {
            "phase": "dm_intervention",
            "requires_dm_intervention": True,
            "error": f"LLM API calls failed for: {', '.join(failed_players)}"
        }

    return {
        "strategic_intents": results,
        "phase": "character_action",
        "last_stable_phase": "strategic_intent_pending"
    }

def character_action_node(state: TurnState) -> dict:
    """
    Character Action phase: Characters interpret strategic intent.
    """
    # TODO: Implement character layer interpretation
    print("\n--- Strategic Intents ---")
    for player_id, intent in state["strategic_intents"].items():
        print(f"{player_id}: {intent}")

    return {
        "phase": "validation",
        "last_stable_phase": "character_action"
    }

def validation_node(state: TurnState) -> dict:
    """
    Validation phase: Check for narrative overreach.
    """
    # TODO: Implement validation logic (FR-003)
    validation_errors = []  # Placeholder

    return {
        "validation_attempts": state.get("validation_attempts", 0) + 1,
        "validation_errors": validation_errors,
        "phase": "dm_adjudication" if not validation_errors else "validation_retry"
    }

# ========================================
# Routing Functions
# ========================================

def route_after_strategic_intent(state: TurnState) -> str:
    """Route after strategic intent enqueuing."""
    return "await_results"

def route_after_validation(state: TurnState) -> str:
    """Route after validation."""
    if state.get("validation_errors"):
        if state.get("validation_attempts", 0) >= 3:
            return "dm_intervention"
        return "strategic_intent"  # Retry
    return "dm_adjudication"

# ========================================
# Graph Construction
# ========================================

def create_turn_phase_graph():
    """Build turn phase state machine."""
    graph = StateGraph(TurnState)

    # Add nodes
    graph.add_node("dm_narration", dm_narration_node)
    graph.add_node("memory_query", memory_query_node)
    graph.add_node("strategic_intent", strategic_intent_node)
    graph.add_node("await_results", await_strategic_intent_results_node)
    graph.add_node("character_action", character_action_node)
    graph.add_node("validation", validation_node)

    # Add edges
    graph.add_edge(START, "dm_narration")
    graph.add_edge("dm_narration", "memory_query")
    graph.add_edge("memory_query", "strategic_intent")
    graph.add_edge("strategic_intent", "await_results")

    graph.add_conditional_edges(
        "await_results",
        lambda s: "dm_intervention" if s.get("requires_dm_intervention") else "character_action"
    )

    graph.add_edge("character_action", "validation")

    graph.add_conditional_edges(
        "validation",
        route_after_validation,
        {
            "dm_adjudication": END,
            "strategic_intent": "strategic_intent",
            "dm_intervention": END
        }
    )

    return graph.compile(checkpointer=checkpointer)

# ========================================
# Execution
# ========================================

if __name__ == "__main__":
    turn_app = create_turn_phase_graph()

    session_id = "session_2025-10-19_game1"

    initial_state = TurnState(
        session_id=session_id,
        turn_number=1,
        phase="dm_narration",
        dm_narration="",
        player_memories={},
        llm_job_ids={},
        strategic_intents={},
        validation_attempts=0,
        last_stable_phase="dm_narration",
        retry_count=0,
        requires_dm_intervention=False
    )

    config = {
        "configurable": {
            "thread_id": session_id,
            "checkpoint_ns": "turn_phases"
        }
    }

    # Execute turn
    result = turn_app.invoke(initial_state, config)

    print(f"\n--- Turn Complete ---")
    print(f"Final Phase: {result['phase']}")

    if result.get("requires_dm_intervention"):
        print(f"⚠️  DM intervention required: {result.get('error')}")
```

---

## References

### RQ Documentation & Guides
- **RQ Official Docs**: https://python-rq.org/docs/
- **RQ Workers**: https://python-rq.org/docs/workers/
- **RQ Exceptions & Retries**: https://python-rq.org/docs/exceptions/
- **RQ GitHub Repository**: https://github.com/rq/rq

### Redis Persistence & Transactions
- **Redis Transactions (WATCH/MULTI/EXEC)**: https://redis.io/docs/latest/develop/using-commands/transactions/
- **Redis Persistence (AOF)**: https://redis.io/docs/latest/operate/oss_and_stack/management/persistence/

### LangGraph + Redis Integration
- **LangGraph Redis Checkpointer**: https://github.com/redis-developer/langgraph-redis
- **LangGraph & Redis Blog**: https://redis.io/blog/langgraph-redis-build-smarter-ai-agents-with-memory-persistence/
- **LangGraph Fault-Tolerant Execution**: https://neuralware.github.io/posts/langgraph-redis/
- **LangGraph Checkpointing Docs**: https://langchain-ai.github.io/langgraph/how-tos/memory/add-memory/

### Retry Strategies for LLM APIs
- **Retry Logic for LLM APIs (2025)**: https://markaicode.com/llm-api-retry-logic-implementation/
- **Tenacity Library (Python)**: https://tenacity.readthedocs.io/
- **OpenAI Rate Limit Handling**: https://cookbook.openai.com/examples/how_to_handle_rate_limits
- **Exponential Backoff Patterns**: https://medium.com/@suryasekhar/exponential-backoff-decorator-in-python-26ddf783aea0

### Worker Management & Production Patterns
- **RQ Workers Best Practices**: https://www.sankalpjonna.com/posts/handling-more-than-200-transactions-per-second-using-python-rq
- **RQ Interrupted Tasks**: https://medium.com/picus-security-engineering/the-interrupted-asynchronous-task-problem-and-solution-with-python-rq-435f1a597631
- **RQ vs Celery Comparison**: https://stackoverflow.com/questions/13440875/pros-and-cons-to-use-celery-vs-rq

### RQ Alternatives (For Context)
- **arq (Async RQ Alternative)**: https://arq-docs.helpmanual.io/
- **Celery Documentation**: https://docs.celeryq.dev/

---

## Implementation Checklist

### Phase 1: Core Infrastructure
- [ ] Set up Redis 7.x with AOF persistence enabled
- [ ] Install RQ and configure job queue
- [ ] Install LangGraph Redis checkpointer (`langgraph-checkpoint-redis`)
- [ ] Create basic turn phase state machine with LangGraph
- [ ] Test checkpoint persistence across sessions

### Phase 2: LLM API Integration
- [ ] Implement `call_llm_strategic_intent()` with Tenacity retry
- [ ] Configure RQ retry policy (2s, 5s, 10s intervals)
- [ ] Test exponential backoff with simulated API failures
- [ ] Verify total retry time stays within 35s (FR-013)

### Phase 3: Worker Management
- [ ] Create `worker_manager.py` with SpawnWorker
- [ ] Set up Docker Compose with 4 RQ workers
- [ ] Configure exception handlers for job failures
- [ ] Test worker crash recovery with abandoned jobs

### Phase 4: Crash Recovery
- [ ] Implement `TurnPhaseManager` class
- [ ] Add `execute_turn_phase()` with rollback logic
- [ ] Add `recover_abandoned_jobs()` for session resume
- [ ] Test crash scenarios (worker crash, Redis crash, job timeout)

### Phase 5: Validation & DM Intervention
- [ ] Integrate validation retry loop (max 3 attempts per FR-004)
- [ ] Add DM intervention flag on max retries (per FR-002)
- [ ] Test validation failure scenarios
- [ ] Implement DM CLI prompts for intervention

### Phase 6: Research Instrumentation
- [ ] Add logging for API retry patterns (FR-022)
- [ ] Track validation failure rates
- [ ] Log phase transition timing
- [ ] Set up RQ Dashboard for monitoring (optional)

---

## Production Deployment Notes

### Redis Configuration
```bash
# redis.conf (for production)
appendonly yes                    # Enable AOF persistence
appendfsync everysec              # Fsync every second (balance safety/performance)
auto-aof-rewrite-percentage 100   # Auto-compact AOF when 2x size
maxmemory 2gb                     # Set memory limit
maxmemory-policy allkeys-lru      # Evict least recently used keys
```

### RQ Worker Supervisor (systemd)
```ini
# /etc/systemd/system/ttrpg-worker@.service
[Unit]
Description=TTRPG RQ Worker %i
After=network.target redis.service

[Service]
Type=simple
User=ttrpg
WorkingDirectory=/opt/ttrpg-ai
Environment="WORKER_ID=%i"
ExecStart=/opt/ttrpg-ai/.venv/bin/python worker_manager.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target

# Enable multiple workers:
# systemctl enable ttrpg-worker@{1..4}
# systemctl start ttrpg-worker@{1..4}
```

### Monitoring Recommendations
- **RQ Dashboard**: Web UI for job monitoring (http://localhost:9181)
- **Redis INFO command**: Monitor memory usage, AOF status
- **Job Metrics**: Track job duration, failure rates, retry counts
- **LangGraph Studio**: Visual debugging of state machine (development only)

---

**Research Conducted By**: Claude (Sonnet 4.5)
**For**: Ryan (ttrpg-ai project)
**Date**: 2025-10-19
