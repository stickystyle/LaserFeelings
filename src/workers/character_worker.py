# ABOUTME: RQ worker functions for CharacterAgent (perform action, react to outcome).
# ABOUTME: Module-level functions run in separate processes with internal imports.

from typing import Any

from loguru import logger


def perform_action(
    character_id: str,
    directive: dict[str, Any],
    scene_context: str,
    character_sheet_config: dict[str, Any],
) -> dict[str, Any]:
    """
    RQ worker function: CharacterAgent performs in-character action based on directive.

    Worker pattern: Imports agent class inside function (runs in separate process).
    Uses exponential backoff for LLM calls via @llm_retry decorator.

    Args:
        character_id: Unique character identifier (e.g., 'char_zara_001')
        directive: Directive dict from BasePersonaAgent
            Keys: {from_player, to_character, instruction, tactical_guidance, emotional_tone}
        scene_context: Current scene description from DM
        character_sheet_config: Character sheet configuration dict with keys:
            {name, style, role, number, character_goal, equipment, speech_patterns,
            mannerisms, approach_bias}

    Returns:
        Action dict with full Pydantic model - character's in-character action attempt
        (intent only, no outcomes)

    Raises:
        RuntimeError: When character cannot be loaded or initialized
        ValidationFailed: When action contains narrative overreach
        LLMCallFailed: When OpenAI API fails after retries
    """
    # Import dependencies inside worker (separate process)
    import asyncio

    from openai import AsyncOpenAI

    from src.agents.character import CharacterAgent
    from src.config.settings import Settings
    from src.models.agent_actions import Directive
    from src.models.personality import CharacterSheet
    from src.workers.llm_retry import llm_retry

    try:
        # Load configuration
        settings = Settings()

        # Initialize OpenAI client
        openai_client = AsyncOpenAI(api_key=settings.openai_api_key)

        # Convert directive dict to Directive model
        directive_obj = Directive(**directive)

        # Load character sheet from configuration
        character_sheet = CharacterSheet(**character_sheet_config)

        # Initialize agent
        agent = CharacterAgent(
            character_id=character_id,
            character_sheet=character_sheet,
            openai_client=openai_client,
            model="gpt-4o",
            temperature=0.8,
        )

        # Call agent method with retry protection
        @llm_retry
        async def _perform() -> Any:
            return await agent.perform_action(
                directive=directive_obj,
                scene_context=scene_context,
            )

        # Run async function in event loop
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            action = loop.run_until_complete(_perform())
            return action.model_dump()
        finally:
            loop.close()

    except Exception as e:
        logger.error(f"Worker perform_action failed for {character_id}: {e}")
        raise


def react_to_outcome(
    character_id: str,
    outcome: str,
    prior_action: str,
    character_sheet_config: dict[str, Any],
) -> dict[str, Any]:
    """
    RQ worker function: CharacterAgent reacts to DM's outcome narration.

    Worker pattern: Imports agent class inside function (runs in separate process).
    Uses exponential backoff for LLM calls via @llm_retry decorator.

    Args:
        character_id: Unique character identifier
        outcome: DM's narration of what actually happened
        prior_action: Character's previous action (for context)
        character_sheet_config: Character sheet configuration dict with keys:
            {name, style, role, number, character_goal, equipment, speech_patterns,
            mannerisms, approach_bias}

    Returns:
        Reaction dict with full Pydantic model - character's in-character emotional response

    Raises:
        RuntimeError: When character cannot be loaded
        LLMCallFailed: When OpenAI API fails after retries
    """
    # Import dependencies inside worker (separate process)
    import asyncio

    from openai import AsyncOpenAI

    from src.agents.character import CharacterAgent
    from src.config.settings import Settings
    from src.models.agent_actions import EmotionalState
    from src.models.personality import CharacterSheet
    from src.workers.llm_retry import llm_retry

    try:
        # Load configuration
        settings = Settings()

        # Initialize OpenAI client
        openai_client = AsyncOpenAI(api_key=settings.openai_api_key)

        # Load character sheet from configuration
        character_sheet = CharacterSheet(**character_sheet_config)

        # Initialize agent
        agent = CharacterAgent(
            character_id=character_id,
            character_sheet=character_sheet,
            openai_client=openai_client,
            model="gpt-4o",
            temperature=0.8,
        )

        # Derive emotional state from outcome context (TODO: track state properly)
        # For now, use neutral emotional state
        emotional_state = EmotionalState(
            primary_emotion="neutral",
            intensity=0.5,
            secondary_emotions=[],  # Empty list instead of None
        )

        # Call agent method with retry protection
        @llm_retry
        async def _react() -> Any:
            return await agent.react_to_outcome(
                dm_narration=outcome,
                emotional_state=emotional_state,
            )

        # Run async function in event loop
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            reaction = loop.run_until_complete(_react())
            return reaction.model_dump()
        finally:
            loop.close()

    except Exception as e:
        logger.error(f"Worker react_to_outcome failed for {character_id}: {e}")
        raise
