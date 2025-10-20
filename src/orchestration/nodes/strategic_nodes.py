# ABOUTME: Strategic intent formulation and player-to-character directive node factories.
# ABOUTME: Contains LangGraph node factory functions for player-level strategic decision-making.

from datetime import datetime

from loguru import logger
from rq import Queue
from rq.job import Job

from src.models.game_state import GamePhase, GameState
from src.models.messages import MessageChannel, MessageType
from src.orchestration.message_router import MessageRouter
from src.orchestration.nodes.helpers import (
    JobFailedError,
    _get_character_id_for_agent,
    _poll_job_with_backoff,
)


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
                "base_decay_rate": 0.3,  # Low memory decay (good retention)
            }
            placeholder_character_number = 2  # Android Engineer (good at Lasers)

            job = base_persona_queue.enqueue(
                "src.workers.base_persona_worker.formulate_strategic_intent",
                args=(
                    agent_id,
                    state["dm_narration"],
                    state["retrieved_memories"].get(agent_id, []),
                    placeholder_personality,
                    placeholder_character_number,
                ),
                job_timeout=30,
                result_ttl=300,
                failure_ttl=600,
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
            "phase_start_time": datetime.now(),
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
                session_number=state.get("session_number"),
            )

            logger.debug(f"Sent P2C directive from {agent_id} to {character_id}")

        return {
            **state,
            "current_phase": GamePhase.CHARACTER_ACTION.value,
            "phase_start_time": datetime.now(),
        }

    return p2c_directive_node
