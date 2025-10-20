# ABOUTME: Shared pytest fixtures for all test modules (unit, integration, contract, e2e).
# ABOUTME: Provides mock clients, test data, and common test utilities.

from datetime import datetime, timedelta
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.models.game_state import GameState
from src.models.messages import Message, MessageChannel

# Core models (these exist in Phase 2)
from src.models.personality import CharacterRole, CharacterSheet, CharacterStyle, PlayerPersonality


# --- Helper Functions ---

def make_action_dict(
    character_id: str,
    narrative_text: str,
    task_type: str | None = None,
    is_prepared: bool = False,
    prepared_justification: str | None = None,
    is_expert: bool = False,
    expert_justification: str | None = None,
    is_helping: bool = False,
    helping_character_id: str | None = None,
    help_justification: str | None = None
) -> dict[str, Any]:
    """Helper to create ActionDict-compatible dictionaries for test fixtures"""
    return {
        "character_id": character_id,
        "narrative_text": narrative_text,
        "task_type": task_type,
        "is_prepared": is_prepared,
        "prepared_justification": prepared_justification,
        "is_expert": is_expert,
        "expert_justification": expert_justification,
        "is_helping": is_helping,
        "helping_character_id": helping_character_id,
        "help_justification": help_justification
    }


# --- Personality and Character Fixtures ---

@pytest.fixture
def standard_personality() -> PlayerPersonality:
    """Standard balanced personality for testing"""
    return PlayerPersonality(
        analytical_score=0.7,
        risk_tolerance=0.5,
        detail_oriented=0.6,
        emotional_memory=0.4,
        assertiveness=0.6,
        cooperativeness=0.7,
        openness=0.7,
        rule_adherence=0.7,
        roleplay_intensity=0.8,
        base_decay_rate=0.5
    )


@pytest.fixture
def high_detail_personality() -> PlayerPersonality:
    """High detail-oriented personality (good memory retention)"""
    return PlayerPersonality(
        analytical_score=0.8,
        risk_tolerance=0.4,
        detail_oriented=0.9,
        emotional_memory=0.3,
        assertiveness=0.5,
        cooperativeness=0.7,
        openness=0.6,
        rule_adherence=0.8,
        roleplay_intensity=0.7,
        base_decay_rate=0.3  # Low decay
    )


@pytest.fixture
def risk_taker_personality() -> PlayerPersonality:
    """Risk-taking personality (high risk tolerance, low rule adherence)"""
    return PlayerPersonality(
        analytical_score=0.5,
        risk_tolerance=0.9,
        detail_oriented=0.4,
        emotional_memory=0.6,
        assertiveness=0.8,
        cooperativeness=0.5,
        openness=0.9,
        rule_adherence=0.4,
        roleplay_intensity=0.9,
        base_decay_rate=0.6
    )


@pytest.fixture
def explorer_character() -> CharacterSheet:
    """Standard explorer character (balanced lasers/feelings)"""
    return CharacterSheet(
        name="Kai Nova",
        style=CharacterStyle.INTREPID,
        role=CharacterRole.EXPLORER,
        number=3,  # Balanced
        character_goal="Discover ancient ruins and map the unknown",
        equipment=["Scanner", "Grappling hook", "Field journal"],
        speech_patterns=["Enthusiastic", "Uses explorer jargon", "Speaks in present tense"],
        mannerisms=["Points at interesting details", "Sketches while talking"]
    )


@pytest.fixture
def scientist_character() -> CharacterSheet:
    """Scientist character (lasers-oriented, number=2)"""
    return CharacterSheet(
        name="Lyra Chen",
        style=CharacterStyle.SAVVY,
        role=CharacterRole.SCIENTIST,
        number=2,  # Lasers-oriented
        character_goal="Catalog all alien species encountered",
        equipment=["Tricorder", "Sample kit", "Lab tablet"],
        speech_patterns=["Precise language", "Scientific terms", "Questioning tone"],
        mannerisms=["Takes notes constantly", "Peers intently at subjects"]
    )


@pytest.fixture
def diplomat_character() -> CharacterSheet:
    """Diplomat character (feelings-oriented, number=5)"""
    return CharacterSheet(
        name="Ambassador Trell",
        style=CharacterStyle.SMOOTH,
        role=CharacterRole.DIPLOMAT,
        number=5,  # Feelings-oriented
        character_goal="Establish peaceful relations with all sentient species",
        equipment=["Universal translator", "Diplomatic credentials", "Gift collection"],
        speech_patterns=["Formal address", "Empathetic phrasing", "Conflict de-escalation"],
        mannerisms=["Open body language", "Maintains eye contact", "Graceful gestures"]
    )


# --- Mock Client Fixtures ---

@pytest.fixture
def mock_openai_client():
    """Mock OpenAI client with contextual responses based on prompt"""
    import json
    client = MagicMock()

    def dynamic_response(*args, **kwargs):
        """Return contextual LLM responses based on input"""
        messages = kwargs.get("messages", [])
        # Combine all message content for better matching
        all_content = " ".join([msg.get("content", "") for msg in messages])
        last_content = all_content.lower()

        # Return contextual responses based on prompt content
        # Check for specific JSON response formats first - ORDER MATTERS!
        # Most specific checks first, then more general ones
        if ("narrative_text" in last_content and "your current emotional state" in last_content or "primary emotion" in last_content or "dm narration" in last_content) and "json" in last_content:
            # Reaction to outcome - context-aware responses
            narrative_text = "Fascinating. The readings are quite unusual. 'Well I'll be, lad. Never seen anything quite like this.'"

            if "explosion" in last_content or "fear" in last_content:
                narrative_text = "The ship lurches violently and I grab onto the console for support. 'By the stars!' I exclaim, my voice tense. 'We need to stabilize the ship immediately!'"
            elif "machinery" in last_content or "joy" in last_content:
                narrative_text = "A satisfied smile spreads across my face as the systems hum to life. 'Excellent!' I say with pride. 'Just as I calculated, lad.'"
            elif "goblin" in last_content or "relief" in last_content or "neutral" in last_content:
                narrative_text = "I let out a breath I didn't know I was holding. 'Well,' I mutter, 'that's one less problem to worry about.'"
            elif "corridor" in last_content or "surprise" in last_content:
                narrative_text = "I peer down the long corridor with curiosity. 'Interesting,' I say quietly. 'Let's see what lies ahead. I want to proceed cautiously.'"

            content = json.dumps({
                "character_id": "char_thrain",
                "narrative_text": narrative_text
            })
        elif "strategic_goal" in last_content and "json" in last_content:
            # Intent formulation
            content = json.dumps({
                "agent_id": "agent_test",
                "strategic_goal": "Carefully assess the situation and proceed cautiously",
                "reasoning": "Given the unknown factors, a cautious approach minimizes risk",
                "risk_assessment": "Moderate risk due to unknown threats",
                "fallback_plan": "Retreat if situation becomes too dangerous"
            })
        elif ("from_player" in last_content or "to_character" in last_content or "instruction" in last_content) and "json" in last_content:
            # Directive creation - extract context from the prompt
            instruction_text = "Investigate the area carefully"
            emotion_tone = "cautious"

            # Try to extract actual intent from prompt
            if "intimidate" in last_content:
                instruction_text = "Attempt to intimidate them with your presence and authority"
                emotion_tone = "confident"
            elif "comfort" in last_content:
                instruction_text = "Offer reassurance and support"
                emotion_tone = "compassionate"

            content = json.dumps({
                "from_player": "agent_test",
                "to_character": "char_thrain",
                "instruction": instruction_text,
                "emotional_tone": emotion_tone
            })
        elif "narrative_text" in last_content and "scene" in last_content and "json" in last_content:
            # Action performance - now uses narrative_text field
            content = json.dumps({
                "character_id": "char_thrain",
                "narrative_text": "I tap my fingers on the tricorder while waiting for results. 'Let me check these readings, lad,' I say, attempting to scan the area for signs of life."
            })
        elif "strategic" in last_content or "intent" in last_content:
            content = "Carefully examine the situation before acting. Assess risks."
        elif "directive" in last_content or "character" in last_content:
            content = "Use your scanner to gather information about the area."
        elif "action" in last_content or "perform" in last_content:
            content = "I attempt to scan the area with my tricorder, looking for signs of life."
        elif "react" in last_content or "outcome" in last_content:
            content = "Fascinating. The readings suggest an unusual energy signature."
        elif "validate" in last_content or "check" in last_content:
            content = json.dumps({"is_valid": True, "issues": []})
        elif "consensus" in last_content:
            content = json.dumps({"stance": "agree", "rationale": "Logical approach"})
        else:
            content = "Acknowledged. Proceeding with analysis."

        return MagicMock(
            choices=[MagicMock(message=MagicMock(content=content))],
            model="gpt-4o",
            usage=MagicMock(total_tokens=150, prompt_tokens=75, completion_tokens=75)
        )

    client.chat.completions.create = AsyncMock(side_effect=dynamic_response)
    return client


@pytest.fixture
def mock_graphiti_client():
    """Mock GraphitiClient for testing without Neo4j/OpenAI"""
    from src.memory.graphiti_client import GraphitiClient

    client = MagicMock(spec=GraphitiClient)

    # Configure async methods for GraphitiClient
    client.create_session_episode = AsyncMock(return_value="episode_123")
    client.query_memories_at_time = AsyncMock(return_value=[])
    client.extract_entities = AsyncMock(return_value=[])
    client.initialize = AsyncMock(return_value={
        "success": True,
        "version": "0.3.0",
        "indexes_created": ["agent_session_temporal", "valid_at_range"]
    })
    client.create_indexes = AsyncMock(return_value={
        "indexes_created": ["agent_session_temporal", "valid_at_range"]
    })
    client.close = AsyncMock()

    return client


@pytest.fixture
def mock_neo4j_driver():
    """Mock Neo4j driver for direct database operations"""
    driver = MagicMock()

    # Mock session context manager
    session_mock = MagicMock()
    session_mock.__enter__ = MagicMock(return_value=session_mock)
    session_mock.__exit__ = MagicMock(return_value=None)

    # Mock run method - returns empty result by default
    result_mock = MagicMock()
    result_mock.data = MagicMock(return_value=[])
    session_mock.run = MagicMock(return_value=result_mock)

    driver.session = MagicMock(return_value=session_mock)

    return driver


@pytest.fixture
def mock_redis_client():
    """Mock Redis client for message routing and state"""
    redis = MagicMock()

    # Mock basic Redis operations
    redis.rpush = MagicMock(return_value=1)
    redis.lrange = MagicMock(return_value=[])
    redis.lpop = MagicMock(return_value=None)
    redis.get = MagicMock(return_value=None)
    redis.set = MagicMock(return_value=True)
    redis.setex = MagicMock(return_value=True)
    redis.delete = MagicMock(return_value=1)
    redis.expire = MagicMock(return_value=True)
    redis.exists = MagicMock(return_value=0)
    redis.keys = MagicMock(return_value=[])
    redis.hset = MagicMock(return_value=1)
    redis.hget = MagicMock(return_value=None)
    redis.hgetall = MagicMock(return_value={})

    return redis


# --- Game State Fixtures ---

@pytest.fixture
def initial_game_state() -> GameState:
    """Initial game state at start of turn"""
    return GameState(
        current_phase="dm_narration",
        phase_start_time=datetime.now(),
        turn_number=1,
        dm_narration="",
        dm_adjudication_needed=True,
        active_agents=["agent_001"],
        strategic_intents={},
        ooc_messages=[],
        character_actions={},
        character_reactions={},
        validation_attempt=0,
        validation_valid=False,
        validation_failures={},
        retrieved_memories={},
        retry_count=0
    )


@pytest.fixture
def mid_turn_game_state() -> GameState:
    """Game state in middle of turn (after strategic intent)"""
    return GameState(
        current_phase="character_action",
        phase_start_time=datetime.now(),
        turn_number=3,
        dm_narration="You encounter a mysterious alien artifact.",
        dm_adjudication_needed=True,
        active_agents=["agent_001"],
        strategic_intents={
            "agent_001": "Carefully examine the artifact without touching it"
        },
        ooc_messages=[],
        character_actions={},
        character_reactions={},
        validation_attempt=0,
        validation_valid=False,
        validation_failures={},
        retrieved_memories={
            "agent_001": [
                {"fact": "Ancient artifacts can be dangerous", "confidence": 0.9}
            ]
        },
        retry_count=0
    )


@pytest.fixture
def multi_agent_game_state() -> GameState:
    """Game state with multiple active agents"""
    return GameState(
        current_phase="strategic_intent",
        phase_start_time=datetime.now(),
        turn_number=5,
        dm_narration="A hostile alien approaches your group.",
        dm_adjudication_needed=True,
        active_agents=["agent_001", "agent_002", "agent_003"],
        strategic_intents={},
        ooc_messages=[],
        character_actions={},
        character_reactions={},
        validation_attempt=0,
        validation_valid=False,
        validation_failures={},
        retrieved_memories={},
        retry_count=0
    )


# --- Turn Data Fixtures ---

@pytest.fixture
def simple_turn_data() -> dict[str, Any]:
    """Simple turn data for memory storage tests"""
    return {
        "session_number": 1,
        "turn_number": 1,
        "dm_narration": "You enter a dimly lit corridor.",
        "character_actions": {
            "char_001": make_action_dict(
                "char_001",
                "I cautiously move forward, scanning for threats."
            )
        },
        "dm_outcome": "The corridor is clear. You see a door at the end.",
        "character_reactions": {
            "char_001": "I approach the door carefully."
        }
    }


@pytest.fixture
def npc_interaction_turn_data() -> dict[str, Any]:
    """Turn data with NPC interaction"""
    return {
        "session_number": 2,
        "turn_number": 8,
        "dm_narration": "The merchant Galvin greets you at his stall in the marketplace.",
        "character_actions": {
            "char_001": make_action_dict(
                "char_001",
                "I greet Galvin and ask about rare artifacts."
            )
        },
        "dm_outcome": "Galvin leans in and whispers about a hidden temple in the northern desert.",
        "character_reactions": {
            "char_001": "This sounds like exactly what I've been searching for!"
        }
    }


@pytest.fixture
def combat_turn_data() -> dict[str, Any]:
    """Turn data with combat action"""
    return {
        "session_number": 1,
        "turn_number": 15,
        "dm_narration": "A hostile robot blocks your path, weapon armed.",
        "character_actions": {
            "char_001": make_action_dict(
                "char_001",
                "I attempt to disable it with my EMP device.",
                task_type="lasers"
            )
        },
        "dm_outcome": "Roll lasers. [Result: 5] Success! The robot's systems shut down.",
        "character_reactions": {
            "char_001": "I move quickly past the disabled robot."
        },
        "dice_result": 5,
        "dice_task_type": "lasers",
        "dice_success": True
    }


# --- Message Fixtures ---

@pytest.fixture
def sample_dm_narration_message() -> Message:
    """DM narration message"""
    return Message(
        channel=MessageChannel.DM_NARRATIVE,
        sender_id="dm",
        content="A mysterious alien ship appears on your scanners.",
        timestamp=datetime.now(),
        metadata={"turn_number": 1, "session_number": 1}
    )


@pytest.fixture
def sample_character_action_message() -> Message:
    """Character action message"""
    return Message(
        channel=MessageChannel.CHARACTER_ACTION,
        sender_id="char_001",
        content="I scan the alien ship for life signs.",
        timestamp=datetime.now(),
        metadata={"character_name": "Kai Nova", "intent_only": True}
    )


@pytest.fixture
def sample_ooc_message() -> Message:
    """Out-of-character discussion message"""
    return Message(
        channel=MessageChannel.OOC_PLAYER,
        sender_id="agent_001",
        content="Should we approach the ship or wait for backup?",
        timestamp=datetime.now(),
        metadata={"discussion_phase": True}
    )


# --- Memory Fixtures ---

@pytest.fixture
def sample_memory_result():
    """Sample memory search result"""
    return MagicMock(
        uuid="mem_001",
        fact="The merchant Galvin sells rare artifacts in the marketplace",
        valid_at=datetime.now() - timedelta(days=5),
        session_number=1,
        days_elapsed=10,
        confidence=0.9,
        importance=0.7,
        rehearsal_count=2,
        source="dm_narration"
    )


@pytest.fixture
def sample_corrupted_memory():
    """Sample corrupted memory (low confidence, old)"""
    return MagicMock(
        uuid="mem_old_001",
        fact="The guard at the gate was friendly",  # May be corrupted
        valid_at=datetime.now() - timedelta(days=90),
        session_number=1,
        days_elapsed=15,
        confidence=0.4,  # Decayed confidence
        importance=0.3,
        rehearsal_count=0,
        source="player_observation",
        corruption_applied=True
    )


# --- Validation Fixtures ---

@pytest.fixture
def valid_intent_action() -> str:
    """Valid character action expressing intent only"""
    return "I attempt to hack the security terminal with my data spike."


@pytest.fixture
def invalid_outcome_action() -> str:
    """Invalid action containing forbidden outcome language"""
    return "I successfully hack the terminal and the door opens."


@pytest.fixture
def invalid_dm_narration_action() -> str:
    """Invalid action attempting to narrate outcomes"""
    return "I strike the guard and he falls unconscious to the ground."


# --- Utility Functions ---

@pytest.fixture
def make_game_state():
    """Factory fixture for creating custom game states"""
    def _make_game_state(**kwargs) -> GameState:
        defaults = {
            "current_phase": "dm_narration",
            "phase_start_time": datetime.now(),
            "turn_number": 1,
            "dm_narration": "",
            "dm_adjudication_needed": True,
            "active_agents": ["agent_001"],
            "strategic_intents": {},
            "ooc_messages": [],
            "character_actions": {},
            "character_reactions": {},
            "validation_attempt": 0,
            "validation_valid": False,
            "validation_failures": {},
            "retrieved_memories": {},
            "retry_count": 0
        }
        defaults.update(kwargs)
        return GameState(**defaults)
    return _make_game_state


@pytest.fixture
def make_turn_data():
    """Factory fixture for creating custom turn data"""
    def _make_turn_data(session=1, turn=1, **kwargs) -> dict[str, Any]:
        defaults = {
            "session_number": session,
            "turn_number": turn,
            "dm_narration": f"Turn {turn} narration",
            "character_actions": {
                "char_001": make_action_dict("char_001", f"Action {turn}")
            },
            "dm_outcome": f"Outcome {turn}",
            "character_reactions": {"char_001": f"Reaction {turn}"}
        }
        defaults.update(kwargs)
        return defaults
    return _make_turn_data


# --- Async Testing Utilities ---

@pytest.fixture
def anyio_backend():
    """Configure anyio backend for async tests"""
    return "asyncio"
