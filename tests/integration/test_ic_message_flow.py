# ABOUTME: Integration tests for IC message context flow through the system.
# ABOUTME: Verifies IC messages reach CharacterAgent prompts via MessageRouter, state machine, and worker layer.

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from openai import AsyncOpenAI
from redis import Redis
from rq import Queue

from src.agents.character import CharacterAgent
from src.config.settings import get_settings
from src.models.agent_actions import Directive
from src.models.game_state import GameState
from src.models.messages import MessageChannel, MessageType
from src.models.personality import CharacterRole, CharacterSheet, CharacterStyle
from src.orchestration.message_router import MessageRouter


@pytest.fixture
def redis_client():
    """
    Real Redis client for integration testing.

    Requires docker-compose services to be running.
    """
    settings = get_settings()
    client = Redis.from_url(settings.redis_url, decode_responses=False)

    # Verify connection
    try:
        client.ping()
    except Exception as e:
        pytest.skip(f"Redis not available: {e}")

    # Clean IC channel before test
    client.delete("channel:ic:messages")

    yield client

    # Cleanup after test
    client.delete("channel:ic:messages")
    client.close()


@pytest.fixture
def character_config_file(tmp_path):
    """Create Zara-7 character config file for testing"""
    config_dir = tmp_path / "config" / "personalities"
    config_dir.mkdir(parents=True, exist_ok=True)

    character_config = {
        "agent_id": "agent_alex_001",
        "character_id": "char_zara_001",
        "name": "Zara-7",
        "style": "Android",
        "role": "Engineer",
        "number": 2,
        "character_goal": "Protect the crew through technical excellence",
        "equipment": ["Advanced toolkit", "Repair drone"],
        "speech_patterns": ["Precise technical language"],
        "mannerisms": ["Tilts head when analyzing"],
        "approach_bias": "lasers"
    }

    config_file = config_dir / "char_zara_001_character.json"
    with open(config_file, "w") as f:
        json.dump(character_config, f)

    return config_file


def test_ic_messages_flow_through_state_machine_to_worker(
    redis_client,
    character_config_file,
    tmp_path,
    monkeypatch
):
    """
    Integration test: IC messages flow from MessageRouter through state machine node to worker.

    This tests the full system flow:
    1. IC messages are added to MessageRouter (stored in real Redis)
    2. State machine node fetches IC messages via MessageRouter
    3. State machine dispatches worker job with ic_messages parameter
    4. Worker calls CharacterAgent with ic_messages
    5. CharacterAgent includes IC messages in LLM prompt

    Verifies:
    - Real Redis is used for message storage
    - MessageRouter correctly stores and retrieves IC messages
    - State machine node fetches IC messages before dispatching worker
    - IC messages reach the LLM prompt with correct formatting
    - Only OpenAI API is mocked
    """
    # Change working directory to tmp_path so character config is found
    monkeypatch.chdir(tmp_path)

    # Arrange: Create router with REAL Redis and send IC messages
    router = MessageRouter(redis_client)

    # Send 3 IC messages from different sources
    router.add_message(
        channel=MessageChannel.IC,
        from_agent="char_zara_001",
        content="I attempt to repair the damaged console.",
        message_type=MessageType.ACTION,
        phase="character_action",
        turn_number=1,
        session_number=1
    )

    router.add_message(
        channel=MessageChannel.IC,
        from_agent="dm",
        content="The console sparks as Zara works on it.",
        message_type=MessageType.NARRATION,
        phase="dm_outcome",
        turn_number=1,
        session_number=1
    )

    router.add_message(
        channel=MessageChannel.IC,
        from_agent="char_thrain_002",
        content="I keep watch at the door, weapon ready.",
        message_type=MessageType.ACTION,
        phase="character_action",
        turn_number=1,
        session_number=1
    )

    # Verify messages were stored in real Redis
    stored_messages = router.get_messages_for_agent("char_zara_001", "character", limit=10)
    ic_stored = [msg for msg in stored_messages if msg.channel == MessageChannel.IC]
    assert len(ic_stored) == 3, "All 3 IC messages should be stored in real Redis"

    # Create a mock OpenAI client to capture prompts
    captured_prompts = []

    async def mock_llm_call(system_prompt, user_prompt, temperature=0.8, response_format=None):
        """Capture prompts sent to LLM"""
        captured_prompts.append({
            "system_prompt": system_prompt,
            "user_prompt": user_prompt,
            "temperature": temperature,
            "response_format": response_format
        })
        # Return a valid action response
        return json.dumps({
            "narrative_text": (
                "I tilt my head, analyzing the console's circuitry. "
                "I attempt to interface with the diagnostic port."
            ),
            "task_type": "lasers",
            "is_prepared": False,
            "is_expert": True,
            "expert_justification": "As an engineer, this is my specialty",
            "is_helping": False
        })

    # Mock the LLMClient at the module level (where worker imports it)
    with patch('src.agents.character.LLMClient') as mock_llm_client_class:
        mock_llm_instance = MagicMock()
        mock_llm_instance.call = AsyncMock(side_effect=mock_llm_call)
        mock_llm_client_class.return_value = mock_llm_instance

        # Mock AsyncOpenAI to prevent actual API calls
        with patch('src.agents.character.AsyncOpenAI') as mock_openai_class:
            mock_openai_client = MagicMock(spec=AsyncOpenAI)
            mock_openai_class.return_value = mock_openai_client

            # Act: Call worker function directly (simulating what state machine does)
            from src.workers.character_worker import perform_action

            character_id = "char_zara_001"

            directive = {
                "from_player": "agent_alex_001",
                "to_character": character_id,
                "instruction": "Repair the console",
                "tactical_guidance": "Be careful with the damaged circuits",
                "emotional_tone": "focused"
            }

            scene_context = "You are in the ship's engine room. The main console is damaged."

            character_sheet_config = {
                "name": "Zara-7",
                "style": "Android",
                "role": "Engineer",
                "number": 2,
                "character_goal": "Protect the crew through technical excellence",
                "equipment": ["Advanced toolkit", "Repair drone"],
                "speech_patterns": ["Precise technical language"],
                "mannerisms": ["Tilts head when analyzing"],
                "approach_bias": "lasers"
            }

            # Simulate state machine: Fetch IC messages before calling worker
            all_messages = router.get_messages_for_agent(character_id, "character", limit=10)
            ic_messages = [
                msg.model_dump()  # Serialize as state machine does
                for msg in all_messages
                if msg.channel == MessageChannel.IC
            ]

            # Execute worker function with ic_messages (as state machine does)
            action_result = perform_action(
                character_id=character_id,
                directive=directive,
                scene_context=scene_context,
                character_sheet_config=character_sheet_config,
                ic_messages=ic_messages  # Pass IC messages from router
            )

    # Assert: Verify IC messages reached the LLM prompt
    assert len(captured_prompts) > 0, "LLM should have been called at least once"

    # Get the user prompt that was sent to the LLM
    user_prompt = captured_prompts[0]["user_prompt"]

    # Verify the header is present
    assert "Recent events you've witnessed:" in user_prompt, \
        "Prompt should include IC message header"

    # Verify all 3 IC messages are present in the prompt
    assert "I attempt to repair the damaged console" in user_prompt, \
        "First IC message should be in prompt"

    assert "The console sparks" in user_prompt, \
        "Second IC message (DM narration) should be in prompt"

    assert "I keep watch at the door" in user_prompt, \
        "Third IC message (other character) should be in prompt"

    # Verify formatting: messages should be formatted as "- {from_agent}: {content}"
    assert "- char_zara_001:" in user_prompt, \
        "First message should be formatted with character ID"

    assert "- dm:" in user_prompt, \
        "DM message should be formatted correctly"

    assert "- char_thrain_002:" in user_prompt, \
        "Third message should be formatted with character ID"

    # Verify the action was successfully generated
    assert action_result is not None
    assert "narrative_text" in action_result
    assert len(action_result["narrative_text"]) > 0


def test_ic_messages_empty_when_none_present(
    redis_client,
    character_config_file,
    tmp_path,
    monkeypatch
):
    """
    Integration test: Character action works correctly when no IC messages present.

    Verifies:
    - Empty IC message list doesn't break character action
    - No IC message header in prompt when messages are empty
    - Action is still successfully generated
    """
    monkeypatch.chdir(tmp_path)

    # Arrange: Create router but don't send any IC messages
    router = MessageRouter(redis_client)

    # Verify no IC messages in Redis
    stored_messages = router.get_messages_for_agent("char_zara_001", "character", limit=10)
    ic_stored = [msg for msg in stored_messages if msg.channel == MessageChannel.IC]
    assert len(ic_stored) == 0, "Should be no IC messages"

    # Create mock OpenAI client
    captured_prompts = []

    async def mock_llm_call(system_prompt, user_prompt, temperature=0.8, response_format=None):
        captured_prompts.append({"user_prompt": user_prompt})
        return json.dumps({
            "narrative_text": "I examine the console.",
            "task_type": "lasers",
            "is_prepared": False,
            "is_expert": False,
            "is_helping": False
        })

    with patch('src.agents.character.LLMClient') as mock_llm_client_class:
        mock_llm_instance = MagicMock()
        mock_llm_instance.call = AsyncMock(side_effect=mock_llm_call)
        mock_llm_client_class.return_value = mock_llm_instance

        with patch('src.agents.character.AsyncOpenAI') as mock_openai_class:
            mock_openai_client = MagicMock(spec=AsyncOpenAI)
            mock_openai_class.return_value = mock_openai_client

            # Act: Call worker function
            from src.workers.character_worker import perform_action

            character_id = "char_zara_001"

            directive = {
                "from_player": "agent_alex_001",
                "to_character": character_id,
                "instruction": "Examine the console",
                "tactical_guidance": None,
                "emotional_tone": "curious"
            }

            scene_context = "You are in the engine room."

            character_sheet_config = {
                "name": "Zara-7",
                "style": "Android",
                "role": "Engineer",
                "number": 2,
                "character_goal": "Protect the crew",
                "equipment": ["Toolkit"],
                "speech_patterns": ["Precise language"],
                "mannerisms": ["Tilts head"],
                "approach_bias": "lasers"
            }

            # Fetch IC messages (should be empty)
            all_messages = router.get_messages_for_agent(character_id, "character", limit=10)
            ic_messages = [
                msg.model_dump()
                for msg in all_messages
                if msg.channel == MessageChannel.IC
            ]

            # Execute worker function
            action_result = perform_action(
                character_id=character_id,
                directive=directive,
                scene_context=scene_context,
                character_sheet_config=character_sheet_config,
                ic_messages=ic_messages
            )

    # Assert: Verify it worked without IC messages
    assert len(captured_prompts) > 0
    user_prompt = captured_prompts[0]["user_prompt"]

    # Should NOT have the IC message header when no messages
    assert "Recent events you've witnessed:" not in user_prompt, \
        "Should not include header when no IC messages"

    # Action should still be generated
    assert action_result is not None
    assert "narrative_text" in action_result


def test_ic_messages_filtered_from_mixed_channels(
    redis_client,
    character_config_file,
    tmp_path,
    monkeypatch
):
    """
    Integration test: Only IC messages are included in prompt, not OOC or P2C.

    Verifies:
    - Messages from different channels stored in real Redis
    - Only IC messages are fetched and included in prompt
    - OOC and P2C messages are not included in IC context
    """
    monkeypatch.chdir(tmp_path)

    # Arrange: Create router and send messages to different channels
    router = MessageRouter(redis_client)

    # Send IC message
    router.add_message(
        channel=MessageChannel.IC,
        from_agent="char_zara_001",
        content="I repair the console.",
        message_type=MessageType.ACTION,
        phase="character_action",
        turn_number=1,
        session_number=1
    )

    # Send OOC message (should NOT appear in IC context)
    router.add_message(
        channel=MessageChannel.OOC,
        from_agent="agent_alex_001",
        content="Let's coordinate our actions.",
        message_type=MessageType.DISCUSSION,
        phase="ooc_discussion",
        turn_number=1,
        session_number=1
    )

    # Send P2C message (should NOT appear in IC context)
    router.add_message(
        channel=MessageChannel.P2C,
        from_agent="agent_alex_001",
        content="Focus on technical solutions.",
        message_type=MessageType.DIRECTIVE,
        phase="p2c_directive",
        turn_number=1,
        to_agents=["char_zara_001"],
        session_number=1
    )

    # Verify all messages stored in real Redis
    all_stored = router.get_messages_for_agent("char_zara_001", "character", limit=10)
    assert len(all_stored) >= 1, "Should have at least IC message"

    # Verify filtering works
    ic_only = [msg for msg in all_stored if msg.channel == MessageChannel.IC]
    assert len(ic_only) == 1, "Should have exactly 1 IC message"

    captured_prompts = []

    async def mock_llm_call(system_prompt, user_prompt, temperature=0.8, response_format=None):
        captured_prompts.append({"user_prompt": user_prompt})
        return json.dumps({
            "narrative_text": "I work on the console.",
            "task_type": "lasers",
            "is_prepared": False,
            "is_expert": False,
            "is_helping": False
        })

    with patch('src.agents.character.LLMClient') as mock_llm_client_class:
        mock_llm_instance = MagicMock()
        mock_llm_instance.call = AsyncMock(side_effect=mock_llm_call)
        mock_llm_client_class.return_value = mock_llm_instance

        with patch('src.agents.character.AsyncOpenAI') as mock_openai_class:
            mock_openai_client = MagicMock(spec=AsyncOpenAI)
            mock_openai_class.return_value = mock_openai_client

            # Act: Call worker function
            from src.workers.character_worker import perform_action

            character_id = "char_zara_001"

            directive = {
                "from_player": "agent_alex_001",
                "to_character": character_id,
                "instruction": "Work on console",
                "tactical_guidance": None,
                "emotional_tone": "focused"
            }

            scene_context = "Engine room"

            character_sheet_config = {
                "name": "Zara-7",
                "style": "Android",
                "role": "Engineer",
                "number": 2,
                "character_goal": "Protect the crew",
                "equipment": ["Toolkit"],
                "speech_patterns": ["Precise"],
                "mannerisms": ["Analytical"],
                "approach_bias": "lasers"
            }

            # Fetch messages - filter to IC only (as state machine does)
            all_messages = router.get_messages_for_agent(character_id, "character", limit=10)
            ic_messages = [
                msg.model_dump()
                for msg in all_messages
                if msg.channel == MessageChannel.IC
            ]

            # Execute worker function
            perform_action(
                character_id=character_id,
                directive=directive,
                scene_context=scene_context,
                character_sheet_config=character_sheet_config,
                ic_messages=ic_messages
            )

    # Assert: Only IC messages should be in prompt
    user_prompt = captured_prompts[0]["user_prompt"]

    # IC message should be present
    assert "I repair the console" in user_prompt, \
        "IC message should be in prompt"

    # OOC and P2C should NOT be present
    assert "Let's coordinate our actions" not in user_prompt, \
        "OOC message should not be in prompt"

    assert "Focus on technical solutions" not in user_prompt, \
        "P2C message should not be in prompt (it's in directive, not IC history)"


def test_state_machine_node_fetches_ic_messages_before_worker_dispatch(
    redis_client,
    character_config_file,
    tmp_path,
    monkeypatch
):
    """
    Integration test: State machine node fetches IC messages before dispatching worker job.

    This tests the critical integration point where:
    1. State machine node calls MessageRouter.get_messages_for_agent()
    2. State machine filters to IC messages only
    3. State machine passes ic_messages to worker job

    Verifies:
    - State machine node factory creates proper node function
    - Node function fetches IC messages from router
    - Node function includes ic_messages in worker job parameters
    """
    monkeypatch.chdir(tmp_path)

    # Arrange: Create router with real Redis and send IC messages
    router = MessageRouter(redis_client)

    router.add_message(
        channel=MessageChannel.IC,
        from_agent="char_zara_001",
        content="I examine the control panel carefully.",
        message_type=MessageType.ACTION,
        phase="character_action",
        turn_number=1,
        session_number=1
    )

    router.add_message(
        channel=MessageChannel.IC,
        from_agent="dm",
        content="The panel flickers with warning lights.",
        message_type=MessageType.NARRATION,
        phase="dm_outcome",
        turn_number=1,
        session_number=1
    )

    # Create mock RQ queue to capture job parameters
    mock_queue = MagicMock(spec=Queue)
    dispatched_jobs = []

    def mock_enqueue(func, *args, **kwargs):
        """Capture job parameters"""
        job = MagicMock()
        job.id = "test_job_123"
        job.is_failed = False

        # Capture what was passed to the worker
        dispatched_jobs.append({
            "func": func,
            "args": args,
            "kwargs": kwargs
        })

        # Return mock result
        job.result = {
            "character_id": "char_zara_001",
            "narrative_text": "Test action",
            "task_type": "lasers",
            "is_prepared": False,
            "is_expert": False,
            "is_helping": False
        }
        return job

    mock_queue.enqueue = MagicMock(side_effect=mock_enqueue)

    # Act: Create state machine node using factory
    from src.orchestration.nodes.action_nodes import _create_character_action_node

    character_action_node = _create_character_action_node(mock_queue, router)

    # Create a GameState with all required fields
    from datetime import datetime

    game_state: GameState = {
        "current_phase": "character_action",
        "phase_start_time": datetime.now(),
        "turn_number": 1,
        "session_number": 1,
        "dm_narration": "You see a control panel.",
        "dm_adjudication_needed": False,
        "active_agents": ["agent_alex_001"],
        "strategic_intents": {
            "agent_alex_001": {
                "agent_id": "agent_alex_001",
                "strategic_goal": "Examine the panel",
                "reasoning": "Test reasoning",
                "risk_assessment": "Low",
                "fallback_plan": "Test fallback"
            }
        },
        "ooc_messages": [],
        "character_actions": {},
        "character_reactions": {},
        "validation_attempt": 0,
        "validation_valid": True,
        "validation_failures": {},
        "retrieved_memories": {},
        "retry_count": 0
    }

    # Execute the node (this should fetch IC messages and dispatch worker)
    result_state = character_action_node(game_state)

    # Assert: Verify worker job was dispatched with ic_messages parameter
    assert len(dispatched_jobs) == 1, "Should have dispatched one worker job"

    dispatched = dispatched_jobs[0]

    # The worker function path is the first positional arg, actual worker args are in kwargs["args"]
    assert "args" in dispatched["kwargs"], "Should have 'args' in kwargs"

    # ic_messages is the 5th element in the worker args tuple
    # worker args = (character_id, directive, scene_context, character_sheet, ic_messages)
    worker_args = dispatched["kwargs"]["args"]
    assert len(worker_args) == 5, f"Should have 5 worker arguments, got {len(worker_args)}"

    ic_messages_param = worker_args[4]
    assert ic_messages_param is not None, "ic_messages should not be None"
    assert isinstance(ic_messages_param, list), "ic_messages should be a list"
    assert len(ic_messages_param) == 2, "Should have 2 IC messages"

    # Verify IC messages content
    message_contents = [msg["content"] for msg in ic_messages_param]
    assert "I examine the control panel carefully" in message_contents[0]
    assert "The panel flickers with warning lights" in message_contents[1]

    # Verify both messages are IC channel
    for msg in ic_messages_param:
        assert msg["channel"] == "in_character", "All messages should be IC channel"

    # Verify state was updated
    assert "char_zara_001" in result_state["character_actions"], \
        "State should include character action result"
