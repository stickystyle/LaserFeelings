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
    async def test_prompt_focuses_on_roleplay_not_mechanics(
        self, character_agent, mock_openai_client
    ):
        """Test that the prompt focuses on roleplay rather than mechanics education"""
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

            # Assert - check prompt is roleplay-focused
            call_args = mock_call.call_args
            user_prompt = call_args[0][1]

            # Should focus on acting, not mechanics
            assert "IN CHARACTER" in user_prompt
            assert "narrative" in user_prompt
            assert "ATTEMPT" in user_prompt.upper()

            # Should NOT have detailed mechanics explanations (removed from character layer)
            assert "LASER FEELINGS" not in user_prompt
            assert "roll UNDER" not in user_prompt
            assert "roll OVER" not in user_prompt
            # Should be concise compared to old prompt which had extensive mechanics education
            # Note: The addition of valid_character_ids section increased line count slightly
            assert len(user_prompt.split('\n')) < 60

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


class TestFormatIcHistory:
    """Test _format_ic_history() method for message history formatting"""

    def test_format_ic_history_with_none(self, character_agent):
        """Test that None returns empty string"""
        # Act
        result = character_agent._format_ic_history(None)

        # Assert
        assert result == ""

    def test_format_ic_history_with_empty_list(self, character_agent):
        """Test that empty list returns empty string"""
        # Act
        result = character_agent._format_ic_history([])

        # Assert
        assert result == ""

    def test_format_ic_history_with_single_message(self, character_agent):
        """Test formatting a single message"""
        # Arrange
        ic_messages = [
            {
                "from_agent": "Zara-7",
                "content": "I attempt to repair the console"
            }
        ]

        # Act
        result = character_agent._format_ic_history(ic_messages)

        # Assert
        expected = "Recent events you've witnessed:\n- Zara-7: I attempt to repair the console\n"
        assert result == expected

    def test_format_ic_history_with_multiple_messages(self, character_agent):
        """Test formatting multiple messages from different characters"""
        # Arrange
        ic_messages = [
            {
                "from_agent": "Zara-7",
                "content": "I attempt to repair the console"
            },
            {
                "from_agent": "dm",
                "content": "The console sparks as you work on it"
            },
            {
                "from_agent": "Kael",
                "content": "I move to cover the engineer"
            }
        ]

        # Act
        result = character_agent._format_ic_history(ic_messages)

        # Assert
        expected = (
            "Recent events you've witnessed:\n"
            "- Zara-7: I attempt to repair the console\n"
            "- dm: The console sparks as you work on it\n"
            "- Kael: I move to cover the engineer\n"
        )
        assert result == expected

    def test_format_ic_history_with_missing_keys(self, character_agent):
        """Test graceful handling of messages with missing from_agent or content keys"""
        # Arrange
        ic_messages = [
            {
                "from_agent": "Zara-7",
                "content": "I attempt to scan"
            },
            {
                # Missing from_agent
                "content": "The scan reveals something"
            },
            {
                "from_agent": "dm",
                # Missing content
            },
            {
                "from_agent": "Kael",
                "content": "I respond to the findings"
            }
        ]

        # Act
        result = character_agent._format_ic_history(ic_messages)

        # Assert
        expected = (
            "Recent events you've witnessed:\n"
            "- Zara-7: I attempt to scan\n"
            "- unknown: The scan reveals something\n"
            "- dm: \n"
            "- Kael: I respond to the findings\n"
        )
        assert result == expected


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


class TestValidCharacterIdsForHelping:
    """Test valid_character_ids parameter for helping mechanic"""

    @pytest.mark.asyncio
    async def test_perform_action_with_valid_helping_character(
        self, character_agent, mock_openai_client
    ):
        """Test that action succeeds with valid helping_character_id from provided list"""
        # Arrange
        directive = Directive(
            from_player="agent_alex_001",
            to_character="char_zara_001",
            instruction="Help Kai repair the engine",
        )
        scene_context = "Kai is struggling with the damaged engine."
        valid_character_ids = ["char_kai_004", "char_quinn_003", "char_zara_001"]

        llm_response = {
            "narrative_text": "I provide technical assistance to Kai with my tools.",
            "task_type": "lasers",
            "is_helping": True,
            "helping_character_id": "char_kai_004",
            "help_justification": "Providing technical expertise for engine repair"
        }

        # Mock the LLM client
        with patch.object(
            character_agent._llm_client, 'call', new_callable=AsyncMock
        ) as mock_call:
            mock_call.return_value = json.dumps(llm_response)

            # Act
            action = await character_agent.perform_action(
                directive, scene_context, valid_character_ids=valid_character_ids
            )

            # Assert
            assert action.is_helping is True
            assert action.helping_character_id == "char_kai_004"
            assert action.help_justification == "Providing technical expertise for engine repair"
            assert action.narrative_text == "I provide technical assistance to Kai with my tools."

    @pytest.mark.asyncio
    async def test_perform_action_rejects_invalid_helping_character(
        self, character_agent, mock_openai_client
    ):
        """Test that Pydantic validation fails when helping_character_id doesn't match pattern"""
        # Arrange
        directive = Directive(
            from_player="agent_alex_001",
            to_character="char_zara_001",
            instruction="Help with the task",
        )
        scene_context = "Someone needs help."
        valid_character_ids = ["char_kai_004"]

        # LLM returns invalid character ID (like an NPC name)
        llm_response = {
            "narrative_text": "I help Zorgon with the controls.",
            "task_type": "lasers",
            "is_helping": True,
            "helping_character_id": "Zorgon",  # Invalid - doesn't match pattern
            "help_justification": "Assisting with controls"
        }

        # Mock the LLM client
        with patch.object(
            character_agent._llm_client, 'call', new_callable=AsyncMock
        ) as mock_call:
            mock_call.return_value = json.dumps(llm_response)

            # Act & Assert
            # Pydantic should raise ValidationError due to pattern mismatch
            with pytest.raises(Exception) as exc_info:
                await character_agent.perform_action(
                    directive, scene_context, valid_character_ids=valid_character_ids
                )

            # Check that it's a validation error (could be wrapped)
            assert "pattern" in str(exc_info.value).lower() or "char_" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_perform_action_with_npc_in_scene(
        self, character_agent, mock_openai_client
    ):
        """Test that NPC actions work without is_helping (it's the character's own action)"""
        # Arrange
        directive = Directive(
            from_player="agent_alex_001",
            to_character="char_zara_001",
            instruction="Disable Zorgon's ship systems",
        )
        scene_context = "Zorgon's ship is nearby. The NPC Zorgon is hostile."
        valid_character_ids = ["char_kai_004", "char_zara_001"]

        # This is Zara's action (disabling ship), NOT helping Zorgon
        llm_response = {
            "narrative_text": "I attempt to remotely disable Zorgon's ship propulsion systems.",
            "task_type": "lasers",
            "is_helping": False,
            "helping_character_id": None,
            "is_expert": True,
            "expert_justification": "Ship systems hacking is my specialty"
        }

        # Mock the LLM client
        with patch.object(
            character_agent._llm_client, 'call', new_callable=AsyncMock
        ) as mock_call:
            mock_call.return_value = json.dumps(llm_response)

            # Act
            action = await character_agent.perform_action(
                directive, scene_context, valid_character_ids=valid_character_ids
            )

            # Assert - should succeed without is_helping
            assert action.is_helping is False
            assert action.helping_character_id is None
            expected = "I attempt to remotely disable Zorgon's ship propulsion systems."
            assert action.narrative_text == expected

    @pytest.mark.asyncio
    async def test_perform_action_without_valid_character_ids(
        self, character_agent, mock_openai_client
    ):
        """Test backward compatibility when valid_character_ids is None"""
        # Arrange
        directive = Directive(
            from_player="agent_alex_001",
            to_character="char_zara_001",
            instruction="Scan the area",
        )
        scene_context = "Unknown territory."

        llm_response = {
            "narrative_text": "I attempt to scan for life signs and hazards.",
            "task_type": "lasers",
            "is_helping": False,
        }

        # Mock the LLM client
        with patch.object(
            character_agent._llm_client, 'call', new_callable=AsyncMock
        ) as mock_call:
            mock_call.return_value = json.dumps(llm_response)

            # Act - call without valid_character_ids parameter (backward compatibility)
            action = await character_agent.perform_action(directive, scene_context)

            # Assert
            assert action.narrative_text == "I attempt to scan for life signs and hazards."
            assert action.is_helping is False

    @pytest.mark.asyncio
    async def test_prompt_includes_valid_character_ids_when_provided(
        self, character_agent, mock_openai_client
    ):
        """Test that the prompt includes valid character IDs section when provided"""
        # Arrange
        directive = Directive(
            from_player="agent_alex_001",
            to_character="char_zara_001",
            instruction="Help with repairs",
        )
        scene_context = "Repair scenario."
        valid_character_ids = ["char_kai_004", "char_quinn_003"]

        llm_response = {
            "narrative_text": "I help with repairs.",
            "task_type": "lasers",
        }

        # Mock the LLM client
        with patch.object(
            character_agent._llm_client, 'call', new_callable=AsyncMock
        ) as mock_call:
            mock_call.return_value = json.dumps(llm_response)

            # Act
            await character_agent.perform_action(
                directive, scene_context, valid_character_ids=valid_character_ids
            )

            # Assert - check prompt includes valid character IDs
            call_args = mock_call.call_args
            user_prompt = call_args[0][1]

            assert "VALID CHARACTERS IN YOUR PARTY:" in user_prompt
            assert "char_kai_004" in user_prompt
            assert "char_quinn_003" in user_prompt
            assert "is_helping" in user_prompt.lower()
            assert "party member" in user_prompt.lower()
            assert "NOT NPCs" in user_prompt or "not npc" in user_prompt.lower()

    @pytest.mark.asyncio
    async def test_prompt_shows_none_specified_when_no_valid_ids(
        self, character_agent, mock_openai_client
    ):
        """Test that the prompt shows (None specified) when valid_character_ids is empty or None"""
        # Arrange
        directive = Directive(
            from_player="agent_alex_001",
            to_character="char_zara_001",
            instruction="Do something",
        )
        scene_context = "Scene."

        llm_response = {
            "narrative_text": "I do something.",
            "task_type": "lasers",
        }

        # Mock the LLM client
        with patch.object(
            character_agent._llm_client, 'call', new_callable=AsyncMock
        ) as mock_call:
            mock_call.return_value = json.dumps(llm_response)

            # Act - call with None
            await character_agent.perform_action(directive, scene_context, valid_character_ids=None)

            # Assert
            call_args = mock_call.call_args
            user_prompt = call_args[0][1]

            assert "VALID CHARACTERS IN YOUR PARTY:" in user_prompt
            assert "(None specified)" in user_prompt
