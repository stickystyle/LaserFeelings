# ABOUTME: TurnOrchestrator class for executing turn cycles with DM input handling and phase control.
# ABOUTME: Provides high-level interface for turn execution, interruption, and resumption with DM interaction.

from datetime import datetime
from typing import Literal

from loguru import logger
from redis import Redis

from src.models.game_state import GamePhase, GameState
from src.models.messages import MessageChannel, MessageType
from src.orchestration.graph_builder import build_turn_graph
from src.orchestration.message_router import MessageRouter


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
        self, dm_input: str, active_agents: list[str], turn_number: int = 1, session_number: int = 1
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
            PhaseTransitionFailed: When state machine cannot proceed
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
                    "session_number": session_number,
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
                "awaiting_dm_input": False,
            }

            logger.info(f"=== TURN {turn_number} COMPLETED SUCCESSFULLY ===")
            return turn_result

        except Exception as e:
            logger.error(f"Turn execution failed: {e}")
            raise

    def resume_turn_with_dm_input(
        self,
        session_number: int,
        dm_input_type: Literal[
            "dm_clarification_answer", "adjudication", "laser_feelings_answer", "outcome"
        ],
        dm_input_data: dict,
    ) -> dict:
        """
        Resume interrupted turn with DM input.

        Phase 2 Issue #3: Added "laser_feelings_answer" input type for LASER FEELINGS flow.
        Phase 2 Extension: Added "dm_clarification_answer" for clarifying questions flow.

        Args:
            session_number: Session to resume
            dm_input_type: Type of DM input:
                - "dm_clarification_answer": DM answers clarifying questions (Phase 2 Extension)
                - "adjudication": DM provides dice ruling
                - "laser_feelings_answer": DM answers LASER FEELINGS question (Phase 2 Issue #3)
                - "outcome": DM provides outcome narration
            dm_input_data: DM's input data:
                - For dm_clarification_answer: {"answers": list[dict]} where each dict has {"agent_id": str, "answer": str}
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

        logger.info(
            f"Resuming session {session_number} at {awaiting_phase} with {dm_input_type} input"
        )

        # Update state based on DM input type
        if dm_input_type == "dm_clarification_answer":
            # Route DM answers to OOC channel
            answers = dm_input_data.get("answers", [])
            force_finish = dm_input_data.get("force_finish", False)

            for answer_dict in answers:
                agent_id = answer_dict.get("agent_id")
                answer_text = answer_dict.get("answer")
                self.router.add_message(
                    channel=MessageChannel.OOC,
                    from_agent="dm",
                    content=f"[Answer to {agent_id}]: {answer_text}",
                    message_type=MessageType.NARRATION,
                    phase=GamePhase.DM_CLARIFICATION.value,
                    turn_number=current_state["turn_number"],
                    session_number=session_number,
                )

            # Get MAX_CLARIFICATION_ROUNDS from the node (should be 3)
            MAX_CLARIFICATION_ROUNDS = 3

            # Handle force_finish by setting round beyond max
            current_round = current_state.get("clarification_round", 1)
            if force_finish:
                logger.info("DM requested force finish - skipping remaining clarification rounds")
                current_state["clarification_round"] = MAX_CLARIFICATION_ROUNDS + 1  # Force exit
            else:
                current_state["clarification_round"] = current_round + 1

            current_state["awaiting_dm_clarifications"] = False

            # Keep phase as DM_CLARIFICATION so conditional edge loops back to collect
            # The collect node will check for follow-up questions (or exit if max rounds)

        elif dm_input_type == "adjudication":
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
            # After LASER FEELINGS answer, proceed to outcome narration with the original successful action
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
                    "session_number": session_number,
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
                "awaiting_dm_input": False,
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
            PhaseTransitionFailed: If transition is not allowed from current phase
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
            "message": f"Transitioned to {target_phase} (MVP: not persisted)",
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

        logger.warning(
            f"[ROLLBACK] Rolling back session {session_number} to {target_phase}: {error_context}"
        )

        # TODO: Restore from checkpoint
        # TODO: Update phase and error context
        # TODO: Save checkpoint

        # For MVP, return placeholder
        return {
            "success": True,
            "session_number": session_number,
            "current_phase": target_phase,
            "error_context": error_context,
            "message": f"Rolled back to {target_phase} (MVP: not persisted)",
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

        logger.debug(
            f"[VALIDATION] Checking if {agent_id} can perform {action_type} in {current_phase}"
        )

        # TODO: Implement phase-based permission enforcement
        # For MVP, allow all actions
        return {
            "allowed": True,
            "agent_id": agent_id,
            "action_type": action_type,
            "current_phase": current_phase,
            "reason": "MVP: all actions allowed",
        }
