# ABOUTME: Unit tests for clarification question handling in Textual DM interface.
# ABOUTME: Tests fire-and-forget answer submission and round-based follow-up detection.

from unittest.mock import MagicMock, patch

import pytest

from src.interface.dm_textual import DMTextualInterface
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
    app = DMTextualInterface(orchestrator=mock_orchestrator, router=mock_router)
    # Set up necessary state
    app.session_number = 1
    app.turn_number = 5
    app._clarification_mode = True
    app._pending_questions = [
        {"agent_id": "agent_alex_001", "question_text": "How far is the door?"}
    ]
    app._questions_round = 1
    return app


class TestClarificationAnswerFireAndForget:
    """Test that answering clarification questions uses fire-and-forget pattern"""

    @pytest.mark.asyncio
    async def test_clarification_answer_uses_fire_and_forget(self, textual_app):
        """Test answering uses _run_blocking_in_background (fire-and-forget)"""
        user_input = "1 About 10 meters"

        mock_input = MagicMock()
        mock_input.id = "dm-input"
        mock_input.value = user_input

        mock_event = MagicMock()
        mock_event.input = mock_input
        mock_event.value = user_input

        with patch.object(textual_app, "write_game_log"):
            with patch.object(textual_app, "_run_blocking_in_background") as mock_bg:
                await textual_app.on_input_submitted(mock_event)

                # Verify fire-and-forget was used
                assert mock_bg.called, "Expected _run_blocking_in_background to be used"

    @pytest.mark.asyncio
    async def test_clarification_answer_does_not_use_blocking_call(self, textual_app):
        """Test answering does NOT use await _run_blocking_call (blocking)"""
        user_input = "1 About 10 meters"

        mock_input = MagicMock()
        mock_input.id = "dm-input"
        mock_input.value = user_input

        mock_event = MagicMock()
        mock_event.input = mock_input
        mock_event.value = user_input

        with patch.object(textual_app, "write_game_log"):
            with patch.object(textual_app, "_run_blocking_in_background"):
                with patch.object(textual_app, "_run_blocking_call") as mock_blocking:
                    await textual_app.on_input_submitted(mock_event)

                    # Verify blocking call was NOT used
                    assert not mock_blocking.called, (
                        "Expected _run_blocking_call to NOT be used"
                    )

    @pytest.mark.asyncio
    async def test_clarification_does_not_show_processing_message(self, textual_app):
        """Test that processing message is NOT shown (returns immediately)"""
        user_input = "1 About 10 meters"

        mock_input = MagicMock()
        mock_input.id = "dm-input"
        mock_input.value = user_input

        mock_event = MagicMock()
        mock_event.input = mock_input
        mock_event.value = user_input

        with patch.object(textual_app, "write_game_log") as mock_write:
            with patch.object(textual_app, "_run_blocking_in_background"):
                await textual_app.on_input_submitted(mock_event)

                # Check for processing message - should NOT be present
                calls = [str(call) for call in mock_write.call_args_list]
                has_processing = any(
                    "processing" in str(call).lower()
                    or "waiting for agents" in str(call).lower()
                    for call in calls
                )
                assert not has_processing, "Expected NO processing message (returns immediately)"


class TestClarificationErrorHandling:
    """Test error handling during clarification answer processing"""

    @pytest.mark.asyncio
    async def test_orchestrator_error_displays_error_message(self, textual_app):
        """Test that orchestrator errors are caught and displayed"""
        user_input = "1 About 10 meters"

        mock_input = MagicMock()
        mock_input.id = "dm-input"
        mock_input.value = user_input

        mock_event = MagicMock()
        mock_event.input = mock_input
        mock_event.value = user_input

        with patch.object(textual_app, "write_game_log") as mock_write:
            with patch.object(textual_app, "_run_blocking_in_background") as mock_bg:
                mock_bg.side_effect = Exception("Connection error")

                await textual_app.on_input_submitted(mock_event)

                # Check for error message
                calls = [str(call) for call in mock_write.call_args_list]
                has_error = any("failed to send answer" in str(call).lower() for call in calls)
                assert has_error, "Expected error message when orchestrator fails"


class TestRoundBasedFollowUpDetection:
    """Test that follow-up questions are detected after DM types 'done'"""

    @pytest.mark.asyncio
    async def test_done_polls_for_followups(self, textual_app):
        """Test that 'done' command polls for follow-up questions"""
        user_input = "done"
        mock_input = MagicMock()
        mock_input.id = "dm-input"
        mock_input.value = user_input

        mock_event = MagicMock()
        mock_event.input = mock_input
        mock_event.value = user_input

        with patch.object(textual_app, "write_game_log"):
            with patch.object(textual_app, "_run_blocking_in_background"):
                with patch.object(
                    textual_app, "_fetch_new_clarification_questions", return_value=[]
                ) as mock_fetch:
                    await textual_app.on_input_submitted(mock_event)

                    # Verify fetch was called (polling for follow-ups)
                    assert mock_fetch.called, "Expected _fetch_new_clarification_questions to be called"

    @pytest.mark.asyncio
    async def test_done_shows_followup_questions_if_found(self, textual_app):
        """Test that follow-up questions are displayed if found"""
        user_input = "done"
        mock_input = MagicMock()
        mock_input.id = "dm-input"
        mock_input.value = user_input

        mock_event = MagicMock()
        mock_event.input = mock_input
        mock_event.value = user_input

        follow_up_questions = [
            {"agent_id": "agent_alex_001", "question_text": "Follow-up question?"}
        ]

        with patch.object(textual_app, "write_game_log"):
            with patch.object(textual_app, "_run_blocking_in_background"):
                with patch.object(
                    textual_app,
                    "_fetch_new_clarification_questions",
                    return_value=follow_up_questions,
                ):
                    with patch.object(textual_app, "show_clarification_questions") as mock_show:
                        await textual_app.on_input_submitted(mock_event)

                        # Verify follow-up questions were displayed
                        assert mock_show.called, "Expected show_clarification_questions to be called"
                        call_args = mock_show.call_args[0][0]
                        assert call_args["round"] == 2, "Expected round 2"
                        assert call_args["questions"] == follow_up_questions

    @pytest.mark.asyncio
    async def test_done_proceeds_if_no_followups(self, textual_app):
        """Test that turn proceeds if no follow-up questions"""
        user_input = "done"
        mock_input = MagicMock()
        mock_input.id = "dm-input"
        mock_input.value = user_input

        mock_event = MagicMock()
        mock_event.input = mock_input
        mock_event.value = user_input

        with patch.object(textual_app, "write_game_log"):
            with patch.object(textual_app, "_run_blocking_in_background") as mock_bg:
                with patch.object(
                    textual_app, "_fetch_new_clarification_questions", return_value=[]
                ):
                    await textual_app.on_input_submitted(mock_event)

                    # Verify orchestrator was called to proceed
                    assert mock_bg.called, "Expected orchestrator to be called to proceed"
                    # Verify clarification mode was exited
                    assert not textual_app._clarification_mode
