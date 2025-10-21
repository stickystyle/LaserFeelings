# ABOUTME: Unit tests for LASER FEELINGS question phase in Textual DM interface.
# ABOUTME: Tests phase detection, question display, answer handling, and orchestrator integration.

from unittest.mock import MagicMock

import pytest
from textual.widgets import Input

from src.interface.dm_textual import DMTextualInterface
from src.orchestration.message_router import MessageRouter
from src.orchestration.turn_orchestrator import TurnOrchestrator


@pytest.fixture
def mock_orchestrator():
    """Mock TurnOrchestrator for testing"""
    return MagicMock(spec=TurnOrchestrator)


@pytest.fixture
def mock_router():
    """Mock MessageRouter for testing"""
    return MagicMock(spec=MessageRouter)


@pytest.fixture
def interface(mock_orchestrator, mock_router):
    """Create DMTextualInterface with mocked dependencies"""
    return DMTextualInterface(orchestrator=mock_orchestrator, router=mock_router)


class TestLaserFeelingsQuestionPhaseDetection:
    """Test detection of LASER FEELINGS question phase in display_turn_result"""

    def test_detects_laser_feelings_question_phase(self, interface):
        """Test that interface detects laser_feelings_question awaiting phase"""
        turn_result = {
            "awaiting_dm_input": True,
            "awaiting_phase": "laser_feelings_question",
            "laser_feelings_data": {
                "character_id": "char_zara_001",
                "gm_question": "What do you really want?",
            },
            "phase_completed": "dice_resolution",
        }

        # Mock write_game_log to avoid AttributeError
        interface.write_game_log = MagicMock()
        interface.update_turn_status = MagicMock()
        interface._get_character_name = MagicMock(return_value="Zara-7")

        interface.display_turn_result(turn_result)

        # Verify LASER FEELINGS question mode is activated
        assert interface._laser_feelings_question_mode is True

    def test_extracts_question_data_from_turn_result(self, interface):
        """Test that interface correctly extracts character's question from turn result"""
        turn_result = {
            "awaiting_dm_input": True,
            "awaiting_phase": "laser_feelings_question",
            "laser_feelings_data": {
                "character_id": "char_zara_001",
                "gm_question": "What is your greatest fear?",
            },
        }

        interface.write_game_log = MagicMock()
        interface.update_turn_status = MagicMock()
        interface._get_character_name = MagicMock(return_value="Zara-7")

        interface.display_turn_result(turn_result)

        # Verify data is stored
        assert interface._laser_feelings_question_data is not None
        assert interface._laser_feelings_question_data["character_id"] == "char_zara_001"
        assert (
            interface._laser_feelings_question_data["gm_question"]
            == "What is your greatest fear?"
        )

    def test_handles_missing_laser_feelings_data(self, interface):
        """Test graceful handling when laser_feelings_data is missing"""
        turn_result = {
            "awaiting_dm_input": True,
            "awaiting_phase": "laser_feelings_question",
            # Missing laser_feelings_data
        }

        interface.write_game_log = MagicMock()
        interface.update_turn_status = MagicMock()
        interface._get_character_name = MagicMock(return_value="Unknown")

        # Should not raise error
        interface.display_turn_result(turn_result)

        # Mode should still be activated
        assert interface._laser_feelings_question_mode is True


class TestQuestionDisplay:
    """Test display of character's LASER FEELINGS question to DM"""

    def test_displays_question_with_character_name(self, interface):
        """Test that character's question is displayed with their name"""
        turn_result = {
            "laser_feelings_data": {
                "character_id": "char_zara_001",
                "gm_question": "Do you trust me?",
            }
        }

        interface.write_game_log = MagicMock()
        interface._get_character_name = MagicMock(return_value="Zara-7")

        interface._show_laser_feelings_question_prompt(turn_result)

        # Verify character name is used
        interface._get_character_name.assert_called_once_with("char_zara_001")

        # Verify question is displayed
        calls = [str(call_obj) for call_obj in interface.write_game_log.call_args_list]
        assert any("Zara-7 asks:" in str(c) for c in calls)
        assert any("Do you trust me?" in str(c) for c in calls)

    def test_displays_fallback_when_no_question_text(self, interface):
        """Test fallback message when gm_question is None"""
        turn_result = {
            "laser_feelings_data": {
                "character_id": "char_alex_001",
                "gm_question": None,
            }
        }

        interface.write_game_log = MagicMock()
        interface._get_character_name = MagicMock(return_value="Alex")

        interface._show_laser_feelings_question_prompt(turn_result)

        # Verify fallback message
        calls = [str(call_obj) for call_obj in interface.write_game_log.call_args_list]
        assert any("rolled LASER FEELINGS and asked a question" in str(c) for c in calls)

    def test_displays_header_and_instructions(self, interface):
        """Test that header and instructions are shown"""
        turn_result = {
            "laser_feelings_data": {
                "character_id": "char_zara_001",
                "gm_question": "Why are we here?",
            }
        }

        interface.write_game_log = MagicMock()
        interface._get_character_name = MagicMock(return_value="Zara-7")

        interface._show_laser_feelings_question_prompt(turn_result)

        calls = [str(call_obj) for call_obj in interface.write_game_log.call_args_list]

        # Check for header
        assert any("LASER FEELINGS Question Response" in str(c) for c in calls)

        # Check for instructions
        assert any("honest answer" in str(c) for c in calls)


class TestAnswerHandling:
    """Test handling of DM's answer to character's question"""

    @pytest.mark.asyncio
    async def test_accepts_valid_answer(self, interface):
        """Test that valid DM answer is accepted"""
        # Set up LASER FEELINGS question mode
        interface._laser_feelings_question_mode = True
        interface._laser_feelings_question_data = {
            "character_id": "char_zara_001",
            "gm_question": "What do you want?",
        }
        interface.session_number = 1

        interface.write_game_log = MagicMock()
        interface._run_blocking_in_background = MagicMock()

        # Simulate input submission
        mock_input = MagicMock(spec=Input)
        mock_input.id = "dm-input"
        mock_input.value = "I want you to succeed"

        event = Input.Submitted(input=mock_input, value="I want you to succeed")

        await interface.on_input_submitted(event)

        # Verify answer was recorded
        assert interface._laser_feelings_question_mode is False
        assert interface._laser_feelings_question_data is None

        # Verify orchestrator was called
        interface._run_blocking_in_background.assert_called_once()

    @pytest.mark.asyncio
    async def test_rejects_empty_answer(self, interface):
        """Test that empty answer is rejected with error message"""
        interface._laser_feelings_question_mode = True
        interface._laser_feelings_question_data = {
            "character_id": "char_zara_001",
            "gm_question": "What do you want?",
        }

        interface.write_game_log = MagicMock()
        interface._run_blocking_in_background = MagicMock()

        # Simulate empty input
        mock_input = MagicMock(spec=Input)
        mock_input.id = "dm-input"
        mock_input.value = ""

        event = Input.Submitted(input=mock_input, value="")

        await interface.on_input_submitted(event)

        # Verify error message was shown
        calls = [str(call_obj) for call_obj in interface.write_game_log.call_args_list]
        assert any("cannot be empty" in str(c).lower() for c in calls)

        # Verify mode was NOT cleared (still waiting for answer)
        assert interface._laser_feelings_question_mode is True

        # Verify orchestrator was NOT called
        interface._run_blocking_in_background.assert_not_called()

    @pytest.mark.asyncio
    async def test_rejects_whitespace_only_answer(self, interface):
        """Test that whitespace-only answer is rejected"""
        interface._laser_feelings_question_mode = True
        interface._laser_feelings_question_data = {
            "character_id": "char_zara_001",
            "gm_question": "What do you want?",
        }

        interface.write_game_log = MagicMock()
        interface._run_blocking_in_background = MagicMock()

        # Simulate whitespace-only input
        mock_input = MagicMock(spec=Input)
        mock_input.id = "dm-input"
        mock_input.value = "   \n\t   "

        event = Input.Submitted(input=mock_input, value="   \n\t   ")

        await interface.on_input_submitted(event)

        # Verify error message
        calls = [str(call_obj) for call_obj in interface.write_game_log.call_args_list]
        assert any("cannot be empty" in str(c).lower() for c in calls)

        # Mode should still be active
        assert interface._laser_feelings_question_mode is True


class TestOrchestratorIntegration:
    """Test integration with TurnOrchestrator"""

    @pytest.mark.asyncio
    async def test_sends_answer_to_orchestrator(self, interface):
        """Test that answer is sent to orchestrator with correct format"""
        interface._laser_feelings_question_mode = True
        interface._laser_feelings_question_data = {
            "character_id": "char_zara_001",
            "gm_question": "What do you want?",
        }
        interface.session_number = 1

        interface.write_game_log = MagicMock()

        # Create a mock that captures the lambda function
        captured_lambda = None

        def capture_lambda(func):
            nonlocal captured_lambda
            captured_lambda = func

        interface._run_blocking_in_background = MagicMock(side_effect=capture_lambda)
        interface.orchestrator.resume_turn_with_dm_input = MagicMock()

        # Submit answer
        mock_input = MagicMock(spec=Input)
        mock_input.id = "dm-input"
        mock_input.value = "I want the truth"

        event = Input.Submitted(input=mock_input, value="I want the truth")

        await interface.on_input_submitted(event)

        # Execute the captured lambda
        assert captured_lambda is not None
        captured_lambda()

        # Verify orchestrator was called with correct arguments
        interface.orchestrator.resume_turn_with_dm_input.assert_called_once_with(
            session_number=1,
            dm_input_type="laser_feelings_answer",
            dm_input_data={"answer": "I want the truth"},
        )

    @pytest.mark.asyncio
    async def test_uses_fire_and_forget_pattern(self, interface):
        """Test that orchestrator call uses fire-and-forget background task"""
        interface._laser_feelings_question_mode = True
        interface._laser_feelings_question_data = {
            "character_id": "char_zara_001",
            "gm_question": "What do you want?",
        }
        interface.session_number = 1

        interface.write_game_log = MagicMock()
        interface._run_blocking_in_background = MagicMock()

        mock_input = MagicMock(spec=Input)
        mock_input.id = "dm-input"
        mock_input.value = "I want peace"

        event = Input.Submitted(input=mock_input, value="I want peace")

        await interface.on_input_submitted(event)

        # Verify _run_blocking_in_background was used (fire-and-forget)
        interface._run_blocking_in_background.assert_called_once()


class TestModeManagement:
    """Test state management for LASER FEELINGS question mode"""

    @pytest.mark.asyncio
    async def test_clears_mode_after_answer(self, interface):
        """Test that mode is cleared after answer is submitted"""
        interface._laser_feelings_question_mode = True
        interface._laser_feelings_question_data = {
            "character_id": "char_zara_001",
            "gm_question": "What do you want?",
        }

        interface.write_game_log = MagicMock()
        interface._run_blocking_in_background = MagicMock()

        mock_input = MagicMock(spec=Input)
        mock_input.id = "dm-input"
        mock_input.value = "I want success"

        event = Input.Submitted(input=mock_input, value="I want success")

        await interface.on_input_submitted(event)

        # Verify mode is cleared
        assert interface._laser_feelings_question_mode is False
        assert interface._laser_feelings_question_data is None

    @pytest.mark.asyncio
    async def test_does_not_accept_other_commands_in_question_mode(self, interface):
        """Test that normal commands are not processed during question mode"""
        interface._laser_feelings_question_mode = True
        interface._laser_feelings_question_data = {
            "character_id": "char_zara_001",
            "gm_question": "What do you want?",
        }

        interface.write_game_log = MagicMock()
        interface._run_blocking_in_background = MagicMock()
        interface.parser.parse_command = MagicMock()

        # Try to submit a command instead of an answer
        mock_input = MagicMock(spec=Input)
        mock_input.id = "dm-input"
        mock_input.value = "start"

        event = Input.Submitted(input=mock_input, value="start")

        await interface.on_input_submitted(event)

        # Verify that parser was NOT called (answer treated as plain text)
        interface.parser.parse_command.assert_not_called()

        # Verify orchestrator was called with "start" as the answer
        assert interface._run_blocking_in_background.call_count == 1

    def test_mode_not_active_by_default(self, interface):
        """Test that LASER FEELINGS question mode is not active by default"""
        assert interface._laser_feelings_question_mode is False
        assert interface._laser_feelings_question_data is None


class TestEdgeCases:
    """Test edge cases and error handling"""

    def test_handles_missing_character_name(self, interface):
        """Test graceful handling when character name lookup fails"""
        turn_result = {
            "laser_feelings_data": {
                "character_id": "char_unknown_999",
                "gm_question": "Who am I?",
            }
        }

        interface.write_game_log = MagicMock()
        interface._get_character_name = MagicMock(return_value="Unknown")

        # Should not raise error
        interface._show_laser_feelings_question_prompt(turn_result)

        # Verify method completed
        assert interface._laser_feelings_question_data is not None

    def test_handles_empty_laser_feelings_data(self, interface):
        """Test handling when laser_feelings_data is empty dict"""
        turn_result = {"laser_feelings_data": {}}

        interface.write_game_log = MagicMock()
        interface._get_character_name = MagicMock(return_value="Unknown")

        # Should not raise error
        interface._show_laser_feelings_question_prompt(turn_result)

        # Verify data is set to defaults
        assert interface._laser_feelings_question_data["character_id"] == "unknown"
        assert interface._laser_feelings_question_data["gm_question"] is None

    @pytest.mark.asyncio
    async def test_priority_over_other_modes(self, interface):
        """Test that LASER FEELINGS question mode has correct priority"""
        # Set up multiple modes
        interface._laser_feelings_question_mode = True
        interface._laser_feelings_question_data = {
            "character_id": "char_zara_001",
            "gm_question": "What do you want?",
        }
        interface._clarification_mode = True  # Lower priority

        interface.write_game_log = MagicMock()
        interface._run_blocking_in_background = MagicMock()

        mock_input = MagicMock(spec=Input)
        mock_input.id = "dm-input"
        mock_input.value = "I want truth"

        event = Input.Submitted(input=mock_input, value="I want truth")

        await interface.on_input_submitted(event)

        # Verify LASER FEELINGS question mode was handled (not clarification)
        # Check orchestrator was called with laser_feelings_answer type
        captured_lambda = interface._run_blocking_in_background.call_args[0][0]
        interface.orchestrator.resume_turn_with_dm_input = MagicMock()
        captured_lambda()

        call_kwargs = interface.orchestrator.resume_turn_with_dm_input.call_args[1]
        assert call_kwargs["dm_input_type"] == "laser_feelings_answer"

    def test_stores_question_data_for_later_use(self, interface):
        """Test that question data is stored for use in input handler"""
        turn_result = {
            "laser_feelings_data": {
                "character_id": "char_zara_001",
                "gm_question": "What drives you?",
            }
        }

        interface.write_game_log = MagicMock()
        interface._get_character_name = MagicMock(return_value="Zara-7")

        interface._show_laser_feelings_question_prompt(turn_result)

        # Verify data is available for input handler
        assert interface._laser_feelings_question_data is not None
        assert "character_id" in interface._laser_feelings_question_data
        assert "gm_question" in interface._laser_feelings_question_data
