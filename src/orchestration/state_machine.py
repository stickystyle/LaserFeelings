# ABOUTME: LangGraph state machine orchestrating turn-based TTRPG gameplay through 10 phase handlers.
# ABOUTME: Implements phase transitions, RQ job dispatch, error recovery, and checkpointing for turn cycle.

import random
import time
from datetime import datetime
from typing import Literal

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph
from loguru import logger
from redis import Redis
from rq import Queue
from rq.job import Job

from src.models.game_state import GamePhase, GameState
from src.models.messages import MessageChannel, MessageType
from src.orchestration.message_router import MessageRouter
from src.utils.dice import roll_lasers_feelings


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


def _load_agent_character_mapping() -> dict[str, str]:
    """
    Load agent_id → character_id mapping from config files.

    Returns:
        Dict mapping agent IDs to character IDs
    """
    import json
    from pathlib import Path

    mapping = {}
    config_dir = Path("config/personalities")

    if not config_dir.exists():
        logger.warning(f"Config directory not found: {config_dir}")
        return mapping

    for config_file in config_dir.glob("char_*_character.json"):
        try:
            with open(config_file) as f:
                char_config = json.load(f)
                agent_id = char_config.get("agent_id")
                character_id = char_config.get("character_id")

                if agent_id and character_id:
                    mapping[agent_id] = character_id
        except Exception as e:
            logger.warning(f"Failed to load {config_file}: {e}")

    logger.info(f"Loaded agent-to-character mappings: {mapping}")
    return mapping


# Load mapping once at module level
_AGENT_CHARACTER_MAPPING = _load_agent_character_mapping()


def _get_character_id_for_agent(agent_id: str) -> str:
    """
    Map agent ID to character ID using config files.

    Args:
        agent_id: Agent identifier (e.g., "agent_alex_001")

    Returns:
        Character identifier (e.g., "char_zara_001")

    Raises:
        ValueError: If agent_id not found in mapping
    """
    character_id = _AGENT_CHARACTER_MAPPING.get(agent_id)

    if not character_id:
        raise ValueError(
            f"No character mapping found for agent {agent_id}. "
            f"Available agents: {list(_AGENT_CHARACTER_MAPPING.keys())}"
        )

    return character_id


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

        character_actions: dict[str, dict] = {}

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

            # Store full Action dict (not just narrative_text)
            action_dict = job.result
            character_actions[character_id] = action_dict

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


def _load_character_number(character_id: str) -> int:
    """
    Load character number from config file.

    Args:
        character_id: Character ID (e.g., 'char_zara_001')

    Returns:
        Character number (2-5) from config file

    Raises:
        FileNotFoundError: If config file doesn't exist
        ValueError: If number is invalid or missing
    """
    import json
    from pathlib import Path

    config_path = Path(f"config/personalities/{character_id}_character.json")

    if not config_path.exists():
        raise FileNotFoundError(f"No config found for {character_id} at {config_path}")

    with open(config_path) as f:
        config = json.load(f)
        number = config.get("number")

        if number is None:
            raise ValueError(f"Missing 'number' field in config for {character_id}")

        if not isinstance(number, int) or not (2 <= number <= 5):
            raise ValueError(f"Invalid number {number} for {character_id} (must be 2-5)")

        return number


def resolve_helpers_node(state: GameState) -> GameState:
    """
    Phase 1 Issue #2: Resolve all helping actions before main action.

    Helper Success Threshold:
    - Helper is "successful" if their roll achieves total_successes >= 1
    - Each successful helper grants +1d6 to the character they're helping
    - Failed helpers (0 successes) provide no bonus and no penalty

    Process:
    1. Identify primary actions (non-helping actions)
    2. For each primary character:
       a. Find all helpers targeting this character
       b. Validate helpers are targeting valid characters
       c. For each valid helper:
          - Load helper's character number from config
          - Build dice pool (helper's own prepared/expert bonuses apply)
          - Roll dice using roll_lasers_feelings() with successful_helpers=0
          - Check if total_successes >= 1 (threshold for successful help)
       d. Count successful helpers
       e. Store count in state.successful_helper_counts dict

    Args:
        state: Current game state with character_actions populated

    Returns:
        Updated state with:
        - successful_helper_counts: dict mapping character_id → helper count
        - current_phase: Set to DICE_RESOLUTION
        - phase_start_time: Updated to current time

    Raises:
        No exceptions - errors are logged and handled gracefully

    Notes:
        - Helpers use their own character_number (loaded from config)
        - Helpers do not receive helper bonuses themselves (successful_helpers=0)
        - Invalid helpers (nonexistent targets, config errors) are skipped with warnings
        - Helper roll failures are treated as 0 successes, not crashes
    """
    logger.info(f"[PHASE: RESOLVE_HELPERS] Turn {state['turn_number']}")

    character_actions = state.get("character_actions", {})

    # Initialize successful_helper_counts dict
    successful_helper_counts: dict[str, int] = {}

    # Identify primary actions (not helping others)
    primary_actions = {
        char_id: action
        for char_id, action in character_actions.items()
        if not action.get("is_helping", False)
    }

    logger.debug(f"Found {len(primary_actions)} primary actions")

    # For each primary action, find and process helpers
    for primary_char_id, primary_action in primary_actions.items():
        # Find all helpers for this primary character
        helpers = [
            action
            for action in character_actions.values()
            if (action.get("is_helping", False) and
                action.get("helping_character_id") == primary_char_id)
        ]

        if not helpers:
            # No helpers for this character
            successful_helper_counts[primary_char_id] = 0
            logger.debug(f"{primary_char_id} has no helpers")
            continue

        logger.debug(f"{primary_char_id} has {len(helpers)} helper(s)")

        # Validate all helpers before processing
        valid_helpers = []
        for helper_action in helpers:
            helper_char_id = helper_action.get("character_id", "unknown")
            target_char_id = helper_action.get("helping_character_id")

            # Check if target exists in primary actions
            if target_char_id not in primary_actions:
                logger.warning(
                    f"Helper {helper_char_id} targeting nonexistent character "
                    f"{target_char_id} - skipping this helper"
                )
                continue  # Skip invalid helper

            valid_helpers.append(helper_action)

        # Process only valid helpers
        helpers = valid_helpers
        if not helpers:
            successful_helper_counts[primary_char_id] = 0
            logger.debug(f"{primary_char_id} has no valid helpers after validation")
            continue

        logger.info(f"{primary_char_id} has {len(helpers)} valid helper(s)")

        # Roll for each helper and count successes
        successful_count = 0
        for helper_action in helpers:
            helper_char_id = helper_action.get("character_id", "unknown")

            # Extract helper's dice modifiers
            task_type = helper_action.get("task_type", "lasers")
            is_prepared = helper_action.get("is_prepared", False)
            is_expert = helper_action.get("is_expert", False)

            # Load helper's character number from config
            try:
                helper_character_number = _load_character_number(helper_char_id)
            except (FileNotFoundError, ValueError) as e:
                logger.warning(
                    f"Could not load character number for {helper_char_id}: {e}. "
                    f"Using fallback number 3 (balanced character)"
                )
                helper_character_number = 3

            # Roll dice for helper (with their own modifiers, no successful_helpers bonus)
            try:
                helper_roll_result = roll_lasers_feelings(
                    character_number=helper_character_number,
                    task_type=task_type,
                    is_prepared=is_prepared,
                    is_expert=is_expert,
                    successful_helpers=0  # Helpers don't get helper bonuses
                )

                # Check if helper succeeded (≥1 success)
                if helper_roll_result.total_successes >= 1:
                    successful_count += 1
                    logger.info(
                        f"Helper {helper_char_id} succeeded: "
                        f"{helper_roll_result.individual_rolls} → {helper_roll_result.total_successes} successes"
                    )
                else:
                    logger.info(
                        f"Helper {helper_char_id} failed: "
                        f"{helper_roll_result.individual_rolls} → 0 successes (no bonus)"
                    )
            except Exception as e:
                logger.error(
                    f"Helper {helper_char_id} roll failed with error: {e}. "
                    f"Treating as failed roll (0 successes)"
                )
                # Continue with next helper - don't crash the turn
                continue

        # Store successful helper count for this primary character
        successful_helper_counts[primary_char_id] = successful_count
        logger.info(f"{primary_char_id} has {successful_count} successful helper(s)")

    logger.debug(f"Successful helper counts: {successful_helper_counts}")

    return {
        **state,
        "successful_helper_counts": successful_helper_counts,
        "current_phase": GamePhase.DICE_RESOLUTION.value,
        "phase_start_time": datetime.now()
    }


def dice_resolution_node(state: GameState) -> GameState:
    """
    T053: Execute dice rolls using Lasers & Feelings multi-die system.

    Phase 2 Issue #3: Detects LASER FEELINGS (exact match) and pauses for GM question.

    Args:
        state: Current game state

    Returns:
        Updated state with dice roll result fields, or LASER_FEELINGS_QUESTION pause
    """
    logger.info(f"[PHASE: DICE_RESOLUTION] Turn {state['turn_number']}")

    # Get character ID from state (first active agent for single-agent MVP)
    character_id = state["active_agents"][0] if state["active_agents"] else None
    if not character_id:
        raise ValueError("No active agents found for dice resolution")

    # Map agent_id to character_id
    character_id = _get_character_id_for_agent(character_id)

    # Get character action to extract dice modifiers
    character_action_dict = state["character_actions"].get(character_id, {})

    # Extract action details
    task_type = character_action_dict.get("task_type", "lasers")
    is_prepared = character_action_dict.get("is_prepared", False)
    is_expert = character_action_dict.get("is_expert", False)
    is_helping = character_action_dict.get("is_helping", False)
    gm_question = character_action_dict.get("gm_question")

    # Get character number from config (MVP hardcoded)
    # TODO: Load from character config in full implementation
    character_number = 2  # Android Engineer (good at Lasers)

    # Get successful helper count from state (Phase 1 Issue #2)
    successful_helper_counts = state.get("successful_helper_counts", {})
    successful_helpers = successful_helper_counts.get(character_id, 0)

    # Perform Lasers & Feelings roll
    roll_result = roll_lasers_feelings(
        character_number=character_number,
        task_type=task_type,
        is_prepared=is_prepared,
        is_expert=is_expert,
        successful_helpers=successful_helpers,  # Phase 1 Issue #2: Use actual helper count
        gm_question=gm_question
    )

    # Log roll details
    logger.info(
        f"Dice resolution: {roll_result.individual_rolls} "
        f"({roll_result.dice_count}d6, prepared={is_prepared}, expert={is_expert}, helping={is_helping}) "
        f"vs number {character_number} ({task_type}) = "
        f"{roll_result.total_successes} successes → {roll_result.outcome.value.upper()}"
    )

    if roll_result.has_laser_feelings:
        logger.info(f"LASER FEELINGS! (rolled exact {character_number} on die(s) {roll_result.laser_feelings_indices})")

    # Phase 2 Issue #3: Check for LASER FEELINGS and pause for GM question
    if len(roll_result.laser_feelings_indices) > 0:
        logger.info(f"{character_id} rolled LASER FEELINGS on die {roll_result.laser_feelings_indices[0] + 1}")

        # Map roll result to state fields (same as normal flow for backward compatibility)
        dice_roll_result = {
            "character_number": roll_result.character_number,
            "task_type": roll_result.task_type,
            "is_prepared": roll_result.is_prepared,
            "is_expert": roll_result.is_expert,
            "is_helping": roll_result.is_helping,
            "individual_rolls": roll_result.individual_rolls,
            "die_successes": roll_result.die_successes,
            "laser_feelings_indices": roll_result.laser_feelings_indices,
            "total_successes": roll_result.total_successes,
            "outcome": roll_result.outcome.value,
            "timestamp": roll_result.timestamp
        }

        # Deprecated fields (backward compatibility)
        dice_result = roll_result.individual_rolls[0] if roll_result.individual_rolls else 0
        dice_success = roll_result.total_successes > 0
        dice_complication = roll_result.has_laser_feelings

        # Store original roll and action for potential modification
        return {
            **state,
            "current_phase": GamePhase.LASER_FEELINGS_QUESTION.value,
            # Store dice results (for backward compatibility with existing tests)
            "dice_roll_result": dice_roll_result,
            "dice_action_character": character_id,
            "dice_result": dice_result,
            "dice_success": dice_success,
            "dice_complication": dice_complication,
            # LASER FEELINGS specific data
            "laser_feelings_data": {
                "character_id": character_id,
                "original_action": character_action_dict,
                "original_roll": {
                    "character_number": roll_result.character_number,
                    "task_type": roll_result.task_type,
                    "is_prepared": roll_result.is_prepared,
                    "is_expert": roll_result.is_expert,
                    "is_helping": roll_result.is_helping,
                    "individual_rolls": roll_result.individual_rolls,
                    "die_successes": roll_result.die_successes,
                    "laser_feelings_indices": roll_result.laser_feelings_indices,
                    "total_successes": roll_result.total_successes,
                    "outcome": roll_result.outcome.value,
                    "timestamp": roll_result.timestamp
                },
                "gm_question": gm_question,
                "dice_parameters": {
                    "character_number": character_number,
                    "task_type": task_type,
                    "is_prepared": is_prepared,
                    "is_expert": is_expert,
                    "successful_helpers": successful_helpers
                }
            },
            "phase_start_time": datetime.now()
        }

    # No LASER FEELINGS - proceed with normal outcome
    # Map LasersFeelingRollResult to GameState fields
    # New fields (primary)
    dice_roll_result = {
        "character_number": roll_result.character_number,
        "task_type": roll_result.task_type,
        "is_prepared": roll_result.is_prepared,
        "is_expert": roll_result.is_expert,
        "is_helping": roll_result.is_helping,
        "individual_rolls": roll_result.individual_rolls,
        "die_successes": roll_result.die_successes,
        "laser_feelings_indices": roll_result.laser_feelings_indices,
        "total_successes": roll_result.total_successes,
        "outcome": roll_result.outcome.value,
        "timestamp": roll_result.timestamp
    }

    # Deprecated fields (backward compatibility)
    dice_result = roll_result.individual_rolls[0] if roll_result.individual_rolls else 0
    dice_success = roll_result.total_successes > 0
    dice_complication = roll_result.has_laser_feelings

    return {
        **state,
        # New fields (primary)
        "dice_roll_result": dice_roll_result,
        "dice_action_character": character_id,  # Store which character rolled
        # Deprecated fields (backward compatibility)
        "dice_result": dice_result,
        "dice_success": dice_success,
        "dice_complication": dice_complication,
        "current_phase": GamePhase.DM_OUTCOME.value,
        "phase_start_time": datetime.now()
    }


def laser_feelings_question_node(state: GameState) -> GameState:
    """
    Phase 2 Issue #3: Pause turn and wait for GM to answer character's LASER FEELINGS question.

    This is an interrupt point - the state machine will pause here until
    the DM provides an answer via the CLI.

    Args:
        state: Current game state with laser_feelings_data populated

    Returns:
        State with prompt for DM to answer question
    """
    laser_data = state.get("laser_feelings_data", {})
    character_id = laser_data.get("character_id", "unknown")
    gm_question = laser_data.get("gm_question", "No question provided")

    logger.info(f"LASER FEELINGS: {character_id} asks GM: {gm_question}")

    # This node just waits - the DM will trigger continuation via CLI
    return {
        **state,
        "waiting_for_gm_answer": True,
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

        # Route LASER FEELINGS answer to character if provided
        laser_feelings_answer = state.get("laser_feelings_answer")
        if laser_feelings_answer:
            # Get character ID from dice roll result
            character_id = state.get("dice_action_character")
            if not character_id:
                # Fallback: Get first active agent and map to character
                if state["active_agents"]:
                    agent_id = state["active_agents"][0]
                    character_id = _get_character_id_for_agent(agent_id)

            if character_id:
                logger.info(f"Routing LASER FEELINGS answer to {character_id}")
                router.add_message(
                    channel=MessageChannel.P2C,
                    from_agent="dm",
                    content=f"[LASER FEELINGS Insight]: {laser_feelings_answer}",
                    message_type=MessageType.DIRECTIVE,
                    phase=GamePhase.DM_OUTCOME.value,
                    turn_number=state["turn_number"],
                    to_agents=[character_id],
                    session_number=state.get("session_number")
                )
            else:
                logger.warning("Cannot route LASER FEELINGS answer: no character_id found")

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

            # Get prior action for context (extract narrative_text from Action dict)
            prior_action_dict = state["character_actions"].get(character_id, {})
            prior_action = prior_action_dict.get("narrative_text", "") if prior_action_dict else ""

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

            # Extract narrative_text from Reaction dict
            reaction_dict = job.result
            character_reactions[character_id] = reaction_dict.get("narrative_text", str(reaction_dict))

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


def check_laser_feelings(state: GameState) -> Literal["question", "outcome"]:
    """
    Conditional edge for LASER FEELINGS detection.

    Phase 2 Issue #3: Routes to laser_feelings_question if exact match detected,
    otherwise proceeds to dm_outcome.

    Args:
        state: Current game state

    Returns:
        Route key: "question" if LASER FEELINGS detected, "outcome" otherwise
    """
    if state["current_phase"] == GamePhase.LASER_FEELINGS_QUESTION.value:
        return "question"
    else:
        return "outcome"


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
    logger.error("[VALIDATION ESCALATE] Max retries exceeded, flagging for DM review")

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
    workflow.add_node("resolve_helpers", resolve_helpers_node)  # Phase 1 Issue #2
    workflow.add_node("dice_resolution", dice_resolution_node)
    workflow.add_node("laser_feelings_question", laser_feelings_question_node)  # Phase 2 Issue #3
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

    # Phase 1 Issue #2: Resolve helpers before dice resolution
    workflow.add_edge("dm_adjudication", "resolve_helpers")
    workflow.add_edge("resolve_helpers", "dice_resolution")

    # Phase 2 Issue #3: Conditional routing after dice_resolution
    # If LASER FEELINGS detected, pause for GM question
    # Otherwise proceed directly to outcome
    workflow.add_conditional_edges(
        "dice_resolution",
        check_laser_feelings,
        {
            "question": "laser_feelings_question",
            "outcome": "dm_outcome"
        }
    )

    workflow.add_edge("laser_feelings_question", "dm_outcome")  # After GM answers, proceed to outcome
    workflow.add_edge("dm_outcome", "character_reaction")
    workflow.add_edge("character_reaction", "memory_consolidation")

    # Memory consolidation ends turn
    workflow.add_edge("memory_consolidation", END)

    # T058: Compile with checkpointing and interrupt points
    # Interrupt before DM input phases to allow interactive CLI prompting
    # Phase 2 Issue #3: Add laser_feelings_question as interrupt point
    checkpointer = MemorySaver()
    app = workflow.compile(
        checkpointer=checkpointer,
        interrupt_before=["dm_adjudication", "laser_feelings_question", "dm_outcome"]
    )

    logger.info("Turn cycle state machine built successfully with interrupt points at dm_adjudication, laser_feelings_question, and dm_outcome")
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
            If interrupted, includes "awaiting_dm_input": True and "awaiting_phase"

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

            # Check if graph was interrupted (awaiting DM input)
            snapshot = self.graph.get_state(config)
            next_nodes = snapshot.next

            if next_nodes:
                # Graph is paused, awaiting DM input
                awaiting_phase = next_nodes[0] if next_nodes else None
                logger.info(f"Graph interrupted at {awaiting_phase}, awaiting DM input")

                return {
                    "turn_number": turn_number,
                    "phase_completed": result["current_phase"],
                    "success": True,
                    "awaiting_dm_input": True,
                    "awaiting_phase": awaiting_phase,
                    "strategic_intents": result.get("strategic_intents", {}),
                    "character_actions": result.get("character_actions", {}),
                    "session_number": session_number
                }

            # Extract turn result (turn completed fully)
            turn_result = {
                "turn_number": turn_number,
                "phase_completed": result["current_phase"],
                "success": True,
                "strategic_intents": result.get("strategic_intents", {}),
                "character_actions": result.get("character_actions", {}),
                "validation_warnings": [],  # TODO: Extract from validation state
                "consensus_state": result.get("consensus_state"),
                "awaiting_dm_input": False
            }

            logger.info(f"=== TURN {turn_number} COMPLETED SUCCESSFULLY ===")
            return turn_result

        except Exception as e:
            logger.error(f"Turn execution failed: {e}")
            raise

    def resume_turn_with_dm_input(
        self,
        session_number: int,
        dm_input_type: Literal["adjudication", "laser_feelings_answer", "outcome"],
        dm_input_data: dict
    ) -> dict:
        """
        Resume interrupted turn with DM input.

        Phase 2 Issue #3: Added "laser_feelings_answer" input type for LASER FEELINGS flow.

        Args:
            session_number: Session to resume
            dm_input_type: Type of DM input:
                - "adjudication": DM provides dice ruling
                - "laser_feelings_answer": DM answers LASER FEELINGS question (Phase 2 Issue #3)
                - "outcome": DM provides outcome narration
            dm_input_data: DM's input data:
                - For adjudication: {"needs_dice": bool, "dice_override": int | None, "laser_feelings_answer": str | None}
                - For laser_feelings_answer: {"answer": str}
                - For outcome: {"outcome_text": str, "laser_feelings_answer": str | None}

        Returns:
            TurnResult dict, possibly with another interruption

        Raises:
            ValueError: If session has no interrupted state
        """
        thread_id = f"session_{session_number}"
        config = {"configurable": {"thread_id": thread_id}}

        # Get current state
        snapshot = self.graph.get_state(config)
        if not snapshot.next:
            raise ValueError(f"Session {session_number} is not in an interrupted state")

        current_state = snapshot.values
        awaiting_phase = snapshot.next[0]

        logger.info(f"Resuming session {session_number} at {awaiting_phase} with {dm_input_type} input")

        # Update state based on DM input type
        if dm_input_type == "adjudication":
            # DM provided adjudication (needs dice? manual override?)
            current_state["dm_adjudication_needed"] = dm_input_data.get("needs_dice", True)
            if "dice_override" in dm_input_data:
                current_state["dice_override"] = dm_input_data["dice_override"]
            # If DM provided manual success/fail ruling, set dice_success flag
            if "manual_success" in dm_input_data:
                current_state["dice_success"] = dm_input_data["manual_success"]
            # Extract LASER FEELINGS answer if provided
            if "laser_feelings_answer" in dm_input_data:
                current_state["laser_feelings_answer"] = dm_input_data["laser_feelings_answer"]

        elif dm_input_type == "laser_feelings_answer":
            # Phase 2 Issue #3: DM answered LASER FEELINGS question
            current_state["laser_feelings_answer"] = dm_input_data["answer"]
            current_state["waiting_for_gm_answer"] = False
            # Transition to dm_outcome phase (skip re-roll for MVP)
            current_state["current_phase"] = GamePhase.DM_OUTCOME.value

        elif dm_input_type == "outcome":
            # DM provided outcome narration
            current_state["dm_outcome"] = dm_input_data["outcome_text"]
            # Extract LASER FEELINGS answer if provided during outcome phase
            if "laser_feelings_answer" in dm_input_data:
                current_state["laser_feelings_answer"] = dm_input_data["laser_feelings_answer"]

        else:
            raise ValueError(f"Invalid dm_input_type: {dm_input_type}")

        # Update graph state with DM input
        self.graph.update_state(config, current_state)

        # Resume execution
        try:
            result = self.graph.invoke(None, config=config)

            # Check if interrupted again
            snapshot = self.graph.get_state(config)
            next_nodes = snapshot.next

            if next_nodes:
                # Still interrupted, awaiting more DM input
                awaiting_phase = next_nodes[0]
                logger.info(f"Graph interrupted again at {awaiting_phase}, awaiting DM input")

                return {
                    "turn_number": result["turn_number"],
                    "phase_completed": result["current_phase"],
                    "success": True,
                    "awaiting_dm_input": True,
                    "awaiting_phase": awaiting_phase,
                    "strategic_intents": result.get("strategic_intents", {}),
                    "character_actions": result.get("character_actions", {}),
                    "session_number": session_number
                }

            # Turn completed
            logger.info(f"=== TURN {result['turn_number']} COMPLETED SUCCESSFULLY ===")
            return {
                "turn_number": result["turn_number"],
                "phase_completed": result["current_phase"],
                "success": True,
                "strategic_intents": result.get("strategic_intents", {}),
                "character_actions": result.get("character_actions", {}),
                "character_reactions": result.get("character_reactions", {}),
                "validation_warnings": [],
                "consensus_state": result.get("consensus_state"),
                "awaiting_dm_input": False
            }

        except Exception as e:
            logger.error(f"Turn resume failed: {e}")
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
