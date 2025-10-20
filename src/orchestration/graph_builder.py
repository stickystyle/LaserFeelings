# ABOUTME: LangGraph state machine builder for turn cycle orchestration with 15 phase handlers.
# ABOUTME: Constructs workflow graph with dependency injection, node instantiation, and conditional routing.

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph
from loguru import logger
from redis import Redis
from rq import Queue

from src.models.game_state import GameState
from src.orchestration.message_router import MessageRouter
from src.orchestration.nodes import (
    _create_character_action_node,
    _create_character_reaction_node,
    _create_dm_clarification_collect_node,
    _create_dm_clarification_wait_node,
    _create_dm_outcome_node,
    _create_p2c_directive_node,
    _create_strategic_intent_node,
    check_clarification_after_collect,
    check_clarification_after_wait,
    check_laser_feelings,
    dice_resolution_node,
    dm_adjudication_node,
    dm_narration_node,
    laser_feelings_question_node,
    memory_consolidation_node,
    memory_retrieval_node,
    resolve_helpers_node,
    rollback_handler_node,
    second_memory_query_node,
    validation_escalate_node,
    validation_retry_node,
)


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
    base_persona_queue = Queue("base_persona", connection=redis_client)
    character_queue = Queue("character", connection=redis_client)
    router = MessageRouter(redis_client)

    # Create node functions with injected dependencies (factory pattern)
    dm_clarification_collect_node = _create_dm_clarification_collect_node(
        base_persona_queue, router
    )
    dm_clarification_wait_node = _create_dm_clarification_wait_node(router)
    strategic_intent_node = _create_strategic_intent_node(base_persona_queue)
    p2c_directive_node = _create_p2c_directive_node(router)
    character_action_node = _create_character_action_node(character_queue, router)
    dm_outcome_node = _create_dm_outcome_node(router)
    character_reaction_node = _create_character_reaction_node(character_queue, router)

    # Initialize graph
    workflow = StateGraph(GameState)  # Use GameState TypedDict for schema

    # Add phase handler nodes (T047-T056)
    workflow.add_node("dm_narration", dm_narration_node)
    workflow.add_node("memory_retrieval", memory_retrieval_node)
    workflow.add_node(
        "dm_clarification_collect", dm_clarification_collect_node
    )  # Phase 2 Extension: collect questions
    workflow.add_node(
        "dm_clarification_wait", dm_clarification_wait_node
    )  # Phase 2 Extension: wait for DM answers
    workflow.add_node(
        "second_memory_query", second_memory_query_node
    )  # Re-query memories with clarification context
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

    # Memory retrieval → clarification collect
    workflow.add_edge("memory_retrieval", "dm_clarification_collect")

    # Conditional routing after collect:
    # - If questions exist: route to wait node (which interrupts)
    # - If no questions: skip to second_memory_query
    workflow.add_conditional_edges(
        "dm_clarification_collect",
        check_clarification_after_collect,
        {
            "wait": "dm_clarification_wait",  # Questions exist, pause for DM
            "skip": "second_memory_query",  # No questions, proceed automatically
        },
    )

    # Conditional routing after wait (after DM answers):
    # - Loop back to collect for follow-up questions
    # - Or proceed to memory query if max rounds reached
    workflow.add_conditional_edges(
        "dm_clarification_wait",
        check_clarification_after_wait,
        {
            "loop": "dm_clarification_collect",  # Check for follow-ups
            "proceed": "second_memory_query",  # Max rounds, exit clarification
        },
    )

    # Second memory query → strategic intent
    workflow.add_edge("second_memory_query", "strategic_intent")

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
        {"question": "laser_feelings_question", "outcome": "dm_outcome"},
    )

    # After LASER FEELINGS question answered, proceed to outcome
    workflow.add_edge("laser_feelings_question", "dm_outcome")
    workflow.add_edge("dm_outcome", "character_reaction")
    workflow.add_edge("character_reaction", "memory_consolidation")

    # Memory consolidation ends turn
    workflow.add_edge("memory_consolidation", END)

    # T058: Compile with checkpointing and interrupt points
    # Interrupt before DM input phases to allow interactive CLI prompting
    # Phase 2 Issue #3: Add laser_feelings_question as interrupt point
    # Phase 2 Extension: dm_clarification_wait is interrupt point (not collect)
    #   - collect node runs immediately after memory_retrieval (no interrupt)
    #   - If questions exist: collect routes to wait node
    #   - wait node is in interrupt_before to pause for DM input
    #   - DM provides answers via resume_turn (dm_clarification_answer)
    #   - Resume routes back to collect to check for follow-up questions
    #   - If no questions: collect skips directly to second_memory_query
    #   - Continues until no questions or max rounds reached
    #
    # ONLY interrupt at dm_clarification_wait (not collect)
    checkpointer = MemorySaver()
    app = workflow.compile(
        checkpointer=checkpointer,
        interrupt_before=[
            "dm_clarification_wait",
            "dm_adjudication",
            "laser_feelings_question",
            "dm_outcome",
        ],
    )

    logger.info(
        "Turn cycle state machine built successfully with interrupt points at dm_clarification_wait, dm_adjudication, laser_feelings_question, and dm_outcome"
    )
    return app
