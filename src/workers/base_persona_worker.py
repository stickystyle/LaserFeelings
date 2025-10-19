# ABOUTME: RQ worker functions for BasePersonaAgent (OOC discussion, intent, directives).
# ABOUTME: Module-level functions run in separate processes with internal imports.

from typing import Any

from loguru import logger


def participate_in_ooc_discussion(
    agent_id: str,
    discussion_context: str,
    previous_messages: list[dict[str, Any]],
    personality_config: dict[str, Any],
) -> dict[str, Any]:
    """
    RQ worker function: BasePersonaAgent participates in out-of-character discussion.

    Worker pattern: Imports agent class inside function (runs in separate process).
    Uses exponential backoff for LLM calls via @llm_retry decorator.

    Args:
        agent_id: Unique agent identifier (e.g., 'agent_alex_001')
        discussion_context: Current DM narration or scene description
        previous_messages: List of previous OOC messages from other agents
            Each message dict has: {from_agent, content, timestamp, ...}
        personality_config: Personality configuration dict with keys:
            {decision_style, risk_tolerance, cooperativeness, analytical_score, roleplay_intensity}

    Returns:
        Message dict with full Pydantic model - agent's contribution to OOC discussion

    Raises:
        RuntimeError: When agent cannot be loaded or initialized
        LLMCallFailed: When OpenAI API fails after retries
        InvalidMessageFormat: When message creation fails
    """
    # Import dependencies inside worker (separate process)
    import asyncio

    from openai import AsyncOpenAI

    from src.agents.base_persona import BasePersonaAgent
    from src.config.settings import Settings
    from src.models.messages import Message
    from src.models.personality import PlayerPersonality
    from src.workers.llm_retry import llm_retry

    try:
        # Load configuration
        settings = Settings()

        # Initialize dependencies
        openai_client = AsyncOpenAI(api_key=settings.openai_api_key)

        # TODO(Phase 4): Accept memory as parameter from orchestration layer
        # For Phase 3 MVP, agents operate without memory to avoid connection pool exhaustion
        memory = None

        # Load agent personality from configuration
        personality = PlayerPersonality(**personality_config)

        # Initialize agent
        agent = BasePersonaAgent(
            agent_id=agent_id,
            personality=personality,
            memory=memory,
            openai_client=openai_client,
            model="gpt-4o",
            temperature=0.7,
        )

        # Convert previous_messages dicts to Message objects
        message_objects = []
        for msg_dict in previous_messages:
            try:
                msg = Message(**msg_dict)
                message_objects.append(msg)
            except Exception as e:
                logger.warning(f"Failed to parse message dict: {e}")
                continue

        # Call agent method with retry protection
        @llm_retry
        async def _participate() -> Message:
            return await agent.participate_in_ooc_discussion(
                dm_narration=discussion_context,
                other_messages=message_objects,
            )

        # Run async function in event loop
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            message = loop.run_until_complete(_participate())
            return message.model_dump()
        finally:
            loop.close()

    except Exception as e:
        logger.error(f"Worker participate_in_ooc_discussion failed for {agent_id}: {e}")
        raise


def formulate_strategic_intent(
    agent_id: str,
    scene_context: str,
    memories: list[dict[str, Any]],
    personality_config: dict[str, Any],
) -> dict[str, Any]:
    """
    RQ worker function: BasePersonaAgent formulates strategic intent from discussion.

    Worker pattern: Imports agent class inside function (runs in separate process).
    Uses exponential backoff for LLM calls via @llm_retry decorator.

    Args:
        agent_id: Unique agent identifier
        scene_context: Discussion summary or consensus from OOC phase
        memories: List of relevant memories to inform intent
            Each memory dict has: {fact, confidence, timestamp, ...}
        personality_config: Personality configuration dict with keys:
            {decision_style, risk_tolerance, cooperativeness, analytical_score, roleplay_intensity}

    Returns:
        Intent dict with keys: {agent_id, strategic_goal, reasoning, risk_assessment, fallback_plan}

    Raises:
        RuntimeError: When agent cannot be loaded
        NoConsensusReached: When discussion lacks clear direction
        LLMCallFailed: When OpenAI API fails after retries
    """
    # Import dependencies inside worker (separate process)
    import asyncio

    from openai import AsyncOpenAI

    from src.agents.base_persona import BasePersonaAgent
    from src.config.settings import Settings
    from src.models.personality import PlayerPersonality
    from src.workers.llm_retry import llm_retry

    try:
        # Load configuration
        settings = Settings()

        # Initialize OpenAI client
        openai_client = AsyncOpenAI(api_key=settings.openai_api_key)

        # Load agent personality from configuration
        personality = PlayerPersonality(**personality_config)

        # Initialize agent
        agent = BasePersonaAgent(
            agent_id=agent_id,
            personality=personality,
            openai_client=openai_client,
            model="gpt-4o",
            temperature=0.7,
        )

        # Call agent method with retry protection
        @llm_retry
        async def _formulate() -> Any:
            return await agent.formulate_strategic_intent(
                discussion_summary=scene_context,
            )

        # Run async function in event loop
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            intent = loop.run_until_complete(_formulate())
            # Convert Intent model to dict
            return intent.model_dump()
        finally:
            loop.close()

    except Exception as e:
        logger.error(f"Worker formulate_strategic_intent failed for {agent_id}: {e}")
        raise


def create_character_directive(
    agent_id: str,
    strategic_intent: dict[str, Any],
    personality_config: dict[str, Any],
) -> dict[str, Any]:
    """
    RQ worker function: BasePersonaAgent creates directive for character layer.

    Worker pattern: Imports agent class inside function (runs in separate process).
    Uses exponential backoff for LLM calls via @llm_retry decorator.

    Args:
        agent_id: Unique agent identifier
        strategic_intent: Intent dict from formulate_strategic_intent
            Keys: {agent_id, strategic_goal, reasoning, risk_assessment, fallback_plan}
        personality_config: Personality configuration dict with keys:
            {decision_style, risk_tolerance, cooperativeness, analytical_score, roleplay_intensity}

    Returns:
        Directive dict with keys:
        {from_player, to_character, instruction, tactical_guidance, emotional_tone}

    Raises:
        RuntimeError: When agent cannot be loaded
        CharacterNotFound: When character_id doesn't exist
        InvalidCharacterState: When character state is corrupted
        LLMCallFailed: When OpenAI API fails after retries
    """
    # Import dependencies inside worker (separate process)
    import asyncio

    from openai import AsyncOpenAI

    from src.agents.base_persona import BasePersonaAgent
    from src.config.settings import Settings
    from src.models.agent_actions import CharacterState, Intent
    from src.models.personality import PlayerPersonality
    from src.workers.llm_retry import llm_retry

    try:
        # Load configuration
        settings = Settings()

        # Initialize OpenAI client
        openai_client = AsyncOpenAI(api_key=settings.openai_api_key)

        # Load agent personality from configuration
        personality = PlayerPersonality(**personality_config)

        # Initialize agent
        agent = BasePersonaAgent(
            agent_id=agent_id,
            personality=personality,
            openai_client=openai_client,
            model="gpt-4o",
            temperature=0.7,
        )

        # Convert strategic_intent dict to Intent model
        intent = Intent(**strategic_intent)

        # Create character state (TODO: load from game state in future)
        # For now, derive character_id from agent_id
        if "_" in agent_id:
            character_id = f"char_{agent_id.split('_')[1]}_001"
        else:
            character_id = "char_unknown_001"

        character_state = CharacterState(
            character_id=character_id,
            current_location="Unknown",
            health_status="Normal",
            emotional_state="Neutral",
            active_effects=None,
        )

        # Call agent method with retry protection
        @llm_retry
        async def _create_directive() -> Any:
            return await agent.create_character_directive(
                intent=intent,
                character_state=character_state,
            )

        # Run async function in event loop
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            directive = loop.run_until_complete(_create_directive())
            # Convert Directive model to dict
            return directive.model_dump()
        finally:
            loop.close()

    except Exception as e:
        logger.error(f"Worker create_character_directive failed for {agent_id}: {e}")
        raise
