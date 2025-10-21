# ABOUTME: Unit tests for CharacterAgent in-character roleplay logic.
# ABOUTME: Tests directive interpretation, personality expression, intent validation, and error handling.

import json
from unittest.mock import AsyncMock, MagicMock, Mock

import pytest

from src.agents.character import CharacterAgent
from src.agents.exceptions import LLMCallFailed, ValidationFailed
from src.models.agent_actions import Action, Directive, EmotionalState, PrimaryEmotion, Reaction
from src.models.personality import CharacterRole, CharacterSheet, CharacterStyle, PlayerPersonality


class TestCharacterAgentInitialization:
    """Test CharacterAgent initialization and configuration"""

    def test_initialization_minimal(self):
        """Test agent initializes with minimal required parameters"""
        agent = CharacterAgent(character_id="char_test_001")

        assert agent.character_id == "char_test_001"
        assert agent.character_sheet is None
        assert agent.personality is None
        assert agent.temperature == 0.8  # Default temperature

    def test_initialization_with_character_sheet(self, explorer_character):
        """Test agent initializes with character sheet"""
        agent = CharacterAgent(
            character_id="char_kai_001",
            character_sheet=explorer_character,
        )

        assert agent.character_id == "char_kai_001"
        assert agent.character_sheet == explorer_character
        assert agent.character_sheet.name == "Kai Nova"

    def test_initialization_with_personality(self, standard_personality):
        """Test agent initializes with player personality"""
        agent = CharacterAgent(
            character_id="char_test_001",
            personality=standard_personality,
        )

        assert agent.personality == standard_personality

    def test_initialization_with_custom_temperature(self):
        """Test agent accepts custom temperature parameter"""
        agent = CharacterAgent(
            character_id="char_test_001",
            temperature=0.9,
        )

        assert agent.temperature == 0.9

    def test_initialization_with_openai_client(self, mock_openai_client):
        """Test agent initializes with openai client and creates LLM wrapper"""
        agent = CharacterAgent(
            character_id="char_test_001",
            openai_client=mock_openai_client,
        )

        assert agent._openai_client is mock_openai_client
        assert agent._llm_client is not None

    def test_initialization_with_memory(self, mock_graphiti_client):
        """Test agent initializes with memory interface"""
        agent = CharacterAgent(
            character_id="char_test_001",
            memory=mock_graphiti_client,
        )

        assert agent._memory is mock_graphiti_client


class TestPerformAction:
    """Test perform_action method (in-character action execution)"""

    @pytest.fixture
    def agent_with_deps(self, explorer_character, standard_personality, mock_openai_client):
        """Create character agent with all dependencies"""
        return CharacterAgent(
            character_id="char_kai_001",
            character_sheet=explorer_character,
            personality=standard_personality,
            openai_client=mock_openai_client,
        )

    @pytest.fixture
    def simple_directive(self):
        """Simple directive for testing"""
        return Directive(
            from_player="agent_test_001",
            to_character="char_kai_001",
            instruction="Scan the area for anomalies",
        )

    @pytest.mark.asyncio
    async def test_perform_without_openai_raises_error(self, explorer_character, simple_directive):
        """Test method fails when openai_client not provided"""
        agent = CharacterAgent(
            character_id="char_kai_001",
            character_sheet=explorer_character,
            # No openai_client
        )

        with pytest.raises(RuntimeError, match="requires openai_client"):
            await agent.perform_action(
                directive=simple_directive,
                scene_context="You are on a derelict ship",
            )

    @pytest.mark.asyncio
    async def test_generates_valid_action(self, agent_with_deps, simple_directive):
        """Test generates valid Action object"""
        mock_response = json.dumps({
            "narrative_text": "I pull out my scanner and attempt to detect any unusual energy signatures in the area.",
            "task_type": "lasers",
            "is_prepared": False,
            "is_expert": False,
            "is_helping": False,
        })
        agent_with_deps._llm_client.call = AsyncMock(return_value=mock_response)

        action = await agent_with_deps.perform_action(
            directive=simple_directive,
            scene_context="You are in the ship's engine room",
        )

        assert isinstance(action, Action)
        assert action.character_id == "char_kai_001"
        assert len(action.narrative_text) > 0
        assert "attempt" in action.narrative_text.lower() or "try" in action.narrative_text.lower()

    @pytest.mark.asyncio
    async def test_interprets_directive_through_character(self, agent_with_deps, simple_directive):
        """Test directive interpretation includes character personality"""
        actual_calls = []

        async def capture_call(*args, **kwargs):
            actual_calls.append((args, kwargs))
            return json.dumps({
                "narrative_text": "Enthusiastically, I scan the area!",
            })

        agent_with_deps._llm_client.call = AsyncMock(side_effect=capture_call)

        await agent_with_deps.perform_action(
            directive=simple_directive,
            scene_context="You are in the engine room",
        )

        # Verify character traits in system prompt
        system_prompt = actual_calls[0][0][0]
        assert "Kai Nova" in system_prompt
        assert "Enthusiastic" in system_prompt or "enthusiastic" in system_prompt

    @pytest.mark.asyncio
    async def test_uses_speech_patterns(self, agent_with_deps, simple_directive):
        """Test character speech patterns included in system prompt"""
        actual_calls = []

        async def capture_call(*args, **kwargs):
            actual_calls.append((args, kwargs))
            return json.dumps({
                "narrative_text": "I scan the area using my equipment.",
            })

        agent_with_deps._llm_client.call = AsyncMock(side_effect=capture_call)

        await agent_with_deps.perform_action(
            directive=simple_directive,
            scene_context="Test scene",
        )

        system_prompt = actual_calls[0][0][0]
        assert "Enthusiastic" in system_prompt or "enthusiastic" in system_prompt
        assert "explorer jargon" in system_prompt.lower() or "jargon" in system_prompt.lower()

    @pytest.mark.asyncio
    async def test_includes_mannerisms(self, agent_with_deps, simple_directive):
        """Test character mannerisms included in system prompt"""
        actual_calls = []

        async def capture_call(*args, **kwargs):
            actual_calls.append((args, kwargs))
            return json.dumps({
                "narrative_text": "I point at the console and scan it.",
            })

        agent_with_deps._llm_client.call = AsyncMock(side_effect=capture_call)

        await agent_with_deps.perform_action(
            directive=simple_directive,
            scene_context="Test scene",
        )

        system_prompt = actual_calls[0][0][0]
        assert "Points at interesting details" in system_prompt or "points" in system_prompt.lower()

    @pytest.mark.asyncio
    async def test_expresses_intent_only(self, agent_with_deps, simple_directive):
        """Test action expresses intent without narrating outcomes"""
        mock_response = json.dumps({
            "narrative_text": "I attempt to scan the area with my device.",
        })
        agent_with_deps._llm_client.call = AsyncMock(return_value=mock_response)

        action = await agent_with_deps.perform_action(
            directive=simple_directive,
            scene_context="Test scene",
        )

        # Should use intent language
        assert "attempt" in action.narrative_text.lower() or "try" in action.narrative_text.lower()

    @pytest.mark.asyncio
    async def test_follows_directive(self, agent_with_deps):
        """Test action aligns with directive instruction"""
        directive = Directive(
            from_player="agent_test_001",
            to_character="char_kai_001",
            instruction="Carefully examine the ancient artifact without touching it",
        )

        actual_calls = []

        async def capture_call(*args, **kwargs):
            actual_calls.append((args, kwargs))
            return json.dumps({
                "narrative_text": "I lean in close to examine the artifact, being careful not to touch it.",
            })

        agent_with_deps._llm_client.call = AsyncMock(side_effect=capture_call)

        await agent_with_deps.perform_action(
            directive=directive,
            scene_context="You see an ancient artifact",
        )

        # Verify directive in user prompt
        user_prompt = actual_calls[0][0][1]
        assert "Carefully examine the ancient artifact" in user_prompt

    @pytest.mark.asyncio
    async def test_includes_tactical_guidance(self, agent_with_deps):
        """Test includes tactical guidance when provided"""
        directive = Directive(
            from_player="agent_test_001",
            to_character="char_kai_001",
            instruction="Disable the security system",
            tactical_guidance="Target the main power relay first",
        )

        actual_calls = []

        async def capture_call(*args, **kwargs):
            actual_calls.append((args, kwargs))
            return json.dumps({
                "narrative_text": "I attempt to disable the power relay.",
            })

        agent_with_deps._llm_client.call = AsyncMock(side_effect=capture_call)

        await agent_with_deps.perform_action(
            directive=directive,
            scene_context="Test scene",
        )

        user_prompt = actual_calls[0][0][1]
        assert "Target the main power relay first" in user_prompt

    @pytest.mark.asyncio
    async def test_includes_emotional_tone(self, agent_with_deps):
        """Test includes emotional tone when provided"""
        directive = Directive(
            from_player="agent_test_001",
            to_character="char_kai_001",
            instruction="Approach the stranger",
            emotional_tone="cautious but friendly",
        )

        actual_calls = []

        async def capture_call(*args, **kwargs):
            actual_calls.append((args, kwargs))
            return json.dumps({
                "narrative_text": "I cautiously approach with a friendly smile.",
            })

        agent_with_deps._llm_client.call = AsyncMock(side_effect=capture_call)

        await agent_with_deps.perform_action(
            directive=directive,
            scene_context="Test scene",
        )

        user_prompt = actual_calls[0][0][1]
        assert "cautious but friendly" in user_prompt

    @pytest.mark.asyncio
    async def test_validates_against_forbidden_language_successfully(self, agent_with_deps, simple_directive):
        """Test allows valid intent language: 'successfully'"""
        mock_response = json.dumps({
            "narrative_text": "I successfully attempt to scan the device.",
        })
        agent_with_deps._llm_client.call = AsyncMock(return_value=mock_response)

        with pytest.raises(ValidationFailed, match="successfully"):
            await agent_with_deps.perform_action(
                directive=simple_directive,
                scene_context="Test scene",
            )

    @pytest.mark.asyncio
    async def test_validates_against_forbidden_language_manages(self, agent_with_deps, simple_directive):
        """Test rejects outcome language: 'manages to'"""
        mock_response = json.dumps({
            "narrative_text": "I manage to hack the terminal.",
        })
        agent_with_deps._llm_client.call = AsyncMock(return_value=mock_response)

        with pytest.raises(ValidationFailed, match="manages to"):
            await agent_with_deps.perform_action(
                directive=simple_directive,
                scene_context="Test scene",
            )

    @pytest.mark.asyncio
    async def test_validates_against_forbidden_language_kills(self, agent_with_deps, simple_directive):
        """Test rejects outcome language: 'kills'"""
        mock_response = json.dumps({
            "narrative_text": "I attempt to shoot and kill the alien.",
        })
        agent_with_deps._llm_client.call = AsyncMock(return_value=mock_response)

        with pytest.raises(ValidationFailed, match="kills/defeats target"):
            await agent_with_deps.perform_action(
                directive=simple_directive,
                scene_context="Test scene",
            )

    @pytest.mark.asyncio
    async def test_validates_against_forbidden_language_hits(self, agent_with_deps, simple_directive):
        """Test rejects outcome language: 'hits the target'"""
        mock_response = json.dumps({
            "narrative_text": "I fire my weapon and hits the alien.",
        })
        agent_with_deps._llm_client.call = AsyncMock(return_value=mock_response)

        with pytest.raises(ValidationFailed, match="hits/strikes target"):
            await agent_with_deps.perform_action(
                directive=simple_directive,
                scene_context="Test scene",
            )

    @pytest.mark.asyncio
    async def test_validates_against_forbidden_language_enemy_falls(self, agent_with_deps, simple_directive):
        """Test rejects outcome narration: 'the enemy falls'"""
        mock_response = json.dumps({
            "narrative_text": "I shoot and the alien falls to the ground.",
        })
        agent_with_deps._llm_client.call = AsyncMock(return_value=mock_response)

        with pytest.raises(ValidationFailed, match="enemy falls/dies"):
            await agent_with_deps.perform_action(
                directive=simple_directive,
                scene_context="Test scene",
            )

    @pytest.mark.asyncio
    async def test_missing_narrative_text_raises_validation_failed(self, agent_with_deps, simple_directive):
        """Test raises ValidationFailed when narrative_text missing"""
        mock_response = json.dumps({
            "task_type": "lasers",
            # Missing narrative_text
        })
        agent_with_deps._llm_client.call = AsyncMock(return_value=mock_response)

        with pytest.raises(ValidationFailed, match="missing required narrative_text"):
            await agent_with_deps.perform_action(
                directive=simple_directive,
                scene_context="Test scene",
            )

    @pytest.mark.asyncio
    async def test_invalid_json_raises_validation_failed(self, agent_with_deps, simple_directive):
        """Test raises ValidationFailed when LLM returns invalid JSON"""
        agent_with_deps._llm_client.call = AsyncMock(return_value="Not JSON at all")

        with pytest.raises(ValidationFailed, match="Failed to parse action JSON"):
            await agent_with_deps.perform_action(
                directive=simple_directive,
                scene_context="Test scene",
            )

    @pytest.mark.asyncio
    async def test_includes_ic_message_history(self, agent_with_deps, simple_directive):
        """Test includes recent IC messages for context"""
        ic_messages = [
            {"from_agent": "dm", "content": "The door creaks open"},
            {"from_agent": "char_other_001", "content": "I enter cautiously"},
        ]

        actual_calls = []

        async def capture_call(*args, **kwargs):
            actual_calls.append((args, kwargs))
            return json.dumps({
                "narrative_text": "Following my companion, I also enter.",
            })

        agent_with_deps._llm_client.call = AsyncMock(side_effect=capture_call)

        await agent_with_deps.perform_action(
            directive=simple_directive,
            scene_context="Test scene",
            ic_messages=ic_messages,
        )

        user_prompt = actual_calls[0][0][1]
        assert "Recent events you've witnessed:" in user_prompt
        assert "The door creaks open" in user_prompt
        assert "I enter cautiously" in user_prompt

    @pytest.mark.asyncio
    async def test_supports_task_type_field(self, agent_with_deps, simple_directive):
        """Test action includes task_type field for dice mechanics"""
        mock_response = json.dumps({
            "narrative_text": "I attempt to hack the console.",
            "task_type": "lasers",
        })
        agent_with_deps._llm_client.call = AsyncMock(return_value=mock_response)

        action = await agent_with_deps.perform_action(
            directive=simple_directive,
            scene_context="Test scene",
        )

        assert action.task_type == "lasers"

    @pytest.mark.asyncio
    async def test_supports_prepared_flag(self, agent_with_deps, simple_directive):
        """Test action supports is_prepared flag with justification"""
        mock_response = json.dumps({
            "narrative_text": "I use my pre-configured scanner to detect life.",
            "task_type": "lasers",
            "is_prepared": True,
            "prepared_justification": "I configured my scanner earlier for this task",
        })
        agent_with_deps._llm_client.call = AsyncMock(return_value=mock_response)

        action = await agent_with_deps.perform_action(
            directive=simple_directive,
            scene_context="Test scene",
        )

        assert action.is_prepared is True
        assert action.prepared_justification == "I configured my scanner earlier for this task"

    @pytest.mark.asyncio
    async def test_supports_expert_flag(self, agent_with_deps, simple_directive):
        """Test action supports is_expert flag with justification"""
        mock_response = json.dumps({
            "narrative_text": "I expertly navigate the ship.",
            "task_type": "lasers",
            "is_expert": True,
            "expert_justification": "I am an experienced explorer",
        })
        agent_with_deps._llm_client.call = AsyncMock(return_value=mock_response)

        action = await agent_with_deps.perform_action(
            directive=simple_directive,
            scene_context="Test scene",
        )

        assert action.is_expert is True
        assert action.expert_justification == "I am an experienced explorer"

    @pytest.mark.asyncio
    async def test_supports_helping_mechanic(self, agent_with_deps, simple_directive):
        """Test action supports is_helping flag for helping other characters"""
        mock_response = json.dumps({
            "narrative_text": "I provide cover fire for my companion.",
            "task_type": "lasers",
            "is_helping": True,
            "helping_character_id": "char_zara_001",
            "help_justification": "I cover their advance with suppressing fire",
        })
        agent_with_deps._llm_client.call = AsyncMock(return_value=mock_response)

        action = await agent_with_deps.perform_action(
            directive=simple_directive,
            scene_context="Test scene",
            valid_character_ids=["char_zara_001"],
        )

        assert action.is_helping is True
        assert action.helping_character_id == "char_zara_001"
        assert action.help_justification == "I cover their advance with suppressing fire"


class TestReactToOutcome:
    """Test react_to_outcome method (in-character reactions)"""

    @pytest.fixture
    def agent_with_deps(self, explorer_character, mock_openai_client):
        """Create character agent with dependencies"""
        return CharacterAgent(
            character_id="char_kai_001",
            character_sheet=explorer_character,
            openai_client=mock_openai_client,
        )

    @pytest.fixture
    def sample_emotional_state(self):
        """Sample emotional state for reactions"""
        return EmotionalState(
            primary_emotion=PrimaryEmotion.SURPRISE,
            intensity=0.7,
            secondary_emotions=["curiosity", "excitement"],
        )

    @pytest.mark.asyncio
    async def test_react_without_openai_raises_error(self, explorer_character, sample_emotional_state):
        """Test method fails when openai_client not provided"""
        agent = CharacterAgent(
            character_id="char_kai_001",
            character_sheet=explorer_character,
            # No openai_client
        )

        with pytest.raises(RuntimeError, match="requires openai_client"):
            await agent.react_to_outcome(
                dm_narration="The door opens to reveal a strange chamber",
                emotional_state=sample_emotional_state,
            )

    @pytest.mark.asyncio
    async def test_generates_valid_reaction(self, agent_with_deps, sample_emotional_state):
        """Test generates valid Reaction object"""
        mock_response = json.dumps({
            "narrative_text": "My eyes widen in surprise. 'Fascinating!' I exclaim.",
        })
        agent_with_deps._llm_client.call = AsyncMock(return_value=mock_response)

        reaction = await agent_with_deps.react_to_outcome(
            dm_narration="You discover an ancient alien artifact",
            emotional_state=sample_emotional_state,
        )

        assert isinstance(reaction, Reaction)
        assert reaction.character_id == "char_kai_001"
        assert len(reaction.narrative_text) > 0

    @pytest.mark.asyncio
    async def test_reflects_emotional_state(self, agent_with_deps, sample_emotional_state):
        """Test reaction reflects provided emotional state"""
        actual_calls = []

        async def capture_call(*args, **kwargs):
            actual_calls.append((args, kwargs))
            return json.dumps({
                "narrative_text": "I react with surprise!",
            })

        agent_with_deps._llm_client.call = AsyncMock(side_effect=capture_call)

        await agent_with_deps.react_to_outcome(
            dm_narration="Something unexpected happens",
            emotional_state=sample_emotional_state,
        )

        user_prompt = actual_calls[0][0][1]
        assert "surprise" in user_prompt.lower()
        assert "0.7" in user_prompt or "0.70" in user_prompt  # intensity
        assert "curiosity" in user_prompt.lower()

    @pytest.mark.asyncio
    async def test_uses_character_voice(self, agent_with_deps, sample_emotional_state):
        """Test reaction uses character's unique voice"""
        actual_calls = []

        async def capture_call(*args, **kwargs):
            actual_calls.append((args, kwargs))
            return json.dumps({
                "narrative_text": "Enthusiastically, I examine the discovery!",
            })

        agent_with_deps._llm_client.call = AsyncMock(side_effect=capture_call)

        await agent_with_deps.react_to_outcome(
            dm_narration="You find something interesting",
            emotional_state=sample_emotional_state,
        )

        system_prompt = actual_calls[0][0][0]
        assert "Kai Nova" in system_prompt
        assert "Enthusiastic" in system_prompt or "enthusiastic" in system_prompt

    @pytest.mark.asyncio
    async def test_different_emotions_produce_different_reactions(self, agent_with_deps):
        """Test different emotional states lead to different reaction tones"""
        fear_state = EmotionalState(
            primary_emotion=PrimaryEmotion.FEAR,
            intensity=0.9,
        )

        actual_calls = []

        async def capture_call(*args, **kwargs):
            actual_calls.append((args, kwargs))
            return json.dumps({
                "narrative_text": "I step back in alarm!",
            })

        agent_with_deps._llm_client.call = AsyncMock(side_effect=capture_call)

        await agent_with_deps.react_to_outcome(
            dm_narration="A hostile creature appears",
            emotional_state=fear_state,
        )

        user_prompt = actual_calls[0][0][1]
        assert "fear" in user_prompt.lower()
        assert "0.9" in user_prompt or "0.90" in user_prompt

    @pytest.mark.asyncio
    async def test_includes_ic_message_history(self, agent_with_deps, sample_emotional_state):
        """Test includes recent IC messages for context"""
        ic_messages = [
            {"from_agent": "dm", "content": "The device activates"},
            {"from_agent": "char_other_001", "content": "I back away slowly"},
        ]

        actual_calls = []

        async def capture_call(*args, **kwargs):
            actual_calls.append((args, kwargs))
            return json.dumps({
                "narrative_text": "Following my companion's lead, I also retreat.",
            })

        agent_with_deps._llm_client.call = AsyncMock(side_effect=capture_call)

        await agent_with_deps.react_to_outcome(
            dm_narration="The device emits a strange sound",
            emotional_state=sample_emotional_state,
            ic_messages=ic_messages,
        )

        user_prompt = actual_calls[0][0][1]
        assert "Recent events you've witnessed:" in user_prompt
        assert "The device activates" in user_prompt

    @pytest.mark.asyncio
    async def test_missing_narrative_text_raises_validation_failed(self, agent_with_deps, sample_emotional_state):
        """Test raises ValidationFailed when narrative_text missing"""
        mock_response = json.dumps({
            "emotion": "surprised",
            # Missing narrative_text
        })
        agent_with_deps._llm_client.call = AsyncMock(return_value=mock_response)

        with pytest.raises(ValidationFailed, match="missing required narrative_text"):
            await agent_with_deps.react_to_outcome(
                dm_narration="Test outcome",
                emotional_state=sample_emotional_state,
            )

    @pytest.mark.asyncio
    async def test_invalid_json_raises_validation_failed(self, agent_with_deps, sample_emotional_state):
        """Test raises ValidationFailed when LLM returns invalid JSON"""
        agent_with_deps._llm_client.call = AsyncMock(return_value="Not JSON")

        with pytest.raises(ValidationFailed, match="Failed to parse reaction JSON"):
            await agent_with_deps.react_to_outcome(
                dm_narration="Test outcome",
                emotional_state=sample_emotional_state,
            )


class TestCharacterPersonality:
    """Test character personality influences on behavior"""

    @pytest.mark.asyncio
    async def test_lasers_character_uses_technical_approach(self, scientist_character, mock_openai_client):
        """Test lasers-oriented character (number=2) uses technical language"""
        agent = CharacterAgent(
            character_id="char_lyra_001",
            character_sheet=scientist_character,
            openai_client=mock_openai_client,
        )

        actual_calls = []

        async def capture_call(*args, **kwargs):
            actual_calls.append((args, kwargs))
            return json.dumps({
                "narrative_text": "I analyze the readings with scientific precision.",
            })

        agent._llm_client.call = AsyncMock(side_effect=capture_call)

        directive = Directive(
            from_player="agent_test_001",
            to_character="char_lyra_001",
            instruction="Examine the anomaly",
        )

        await agent.perform_action(
            directive=directive,
            scene_context="Test scene",
        )

        system_prompt = actual_calls[0][0][0]
        assert "logical, technical, and analytical" in system_prompt.lower()
        assert "number: 2" in system_prompt

    @pytest.mark.asyncio
    async def test_feelings_character_uses_emotional_approach(self, mock_openai_client):
        """Test feelings-oriented character (number=5) uses empathetic language"""
        diplomat_char = CharacterSheet(
            name="Ambassador Trell",
            style=CharacterStyle.HEROIC,
            role=CharacterRole.ENVOY,
            number=5,  # Feelings-oriented
            character_goal="Establish peace",
            speech_patterns=["Empathetic", "Diplomatic"],
            mannerisms=["Open gestures", "Warm smile"],
        )

        agent = CharacterAgent(
            character_id="char_trell_001",
            character_sheet=diplomat_char,
            openai_client=mock_openai_client,
        )

        actual_calls = []

        async def capture_call(*args, **kwargs):
            actual_calls.append((args, kwargs))
            return json.dumps({
                "narrative_text": "I approach with understanding and compassion.",
            })

        agent._llm_client.call = AsyncMock(side_effect=capture_call)

        directive = Directive(
            from_player="agent_test_001",
            to_character="char_trell_001",
            instruction="Negotiate with the aliens",
        )

        await agent.perform_action(
            directive=directive,
            scene_context="Test scene",
        )

        system_prompt = actual_calls[0][0][0]
        assert "intuitive, emotional, and empathetic" in system_prompt.lower()
        assert "number: 5" in system_prompt

    @pytest.mark.asyncio
    async def test_character_without_sheet_uses_minimal_prompt(self, mock_openai_client):
        """Test character without sheet uses minimal system prompt"""
        agent = CharacterAgent(
            character_id="char_minimal_001",
            # No character_sheet
            openai_client=mock_openai_client,
        )

        actual_calls = []

        async def capture_call(*args, **kwargs):
            actual_calls.append((args, kwargs))
            return json.dumps({
                "narrative_text": "I attempt to perform the action.",
            })

        agent._llm_client.call = AsyncMock(side_effect=capture_call)

        directive = Directive(
            from_player="agent_test_001",
            to_character="char_minimal_001",
            instruction="Do something",
        )

        await agent.perform_action(
            directive=directive,
            scene_context="Test scene",
        )

        system_prompt = actual_calls[0][0][0]
        # Should have CRITICAL RULES but no character-specific details
        assert "CRITICAL RULES:" in system_prompt
        assert "express intent only" in system_prompt.lower()
        # Should not have character name or traits
        assert "Kai Nova" not in system_prompt


class TestDirectiveInterpretation:
    """Test directive interpretation variations"""

    @pytest.mark.asyncio
    async def test_different_characters_interpret_same_directive_differently(
        self, explorer_character, scientist_character, mock_openai_client
    ):
        """Test same directive produces different actions based on character"""
        directive = Directive(
            from_player="agent_test_001",
            to_character="char_test_001",
            instruction="Investigate the mysterious device",
        )

        # Explorer approach
        explorer_agent = CharacterAgent(
            character_id="char_kai_001",
            character_sheet=explorer_character,
            openai_client=mock_openai_client,
        )

        explorer_calls = []

        async def capture_explorer(*args, **kwargs):
            explorer_calls.append((args, kwargs))
            return json.dumps({
                "narrative_text": "Enthusiastically, I examine the device!",
            })

        explorer_agent._llm_client.call = AsyncMock(side_effect=capture_explorer)

        await explorer_agent.perform_action(
            directive=directive,
            scene_context="Test scene",
        )

        # Scientist approach
        scientist_agent = CharacterAgent(
            character_id="char_lyra_001",
            character_sheet=scientist_character,
            openai_client=mock_openai_client,
        )

        scientist_calls = []

        async def capture_scientist(*args, **kwargs):
            scientist_calls.append((args, kwargs))
            return json.dumps({
                "narrative_text": "I methodically scan the device with scientific precision.",
            })

        scientist_agent._llm_client.call = AsyncMock(side_effect=capture_scientist)

        await scientist_agent.perform_action(
            directive=directive,
            scene_context="Test scene",
        )

        # Verify different character traits in prompts
        explorer_prompt = explorer_calls[0][0][0]
        scientist_prompt = scientist_calls[0][0][0]

        assert "Enthusiastic" in explorer_prompt
        assert "Precise language" in scientist_prompt or "precise" in scientist_prompt.lower()


class TestErrorHandling:
    """Test error handling and edge cases"""

    @pytest.mark.asyncio
    async def test_llm_api_failure_propagates(self, explorer_character, mock_openai_client):
        """Test LLM API failure raises ValidationFailed"""
        agent = CharacterAgent(
            character_id="char_kai_001",
            character_sheet=explorer_character,
            openai_client=mock_openai_client,
        )

        # Mock LLM to raise exception
        agent._llm_client.call = AsyncMock(side_effect=Exception("API Error"))

        directive = Directive(
            from_player="agent_test_001",
            to_character="char_kai_001",
            instruction="Test",
        )

        with pytest.raises(Exception, match="API Error"):
            await agent.perform_action(
                directive=directive,
                scene_context="Test scene",
            )

    @pytest.mark.asyncio
    async def test_empty_ic_messages_handled(self, explorer_character, mock_openai_client):
        """Test empty IC message list doesn't cause errors"""
        agent = CharacterAgent(
            character_id="char_kai_001",
            character_sheet=explorer_character,
            openai_client=mock_openai_client,
        )

        directive = Directive(
            from_player="agent_test_001",
            to_character="char_kai_001",
            instruction="Test",
        )

        mock_response = json.dumps({
            "narrative_text": "I perform the action.",
        })
        agent._llm_client.call = AsyncMock(return_value=mock_response)

        action = await agent.perform_action(
            directive=directive,
            scene_context="Test scene",
            ic_messages=[],  # Empty list
        )

        assert isinstance(action, Action)

    @pytest.mark.asyncio
    async def test_format_ic_history_with_none(self, explorer_character):
        """Test _format_ic_history handles None gracefully"""
        agent = CharacterAgent(
            character_id="char_kai_001",
            character_sheet=explorer_character,
        )

        result = agent._format_ic_history(None)

        assert result == ""

    @pytest.mark.asyncio
    async def test_format_ic_history_with_messages(self, explorer_character):
        """Test _format_ic_history formats messages correctly"""
        agent = CharacterAgent(
            character_id="char_kai_001",
            character_sheet=explorer_character,
        )

        messages = [
            {"from_agent": "dm", "content": "The door opens"},
            {"from_agent": "char_other_001", "content": "I enter"},
        ]

        result = agent._format_ic_history(messages)

        assert "Recent events you've witnessed:" in result
        assert "dm: The door opens" in result
        assert "char_other_001: I enter" in result

    @pytest.mark.asyncio
    async def test_character_sheet_with_enum_values(self, mock_openai_client):
        """Test character sheet with use_enum_values=True handled correctly"""
        char_sheet = CharacterSheet(
            name="Test Character",
            style=CharacterStyle.DANGEROUS,
            role=CharacterRole.SOLDIER,
            number=3,
            character_goal="Test goal",
        )

        agent = CharacterAgent(
            character_id="char_test_001",
            character_sheet=char_sheet,
            openai_client=mock_openai_client,
        )

        # Should not crash when building system prompt
        system_prompt = agent._build_character_system_prompt()

        # Should handle both enum and string values
        assert "Dangerous" in system_prompt or "dangerous" in system_prompt.lower()
        assert "Soldier" in system_prompt or "soldier" in system_prompt.lower()
