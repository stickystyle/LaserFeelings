# ABOUTME: Unit tests for BasePersonaAgent strategic decision-making logic.
# ABOUTME: Tests personality influence, LLM interaction mocking, memory integration, and error handling.

import json
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, Mock, patch
from uuid import uuid4

import pytest

from src.agents.base_persona import BasePersonaAgent
from src.agents.exceptions import (
    CharacterNotFound,
    InvalidCharacterState,
    InvalidMessageFormat,
    LLMCallFailed,
    NoConsensusReached,
)
from src.models.agent_actions import CharacterState, Directive, Intent
from src.models.messages import Message, MessageChannel, MessageType
from src.models.personality import PlayerPersonality


class TestBasePersonaAgentInitialization:
    """Test BasePersonaAgent initialization and validation"""

    def test_initialization_with_valid_personality(self, standard_personality):
        """Test agent initializes correctly with valid personality"""
        agent = BasePersonaAgent(
            agent_id="agent_test_001",
            personality=standard_personality,
            character_number=3,
        )

        assert agent.agent_id == "agent_test_001"
        assert agent.personality == standard_personality
        assert agent.character_number == 3
        assert agent.temperature == 0.7

    def test_initialization_with_custom_temperature(self, standard_personality):
        """Test agent accepts custom temperature parameter"""
        agent = BasePersonaAgent(
            agent_id="agent_test_001",
            personality=standard_personality,
            character_number=3,
            temperature=0.5,
        )

        assert agent.temperature == 0.5

    def test_initialization_with_invalid_character_number_low(self, standard_personality):
        """Test agent initialization fails with character_number < 2"""
        with pytest.raises(ValueError, match="Character number must be 2-5"):
            BasePersonaAgent(
                agent_id="agent_test_001",
                personality=standard_personality,
                character_number=1,
            )

    def test_initialization_with_invalid_character_number_high(self, standard_personality):
        """Test agent initialization fails with character_number > 5"""
        with pytest.raises(ValueError, match="Character number must be 2-5"):
            BasePersonaAgent(
                agent_id="agent_test_001",
                personality=standard_personality,
                character_number=6,
            )

    def test_initialization_with_openai_client(self, standard_personality, mock_openai_client):
        """Test agent initializes with openai client and creates LLM client wrapper"""
        agent = BasePersonaAgent(
            agent_id="agent_test_001",
            personality=standard_personality,
            character_number=3,
            openai_client=mock_openai_client,
        )

        assert agent._openai_client is mock_openai_client
        assert agent._llm_client is not None

    def test_initialization_with_memory(self, standard_personality, mock_graphiti_client):
        """Test agent initializes with memory interface"""
        agent = BasePersonaAgent(
            agent_id="agent_test_001",
            personality=standard_personality,
            character_number=3,
            memory=mock_graphiti_client,
        )

        assert agent._memory is mock_graphiti_client


class TestParticipateInOOCDiscussion:
    """Test participate_in_ooc_discussion method (strategic discussion)"""

    @pytest.fixture
    def agent_with_deps(self, standard_personality, mock_openai_client, mock_graphiti_client):
        """Create agent with all dependencies for OOC discussion"""
        return BasePersonaAgent(
            agent_id="agent_alex_001",
            personality=standard_personality,
            character_number=3,
            memory=mock_graphiti_client,
            openai_client=mock_openai_client,
        )

    @pytest.mark.asyncio
    async def test_participate_without_memory_raises_error(self, standard_personality, mock_openai_client):
        """Test method fails when memory dependency not provided"""
        agent = BasePersonaAgent(
            agent_id="agent_test_001",
            personality=standard_personality,
            character_number=3,
            openai_client=mock_openai_client,
            # No memory provided
        )

        with pytest.raises(RuntimeError, match="requires memory and openai_client"):
            await agent.participate_in_ooc_discussion(
                dm_narration="You see a door",
                other_messages=[],
            )

    @pytest.mark.asyncio
    async def test_participate_without_openai_raises_error(self, standard_personality, mock_graphiti_client):
        """Test method fails when openai_client dependency not provided"""
        agent = BasePersonaAgent(
            agent_id="agent_test_001",
            personality=standard_personality,
            character_number=3,
            memory=mock_graphiti_client,
            # No openai_client provided
        )

        with pytest.raises(RuntimeError, match="requires memory and openai_client"):
            await agent.participate_in_ooc_discussion(
                dm_narration="You see a door",
                other_messages=[],
            )

    @pytest.mark.asyncio
    async def test_generates_strategic_discussion(self, agent_with_deps, mock_graphiti_client):
        """Test generates valid OOC discussion message"""
        mock_graphiti_client.search.return_value = []

        message = await agent_with_deps.participate_in_ooc_discussion(
            dm_narration="You encounter a locked door",
            other_messages=[],
        )

        assert isinstance(message, Message)
        assert message.channel == MessageChannel.OOC
        assert message.from_agent == "agent_alex_001"
        assert message.to_agents is None  # Broadcast
        assert message.message_type == MessageType.DISCUSSION
        assert len(message.content) > 0

    @pytest.mark.asyncio
    async def test_queries_memory_with_narration(self, agent_with_deps, mock_graphiti_client):
        """Test retrieves relevant memories based on narration"""
        mock_graphiti_client.search.return_value = [
            MagicMock(fact="Doors often have traps", confidence=0.9),
            MagicMock(fact="Check for alarms first", confidence=0.8),
        ]

        await agent_with_deps.participate_in_ooc_discussion(
            dm_narration="You encounter a locked door",
            other_messages=[],
        )

        # Verify memory search was called
        mock_graphiti_client.search.assert_called_once()
        call_kwargs = mock_graphiti_client.search.call_args.kwargs
        assert "DM narration:" in call_kwargs["query"]
        assert call_kwargs["agent_id"] == "agent_alex_001"
        assert call_kwargs["limit"] == 5

    @pytest.mark.asyncio
    async def test_considers_personality_traits(self, risk_taker_personality, mock_openai_client, mock_graphiti_client):
        """Test personality traits influence discussion prompt"""
        agent = BasePersonaAgent(
            agent_id="agent_bold_001",
            personality=risk_taker_personality,
            character_number=3,
            memory=mock_graphiti_client,
            openai_client=mock_openai_client,
        )

        mock_graphiti_client.search.return_value = []

        # Capture LLM call to verify personality influence
        actual_calls = []

        async def capture_call(*args, **kwargs):
            actual_calls.append((args, kwargs))
            return "Bold action!"

        agent._llm_client.call = AsyncMock(side_effect=capture_call)

        await agent.participate_in_ooc_discussion(
            dm_narration="You see a mysterious device",
            other_messages=[],
        )

        # Verify personality traits mentioned in system prompt
        assert len(actual_calls) == 1
        system_prompt = actual_calls[0][0][0]  # First positional arg
        assert "bold" in system_prompt.lower() or "risk" in system_prompt.lower()

    @pytest.mark.asyncio
    async def test_includes_other_messages_in_context(self, agent_with_deps, mock_graphiti_client):
        """Test includes other players' messages in discussion context"""
        mock_graphiti_client.search.return_value = []

        other_msg = Message(
            message_id=str(uuid4()),
            channel=MessageChannel.OOC,
            from_agent="agent_bob_002",
            to_agents=None,
            content="I think we should be cautious",
            timestamp=datetime.now(),
            message_type=MessageType.DISCUSSION,
            phase="ooc_discussion",
            turn_number=1,
            session_number=1,
        )

        actual_calls = []

        async def capture_call(*args, **kwargs):
            actual_calls.append((args, kwargs))
            return "I agree with Bob"

        agent_with_deps._llm_client.call = AsyncMock(side_effect=capture_call)

        await agent_with_deps.participate_in_ooc_discussion(
            dm_narration="You see a trap",
            other_messages=[other_msg],
        )

        # Verify other messages included in user prompt
        assert len(actual_calls) == 1
        user_prompt = actual_calls[0][0][1]  # Second positional arg
        assert "agent_bob_002" in user_prompt
        assert "cautious" in user_prompt

    @pytest.mark.asyncio
    async def test_truncates_long_messages(self, agent_with_deps, mock_graphiti_client):
        """Test truncates messages longer than 2000 characters"""
        mock_graphiti_client.search.return_value = []

        # Mock LLM to return very long response
        long_response = "A" * 2500
        agent_with_deps._llm_client.call = AsyncMock(return_value=long_response)

        message = await agent_with_deps.participate_in_ooc_discussion(
            dm_narration="What should we do?",
            other_messages=[],
        )

        # Should be truncated to 2000 chars with ellipsis
        assert len(message.content) == 2000
        assert message.content.endswith("...")

    @pytest.mark.asyncio
    async def test_handles_empty_memory_gracefully(self, agent_with_deps, mock_graphiti_client):
        """Test handles empty memory results without errors"""
        mock_graphiti_client.search.return_value = []

        message = await agent_with_deps.participate_in_ooc_discussion(
            dm_narration="You see a door",
            other_messages=[],
        )

        assert isinstance(message, Message)
        assert len(message.content) > 0


class TestFormulateStrategicIntent:
    """Test formulate_strategic_intent method (high-level goal creation)"""

    @pytest.fixture
    def agent_with_llm(self, standard_personality, mock_openai_client):
        """Create agent with LLM client for intent formulation"""
        return BasePersonaAgent(
            agent_id="agent_test_001",
            personality=standard_personality,
            character_number=3,
            openai_client=mock_openai_client,
        )

    @pytest.mark.asyncio
    async def test_formulate_without_openai_raises_error(self, standard_personality):
        """Test method fails when openai_client not provided"""
        agent = BasePersonaAgent(
            agent_id="agent_test_001",
            personality=standard_personality,
            character_number=3,
            # No openai_client
        )

        with pytest.raises(RuntimeError, match="requires openai_client"):
            await agent.formulate_strategic_intent(
                discussion_summary="We should investigate the door carefully",
            )

    @pytest.mark.asyncio
    async def test_empty_discussion_raises_no_consensus(self, agent_with_llm):
        """Test raises NoConsensusReached when discussion summary is empty"""
        with pytest.raises(NoConsensusReached, match="Empty discussion summary"):
            await agent_with_llm.formulate_strategic_intent(discussion_summary="")

    @pytest.mark.asyncio
    async def test_whitespace_discussion_raises_no_consensus(self, agent_with_llm):
        """Test raises NoConsensusReached when discussion is only whitespace"""
        with pytest.raises(NoConsensusReached, match="Empty discussion summary"):
            await agent_with_llm.formulate_strategic_intent(discussion_summary="   \n  \t  ")

    @pytest.mark.asyncio
    async def test_creates_valid_intent(self, agent_with_llm):
        """Test creates valid Intent object from discussion"""
        # Mock LLM response with valid JSON
        mock_response = json.dumps({
            "strategic_goal": "Investigate door safely",
            "reasoning": "Minimize risk while gathering information",
            "risk_assessment": "Low risk if cautious",
            "fallback_plan": "Retreat if danger detected",
        })
        agent_with_llm._llm_client.call = AsyncMock(return_value=mock_response)

        intent = await agent_with_llm.formulate_strategic_intent(
            discussion_summary="Group agreed to be cautious"
        )

        assert isinstance(intent, Intent)
        assert intent.agent_id == "agent_test_001"
        assert intent.strategic_goal == "Investigate door safely"
        assert intent.reasoning == "Minimize risk while gathering information"
        assert intent.risk_assessment == "Low risk if cautious"
        assert intent.fallback_plan == "Retreat if danger detected"

    @pytest.mark.asyncio
    async def test_personality_influences_intent(self, risk_taker_personality, mock_openai_client):
        """Test risk-tolerant personality influences intent formulation"""
        agent = BasePersonaAgent(
            agent_id="agent_bold_001",
            personality=risk_taker_personality,
            character_number=3,
            openai_client=mock_openai_client,
        )

        actual_calls = []

        async def capture_call(*args, **kwargs):
            actual_calls.append((args, kwargs))
            return json.dumps({
                "strategic_goal": "Charge in boldly",
                "reasoning": "Fortune favors the bold",
                "risk_assessment": "High risk, high reward",
                "fallback_plan": "Fight our way out",
            })

        agent._llm_client.call = AsyncMock(side_effect=capture_call)

        intent = await agent.formulate_strategic_intent(
            discussion_summary="Should we attack?"
        )

        # Verify personality traits in prompt
        system_prompt = actual_calls[0][0][0]
        assert "0.9" in system_prompt or "0.90" in system_prompt  # risk_tolerance

        assert intent.strategic_goal == "Charge in boldly"

    @pytest.mark.asyncio
    async def test_handles_dict_risk_assessment(self, agent_with_llm):
        """Test converts dict risk_assessment to string"""
        # Some LLMs might return structured risk assessment
        mock_response = json.dumps({
            "strategic_goal": "Test goal",
            "reasoning": "Test reasoning",
            "risk_assessment": {"level": "moderate", "factors": ["unknown", "traps"]},
            "fallback_plan": "Retreat",
        })
        agent_with_llm._llm_client.call = AsyncMock(return_value=mock_response)

        intent = await agent_with_llm.formulate_strategic_intent(
            discussion_summary="Test discussion"
        )

        # Should convert dict to JSON string
        assert isinstance(intent.risk_assessment, str)
        assert "moderate" in intent.risk_assessment

    @pytest.mark.asyncio
    async def test_handles_dict_fallback_plan(self, agent_with_llm):
        """Test converts dict fallback_plan to string"""
        mock_response = json.dumps({
            "strategic_goal": "Test goal",
            "reasoning": "Test reasoning",
            "risk_assessment": "Low",
            "fallback_plan": {"primary": "retreat", "secondary": "fight"},
        })
        agent_with_llm._llm_client.call = AsyncMock(return_value=mock_response)

        intent = await agent_with_llm.formulate_strategic_intent(
            discussion_summary="Test discussion"
        )

        # Should convert dict to JSON string
        assert isinstance(intent.fallback_plan, str)
        assert "retreat" in intent.fallback_plan

    @pytest.mark.asyncio
    async def test_missing_strategic_goal_raises_no_consensus(self, agent_with_llm):
        """Test raises NoConsensusReached when LLM omits strategic_goal"""
        mock_response = json.dumps({
            "reasoning": "Some reasoning",
            # Missing strategic_goal
        })
        agent_with_llm._llm_client.call = AsyncMock(return_value=mock_response)

        with pytest.raises(NoConsensusReached, match="failed to provide complete intent"):
            await agent_with_llm.formulate_strategic_intent(discussion_summary="Test")

    @pytest.mark.asyncio
    async def test_missing_reasoning_raises_no_consensus(self, agent_with_llm):
        """Test raises NoConsensusReached when LLM omits reasoning"""
        mock_response = json.dumps({
            "strategic_goal": "Some goal",
            # Missing reasoning
        })
        agent_with_llm._llm_client.call = AsyncMock(return_value=mock_response)

        with pytest.raises(NoConsensusReached, match="failed to provide complete intent"):
            await agent_with_llm.formulate_strategic_intent(discussion_summary="Test")

    @pytest.mark.asyncio
    async def test_invalid_json_raises_llm_call_failed(self, agent_with_llm):
        """Test raises LLMCallFailed when LLM returns invalid JSON"""
        agent_with_llm._llm_client.call = AsyncMock(return_value="Not valid JSON at all")

        with pytest.raises(LLMCallFailed, match="Failed to parse LLM JSON response"):
            await agent_with_llm.formulate_strategic_intent(discussion_summary="Test")


class TestCreateCharacterDirective:
    """Test create_character_directive method (P2C instruction)"""

    @pytest.fixture
    def agent_with_llm(self, standard_personality, mock_openai_client):
        """Create agent with LLM client for directive creation"""
        return BasePersonaAgent(
            agent_id="agent_test_001",
            personality=standard_personality,
            character_number=3,
            openai_client=mock_openai_client,
        )

    @pytest.fixture
    def sample_intent(self):
        """Sample strategic intent for directive creation"""
        return Intent(
            agent_id="agent_test_001",
            strategic_goal="Disable enemy ship non-lethally",
            reasoning="Preserve potential intelligence sources",
            risk_assessment="Moderate - ship might have defenses",
            fallback_plan="Target engines if weapons fire",
        )

    @pytest.fixture
    def sample_character_state(self):
        """Sample character state for context"""
        return CharacterState(
            character_id="char_zara_001",
            current_location="Ship bridge",
            health_status="Healthy",
            emotional_state="Focused",
            active_effects=["tactical_scan_active"],
        )

    @pytest.mark.asyncio
    async def test_create_without_openai_raises_error(self, standard_personality, sample_intent, sample_character_state):
        """Test method fails when openai_client not provided"""
        agent = BasePersonaAgent(
            agent_id="agent_test_001",
            personality=standard_personality,
            character_number=3,
            # No openai_client
        )

        with pytest.raises(RuntimeError, match="requires openai_client"):
            await agent.create_character_directive(
                intent=sample_intent,
                character_state=sample_character_state,
            )

    @pytest.mark.asyncio
    async def test_none_character_state_raises_character_not_found(self, agent_with_llm, sample_intent):
        """Test raises CharacterNotFound when state is None"""
        with pytest.raises(CharacterNotFound, match="Character state is None"):
            await agent_with_llm.create_character_directive(
                intent=sample_intent,
                character_state=None,
            )

    @pytest.mark.asyncio
    async def test_missing_character_id_raises_invalid_state(self, agent_with_llm, sample_intent):
        """Test raises InvalidCharacterState when character_id missing"""
        invalid_state = CharacterState(
            character_id="",  # Empty character_id
            current_location="Bridge",
        )

        with pytest.raises(InvalidCharacterState, match="missing character_id"):
            await agent_with_llm.create_character_directive(
                intent=sample_intent,
                character_state=invalid_state,
            )

    @pytest.mark.asyncio
    async def test_invalid_character_id_format_raises_error(self, agent_with_llm, sample_intent):
        """Test raises InvalidCharacterState when character_id format invalid"""
        invalid_state = CharacterState(
            character_id="invalid_format_123",  # Doesn't start with char_
            current_location="Bridge",
        )

        with pytest.raises(InvalidCharacterState, match="Invalid character_id format"):
            await agent_with_llm.create_character_directive(
                intent=sample_intent,
                character_state=invalid_state,
            )

    @pytest.mark.asyncio
    async def test_creates_valid_directive(self, agent_with_llm, sample_intent, sample_character_state):
        """Test creates valid Directive object"""
        mock_response = json.dumps({
            "instruction": "Disable their engines using your technical expertise",
            "tactical_guidance": "Target propulsion systems first",
            "emotional_tone": "Focused determination",
        })
        agent_with_llm._llm_client.call = AsyncMock(return_value=mock_response)

        directive = await agent_with_llm.create_character_directive(
            intent=sample_intent,
            character_state=sample_character_state,
        )

        assert isinstance(directive, Directive)
        assert directive.from_player == "agent_test_001"
        assert directive.to_character == "char_zara_001"
        assert directive.instruction == "Disable their engines using your technical expertise"
        assert directive.tactical_guidance == "Target propulsion systems first"
        assert directive.emotional_tone == "Focused determination"

    @pytest.mark.asyncio
    async def test_directive_includes_intent_context(self, agent_with_llm, sample_intent, sample_character_state):
        """Test directive creation includes strategic intent context"""
        actual_calls = []

        async def capture_call(*args, **kwargs):
            actual_calls.append((args, kwargs))
            return json.dumps({
                "instruction": "Test instruction",
                "emotional_tone": "calm",
            })

        agent_with_llm._llm_client.call = AsyncMock(side_effect=capture_call)

        await agent_with_llm.create_character_directive(
            intent=sample_intent,
            character_state=sample_character_state,
        )

        # Verify intent details in user prompt
        user_prompt = actual_calls[0][0][1]
        assert "Disable enemy ship non-lethally" in user_prompt
        assert "Preserve potential intelligence sources" in user_prompt

    @pytest.mark.asyncio
    async def test_directive_includes_character_state(self, agent_with_llm, sample_intent, sample_character_state):
        """Test directive creation considers character current state"""
        actual_calls = []

        async def capture_call(*args, **kwargs):
            actual_calls.append((args, kwargs))
            return json.dumps({
                "instruction": "Test instruction",
                "emotional_tone": "calm",
            })

        agent_with_llm._llm_client.call = AsyncMock(side_effect=capture_call)

        await agent_with_llm.create_character_directive(
            intent=sample_intent,
            character_state=sample_character_state,
        )

        # Verify character state in user prompt
        user_prompt = actual_calls[0][0][1]
        assert "Ship bridge" in user_prompt
        assert "Focused" in user_prompt
        assert "tactical_scan_active" in user_prompt

    @pytest.mark.asyncio
    async def test_missing_instruction_raises_llm_call_failed(self, agent_with_llm, sample_intent, sample_character_state):
        """Test raises LLMCallFailed when instruction missing"""
        mock_response = json.dumps({
            "tactical_guidance": "Some guidance",
            # Missing instruction
        })
        agent_with_llm._llm_client.call = AsyncMock(return_value=mock_response)

        with pytest.raises(LLMCallFailed, match="missing required instruction field"):
            await agent_with_llm.create_character_directive(
                intent=sample_intent,
                character_state=sample_character_state,
            )

    @pytest.mark.asyncio
    async def test_invalid_json_raises_llm_call_failed(self, agent_with_llm, sample_intent, sample_character_state):
        """Test raises LLMCallFailed when LLM returns invalid JSON"""
        agent_with_llm._llm_client.call = AsyncMock(return_value="Not JSON")

        with pytest.raises(LLMCallFailed, match="Failed to parse directive JSON"):
            await agent_with_llm.create_character_directive(
                intent=sample_intent,
                character_state=sample_character_state,
            )

    @pytest.mark.asyncio
    async def test_optional_fields_can_be_omitted(self, agent_with_llm, sample_intent, sample_character_state):
        """Test directive valid with only required instruction field"""
        mock_response = json.dumps({
            "instruction": "Disable the ship",
            # Omit tactical_guidance and emotional_tone
        })
        agent_with_llm._llm_client.call = AsyncMock(return_value=mock_response)

        directive = await agent_with_llm.create_character_directive(
            intent=sample_intent,
            character_state=sample_character_state,
        )

        assert directive.instruction == "Disable the ship"
        assert directive.tactical_guidance is None
        assert directive.emotional_tone is None


class TestFormulatingClarifyingQuestion:
    """Test formulate_clarifying_question method (DM Q&A phase)"""

    @pytest.fixture
    def agent_with_llm(self, standard_personality, mock_openai_client):
        """Create agent with LLM client for clarifying questions"""
        return BasePersonaAgent(
            agent_id="agent_test_001",
            personality=standard_personality,
            character_number=3,
            openai_client=mock_openai_client,
        )

    @pytest.mark.asyncio
    async def test_formulate_question_without_openai_raises_error(self, standard_personality):
        """Test method fails when openai_client not provided"""
        agent = BasePersonaAgent(
            agent_id="agent_test_001",
            personality=standard_personality,
            character_number=3,
            # No openai_client
        )

        with pytest.raises(RuntimeError, match="requires openai_client"):
            await agent.formulate_clarifying_question(
                dm_narration="You see a door",
                retrieved_memories=[],
                prior_qa=[],
            )

    @pytest.mark.asyncio
    async def test_returns_question_when_has_question_true(self, agent_with_llm):
        """Test returns question dict when LLM indicates has_question=true"""
        mock_response = json.dumps({
            "has_question": True,
            "question": "How far away is the door?",
            "reasoning": "Distance affects tactical approach",
        })
        agent_with_llm._llm_client.call = AsyncMock(return_value=mock_response)

        result = await agent_with_llm.formulate_clarifying_question(
            dm_narration="You see a door at the end of the hall",
            retrieved_memories=[],
            prior_qa=[],
        )

        assert result is not None
        assert result["question"] == "How far away is the door?"
        assert result["reasoning"] == "Distance affects tactical approach"

    @pytest.mark.asyncio
    async def test_returns_none_when_has_question_false(self, agent_with_llm):
        """Test returns None when LLM indicates has_question=false"""
        mock_response = json.dumps({
            "has_question": False,
        })
        agent_with_llm._llm_client.call = AsyncMock(return_value=mock_response)

        result = await agent_with_llm.formulate_clarifying_question(
            dm_narration="You see a door",
            retrieved_memories=[],
            prior_qa=[],
        )

        assert result is None

    @pytest.mark.asyncio
    async def test_includes_prior_qa_in_prompt(self, agent_with_llm):
        """Test includes prior Q&A in prompt for follow-up questions"""
        prior_msg_1 = Message(
            message_id=str(uuid4()),
            channel=MessageChannel.OOC,
            from_agent="agent_test_001",
            to_agents=None,
            content="How far is the door?",
            timestamp=datetime.now(),
            message_type=MessageType.CLARIFICATION_QUESTION,
            phase="dm_clarification",
            turn_number=1,
            session_number=1,
        )
        prior_msg_2 = Message(
            message_id=str(uuid4()),
            channel=MessageChannel.OOC,
            from_agent="dm",
            to_agents=None,
            content="About 20 meters away",
            timestamp=datetime.now(),
            message_type=MessageType.CLARIFICATION_ANSWER,
            phase="dm_clarification",
            turn_number=1,
            session_number=1,
        )

        actual_calls = []

        async def capture_call(*args, **kwargs):
            actual_calls.append((args, kwargs))
            return json.dumps({"has_question": False})

        agent_with_llm._llm_client.call = AsyncMock(side_effect=capture_call)

        await agent_with_llm.formulate_clarifying_question(
            dm_narration="You see a door",
            retrieved_memories=[],
            prior_qa=[prior_msg_1, prior_msg_2],
        )

        # Verify prior Q&A in user prompt
        user_prompt = actual_calls[0][0][1]
        assert "You: How far is the door?" in user_prompt
        assert "DM: About 20 meters away" in user_prompt

    @pytest.mark.asyncio
    async def test_formats_memories_correctly(self, agent_with_llm):
        """Test formats retrieved memories in prompt"""
        memories = [
            {"fact": "Doors often have traps", "confidence": 0.9},
            {"fact": "Always check for alarms", "confidence": 0.8},
        ]

        actual_calls = []

        async def capture_call(*args, **kwargs):
            actual_calls.append((args, kwargs))
            return json.dumps({"has_question": False})

        agent_with_llm._llm_client.call = AsyncMock(side_effect=capture_call)

        await agent_with_llm.formulate_clarifying_question(
            dm_narration="You see a door",
            retrieved_memories=memories,
            prior_qa=[],
        )

        user_prompt = actual_calls[0][0][1]
        assert "Doors often have traps" in user_prompt
        assert "0.9" in user_prompt or "0.90" in user_prompt

    @pytest.mark.asyncio
    async def test_raises_llm_call_failed_on_invalid_json(self, agent_with_llm):
        """Test raises LLMCallFailed when LLM returns invalid JSON"""
        agent_with_llm._llm_client.call = AsyncMock(return_value="Not JSON")

        with pytest.raises(LLMCallFailed, match="Failed to parse clarifying question JSON"):
            await agent_with_llm.formulate_clarifying_question(
                dm_narration="You see a door",
                retrieved_memories=[],
                prior_qa=[],
            )

    @pytest.mark.asyncio
    async def test_raises_error_when_has_question_true_but_no_question(self, agent_with_llm):
        """Test raises LLMCallFailed when has_question=true but question text missing"""
        mock_response = json.dumps({
            "has_question": True,
            # Missing question field
        })
        agent_with_llm._llm_client.call = AsyncMock(return_value=mock_response)

        with pytest.raises(LLMCallFailed, match="has_question=true but provided no question text"):
            await agent_with_llm.formulate_clarifying_question(
                dm_narration="You see a door",
                retrieved_memories=[],
                prior_qa=[],
            )

    @pytest.mark.asyncio
    async def test_provides_default_reasoning_if_missing(self, agent_with_llm):
        """Test provides default reasoning if LLM omits it"""
        mock_response = json.dumps({
            "has_question": True,
            "question": "Is the door locked?",
            # Missing reasoning
        })
        agent_with_llm._llm_client.call = AsyncMock(return_value=mock_response)

        result = await agent_with_llm.formulate_clarifying_question(
            dm_narration="You see a door",
            retrieved_memories=[],
            prior_qa=[],
        )

        assert result["reasoning"] == "No reasoning provided"


class TestPersonalityInfluence:
    """Test personality trait influence on agent behavior"""

    @pytest.mark.asyncio
    async def test_analytical_personality_produces_detailed_plans(
        self, high_detail_personality, mock_openai_client, mock_graphiti_client
    ):
        """Test high analytical score leads to detailed strategic discussion"""
        agent = BasePersonaAgent(
            agent_id="agent_analytical_001",
            personality=high_detail_personality,
            character_number=3,
            memory=mock_graphiti_client,
            openai_client=mock_openai_client,
        )

        mock_graphiti_client.search.return_value = []

        actual_calls = []

        async def capture_call(*args, **kwargs):
            actual_calls.append((args, kwargs))
            return "Detailed analysis of the situation..."

        agent._llm_client.call = AsyncMock(side_effect=capture_call)

        await agent.participate_in_ooc_discussion(
            dm_narration="You see a complex puzzle",
            other_messages=[],
        )

        # Verify high analytical score reflected in prompt
        system_prompt = actual_calls[0][0][0]
        assert "0.8" in system_prompt or "0.80" in system_prompt  # analytical_score

    @pytest.mark.asyncio
    async def test_risk_tolerant_personality_suggests_bold_actions(
        self, risk_taker_personality, mock_openai_client
    ):
        """Test high risk tolerance influences strategic intent"""
        agent = BasePersonaAgent(
            agent_id="agent_bold_001",
            personality=risk_taker_personality,
            character_number=3,
            openai_client=mock_openai_client,
        )

        actual_calls = []

        async def capture_call(*args, **kwargs):
            actual_calls.append((args, kwargs))
            return json.dumps({
                "strategic_goal": "Charge ahead boldly",
                "reasoning": "Best defense is a good offense",
                "risk_assessment": "High risk, high reward",
            })

        agent._llm_client.call = AsyncMock(side_effect=capture_call)

        intent = await agent.formulate_strategic_intent(
            discussion_summary="Should we attack or retreat?"
        )

        # Verify personality traits in system prompt
        system_prompt = actual_calls[0][0][0]
        assert "0.9" in system_prompt or "0.90" in system_prompt  # risk_tolerance=0.9

        assert "bold" in intent.strategic_goal.lower()

    @pytest.mark.asyncio
    async def test_cooperativeness_influences_directive_style(
        self, standard_personality, mock_openai_client
    ):
        """Test cooperativeness influences how directives are phrased"""
        agent = BasePersonaAgent(
            agent_id="agent_team_001",
            personality=standard_personality,
            character_number=3,
            openai_client=mock_openai_client,
        )

        actual_calls = []

        async def capture_call(*args, **kwargs):
            actual_calls.append((args, kwargs))
            return json.dumps({
                "instruction": "Work with the team to solve this",
                "emotional_tone": "collaborative",
            })

        agent._llm_client.call = AsyncMock(side_effect=capture_call)

        intent = Intent(
            agent_id="agent_team_001",
            strategic_goal="Solve puzzle together",
            reasoning="Teamwork is key",
        )

        character_state = CharacterState(
            character_id="char_test_001",
            current_location="Room",
        )

        directive = await agent.create_character_directive(
            intent=intent,
            character_state=character_state,
        )

        # High cooperativeness (0.7) should influence prompt
        system_prompt = actual_calls[0][0][0]
        assert "0.7" in system_prompt or "0.70" in system_prompt  # cooperativeness


class TestErrorHandling:
    """Test error handling and edge cases"""

    @pytest.mark.asyncio
    async def test_llm_api_failure_propagates(self, standard_personality, mock_openai_client, mock_graphiti_client):
        """Test LLM API failure raises LLMCallFailed"""
        agent = BasePersonaAgent(
            agent_id="agent_test_001",
            personality=standard_personality,
            character_number=3,
            memory=mock_graphiti_client,
            openai_client=mock_openai_client,
        )

        mock_graphiti_client.search.return_value = []

        # Mock LLM to raise exception
        agent._llm_client.call = AsyncMock(side_effect=LLMCallFailed("API Error"))

        with pytest.raises(InvalidMessageFormat):  # Wrapped in InvalidMessageFormat
            await agent.participate_in_ooc_discussion(
                dm_narration="Test narration",
                other_messages=[],
            )

    @pytest.mark.asyncio
    async def test_handles_personality_edge_values(self, mock_openai_client, mock_graphiti_client):
        """Test handles personality traits at edge values (0.0, 1.0)"""
        extreme_personality = PlayerPersonality(
            analytical_score=1.0,
            risk_tolerance=0.0,
            detail_oriented=1.0,
            emotional_memory=0.0,
            assertiveness=1.0,
            cooperativeness=0.0,
            openness=1.0,
            rule_adherence=0.0,
            roleplay_intensity=1.0,
        )

        agent = BasePersonaAgent(
            agent_id="agent_extreme_001",
            personality=extreme_personality,
            character_number=3,
            memory=mock_graphiti_client,
            openai_client=mock_openai_client,
        )

        mock_graphiti_client.search.return_value = []

        # Should not crash with extreme values
        message = await agent.participate_in_ooc_discussion(
            dm_narration="Test",
            other_messages=[],
        )

        assert isinstance(message, Message)

    @pytest.mark.asyncio
    async def test_empty_memory_list_handled(self, standard_personality, mock_openai_client, mock_graphiti_client):
        """Test empty memory list doesn't cause errors"""
        agent = BasePersonaAgent(
            agent_id="agent_test_001",
            personality=standard_personality,
            character_number=3,
            memory=mock_graphiti_client,
            openai_client=mock_openai_client,
        )

        mock_graphiti_client.search.return_value = []

        message = await agent.participate_in_ooc_discussion(
            dm_narration="Test narration",
            other_messages=[],
        )

        assert isinstance(message, Message)

    @pytest.mark.asyncio
    async def test_format_memories_with_empty_list(self, standard_personality, mock_openai_client):
        """Test _format_memories handles empty list correctly"""
        agent = BasePersonaAgent(
            agent_id="agent_test_001",
            personality=standard_personality,
            character_number=3,
            openai_client=mock_openai_client,
        )

        result = agent._format_memories([])

        assert result == "No relevant memories found."

    @pytest.mark.asyncio
    async def test_format_memories_with_valid_memories(self, standard_personality, mock_openai_client):
        """Test _format_memories formats memories correctly"""
        agent = BasePersonaAgent(
            agent_id="agent_test_001",
            personality=standard_personality,
            character_number=3,
            openai_client=mock_openai_client,
        )

        memories = [
            {"fact": "Doors have traps", "confidence": 0.9},
            {"fact": "Always be cautious", "confidence": 0.8},
        ]

        result = agent._format_memories(memories)

        assert "Doors have traps" in result
        assert "0.9" in result or "0.90" in result
        assert "Always be cautious" in result
