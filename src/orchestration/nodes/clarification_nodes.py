# ABOUTME: Clarifying question collection and DM answer wait node factories for multi-round Q&A.
# ABOUTME: Includes dm_narration entry point, collect and wait nodes for player questions.

from datetime import datetime

from loguru import logger
from rq import Queue
from rq.job import Job

from src.models.game_state import GamePhase, GameState
from src.models.messages import MessageChannel, MessageType
from src.orchestration.message_router import MessageRouter
from src.orchestration.nodes.helpers import JobFailedError, _poll_job_with_backoff

# Constants
MAX_CLARIFICATION_ROUNDS = 3  # Safety limit to prevent infinite loops


# ============================================================================
# Entry Point Node
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
        "phase_start_time": datetime.now(),
    }


# ============================================================================
# Clarification Node Factories
# ============================================================================


def _create_dm_clarification_collect_node(base_persona_queue: Queue, router: MessageRouter):
    """
    Factory for dm_clarification_collect_node - collects questions without interrupting.

    This node dispatches RQ jobs to collect clarifying questions from all players.
    If questions exist, routes to dm_clarification_wait (which interrupts).
    If no questions, proceeds to second_memory_query.

    Args:
        base_persona_queue: RQ Queue for base persona worker jobs
        router: MessageRouter for sending OOC messages

    Returns:
        Node function with captured dependencies
    """

    def dm_clarification_collect_node(state: GameState) -> GameState:
        """
        Collect clarifying questions from players (non-interrupting).

        Dispatches RQ jobs to all players to formulate questions.
        Routes questions to OOC channel.
        Returns state with phase set based on whether questions exist:
        - Questions exist: current_phase = DM_CLARIFICATION (routes to wait node)
        - No questions: current_phase = MEMORY_QUERY (skips wait node)
        """
        logger.info(f"[PHASE: DM_CLARIFICATION] Turn {state['turn_number']}")

        # Initialize clarification round tracking
        current_round = state.get("clarification_round", 1)
        logger.debug(f"Clarification round {current_round}/{MAX_CLARIFICATION_ROUNDS}")

        # Check max rounds exit condition
        if current_round > MAX_CLARIFICATION_ROUNDS:
            logger.info(
                f"Max clarification rounds ({MAX_CLARIFICATION_ROUNDS}) reached "
                "- proceeding to memory query"
            )
            return {
                **state,
                "current_phase": GamePhase.MEMORY_QUERY.value,
                "clarification_round": current_round,
                "phase_start_time": datetime.now(),
            }

        # Gather prior Q&A context from OOC channel
        prior_qa_context = router.get_ooc_messages_for_player(limit=100)
        prior_qa_this_turn = [
            msg
            for msg in prior_qa_context
            if (
                msg.phase == GamePhase.DM_CLARIFICATION.value
                and msg.turn_number == state["turn_number"]
            )
        ]

        logger.debug(f"Found {len(prior_qa_this_turn)} prior Q&A messages from this turn")

        # Dispatch RQ jobs to all players to formulate questions
        jobs: dict[str, Job] = {}
        for agent_id in state["active_agents"]:
            logger.debug(f"Dispatching clarifying question job for {agent_id}")

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

            # Convert prior Q&A messages to dicts for serialization
            prior_qa_dicts = [msg.model_dump() for msg in prior_qa_this_turn]

            job = base_persona_queue.enqueue(
                "src.workers.base_persona_worker.formulate_clarifying_question",
                args=(
                    agent_id,
                    state["dm_narration"],
                    state["retrieved_memories"].get(agent_id, []),
                    prior_qa_dicts,
                    placeholder_personality,
                    placeholder_character_number,
                ),
                job_timeout=30,
                result_ttl=300,
                failure_ttl=600,
            )
            jobs[agent_id] = job

        # Wait for all jobs to complete with polling
        questions: dict[str, dict | None] = {}
        for agent_id, job in jobs.items():
            logger.debug(f"Waiting for clarifying question from {agent_id}")

            # Block until complete with exponential backoff polling
            timeout = 35  # Slightly longer than job_timeout
            _poll_job_with_backoff(job, timeout)

            if job.is_failed:
                raise JobFailedError(
                    f"Clarifying question job failed for {agent_id}: {job.exc_info}"
                )

            # Validate question structure
            question_result = job.result
            if question_result is not None:
                if not isinstance(question_result, dict):
                    logger.error(f"Invalid question type from {agent_id}: {type(question_result)}")
                    questions[agent_id] = None
                elif "question" not in question_result:
                    logger.error(f"Missing 'question' key from {agent_id}: {question_result}")
                    questions[agent_id] = None
                else:
                    questions[agent_id] = question_result
            else:
                questions[agent_id] = None

        # Filter to agents with questions
        agents_with_questions = {agent_id: q for agent_id, q in questions.items() if q is not None}

        logger.debug(
            f"{len(agents_with_questions)}/{len(state['active_agents'])} agents have questions"
        )

        # Exit condition: No new questions
        if not agents_with_questions:
            logger.info(
                f"No new clarifying questions in round {current_round} "
                "- skipping wait, proceeding to memory query"
            )
            return {
                **state,
                # Skip to second memory query
                "current_phase": GamePhase.MEMORY_QUERY.value,
                "clarification_round": current_round,  # Track round even when skipping
                "phase_start_time": datetime.now(),
            }

        # Route questions to OOC channel
        for agent_id, question_data in agents_with_questions.items():
            router.add_message(
                channel=MessageChannel.OOC,
                from_agent=agent_id,
                content=question_data["question"],
                message_type=MessageType.DISCUSSION,
                phase=GamePhase.DM_CLARIFICATION.value,
                turn_number=state["turn_number"],
                session_number=state.get("session_number", 1),
            )
            logger.debug(f"Routed question from {agent_id} to OOC channel")

        # Track all questions across rounds for debugging/memory (immutable pattern)
        existing_questions = state.get("all_clarification_questions", [])
        new_questions = [
            {"round": current_round, "agent_id": agent_id, "question": question_data["question"]}
            for agent_id, question_data in agents_with_questions.items()
        ]
        all_questions = existing_questions + new_questions

        logger.info(
            f"Collected {len(agents_with_questions)} clarifying questions in round {current_round}"
        )

        # Questions exist - route to wait node
        return {
            **state,
            "all_clarification_questions": all_questions,  # Use the new list
            "clarifying_questions_this_round": agents_with_questions,
            "clarification_round": current_round,  # Track current round
            "current_phase": GamePhase.DM_CLARIFICATION.value,  # Routes to wait node
            "awaiting_dm_clarifications": True,
            "phase_start_time": datetime.now(),
        }

    return dm_clarification_collect_node


def _create_dm_clarification_wait_node(router: MessageRouter):
    """
    Factory for dm_clarification_wait_node - pauses for DM answers.

    This node is ONLY entered when questions exist. It's in interrupt_before
    to pause the graph and wait for DM to provide answers.

    After DM answers (via resume_turn_with_dm_input), the graph loops back
    to dm_clarification_collect to check for follow-up questions.

    Args:
        router: MessageRouter (not used, but kept for consistency)

    Returns:
        Node function
    """

    def dm_clarification_wait_node(state: GameState) -> GameState:
        """
        Pause and wait for DM to answer clarifying questions.

        This node does minimal work - it just ensures the graph pauses
        via interrupt_before. The actual answer routing happens in
        resume_turn_with_dm_input.

        After resume, the conditional edge routes back to collect node
        to check for follow-up questions.
        """
        current_round = state.get("clarification_round", 1)

        logger.info(f"[PHASE: DM_CLARIFICATION_WAIT] Round {current_round} - Paused for DM answers")

        # State is already set by collect node, just preserve it
        # The interrupt will happen before this node executes
        return {
            **state,
            "current_phase": GamePhase.DM_CLARIFICATION.value,  # Stay in clarification phase
            "phase_start_time": datetime.now(),
        }

    return dm_clarification_wait_node
