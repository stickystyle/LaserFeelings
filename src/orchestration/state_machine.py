# ABOUTME: LangGraph state machine orchestrating turn-based TTRPG gameplay through 10 phase handlers.
# ABOUTME: Implements phase transitions, RQ job dispatch, error recovery, and checkpointing for turn cycle.

from datetime import datetime
from typing import Literal
import time
import json
import random

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from redis import Redis
from rq import Queue
from rq.job import Job
from loguru import logger

from src.models.game_state import GameState, GamePhase
from src.models.messages import MessageChannel, MessageType
from src.orchestration.message_router import MessageRouter


class JobFailedError(Exception):
    """Raised when RQ job fails or times out"""
    pass


class PhaseTransitionError(Exception):
    """Raised when phase transition is invalid"""
    pass


class MaxRetriesExceeded(Exception):
    """Raised when validation fails 3 times for all agents"""
    pass


class InvalidCommand(Exception):
    """Raised when DM command is invalid or cannot be executed"""
    pass


# ============================================================================
# Helper Functions
# ============================================================================


def _get_character_id_for_agent(agent_id: str) -> str:
    """
    Map agent ID to character ID (MVP uses simple pattern).

    Args:
        agent_id: Agent identifier (e.g., "agent_001")

    Returns:
        Character identifier (e.g., "char_001_001")

    Raises:
        ValueError: If agent_id format is invalid

    Note:
        TODO: Load from character config file when implemented (Phase 4+)
    """
    parts = agent_id.split('_')
    if len(parts) < 2:
        raise ValueError(f"Invalid agent_id format: {agent_id}")
    return f"char_{parts[1]}_001"


def _poll_job_with_backoff(job: Job, timeout: float) -> None:
    """
    Poll RQ job with exponential backoff.

    Args:
        job: RQ Job to poll
        timeout: Maximum time to wait in seconds

    Raises:
        JobFailedError: If job times out or fails

    Note:
        Uses exponential backoff capped at 2s to reduce CPU usage
    """
    sleep_time = 0.5
    max_sleep = 2.0
    start_time = time.time()

    while job.result is None and not job.is_failed:
        if time.time() - start_time > timeout:
            raise JobFailedError(f"Job timeout after {timeout}s")
        time.sleep(sleep_time)
        job.refresh()
        sleep_time = min(sleep_time * 1.3, max_sleep)  # Exponential backoff capped at 2s


# ============================================================================
# Phase Handler Nodes (T047-T056)
# ============================================================================


def dm_narration_node(state: GameState) -> GameState:
    """
    T047: Parse DM input and transition to MEMORY_RETRIEVAL.

    Args:
        state: Current game state

    Returns:
        Updated state with dm_narration set
    """
    logger.info(f"[PHASE: DM_NARRATION] Turn {state['turn_number']}")

    # DM narration is already in state from orchestrator input
    # Validate it exists
    if not state.get("dm_narration"):
        raise ValueError("dm_narration must be provided in state")

    logger.debug(f"DM narration: {state['dm_narration'][:100]}...")

    # Transition to memory retrieval
    return {
        **state,
        "current_phase": GamePhase.MEMORY_QUERY.value,
        "phase_start_time": datetime.now()
    }


def memory_retrieval_node(state: GameState) -> GameState:
    """
    T048: Query Graphiti for relevant context and add to state.

    Args:
        state: Current game state

    Returns:
        Updated state with retrieved_memories populated

    Note:
        TODO: Integrate with CorruptedTemporalMemory (requires memory_system injected via build_turn_graph)
        For Phase 3 MVP, returns empty memories to avoid breaking downstream phases.
        Full memory integration will be completed in Phase 3 memory tasks (T028-T037).
    """
    logger.info(f"[PHASE: MEMORY_RETRIEVAL] Turn {state['turn_number']}")

    # MVP placeholder - return empty memories for all agents
    retrieved_memories: dict[str, list[dict]] = {
        agent_id: [] for agent_id in state.get("active_agents", [])
    }

    logger.debug(f"Retrieved memories for {len(retrieved_memories)} agents (MVP: empty)")

    return {
        **state,
        "retrieved_memories": retrieved_memories,
        "current_phase": GamePhase.STRATEGIC_INTENT.value,
        "phase_start_time": datetime.now()
    }


def _create_strategic_intent_node(base_persona_queue: Queue):
    """
    Factory for strategic_intent_node with injected dependencies.

    Args:
        base_persona_queue: RQ Queue for base persona worker jobs

    Returns:
        Node function with captured queue dependency

    Note:
        TODO: Exponential backoff for LLM failures will be implemented in worker files (T062).
        Current implementation uses blocking RQ pattern for MVP - acknowledged as intentional
        for single-agent proof-of-concept. Phase 4+ will explore async patterns.
    """
    def strategic_intent_node(state: GameState) -> GameState:
        """
        T049: Dispatch RQ job to BasePersonaAgent.formulate_strategic_intent().

        Args:
            state: Current game state

        Returns:
            Updated state with strategic_intents populated
        """
        logger.info(f"[PHASE: STRATEGIC_INTENT] Turn {state['turn_number']}")

        strategic_intents: dict[str, str] = {}

        # Dispatch jobs for each agent
        jobs: dict[str, Job] = {}
        for agent_id in state["active_agents"]:
            logger.debug(f"Dispatching strategic intent job for {agent_id}")

            # TODO: Load personality config from character configuration file
            # For MVP, using placeholder personality config (Android Engineer personality)
            placeholder_personality = {
                "analytical_score": 0.8,  # Logical, analytical thinking
                "risk_tolerance": 0.3,  # Cautious, prefers safe solutions
                "detail_oriented": 0.9,  # Very focused on technical details
                "emotional_memory": 0.2,  # Factual memory, not emotion-driven
                "assertiveness": 0.5,  # Balanced, not overly dominant
                "cooperativeness": 0.7,  # Team player
                "openness": 0.6,  # Open to new technical solutions
                "rule_adherence": 0.8,  # Follows protocols closely
                "roleplay_intensity": 0.6,  # Moderate roleplay
                "base_decay_rate": 0.3  # Low memory decay (good retention)
            }
            placeholder_character_number = 2  # Android Engineer (good at Lasers)

            job = base_persona_queue.enqueue(
                'src.workers.base_persona_worker.formulate_strategic_intent',
                args=(
                    agent_id,
                    state["dm_narration"],
                    state["retrieved_memories"].get(agent_id, []),
                    placeholder_personality,
                    placeholder_character_number
                ),
                job_timeout=30,
                result_ttl=300,
                failure_ttl=600
            )
            jobs[agent_id] = job

        # Wait for all jobs to complete
        for agent_id, job in jobs.items():
            logger.debug(f"Waiting for strategic intent from {agent_id}")

            # Block until complete with exponential backoff polling
            timeout = 35  # Slightly longer than job_timeout
            _poll_job_with_backoff(job, timeout)

            if job.is_failed:
                raise JobFailedError(f"Strategic intent job failed for {agent_id}: {job.exc_info}")

            strategic_intents[agent_id] = job.result

        logger.info(f"Collected strategic intents from {len(strategic_intents)} agents")

        # For single-agent games, skip OOC discussion
        if len(state["active_agents"]) == 1:
            next_phase = GamePhase.CHARACTER_ACTION.value
        else:
            # TODO: OOC discussion phase will be implemented in Phase 7 (T146-T149) for multi-agent games
            next_phase = GamePhase.OOC_DISCUSSION.value

        return {
            **state,
            "strategic_intents": strategic_intents,
            "current_phase": next_phase,
            "phase_start_time": datetime.now()
        }

    return strategic_intent_node


def _create_p2c_directive_node(router: MessageRouter):
    """
    Factory for p2c_directive_node with injected dependencies.

    Args:
        router: MessageRouter for sending P2C directives

    Returns:
        Node function with captured router dependency
    """
    def p2c_directive_node(state: GameState) -> GameState:
        """
        T050: Call BasePersonaAgent.create_character_directive().

        Args:
            state: Current game state

        Returns:
            Updated state with directives sent to characters
        """
        logger.info(f"[PHASE: P2C_DIRECTIVE] Turn {state['turn_number']}")

        # For each agent, create directive to their character
        # In full implementation, this calls BasePersonaAgent.create_character_directive()
        # For MVP, we use the strategic intent directly as the directive

        for agent_id in state["active_agents"]:
            strategic_intent = state["strategic_intents"][agent_id]

            # Map agent_id to character_id using helper
            character_id = _get_character_id_for_agent(agent_id)

            # Convert strategic intent to string for message content
            # (strategic_intent is a dict from job.result)
            intent_text = strategic_intent.get("strategic_goal", str(strategic_intent))

            # Send P2C directive
            router.add_message(
                channel=MessageChannel.P2C,
                from_agent=agent_id,
                content=intent_text,
                message_type=MessageType.DIRECTIVE,
                phase=GamePhase.CHARACTER_ACTION.value,
                turn_number=state["turn_number"],
                to_agents=[character_id],
                session_number=state.get("session_number")
            )

            logger.debug(f"Sent P2C directive from {agent_id} to {character_id}")

        return {
            **state,
            "current_phase": GamePhase.CHARACTER_ACTION.value,
            "phase_start_time": datetime.now()
        }

    return p2c_directive_node


def _create_character_action_node(character_queue: Queue):
    """
    Factory for character_action_node with injected dependencies.

    Args:
        character_queue: RQ Queue for character worker jobs

    Returns:
        Node function with captured queue dependency

    Note:
        TODO: Exponential backoff for LLM failures will be implemented in worker files (T062).
    """
    def character_action_node(state: GameState) -> GameState:
        """
        T051: Dispatch RQ job to CharacterAgent.perform_action().

        Args:
            state: Current game state

        Returns:
            Updated state with character_actions populated
        """
        logger.info(f"[PHASE: CHARACTER_ACTION] Turn {state['turn_number']}")

        character_actions: dict[str, str] = {}

        # Dispatch jobs for each character
        jobs: dict[str, Job] = {}
        for agent_id in state["active_agents"]:
            # Map agent_id to character_id using helper
            character_id = _get_character_id_for_agent(agent_id)

            logger.debug(f"Dispatching character action job for {character_id}")

            # Get strategic intent and transform to directive format
            # TODO: In full implementation, call BasePersonaAgent.create_character_directive()
            # For MVP, transform Intent dict to Directive dict
            strategic_intent = state["strategic_intents"][agent_id]
            directive = {
                "from_player": agent_id,
                "to_character": character_id,
                "instruction": strategic_intent.get("strategic_goal", ""),
                "tactical_guidance": strategic_intent.get("reasoning", ""),
                "emotional_tone": "focused"  # Default for MVP
            }
            scene_context = state["dm_narration"]

            # TODO: Load character sheet config from configuration file
            # For MVP, using placeholder character sheet
            placeholder_character_sheet = {
                "name": "Zara-7",
                "style": "Android",
                "role": "Engineer",
                "number": 2,  # Good at Lasers (technical/logical tasks)
                "character_goal": "Protect the crew through technical excellence",
                "equipment": ["Advanced toolkit", "Repair drone"],
                "speech_patterns": ["Precise technical language", "Logical reasoning"],
                "mannerisms": ["Tilts head when analyzing", "LED eyes dim when processing"],
                "approach_bias": "technical_solutions"
            }

            job = character_queue.enqueue(
                'src.workers.character_worker.perform_action',
                args=(character_id, directive, scene_context, placeholder_character_sheet),
                job_timeout=30,
                result_ttl=300,
                failure_ttl=600
            )
            jobs[character_id] = job

        # Wait for all jobs to complete
        for character_id, job in jobs.items():
            logger.debug(f"Waiting for character action from {character_id}")

            timeout = 35
            _poll_job_with_backoff(job, timeout)

            if job.is_failed:
                raise JobFailedError(f"Character action job failed for {character_id}: {job.exc_info}")

            character_actions[character_id] = job.result

        logger.info(f"Collected character actions from {len(character_actions)} characters")

        return {
            **state,
            "character_actions": character_actions,
            "current_phase": GamePhase.VALIDATION.value,
            "validation_attempt": 1,
            "phase_start_time": datetime.now()
        }

    return character_action_node


def dm_adjudication_node(state: GameState) -> GameState:
    """
    T052: Wait for DM success/fail command.

    Args:
        state: Current game state

    Returns:
        Updated state waiting for DM adjudication
    """
    logger.info(f"[PHASE: DM_ADJUDICATION] Turn {state['turn_number']}")

    # In interactive mode, this pauses execution and waits for DM input
    # For now, we assume DM provides adjudication and continue

    # Check if dice roll is needed
    needs_dice = state.get("dm_adjudication_needed", True)

    if needs_dice and "dice_override" not in state:
        next_phase = GamePhase.DICE_RESOLUTION.value
    else:
        # DM provided direct success/fail, skip dice
        next_phase = GamePhase.DM_OUTCOME.value

    return {
        **state,
        "current_phase": next_phase,
        "phase_start_time": datetime.now()
    }


def dice_resolution_node(state: GameState) -> GameState:
    """
    T053: Execute dice rolls if needed.

    Args:
        state: Current game state

    Returns:
        Updated state with dice_result and dice_success
    """
    logger.info(f"[PHASE: DICE_RESOLUTION] Turn {state['turn_number']}")

    # Check for DM override
    if "dice_override" in state and state["dice_override"] is not None:
        dice_result = state["dice_override"]
        logger.info(f"Using DM dice override: {dice_result}")
    else:
        # Roll 1d6 (Lasers & Feelings)
        dice_result = random.randint(1, 6)
        logger.info(f"Rolled 1d6: {dice_result}")

    # Determine success based on character number and task type
    # For MVP, we assume task_type is in state
    task_type = state.get("dice_task_type", "lasers")
    character_id = state.get("dice_action_character")

    # TODO: Load character number from config in full implementation
    # For MVP, assume number = 3 (balanced)
    character_number = 3

    # Lasers & Feelings rules:
    # Lasers task: roll UNDER number to succeed
    # Feelings task: roll OVER number to succeed
    # Roll EXACTLY number: success with complication
    if dice_result == character_number:
        dice_success = True
        dice_complication = True
    elif task_type == "lasers":
        dice_success = dice_result < character_number
        dice_complication = False
    else:  # feelings
        dice_success = dice_result > character_number
        dice_complication = False

    logger.info(f"Dice resolution: {dice_result} vs {character_number} ({task_type}) = {'SUCCESS' if dice_success else 'FAILURE'}{' with COMPLICATION' if dice_complication else ''}")

    return {
        **state,
        "dice_result": dice_result,
        "dice_success": dice_success,
        "dice_complication": dice_complication,
        "current_phase": GamePhase.DM_OUTCOME.value,
        "phase_start_time": datetime.now()
    }


def _create_dm_outcome_node(router: MessageRouter):
    """
    Factory for dm_outcome_node with injected dependencies.

    Args:
        router: MessageRouter for sending IC messages

    Returns:
        Node function with captured router dependency
    """
    def dm_outcome_node(state: GameState) -> GameState:
        """
        T054: Process DM narrated outcome.

        Args:
            state: Current game state

        Returns:
            Updated state with dm_outcome
        """
        logger.info(f"[PHASE: DM_OUTCOME] Turn {state['turn_number']}")

        # In interactive mode, DM provides outcome narration
        # For MVP skeleton, we generate placeholder outcome
        if "dm_outcome" in state and state["dm_outcome"]:
            outcome = state["dm_outcome"]
        else:
            # Generate placeholder based on dice result
            if state.get("dice_success", True):
                outcome = "The action succeeds."
            else:
                outcome = "The action fails."

        logger.debug(f"DM outcome: {outcome[:100]}...")

        # Route outcome as IC message
        router.add_message(
            channel=MessageChannel.IC,
            from_agent="dm",
            content=outcome,
            message_type=MessageType.NARRATION,
            phase=GamePhase.DM_OUTCOME.value,
            turn_number=state["turn_number"],
            session_number=state.get("session_number")
        )

        return {
            **state,
            "dm_outcome": outcome,
            "current_phase": GamePhase.CHARACTER_REACTION.value,
            "phase_start_time": datetime.now()
        }

    return dm_outcome_node


def _create_character_reaction_node(character_queue: Queue):
    """
    Factory for character_reaction_node with injected dependencies.

    Args:
        character_queue: RQ Queue for character worker jobs

    Returns:
        Node function with captured queue dependency

    Note:
        TODO: Exponential backoff for LLM failures will be implemented in worker files (T062).
    """
    def character_reaction_node(state: GameState) -> GameState:
        """
        T055: Dispatch RQ job to CharacterAgent.react_to_outcome().

        Args:
            state: Current game state

        Returns:
            Updated state with character_reactions populated
        """
        logger.info(f"[PHASE: CHARACTER_REACTION] Turn {state['turn_number']}")

        character_reactions: dict[str, str] = {}

        # Dispatch jobs for each character
        jobs: dict[str, Job] = {}
        for agent_id in state["active_agents"]:
            character_id = _get_character_id_for_agent(agent_id)

            logger.debug(f"Dispatching character reaction job for {character_id}")

            # Get prior action for context
            prior_action = state["character_actions"].get(character_id, "")

            # TODO: Load character sheet config from configuration file
            # For MVP, using placeholder character sheet (same as in perform_action)
            placeholder_character_sheet = {
                "name": "Zara-7",
                "style": "Android",
                "role": "Engineer",
                "number": 2,
                "character_goal": "Protect the crew through technical excellence",
                "equipment": ["Advanced toolkit", "Repair drone"],
                "speech_patterns": ["Precise technical language", "Logical reasoning"],
                "mannerisms": ["Tilts head when analyzing", "LED eyes dim when processing"],
                "approach_bias": "technical_solutions"
            }

            job = character_queue.enqueue(
                'src.workers.character_worker.react_to_outcome',
                args=(character_id, state["dm_outcome"], prior_action, placeholder_character_sheet),
                job_timeout=30,
                result_ttl=300,
                failure_ttl=600
            )
            jobs[character_id] = job

        # Wait for all jobs to complete
        for character_id, job in jobs.items():
            logger.debug(f"Waiting for character reaction from {character_id}")

            timeout = 35
            _poll_job_with_backoff(job, timeout)

            if job.is_failed:
                raise JobFailedError(f"Character reaction job failed for {character_id}: {job.exc_info}")

            character_reactions[character_id] = job.result

        logger.info(f"Collected character reactions from {len(character_reactions)} characters")

        return {
            **state,
            "character_reactions": character_reactions,
            "current_phase": GamePhase.MEMORY_STORAGE.value,
            "phase_start_time": datetime.now()
        }

    return character_reaction_node


def memory_consolidation_node(state: GameState) -> GameState:
    """
    T056: Call CorruptedTemporalMemory.add_episode().

    Args:
        state: Current game state

    Returns:
        Updated state with memory stored

    Note:
        TODO: Integrate with CorruptedTemporalMemory (requires memory_system injected via build_turn_graph)
        For Phase 3 MVP, logs consolidation without actually storing to avoid breaking turn cycle.
        Full memory integration will be completed in Phase 3 memory tasks (T028-T037).
    """
    logger.info(f"[PHASE: MEMORY_CONSOLIDATION] Turn {state['turn_number']}")

    # Collect turn events for memory storage
    turn_events = {
        "turn_number": state["turn_number"],
        "dm_narration": state["dm_narration"],
        "strategic_intents": state["strategic_intents"],
        "character_actions": state["character_actions"],
        "dm_outcome": state.get("dm_outcome", ""),
        "character_reactions": state["character_reactions"],
    }

    logger.debug(f"Consolidating memories for turn {state['turn_number']} (MVP: logged only)")

    # TODO: Uncomment when memory system is integrated
    # memory_system.add_episode(
    #     session_number=state["session_number"],
    #     turn_number=state["turn_number"],
    #     events=turn_events
    # )

    return {
        **state,
        "current_phase": GamePhase.DM_NARRATION.value,  # Ready for next turn
        "turn_number": state["turn_number"] + 1,
        "phase_start_time": datetime.now()
    }


# ============================================================================
# Conditional Edge Predicates (T057: Error Recovery)
# ============================================================================


def should_retry_validation(state: GameState) -> Literal["valid", "retry", "escalate"]:
    """
    Conditional edge for validation retry logic.

    Args:
        state: Current game state

    Returns:
        Route key: "valid", "retry", or "escalate"
    """
    if state["validation_valid"]:
        return "valid"
    elif state["validation_attempt"] < 3:
        return "retry"
    else:
        return "escalate"


def should_skip_ooc_discussion(state: GameState) -> Literal["discuss", "skip"]:
    """
    Conditional edge for skipping OOC phase in single-agent games.

    Args:
        state: Current game state

    Returns:
        Route key: "discuss" or "skip"
    """
    if len(state["active_agents"]) == 1:
        return "skip"
    else:
        return "discuss"


def check_error_state(state: GameState) -> Literal["continue", "rollback"]:
    """
    Conditional edge for error recovery.

    Args:
        state: Current game state

    Returns:
        Route key: "continue" or "rollback"
    """
    if state.get("error_state"):
        return "rollback"
    else:
        return "continue"


# ============================================================================
# Validation Retry Node
# ============================================================================


def validation_retry_node(state: GameState) -> GameState:
    """
    Retry character action with stricter validation prompt.

    Args:
        state: Current game state

    Returns:
        Updated state with retry attempt incremented
    """
    logger.warning(f"[VALIDATION RETRY] Attempt {state['validation_attempt'] + 1}/3")

    # Get validation failures
    failures = state["validation_failures"]

    # TODO: In full implementation, re-dispatch character jobs with stricter prompts
    # For MVP, we increment attempt and proceed

    return {
        **state,
        "validation_attempt": state["validation_attempt"] + 1,
        "current_phase": GamePhase.CHARACTER_ACTION.value,
        "phase_start_time": datetime.now()
    }


def validation_escalate_node(state: GameState) -> GameState:
    """
    Escalate validation failures to DM review.

    Args:
        state: Current game state

    Returns:
        Updated state with DM review flag set
    """
    logger.error(f"[VALIDATION ESCALATE] Max retries exceeded, flagging for DM review")

    return {
        **state,
        "dm_review_required": True,
        "current_phase": GamePhase.DM_ADJUDICATION.value,
        "phase_start_time": datetime.now()
    }


# ============================================================================
# Rollback Handler
# ============================================================================


def rollback_handler_node(state: GameState) -> GameState:
    """
    Handle rollback to previous stable phase.

    Args:
        state: Current game state

    Returns:
        Restored state from checkpoint

    Raises:
        MaxRetriesExceeded: When retry count reaches 3
    """
    logger.error(f"[ROLLBACK] Error in phase {state['current_phase']}: {state.get('error_state', 'Unknown')}")

    # Determine rollback target
    rollback_phase = state.get("rollback_phase", GamePhase.DM_NARRATION.value)

    # Increment retry count
    retry_count = state.get("retry_count", 0) + 1

    if retry_count >= 3:
        logger.critical("[ROLLBACK] Max retries exceeded, halting turn cycle")
        raise MaxRetriesExceeded(f"Max retries exceeded after rollback from {state['current_phase']}")

    return {
        **state,
        "current_phase": rollback_phase,
        "retry_count": retry_count,
        "error_state": None,  # Clear error
        "phase_start_time": datetime.now()
    }


# ============================================================================
# State Machine Builder (T046 & T058)
# ============================================================================


def build_turn_graph(redis_client: Redis) -> StateGraph:
    """
    Build LangGraph StateGraph for turn cycle orchestration.

    Args:
        redis_client: Redis connection for RQ queues and messaging

    Returns:
        Compiled StateGraph application with checkpointing

    Implements:
    - T046: LangGraph State Machine structure
    - T058: Checkpointing configuration

    Note:
        Dependency injection pattern resolves LangGraph pure function constraints.
        Node factories capture dependencies via closures, preventing Redis connection
        creation inside node execution.
    """
    logger.info("Building turn cycle state machine with dependency injection")

    # Initialize RQ queues and message router with injected Redis client
    base_persona_queue = Queue('base_persona', connection=redis_client)
    character_queue = Queue('character', connection=redis_client)
    router = MessageRouter(redis_client)

    # Create node functions with injected dependencies (factory pattern)
    strategic_intent_node = _create_strategic_intent_node(base_persona_queue)
    p2c_directive_node = _create_p2c_directive_node(router)
    character_action_node = _create_character_action_node(character_queue)
    dm_outcome_node = _create_dm_outcome_node(router)
    character_reaction_node = _create_character_reaction_node(character_queue)

    # Initialize graph
    workflow = StateGraph(GameState)  # Use GameState TypedDict for schema

    # Add phase handler nodes (T047-T056)
    workflow.add_node("dm_narration", dm_narration_node)
    workflow.add_node("memory_retrieval", memory_retrieval_node)
    workflow.add_node("strategic_intent", strategic_intent_node)
    workflow.add_node("p2c_directive", p2c_directive_node)
    workflow.add_node("character_action", character_action_node)
    workflow.add_node("dm_adjudication", dm_adjudication_node)
    workflow.add_node("dice_resolution", dice_resolution_node)
    workflow.add_node("dm_outcome", dm_outcome_node)
    workflow.add_node("character_reaction", character_reaction_node)
    workflow.add_node("memory_consolidation", memory_consolidation_node)

    # Add error recovery nodes (T057)
    workflow.add_node("validation_retry", validation_retry_node)
    workflow.add_node("validation_escalate", validation_escalate_node)
    workflow.add_node("rollback_handler", rollback_handler_node)

    # Set entry point
    workflow.set_entry_point("dm_narration")

    # Add linear edges for main flow
    workflow.add_edge("dm_narration", "memory_retrieval")
    workflow.add_edge("memory_retrieval", "strategic_intent")
    workflow.add_edge("strategic_intent", "p2c_directive")
    workflow.add_edge("p2c_directive", "character_action")

    # Validation conditional routing (T057)
    # TODO: Validation node will be added in Phase 4 (T084-T097) between character_action and dm_adjudication
    # For Phase 3 MVP, proceed directly to adjudication
    workflow.add_edge("character_action", "dm_adjudication")

    workflow.add_edge("dm_adjudication", "dice_resolution")
    workflow.add_edge("dice_resolution", "dm_outcome")
    workflow.add_edge("dm_outcome", "character_reaction")
    workflow.add_edge("character_reaction", "memory_consolidation")

    # Memory consolidation ends turn
    workflow.add_edge("memory_consolidation", END)

    # T058: Compile with checkpointing
    checkpointer = MemorySaver()
    app = workflow.compile(checkpointer=checkpointer)

    logger.info("Turn cycle state machine built successfully")
    return app


# ============================================================================
# Orchestrator Interface
# ============================================================================


class TurnOrchestrator:
    """
    High-level orchestrator for executing turn cycles.

    Provides interface matching orchestrator_interface.yaml contract.

    Note:
        TODO: ConsensusDetector will be implemented in Phase 7 (T139-T145) for multi-agent support.
        Phase 3 MVP with single agent does not require consensus detection.
    """

    def __init__(self, redis_client: Redis):
        """
        Initialize turn orchestrator.

        Args:
            redis_client: Redis connection for state and messaging
        """
        self.redis = redis_client
        self.router = MessageRouter(redis_client)
        self.graph = build_turn_graph(redis_client)

    def execute_turn_cycle(
        self,
        dm_input: str,
        active_agents: list[str],
        turn_number: int = 1,
        session_number: int = 1
    ) -> dict:
        """
        Execute complete turn from DM input to result.

        Args:
            dm_input: DM narration or command
            active_agents: List of agent_ids participating in turn
            turn_number: Current turn number
            session_number: Current session number

        Returns:
            TurnResult dict with success, phase_completed, actions, etc.

        Raises:
            PhaseTransitionError: When state machine cannot proceed
            JobFailedError: When agent RQ job times out
        """
        logger.info(f"=== EXECUTING TURN {turn_number} ===")

        # Initialize game state
        initial_state: GameState = {
            "current_phase": GamePhase.DM_NARRATION.value,
            "phase_start_time": datetime.now(),
            "turn_number": turn_number,
            "session_number": session_number,
            "dm_narration": dm_input,
            "dm_adjudication_needed": True,
            "active_agents": active_agents,
            "strategic_intents": {},
            "ooc_messages": [],
            "character_actions": {},
            "character_reactions": {},
            "validation_attempt": 0,
            "validation_valid": True,
            "validation_failures": {},
            "retrieved_memories": {},
            "retry_count": 0,
        }

        logger.debug(f"Initial state keys: {list(initial_state.keys())}")
        logger.debug(f"turn_number in initial_state: {'turn_number' in initial_state}")

        # Execute graph with checkpointing
        thread_id = f"session_{session_number}"
        config = {"configurable": {"thread_id": thread_id}}

        try:
            # Run the graph
            result = self.graph.invoke(initial_state, config=config)

            # Extract turn result
            turn_result = {
                "turn_number": turn_number,
                "phase_completed": result["current_phase"],
                "success": True,
                "character_actions": result.get("character_actions", {}),
                "validation_warnings": [],  # TODO: Extract from validation state
                "consensus_state": result.get("consensus_state"),
                "dm_awaiting_input": False
            }

            logger.info(f"=== TURN {turn_number} COMPLETED SUCCESSFULLY ===")
            return turn_result

        except Exception as e:
            logger.error(f"Turn execution failed: {e}")
            raise

    def transition_to_phase(self, session_number: int, target_phase: str) -> dict:
        """
        Explicitly transition to a new phase (DM override).

        Args:
            session_number: Session to modify
            target_phase: Phase to transition to

        Returns:
            Updated state dict after phase transition

        Raises:
            ValueError: If target_phase is not a valid GamePhase
            PhaseTransitionError: If transition is not allowed from current phase
        """
        # Validate phase is legal
        try:
            phase_enum = GamePhase(target_phase)
        except ValueError:
            raise ValueError(f"Invalid phase: {target_phase}")

        logger.info(f"[DM OVERRIDE] Transitioning session {session_number} to phase {target_phase}")

        # TODO: Load current state from checkpoint
        # TODO: Validate transition is legal from current phase
        # TODO: Update phase in state
        # TODO: Save checkpoint

        # For MVP, return placeholder
        return {
            "success": True,
            "session_number": session_number,
            "current_phase": target_phase,
            "message": f"Transitioned to {target_phase} (MVP: not persisted)"
        }

    def rollback_to_phase(self, session_number: int, target_phase: str, error_context: str) -> dict:
        """
        Rollback to previous stable phase after error.

        Args:
            session_number: Session to rollback
            target_phase: Phase to rollback to
            error_context: Description of error that triggered rollback

        Returns:
            Rolled-back state dict

        Raises:
            ValueError: If target_phase is not a valid GamePhase
        """
        # Validate phase is legal
        try:
            phase_enum = GamePhase(target_phase)
        except ValueError:
            raise ValueError(f"Invalid phase: {target_phase}")

        logger.warning(f"[ROLLBACK] Rolling back session {session_number} to {target_phase}: {error_context}")

        # TODO: Restore from checkpoint
        # TODO: Update phase and error context
        # TODO: Save checkpoint

        # For MVP, return placeholder
        return {
            "success": True,
            "session_number": session_number,
            "current_phase": target_phase,
            "error_context": error_context,
            "message": f"Rolled back to {target_phase} (MVP: not persisted)"
        }

    def validate_phase_action(self, agent_id: str, action_type: str, current_phase: str) -> dict:
        """
        Check if agent action allowed in current phase.

        Args:
            agent_id: Agent attempting action
            action_type: Type of action (e.g., "speak", "move", "attack")
            current_phase: Current game phase

        Returns:
            Validation result dict with allowed=True/False and reason

        Raises:
            ValueError: If current_phase is not a valid GamePhase
        """
        # Validate phase is legal
        try:
            phase_enum = GamePhase(current_phase)
        except ValueError:
            raise ValueError(f"Invalid phase: {current_phase}")

        logger.debug(f"[VALIDATION] Checking if {agent_id} can perform {action_type} in {current_phase}")

        # TODO: Implement phase-based permission enforcement
        # For MVP, allow all actions
        return {
            "allowed": True,
            "agent_id": agent_id,
            "action_type": action_type,
            "current_phase": current_phase,
            "reason": "MVP: all actions allowed"
        }
