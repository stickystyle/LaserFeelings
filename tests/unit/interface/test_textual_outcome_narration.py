# ABOUTME: Unit tests for outcome narration phase in Textual DM interface.
# ABOUTME: Tests detection, display, input handling, and orchestrator integration.

from unittest.mock import MagicMock, patch

import pytest

from src.interface.dm_textual import DMTextualInterface
from src.models.game_state import GamePhase
from src.orchestration.message_router import MessageRouter
from src.orchestration.turn_orchestrator import TurnOrchestrator


@pytest.fixture
def mock_orchestrator():
    """Create mock orchestrator"""
    orchestrator = MagicMock(spec=TurnOrchestrator)
    orchestrator.resume_turn_with_dm_input = MagicMock()
    return orchestrator


@pytest.fixture
def mock_router():
    """Create mock router"""
    router = MagicMock(spec=MessageRouter)
    router.get_ooc_messages_for_player = MagicMock(return_value=[])
    return router


@pytest.fixture
def textual_app(mock_orchestrator, mock_router):
    """Create Textual interface instance"""
    app = DMTextualInterface(
        orchestrator=mock_orchestrator,
        router=mock_router
    )
    # Set up necessary state
    app.session_number = 1
    app.turn_number = 5
    return app


class TestOutcomeNarrationDetection:
    """Test detection of DM_OUTCOME phase and outcome narration mode"""

    def test_display_turn_result_detects_dm_outcome_awaiting_phase(self, textual_app):
        """Test that display_turn_result detects dm_outcome awaiting phase"""
        turn_result = {
            "awaiting_dm_input": True,
            "awaiting_phase": "dm_outcome",
            "phase_completed": GamePhase.DICE_RESOLUTION.value,
        }

        # Mock _show_outcome_prompt to track that it was called
        with patch.object(textual_app, '_show_outcome_prompt') as mock_prompt:
            with patch.object(textual_app, 'update_turn_status'):
                textual_app.display_turn_result(turn_result)

                # Check that outcome prompt method was called
                assert mock_prompt.called, "Expected _show_outcome_prompt to be called"

    def test_outcome_narration_mode_flag_set_when_phase_reached(self, textual_app):
        """Test that _outcome_narration_mode flag is set when dm_outcome phase is reached"""
        turn_result = {
            "awaiting_dm_input": True,
            "awaiting_phase": "dm_outcome",
            "phase_completed": GamePhase.DICE_RESOLUTION.value,
        }

        with patch.object(textual_app, 'write_game_log'):
            with patch.object(textual_app, 'update_turn_status'):
                textual_app.display_turn_result(turn_result)

        assert textual_app._outcome_narration_mode is True, \
            "Expected _outcome_narration_mode to be True"

    def test_outcome_narration_mode_not_set_for_other_phases(self, textual_app):
        """Test that outcome narration mode is not triggered for other phases"""
        turn_result = {
            "awaiting_dm_input": True,
            "awaiting_phase": "dm_adjudication_wait",
            "phase_completed": GamePhase.CHARACTER_ACTION.value,
        }

        with patch.object(textual_app, 'write_game_log'):
            with patch.object(textual_app, 'show_roll_suggestion'):
                with patch.object(textual_app, 'update_turn_status'):
                    textual_app.display_turn_result(turn_result)

        # _outcome_narration_mode should not exist or be False
        assert not getattr(textual_app, '_outcome_narration_mode', False), \
            "Expected _outcome_narration_mode to be False for other phases"


class TestOutcomeNarrationDisplay:
    """Test display of outcome narration prompt"""

    def test_outcome_prompt_display_format(self, textual_app):
        """Test that outcome prompt is displayed with correct format"""
        # Directly test _show_outcome_prompt method
        with patch.object(textual_app, 'write_game_log') as mock_write:
            textual_app._show_outcome_prompt()

            # Find the prompt call
            calls = [call[0][0] for call in mock_write.call_args_list]

            # Should contain outcome narration header or "Describe what happens"
            has_prompt = any(
                "Describe what happens" in call or "DM Outcome Narration" in call for call in calls
            )
            assert has_prompt, "Expected outcome narration prompt"

            # Should contain instruction
            assert any("DM Outcome:" in call or "outcome" in call.lower() for call in calls), \
                "Expected instruction text"

    def test_update_turn_status_shows_dm_outcome_phase(self, textual_app):
        """Test that turn status shows DM Outcome phase"""
        textual_app.current_phase = GamePhase.DM_OUTCOME

        with patch.object(textual_app, 'query_one') as mock_query:
            mock_status_widget = MagicMock()
            mock_query.return_value = mock_status_widget

            textual_app.update_turn_status()

            # Check status widget was updated with humanized phase name
            update_call = mock_status_widget.update.call_args[0][0]
            assert "DM Outcome" in update_call, \
                "Expected turn status to show 'DM Outcome' phase"


class TestOutcomeNarrationInputHandling:
    """Test handling of outcome narration input"""

    @pytest.mark.asyncio
    async def test_outcome_narration_accepts_valid_input(self, textual_app):
        """Test that valid outcome narration is accepted"""
        textual_app._outcome_narration_mode = True
        outcome_text = "The door swings open, revealing a dark corridor."

        # Mock Input.Submitted event
        mock_input = MagicMock()
        mock_input.id = "dm-input"
        mock_input.value = outcome_text

        mock_event = MagicMock()
        mock_event.input = mock_input
        mock_event.value = outcome_text

        with patch.object(textual_app, 'write_game_log') as mock_write:
            with patch.object(textual_app, '_run_blocking_in_background') as mock_bg:
                await textual_app.on_input_submitted(mock_event)

                # Check confirmation was displayed
                calls = [str(call) for call in mock_write.call_args_list]
                assert any("recorded" in str(call).lower() or "✓" in str(call) for call in calls), \
                    "Expected confirmation message"

                # Check orchestrator was called
                assert mock_bg.called, "Expected background task to be started"

    @pytest.mark.asyncio
    async def test_outcome_narration_rejects_empty_input(self, textual_app):
        """Test that empty outcome narration is rejected"""
        textual_app._outcome_narration_mode = True

        mock_input = MagicMock()
        mock_input.id = "dm-input"
        mock_input.value = ""

        mock_event = MagicMock()
        mock_event.input = mock_input
        mock_event.value = ""

        with patch.object(textual_app, 'write_game_log') as mock_write:
            with patch.object(textual_app, '_run_blocking_in_background') as mock_bg:
                await textual_app.on_input_submitted(mock_event)

                # Check error was displayed
                calls = [str(call) for call in mock_write.call_args_list]
                has_error = any(
                    "empty" in str(call).lower() or "cannot be empty" in str(call).lower()
                    for call in calls
                )
                assert has_error, "Expected error message for empty input"

                # Check orchestrator was NOT called
                assert not mock_bg.called, "Expected orchestrator to not be called for empty input"

    @pytest.mark.asyncio
    async def test_outcome_narration_exits_mode_after_submission(self, textual_app):
        """Test that outcome narration mode exits after valid submission"""
        textual_app._outcome_narration_mode = True
        outcome_text = "The alarm sounds!"

        mock_input = MagicMock()
        mock_input.id = "dm-input"
        mock_input.value = outcome_text

        mock_event = MagicMock()
        mock_event.input = mock_input
        mock_event.value = outcome_text

        with patch.object(textual_app, 'write_game_log'):
            with patch.object(textual_app, '_run_blocking_in_background'):
                await textual_app.on_input_submitted(mock_event)

        assert textual_app._outcome_narration_mode is False, \
            "Expected _outcome_narration_mode to be False after submission"

    @pytest.mark.asyncio
    async def test_outcome_narration_accepts_multi_line_text(self, textual_app):
        """Test that outcome narration accepts multi-line text"""
        textual_app._outcome_narration_mode = True
        outcome_text = "The door opens.\nYou see guards ahead.\nThey haven't noticed you yet."

        mock_input = MagicMock()
        mock_input.id = "dm-input"
        mock_input.value = outcome_text

        mock_event = MagicMock()
        mock_event.input = mock_input
        mock_event.value = outcome_text

        with patch.object(textual_app, 'write_game_log'):
            with patch.object(textual_app, '_run_blocking_in_background') as mock_bg:
                await textual_app.on_input_submitted(mock_event)

                assert mock_bg.called, "Expected background task for multi-line input"


class TestOutcomeNarrationOrchestratorIntegration:
    """Test integration with orchestrator"""

    @pytest.mark.asyncio
    async def test_orchestrator_called_with_correct_format(self, textual_app, mock_orchestrator):
        """Test that orchestrator is called with correct dm_input_type and data"""
        textual_app._outcome_narration_mode = True
        outcome_text = "The guards attack!"

        mock_input = MagicMock()
        mock_input.id = "dm-input"
        mock_input.value = outcome_text

        mock_event = MagicMock()
        mock_event.input = mock_input
        mock_event.value = outcome_text

        with patch.object(textual_app, 'write_game_log'):
            # Capture the lambda passed to _run_blocking_in_background
            with patch.object(textual_app, '_run_blocking_in_background') as mock_bg:
                await textual_app.on_input_submitted(mock_event)

                # Extract and execute the lambda
                assert mock_bg.called, "Expected background task to be started"
                lambda_func = mock_bg.call_args[0][0]
                lambda_func()

                # Verify orchestrator was called correctly
                mock_orchestrator.resume_turn_with_dm_input.assert_called_once_with(
                    session_number=textual_app.session_number,
                    dm_input_type="outcome",
                    dm_input_data={"outcome_text": outcome_text}
                )

    @pytest.mark.asyncio
    async def test_orchestrator_receives_session_number(self, textual_app, mock_orchestrator):
        """Test that orchestrator receives correct session number"""
        textual_app._outcome_narration_mode = True
        textual_app.session_number = 42
        outcome_text = "Success!"

        mock_input = MagicMock()
        mock_input.id = "dm-input"
        mock_input.value = outcome_text

        mock_event = MagicMock()
        mock_event.input = mock_input
        mock_event.value = outcome_text

        with patch.object(textual_app, 'write_game_log'):
            with patch.object(textual_app, '_run_blocking_in_background') as mock_bg:
                await textual_app.on_input_submitted(mock_event)

                lambda_func = mock_bg.call_args[0][0]
                lambda_func()

                call_kwargs = mock_orchestrator.resume_turn_with_dm_input.call_args[1]
                assert call_kwargs["session_number"] == 42, \
                    "Expected session_number to be 42"


class TestOutcomeNarrationModeRestrictions:
    """Test that other commands are blocked during outcome narration"""

    @pytest.mark.asyncio
    async def test_normal_commands_blocked_during_outcome_mode(self, textual_app):
        """Test that normal commands are not processed during outcome mode"""
        textual_app._outcome_narration_mode = True

        mock_input = MagicMock()
        mock_input.id = "dm-input"
        mock_input.value = "/info"

        mock_event = MagicMock()
        mock_event.input = mock_input
        mock_event.value = "/info"

        with patch.object(textual_app, 'write_game_log'):
            with patch.object(textual_app, 'show_session_info') as mock_info:
                await textual_app.on_input_submitted(mock_event)

                # /info should not be called during outcome mode
                # Instead, "/info" should be treated as outcome text
                assert not mock_info.called, \
                    "Expected /info command to not be processed during outcome mode"

    @pytest.mark.asyncio
    async def test_outcome_mode_has_higher_priority_than_clarification_mode(self, textual_app):
        """Test that outcome mode takes priority over clarification mode if both set"""
        textual_app._outcome_narration_mode = True
        textual_app._clarification_mode = True
        textual_app._pending_questions = [{"agent_id": "agent_test", "question_text": "Test?"}]

        outcome_text = "The door opens"

        mock_input = MagicMock()
        mock_input.id = "dm-input"
        mock_input.value = outcome_text

        mock_event = MagicMock()
        mock_event.input = mock_input
        mock_event.value = outcome_text

        with patch.object(textual_app, 'write_game_log'):
            with patch.object(textual_app, '_run_blocking_in_background') as mock_bg:
                await textual_app.on_input_submitted(mock_event)

                # Check that outcome handling happened (not clarification)
                assert mock_bg.called, "Expected outcome handling, not clarification"
                lambda_func = mock_bg.call_args[0][0]
                lambda_func()

                # Verify it was outcome call (not clarification)
                call_kwargs = textual_app.orchestrator.resume_turn_with_dm_input.call_args[1]
                assert call_kwargs["dm_input_type"] == "outcome", \
                    "Expected outcome handling to take priority"


class TestOutcomeNarrationErrorHandling:
    """Test error handling during outcome narration"""

    @pytest.mark.asyncio
    async def test_whitespace_only_input_rejected(self, textual_app):
        """Test that whitespace-only input is rejected as empty"""
        textual_app._outcome_narration_mode = True

        mock_input = MagicMock()
        mock_input.id = "dm-input"
        mock_input.value = "   \n\t  "

        mock_event = MagicMock()
        mock_event.input = mock_input
        mock_event.value = "   \n\t  "

        with patch.object(textual_app, 'write_game_log') as mock_write:
            with patch.object(textual_app, '_run_blocking_in_background') as mock_bg:
                await textual_app.on_input_submitted(mock_event)

                # Should reject whitespace-only input
                assert not mock_bg.called, "Expected whitespace-only input to be rejected"

                # Should display error
                calls = [str(call) for call in mock_write.call_args_list]
                assert any("empty" in str(call).lower() for call in calls), \
                    "Expected error message for whitespace-only input"
