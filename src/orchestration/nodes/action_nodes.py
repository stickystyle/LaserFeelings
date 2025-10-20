# ABOUTME: Character action performance and reaction node factories for in-character roleplay.
# ABOUTME: Implements RQ worker dispatch for CharacterAgent.perform_action() and react_to_outcome().

from datetime import datetime

from loguru import logger
from rq import Queue
from rq.job import Job

from src.models.game_state import GamePhase, GameState
from src.models.messages import MessageChannel
from src.orchestration.message_router import MessageRouter
from src.orchestration.nodes.helpers import (
    JobFailedError,
    _get_character_id_for_agent,
    _poll_job_with_backoff,
)


def _create_character_action_node(character_queue: Queue, router: MessageRouter):
    """
    Factory for character_action_node with injected dependencies.

    Args:
        character_queue: RQ Queue for character worker jobs
        router: MessageRouter for fetching IC messages

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

        # Compute all character IDs for helping mechanic validation
        all_character_ids = [
            _get_character_id_for_agent(agent_id)
            for agent_id in state["active_agents"]
        ]

        # Dispatch jobs for each character
        jobs: dict[str, Job] = {}
        for agent_id in state["active_agents"]:
            # Map agent_id to character_id using helper
            character_id = _get_character_id_for_agent(agent_id)

            logger.debug(f"Dispatching character action job for {character_id}")

            # Fetch recent IC messages for character context with error handling
            try:
                all_messages = router.get_messages_for_agent(character_id, "character", limit=10)
                ic_messages = [
                    msg.model_dump()  # Preserve all message fields
                    for msg in all_messages
                    if msg.channel == MessageChannel.IC
                ]
            except Exception as e:
                logger.warning(
                    f"Failed to fetch IC messages for {character_id}: {e}. "
                    "Proceeding with empty message context."
                )
                ic_messages = []

            # Get strategic intent and transform to directive format
            # TODO: In full implementation, call BasePersonaAgent.create_character_directive()
            # For MVP, transform Intent dict to Directive dict
            strategic_intent = state["strategic_intents"][agent_id]
            directive = {
                "from_player": agent_id,
                "to_character": character_id,
                "instruction": strategic_intent.get("strategic_goal", ""),
                "tactical_guidance": strategic_intent.get("reasoning", ""),
                "emotional_tone": "focused",  # Default for MVP
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
                "approach_bias": "technical_solutions",
            }

            job = character_queue.enqueue(
                "src.workers.character_worker.perform_action",
                args=(
                    character_id,
                    directive,
                    scene_context,
                    placeholder_character_sheet,
                    ic_messages,
                    all_character_ids,
                ),
                job_timeout=30,
                result_ttl=300,
                failure_ttl=600,
            )
            jobs[character_id] = job

        # Wait for all jobs to complete
        for character_id, job in jobs.items():
            logger.debug(f"Waiting for character action from {character_id}")

            timeout = 35
            _poll_job_with_backoff(job, timeout)

            if job.is_failed:
                raise JobFailedError(
                    f"Character action job failed for {character_id}: {job.exc_info}"
                )

            # Store full Action dict (not just narrative_text)
            action_dict = job.result
            character_actions[character_id] = action_dict

        logger.info(f"Collected character actions from {len(character_actions)} characters")

        return {
            **state,
            "character_actions": character_actions,
            "current_phase": GamePhase.VALIDATION.value,
            "validation_attempt": 1,
            "phase_start_time": datetime.now(),
        }

    return character_action_node


def _create_character_reaction_node(character_queue: Queue, router: MessageRouter):
    """
    Factory for character_reaction_node with injected dependencies.

    Args:
        character_queue: RQ Queue for character worker jobs
        router: MessageRouter for fetching IC messages

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

            # Fetch recent IC messages for character context with error handling
            try:
                all_messages = router.get_messages_for_agent(character_id, "character", limit=10)
                ic_messages = [
                    msg.model_dump()  # Preserve all message fields
                    for msg in all_messages
                    if msg.channel == MessageChannel.IC
                ]
            except Exception as e:
                logger.warning(
                    f"Failed to fetch IC messages for {character_id}: {e}. "
                    "Proceeding with empty message context."
                )
                ic_messages = []

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
                "approach_bias": "technical_solutions",
            }

            job = character_queue.enqueue(
                "src.workers.character_worker.react_to_outcome",
                args=(
                    character_id,
                    state["dm_outcome"],
                    prior_action,
                    placeholder_character_sheet,
                    ic_messages,
                ),
                job_timeout=30,
                result_ttl=300,
                failure_ttl=600,
            )
            jobs[character_id] = job

        # Wait for all jobs to complete
        for character_id, job in jobs.items():
            logger.debug(f"Waiting for character reaction from {character_id}")

            timeout = 35
            _poll_job_with_backoff(job, timeout)

            if job.is_failed:
                raise JobFailedError(
                    f"Character reaction job failed for {character_id}: {job.exc_info}"
                )

            # Extract narrative_text from Reaction dict
            reaction_dict = job.result
            character_reactions[character_id] = reaction_dict.get(
                "narrative_text", str(reaction_dict)
            )

        logger.info(f"Collected character reactions from {len(character_reactions)} characters")

        return {
            **state,
            "character_reactions": character_reactions,
            "current_phase": GamePhase.MEMORY_STORAGE.value,
            "phase_start_time": datetime.now(),
        }

    return character_reaction_node
