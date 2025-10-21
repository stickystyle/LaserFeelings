# ABOUTME: Unit tests for real-time clarification question polling in Textual DM interface.
# ABOUTME: Tests blocking orchestrator calls and immediate follow-up question detection.

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


class TestClarificationAnswerBlocking:
    """Test that answering clarification questions uses blocking orchestrator calls"""

    @pytest.mark.asyncio
    async def test_clarification_answer_uses_blocking_call(self, textual_app):
        """Test answering uses await _run_blocking_call instead of fire-and-forget"""
        user_input = "1 About 10 meters"

        mock_input = MagicMock()
        mock_input.id = "dm-input"
        mock_input.value = user_input

        mock_event = MagicMock()
        mock_event.input = mock_input
        mock_event.value = user_input

        with patch.object(textual_app, "write_game_log"):
            with patch.object(textual_app, "_run_blocking_call") as mock_blocking:
                with patch.object(
                    textual_app, "_fetch_new_clarification_questions", return_value=[]
                ):
                    mock_blocking.return_value = None  # Simulate successful orchestrator call

                    await textual_app.on_input_submitted(mock_event)

                    # Verify _run_blocking_call was used (blocking)
                    assert mock_blocking.called, "Expected _run_blocking_call to be used"

    @pytest.mark.asyncio
    async def test_clarification_answer_does_not_use_fire_and_forget(self, textual_app):
        """Test answering does NOT use _run_blocking_in_background (fire-and-forget)"""
        user_input = "1 About 10 meters"

        mock_input = MagicMock()
        mock_input.id = "dm-input"
        mock_input.value = user_input

        mock_event = MagicMock()
        mock_event.input = mock_input
        mock_event.value = user_input

        with patch.object(textual_app, "write_game_log"):
            with patch.object(textual_app, "_run_blocking_call", return_value=None):
                with patch.object(
                    textual_app, "_fetch_new_clarification_questions", return_value=[]
                ):
                    with patch.object(textual_app, "_run_blocking_in_background") as mock_bg:
                        await textual_app.on_input_submitted(mock_event)

                        # Verify fire-and-forget was NOT used
                        assert not mock_bg.called, (
                            "Expected _run_blocking_in_background to NOT be used"
                        )

    @pytest.mark.asyncio
    async def test_clarification_shows_processing_message(self, textual_app):
        """Test that processing message is shown while waiting for orchestrator"""
        user_input = "1 About 10 meters"

        mock_input = MagicMock()
        mock_input.id = "dm-input"
        mock_input.value = user_input

        mock_event = MagicMock()
        mock_event.input = mock_input
        mock_event.value = user_input

        with patch.object(textual_app, "write_game_log") as mock_write:
            with patch.object(textual_app, "_run_blocking_call", return_value=None):
                with patch.object(
                    textual_app, "_fetch_new_clarification_questions", return_value=[]
                ):
                    await textual_app.on_input_submitted(mock_event)

                    # Check for processing message
                    calls = [str(call) for call in mock_write.call_args_list]
                    has_processing = any(
                        "processing" in str(call).lower()
                        or "waiting for agents" in str(call).lower()
                        for call in calls
                    )
                    assert has_processing, "Expected processing message while waiting"


class TestFollowUpQuestionPolling:
    """Test that follow-up questions are immediately polled after orchestrator completes"""

    @pytest.mark.asyncio
    async def test_fetch_new_clarification_questions_called_after_answer(self, textual_app):
        """Test that _fetch_new_clarification_questions is called immediately after orchestrator"""
        user_input = "1 About 10 meters"

        mock_input = MagicMock()
        mock_input.id = "dm-input"
        mock_input.value = user_input

        mock_event = MagicMock()
        mock_event.input = mock_input
        mock_event.value = user_input

        with patch.object(textual_app, "write_game_log"):
            with patch.object(textual_app, "_run_blocking_call", return_value=None):
                with patch.object(textual_app, "_fetch_new_clarification_questions") as mock_fetch:
                    mock_fetch.return_value = []

                    await textual_app.on_input_submitted(mock_event)

                    # Verify polling happened
                    assert mock_fetch.called, (
                        "Expected _fetch_new_clarification_questions to be called"
                    )

    @pytest.mark.asyncio
    async def test_follow_up_questions_displayed_when_found(self, textual_app):
        """Test that follow-up questions are displayed when polling finds new questions"""
        user_input = "1 About 10 meters"
        follow_up_questions = [{"agent_id": "agent_alex_001", "question_text": "Are there guards?"}]

        mock_input = MagicMock()
        mock_input.id = "dm-input"
        mock_input.value = user_input

        mock_event = MagicMock()
        mock_event.input = mock_input
        mock_event.value = user_input

        with patch.object(textual_app, "write_game_log"):
            with patch.object(textual_app, "_run_blocking_call", return_value=None):
                with patch.object(textual_app, "_fetch_new_clarification_questions") as mock_fetch:
                    with patch.object(textual_app, "show_clarification_questions") as mock_show:
                        mock_fetch.return_value = follow_up_questions

                        await textual_app.on_input_submitted(mock_event)

                        # Verify follow-up questions were displayed
                        assert mock_show.called, (
                            "Expected show_clarification_questions to be called"
                        )

                        # Verify correct round number (incremented)
                        call_args = mock_show.call_args[0][0]
                        assert call_args["round"] == 2, "Expected round to increment from 1 to 2"
                        assert call_args["questions"] == follow_up_questions

    @pytest.mark.asyncio
    async def test_no_follow_up_questions_shows_message(self, textual_app):
        """Test that no-questions message is shown when polling finds nothing"""
        user_input = "1 About 10 meters"

        mock_input = MagicMock()
        mock_input.id = "dm-input"
        mock_input.value = user_input

        mock_event = MagicMock()
        mock_event.input = mock_input
        mock_event.value = user_input

        with patch.object(textual_app, "write_game_log") as mock_write:
            with patch.object(textual_app, "_run_blocking_call", return_value=None):
                with patch.object(
                    textual_app, "_fetch_new_clarification_questions", return_value=[]
                ):
                    await textual_app.on_input_submitted(mock_event)

                    # Check for "no new questions" message
                    calls = [str(call) for call in mock_write.call_args_list]
                    has_no_questions = any(
                        "no new follow-up questions" in str(call).lower() for call in calls
                    )
                    assert has_no_questions, "Expected 'no new questions' message"

    @pytest.mark.asyncio
    async def test_new_questions_detection_message_shown(self, textual_app):
        """Test that detection message is shown when new questions are found"""
        user_input = "1 About 10 meters"
        follow_up_questions = [
            {"agent_id": "agent_alex_001", "question_text": "Are there guards?"},
            {"agent_id": "agent_alex_001", "question_text": "What's the distance?"},
        ]

        mock_input = MagicMock()
        mock_input.id = "dm-input"
        mock_input.value = user_input

        mock_event = MagicMock()
        mock_event.input = mock_input
        mock_event.value = user_input

        with patch.object(textual_app, "write_game_log") as mock_write:
            with patch.object(textual_app, "_run_blocking_call", return_value=None):
                with patch.object(
                    textual_app,
                    "_fetch_new_clarification_questions",
                    return_value=follow_up_questions,
                ):
                    with patch.object(textual_app, "show_clarification_questions"):
                        await textual_app.on_input_submitted(mock_event)

                        # Check for "New follow-up questions detected" message
                        calls = [str(call) for call in mock_write.call_args_list]
                        has_detection = any(
                            "new follow-up questions detected" in str(call).lower()
                            for call in calls
                        )
                        assert has_detection, "Expected new questions detection message"

                        # Verify count is shown
                        has_count = any("2 question" in str(call).lower() for call in calls)
                        assert has_count, "Expected question count in detection message"


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
            with patch.object(textual_app, "_run_blocking_call") as mock_blocking:
                mock_blocking.side_effect = Exception("Connection error")

                await textual_app.on_input_submitted(mock_event)

                # Check for error message
                calls = [str(call) for call in mock_write.call_args_list]
                has_error = any("failed to process answer" in str(call).lower() for call in calls)
                assert has_error, "Expected error message when orchestrator fails"

    @pytest.mark.asyncio
    async def test_orchestrator_error_prevents_polling(self, textual_app):
        """Test that polling is skipped when orchestrator fails"""
        user_input = "1 About 10 meters"

        mock_input = MagicMock()
        mock_input.id = "dm-input"
        mock_input.value = user_input

        mock_event = MagicMock()
        mock_event.input = mock_input
        mock_event.value = user_input

        with patch.object(textual_app, "write_game_log"):
            with patch.object(textual_app, "_run_blocking_call", side_effect=Exception("Error")):
                with patch.object(textual_app, "_fetch_new_clarification_questions") as mock_fetch:
                    await textual_app.on_input_submitted(mock_event)

                    # Verify polling was NOT attempted after error
                    assert not mock_fetch.called, (
                        "Expected polling to be skipped when orchestrator fails"
                    )


class TestRoundNumberIncrement:
    """Test that round numbers increment correctly when follow-ups are found"""

    @pytest.mark.asyncio
    async def test_round_number_increments_from_1_to_2(self, textual_app):
        """Test round increments from 1 to 2 when follow-up found"""
        textual_app._questions_round = 1
        user_input = "1 About 10 meters"
        follow_up = [{"agent_id": "agent_test", "question_text": "Follow up?"}]

        mock_input = MagicMock()
        mock_input.id = "dm-input"
        mock_input.value = user_input

        mock_event = MagicMock()
        mock_event.input = mock_input
        mock_event.value = user_input

        with patch.object(textual_app, "write_game_log"):
            with patch.object(textual_app, "_run_blocking_call", return_value=None):
                with patch.object(
                    textual_app, "_fetch_new_clarification_questions", return_value=follow_up
                ):
                    with patch.object(textual_app, "show_clarification_questions") as mock_show:
                        await textual_app.on_input_submitted(mock_event)

                        # Verify round was incremented
                        call_args = mock_show.call_args[0][0]
                        assert call_args["round"] == 2

    @pytest.mark.asyncio
    async def test_round_number_increments_from_2_to_3(self, textual_app):
        """Test round increments from 2 to 3 when follow-up found"""
        textual_app._questions_round = 2
        user_input = "1 About 10 meters"
        follow_up = [{"agent_id": "agent_test", "question_text": "Final question?"}]

        mock_input = MagicMock()
        mock_input.id = "dm-input"
        mock_input.value = user_input

        mock_event = MagicMock()
        mock_event.input = mock_input
        mock_event.value = user_input

        with patch.object(textual_app, "write_game_log"):
            with patch.object(textual_app, "_run_blocking_call", return_value=None):
                with patch.object(
                    textual_app, "_fetch_new_clarification_questions", return_value=follow_up
                ):
                    with patch.object(textual_app, "show_clarification_questions") as mock_show:
                        await textual_app.on_input_submitted(mock_event)

                        # Verify round was incremented
                        call_args = mock_show.call_args[0][0]
                        assert call_args["round"] == 3
