# ABOUTME: Memory retrieval and consolidation node handlers for turn cycle state machine.
# ABOUTME: Implements initial memory query, post-clarification memory re-query, and turn-end memory storage.

from datetime import datetime

from loguru import logger

from src.models.game_state import GamePhase, GameState


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
        "current_phase": GamePhase.DM_CLARIFICATION.value,
        "phase_start_time": datetime.now(),
    }


def second_memory_query_node(state: GameState) -> GameState:
    """
    Re-query memories after clarifications to capture memories triggered by Q&A.

    This is Option B from the design: After DM answers clarifying questions,
    players query memories again using both the original narration AND the
    clarifications as context. This catches cases where clarifications reveal
    new details (e.g., "Section 7") that trigger previously-missed memories.

    Args:
        state: Current game state

    Returns:
        Updated state with retrieved_memories_post_clarification populated

    Note:
        For Phase 3 MVP, returns empty memories to avoid breaking downstream phases.
        Full memory integration will be completed in Phase 3 memory tasks (T028-T037).

        In production, this would:
        1. Use enhanced_query_context to query Graphiti
        2. Retrieve memories that match clarification details (e.g., "Section 7")
        3. Merge with original retrieved_memories to avoid duplicates
    """
    logger.info(f"[PHASE: SECOND_MEMORY_QUERY] Turn {state['turn_number']}")

    # Build enhanced query context from narration + clarifications
    # This will be used when memory system is integrated
    base_narration = state["dm_narration"]

    # Fetch all OOC messages from dm_clarification phase
    # Note: router is read-only here, so we can access it directly
    # In full implementation, this would be injected via factory pattern
    # For MVP, we'll prepare the context but not use it yet
    clarification_text = ""
    clarification_messages_count = 0

    # Get clarification messages from state if available
    if "all_clarification_questions" in state:
        clarification_questions = state["all_clarification_questions"]
        clarification_messages_count = len(clarification_questions)
        clarification_text = "\n".join(
            [
                f"{q.get('agent_id', 'unknown')}: {q.get('question', '')}"
                for q in clarification_questions
            ]
        )

    enhanced_query_context = f"{base_narration}\n\nClarifications:\n{clarification_text}"

    logger.debug(
        f"Built enhanced query context with {clarification_messages_count} clarification messages "
        f"(context length: {len(enhanced_query_context)} chars)"
    )

    # MVP placeholder - return empty memories for all agents
    # TODO(Phase 3): Integrate with CorruptedTemporalMemory when memory system is ready
    retrieved_memories_post_clarification: dict[str, list[dict]] = {
        agent_id: [] for agent_id in state.get("active_agents", [])
    }

    logger.debug(
        f"Re-queried memories for {len(retrieved_memories_post_clarification)} agents "
        f"with clarification context (MVP: empty)"
    )

    return {
        **state,
        "retrieved_memories_post_clarification": retrieved_memories_post_clarification,
        "current_phase": GamePhase.STRATEGIC_INTENT.value,
        "phase_start_time": datetime.now(),
    }


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

    logger.debug(f"Consolidating memories for turn {state['turn_number']} (MVP: logged only)")

    # TODO: Uncomment when memory system is integrated
    # Collect turn events for memory storage
    # turn_events = {
    #     "turn_number": state["turn_number"],
    #     "dm_narration": state["dm_narration"],
    #     "strategic_intents": state["strategic_intents"],
    #     "character_actions": state["character_actions"],
    #     "dm_outcome": state.get("dm_outcome", ""),
    #     "character_reactions": state["character_reactions"],
    # }
    # memory_system.add_episode(
    #     session_number=state["session_number"],
    #     turn_number=state["turn_number"],
    #     events=turn_events
    # )

    return {
        **state,
        "current_phase": GamePhase.DM_NARRATION.value,  # Ready for next turn
        "turn_number": state["turn_number"] + 1,
        "phase_start_time": datetime.now(),
    }
