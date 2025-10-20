# ABOUTME: Unit tests for CharacterAgent focusing on action generation and gm_question extraction.
# ABOUTME: Tests cover JSON parsing, validation, and prompt structure for LASER FEELINGS mechanic.

import json
from unittest.mock import AsyncMock, patch

import pytest

from src.agents.character import CharacterAgent
from src.agents.exceptions import ValidationFailed
from src.models.agent_actions import Directive
from src.models.personality import CharacterRole, CharacterSheet, CharacterStyle


@pytest.fixture
def character_sheet():
    """Basic character sheet for testing"""
    return CharacterSheet(
        name="Zara-7",
        style=CharacterStyle.ANDROID,
        role=CharacterRole.ENGINEER,
        number=2,
        player_goal="Fix everything that breaks",
        character_goal="Achieve perfect efficiency",
        equipment=["Multi-tool", "Scanner", "Welding torch"],
        speech_patterns=["Speaks precisely", "Uses technical jargon"],
        mannerisms=["Tilts head when thinking", "Blinks slowly"],
        approach_bias="lasers"
    )


@pytest.fixture
def mock_openai_client():
    """Mock OpenAI client for testing"""
    return AsyncMock()


@pytest.fixture
def character_agent(character_sheet, mock_openai_client):
    """CharacterAgent instance with mocked dependencies"""
    return CharacterAgent(
        character_id="char_zara_001",
        character_sheet=character_sheet,
        personality=None,
        memory=None,
        openai_client=mock_openai_client,
        model="gpt-4o",
        temperature=0.8,
    )


class TestPerformActionGmQuestion:
    """Test gm_question field extraction and prompt structure"""

    @pytest.mark.asyncio
    async def test_gm_question_extracted_when_provided(
        self, character_agent, mock_openai_client
    ):
        """Test that gm_question is correctly extracted from LLM response"""
        # Arrange
        directive = Directive(
            from_player="agent_alex_001",
            to_character="char_zara_001",
            instruction="Examine the alien signal",
        )
        scene_context = "You're in the engineering bay with alien signals on screen."

        llm_response = {
            "narrative_text": "I attempt to decode the alien signal patterns.",
            "task_type": "lasers",
            "is_expert": True,
            "expert_justification": "As the ship's Engineer, signal analysis is my specialty",
            "gm_question": "What is the true purpose of this signal?"
        }

        # Mock the LLM client
        with patch.object(
            character_agent._llm_client, 'call', new_callable=AsyncMock
        ) as mock_call:
            mock_call.return_value = json.dumps(llm_response)

            # Act
            action = await character_agent.perform_action(directive, scene_context)

            # Assert
            assert action.gm_question == "What is the true purpose of this signal?"
            assert action.narrative_text == "I attempt to decode the alien signal patterns."
            assert action.task_type == "lasers"

    @pytest.mark.asyncio
    async def test_gm_question_defaults_to_none_when_not_provided(
        self, character_agent, mock_openai_client
    ):
        """Test that gm_question defaults to None when not in LLM response"""
        # Arrange
        directive = Directive(
            from_player="agent_alex_001",
            to_character="char_zara_001",
            instruction="Repair the fuel cell",
        )
        scene_context = "You're near the damaged fuel cell."

        llm_response = {
            "narrative_text": "I attempt to repair the faulty wiring.",
            "task_type": "lasers",
            "is_expert": True,
            "expert_justification": "Fuel cell repair is my core expertise"
            # Note: gm_question is omitted
        }

        # Mock the LLM client
        with patch.object(
            character_agent._llm_client, 'call', new_callable=AsyncMock
        ) as mock_call:
            mock_call.return_value = json.dumps(llm_response)

            # Act
            action = await character_agent.perform_action(directive, scene_context)

            # Assert
            assert action.gm_question is None
            assert action.narrative_text == "I attempt to repair the faulty wiring."

    @pytest.mark.asyncio
    async def test_gm_question_accepts_null_explicitly(
        self, character_agent, mock_openai_client
    ):
        """Test that gm_question can be explicitly set to null"""
        # Arrange
        directive = Directive(
            from_player="agent_alex_001",
            to_character="char_zara_001",
            instruction="Open the door",
        )
        scene_context = "You're standing in front of a locked door."

        llm_response = {
            "narrative_text": "I attempt to override the door lock.",
            "task_type": "lasers",
            "gm_question": None  # Explicitly null
        }

        # Mock the LLM client
        with patch.object(
            character_agent._llm_client, 'call', new_callable=AsyncMock
        ) as mock_call:
            mock_call.return_value = json.dumps(llm_response)

            # Act
            action = await character_agent.perform_action(directive, scene_context)

            # Assert
            assert action.gm_question is None

    @pytest.mark.asyncio
    async def test_prompt_mentions_laser_feelings(
        self, character_agent, mock_openai_client
    ):
        """Test that the prompt includes LASER FEELINGS documentation"""
        # Arrange
        directive = Directive(
            from_player="agent_alex_001",
            to_character="char_zara_001",
            instruction="Scan the area",
        )
        scene_context = "You're in an unknown location."

        llm_response = {
            "narrative_text": "I attempt to scan the surroundings.",
            "task_type": "lasers",
        }

        # Mock the LLM client
        with patch.object(
            character_agent._llm_client, 'call', new_callable=AsyncMock
        ) as mock_call:
            mock_call.return_value = json.dumps(llm_response)

            # Act
            await character_agent.perform_action(directive, scene_context)

            # Assert - check the prompt mentions gm_question field
            call_args = mock_call.call_args
            user_prompt = call_args[0][1]

            # Check for gm_question field (simplified - no mechanics explanation)
            assert "gm_question" in user_prompt
            assert "special insight" in user_prompt

    @pytest.mark.asyncio
    async def test_prompt_includes_example_questions(
        self, character_agent, mock_openai_client
    ):
        """Test that the prompt includes example questions for LASER FEELINGS"""
        # Arrange
        directive = Directive(
            from_player="agent_alex_001",
            to_character="char_zara_001",
            instruction="Investigate the signal",
        )
        scene_context = "Strange signals detected."

        llm_response = {
            "narrative_text": "I attempt to investigate the signal source.",
            "task_type": "lasers",
        }

        # Mock the LLM client
        with patch.object(
            character_agent._llm_client, 'call', new_callable=AsyncMock
        ) as mock_call:
            mock_call.return_value = json.dumps(llm_response)

            # Act
            await character_agent.perform_action(directive, scene_context)

            # Assert - check for example questions
            call_args = mock_call.call_args
            user_prompt = call_args[0][1]

            # Check for example questions from the Lasers & Feelings rules
            assert "What are they really feeling?" in user_prompt
            assert "Who's behind this?" in user_prompt
            assert "What should I be on the lookout for?" in user_prompt

    @pytest.mark.asyncio
    async def test_json_schema_includes_gm_question_field(
        self, character_agent, mock_openai_client
    ):
        """Test that the JSON schema in the prompt includes gm_question"""
        # Arrange
        directive = Directive(
            from_player="agent_alex_001",
            to_character="char_zara_001",
            instruction="Analyze the data",
        )
        scene_context = "Data stream on screen."

        llm_response = {
            "narrative_text": "I attempt to analyze the incoming data.",
            "task_type": "lasers",
        }

        # Mock the LLM client
        with patch.object(
            character_agent._llm_client, 'call', new_callable=AsyncMock
        ) as mock_call:
            mock_call.return_value = json.dumps(llm_response)

            # Act
            await character_agent.perform_action(directive, scene_context)

            # Assert - check JSON schema includes gm_question
            call_args = mock_call.call_args
            user_prompt = call_args[0][1]

            # The JSON schema should include the gm_question field
            assert '"gm_question"' in user_prompt
            # Check it's positioned after help_justification (as per requirements)
            help_pos = user_prompt.find('"help_justification"')
            gm_question_pos = user_prompt.find('"gm_question"')
            assert help_pos < gm_question_pos, "gm_question should appear after help_justification"

    @pytest.mark.asyncio
    async def test_gm_question_with_all_dice_modifiers(
        self, character_agent, mock_openai_client
    ):
        """Test gm_question works alongside all other dice roll fields"""
        # Arrange
        directive = Directive(
            from_player="agent_alex_001",
            to_character="char_zara_001",
            instruction="Help another character repair systems",
        )
        scene_context = "Emergency repair situation."

        llm_response = {
            "narrative_text": "I assist with the repairs using my specialized tools.",
            "task_type": "lasers",
            "is_prepared": True,
            "prepared_justification": "I brought my advanced repair kit",
            "is_expert": True,
            "expert_justification": "Engineering is my specialty",
            "is_helping": True,
            "helping_character_id": "char_other_001",
            "help_justification": "Providing technical assistance",
            "gm_question": "What's the biggest risk in this repair?"
        }

        # Mock the LLM client
        with patch.object(
            character_agent._llm_client, 'call', new_callable=AsyncMock
        ) as mock_call:
            mock_call.return_value = json.dumps(llm_response)

            # Act
            action = await character_agent.perform_action(directive, scene_context)

            # Assert - all fields should be extracted correctly
            assert action.task_type == "lasers"
            assert action.is_prepared is True
            assert action.prepared_justification == "I brought my advanced repair kit"
            assert action.is_expert is True
            assert action.expert_justification == "Engineering is my specialty"
            assert action.is_helping is True
            assert action.helping_character_id == "char_other_001"
            assert action.help_justification == "Providing technical assistance"
            assert action.gm_question == "What's the biggest risk in this repair?"


class TestPerformActionValidation:
    """Test action validation (unrelated to gm_question but comprehensive)"""

    @pytest.mark.asyncio
    async def test_missing_narrative_text_raises_validation_failed(
        self, character_agent, mock_openai_client
    ):
        """Test that missing narrative_text raises ValidationFailed"""
        # Arrange
        directive = Directive(
            from_player="agent_alex_001",
            to_character="char_zara_001",
            instruction="Do something",
        )
        scene_context = "Scene context."

        llm_response = {
            "narrative_text": "",  # Empty narrative text
            "task_type": "lasers",
        }

        # Mock the LLM client
        with patch.object(
            character_agent._llm_client, 'call', new_callable=AsyncMock
        ) as mock_call:
            mock_call.return_value = json.dumps(llm_response)

            # Act & Assert
            with pytest.raises(
                ValidationFailed, match="Action missing required narrative_text field"
            ):
                await character_agent.perform_action(directive, scene_context)

    @pytest.mark.asyncio
    async def test_forbidden_language_raises_validation_failed(
        self, character_agent, mock_openai_client
    ):
        """Test that forbidden outcome language raises ValidationFailed"""
        # Arrange
        directive = Directive(
            from_player="agent_alex_001",
            to_character="char_zara_001",
            instruction="Attack the enemy",
        )
        scene_context = "Combat situation."

        llm_response = {
            "narrative_text": "I successfully kill the enemy.",  # Forbidden language
            "task_type": "lasers",
        }

        # Mock the LLM client
        with patch.object(
            character_agent._llm_client, 'call', new_callable=AsyncMock
        ) as mock_call:
            mock_call.return_value = json.dumps(llm_response)

            # Act & Assert
            with pytest.raises(ValidationFailed, match="forbidden outcome language"):
                await character_agent.perform_action(directive, scene_context)


class TestRuntimeDependencies:
    """Test runtime dependency validation"""

    @pytest.mark.asyncio
    async def test_perform_action_requires_openai_client(self):
        """Test that perform_action raises RuntimeError when openai_client is None"""
        # Arrange
        character_sheet = CharacterSheet(
            name="Test",
            style=CharacterStyle.ANDROID,
            role=CharacterRole.ENGINEER,
            number=2,
            player_goal="Goal",
            character_goal="Goal",
            equipment=[],
            approach_bias="lasers"
        )
        agent = CharacterAgent(
            character_id="char_test_001",
            character_sheet=character_sheet,
            personality=None,
            memory=None,
            openai_client=None,  # No client provided
        )

        directive = Directive(
            from_player="agent_test_001",
            to_character="char_test_001",
            instruction="Do something",
        )

        # Act & Assert
        with pytest.raises(RuntimeError, match="CharacterAgent requires openai_client"):
            await agent.perform_action(directive, "Scene context")
