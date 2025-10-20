# ABOUTME: Integration tests for game mechanics awareness in player layer decisions.
# ABOUTME: Verifies mechanics knowledge improves strategic decision-making without breaking character layer separation.

from datetime import datetime

import pytest

from src.agents.base_persona import BasePersonaAgent
from src.agents.character import CharacterAgent
from src.models.game_state import GamePhase
from src.models.messages import Message, MessageChannel, MessageType
from src.models.personality import (
    CharacterRole,
    CharacterSheet,
    CharacterStyle,
    PlayerPersonality,
)


class TestMechanicsAwarenessIntegration:
    """Integration tests verifying mechanics awareness enhances player decisions"""

    @pytest.mark.asyncio
    async def test_player_aware_of_character_number_strengths(
        self,
        mock_openai_client,
        mock_graphiti_client,
    ):
        """Verify player layer knows character's mechanical strengths/weaknesses"""
        from unittest.mock import AsyncMock, MagicMock

        from src.memory.corrupted_temporal import CorruptedTemporalMemory

        # Create mock memory
        mock_memory = MagicMock(spec=CorruptedTemporalMemory)
        mock_memory.search = AsyncMock(return_value=[])

        # Create LASERS specialist (number 2)
        personality = PlayerPersonality(
            analytical_score=0.8,
            risk_tolerance=0.5,
            detail_oriented=0.7,
            emotional_memory=0.3,
            assertiveness=0.6,
            cooperativeness=0.7,
            openness=0.6,
            rule_adherence=0.7,
            roleplay_intensity=0.6,
        )

        lasers_agent = BasePersonaAgent(
            agent_id="agent_test_lasers",
            personality=personality,
            character_number=2,  # LASERS specialist
            memory=mock_memory,
            openai_client=mock_openai_client,
        )

        # Verify agent can access mechanics context
        mechanics = lasers_agent._build_mechanics_context()
        assert "Your character's number: 2" in mechanics
        assert "LASERS" in mechanics
        assert "FEELINGS" in mechanics
        assert "17%" in mechanics or "16%" in mechanics  # LASERS success rate

    @pytest.mark.asyncio
    async def test_character_layer_has_no_mechanics_knowledge(
        self,
        mock_openai_client,
    ):
        """Verify character layer does NOT have mechanics knowledge (FR-008 compliance)"""
        character_sheet = CharacterSheet(
            name="Test Engineer",
            style=CharacterStyle.INTREPID,
            role=CharacterRole.ENGINEER,
            number=2,  # LASERS-oriented
            character_goal="Fix the ship",
            equipment=["Toolkit"],
            speech_patterns=["Speaks technically"],
            mannerisms=["Adjusts tools"],
        )

        character_agent = CharacterAgent(
            character_id="char_test",
            character_sheet=character_sheet,
            openai_client=mock_openai_client,
        )

        # Character should NOT have mechanics helper
        assert not hasattr(character_agent, "_build_mechanics_context")
        assert not hasattr(character_agent, "character_number")

    def test_mechanics_section_personalized_to_number(self):
        """Verify mechanics section personalizes to different character numbers"""
        from src.config.prompts import build_game_mechanics_section

        # Test each number produces personalized output
        number_2 = build_game_mechanics_section(2)
        number_5 = build_game_mechanics_section(5)

        # Number 2 should emphasize LASERS strength
        assert "LASERS (technical/logical actions)" in number_2
        assert "excel at technology" in number_2

        # Number 5 should emphasize FEELINGS strength
        assert "FEELINGS (social/emotional actions)" in number_5
        assert "excel at intuition" in number_5

        # Probability calculations should differ
        assert "17%" in number_2 or "16%" in number_2  # LASERS: 1/6
        assert "67%" in number_5 or "66%" in number_5  # LASERS: 4/6

    @pytest.mark.asyncio
    async def test_player_can_make_mechanically_informed_decisions(
        self,
        mock_openai_client,
        mock_graphiti_client,
    ):
        """Verify player can access mechanics for strategic planning"""
        from unittest.mock import AsyncMock, MagicMock

        from src.memory.corrupted_temporal import CorruptedTemporalMemory

        mock_memory = MagicMock(spec=CorruptedTemporalMemory)
        mock_memory.search = AsyncMock(return_value=[])

        personality = PlayerPersonality(
            analytical_score=0.7,
            risk_tolerance=0.6,
            detail_oriented=0.6,
            emotional_memory=0.4,
            assertiveness=0.6,
            cooperativeness=0.7,
            openness=0.7,
            rule_adherence=0.6,
            roleplay_intensity=0.6,
        )

        # Create player with specific number
        agent = BasePersonaAgent(
            agent_id="agent_strategic",
            personality=personality,
            character_number=3,  # Balanced
            memory=mock_memory,
            openai_client=mock_openai_client,
        )

        # Participate in discussion - should succeed without error
        messages = [
            Message(
                message_id="msg_1",
                channel=MessageChannel.OOC,
                from_agent="agent_other",
                content="Should we hack the system or sweet-talk the guard?",
                timestamp=datetime.now(),
                turn_number=1,
                session_number=1,
                message_type=MessageType.DISCUSSION,
                phase=GamePhase.OOC_DISCUSSION.value,
            )
        ]

        result = await agent.participate_in_ooc_discussion(
            dm_narration="A guard blocks your path. The system terminal is nearby.",
            other_messages=messages,
        )

        # Should successfully generate response with mechanics awareness
        assert isinstance(result, Message)
        assert len(result.content) > 0
        assert result.channel == MessageChannel.OOC
