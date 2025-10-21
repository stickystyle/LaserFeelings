# ABOUTME: Unit tests for real-time clarification question polling in Textual DM interface.
# ABOUTME: Tests fire-and-forget answer submission with continuous background polling.

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


class TestContinuousBackgroundPolling:
    """Test that continuous background polling runs for follow-up questions"""

    @pytest.mark.asyncio
    async def test_polling_task_started_when_entering_clarification_mode(self, textual_app):
        """Test that polling task is started when clarification mode begins"""
        import asyncio

        questions_data = {
            "round": 1,
            "questions": [{"agent_id": "agent_test", "question_text": "How far?"}],
        }

        with patch.object(textual_app, "write_game_log"):
            with patch.object(asyncio, "create_task") as mock_create_task:
                textual_app.show_clarification_questions(questions_data)

                # Verify polling task was created
                assert mock_create_task.called, "Expected polling task to be created"

    @pytest.mark.asyncio
    async def test_polling_runs_continuously(self, textual_app):
        """Test that polling happens multiple times continuously"""
        import asyncio

        textual_app._clarification_mode = True
        call_count = 0
        max_calls = 3

        def mock_fetch():
            nonlocal call_count
            call_count += 1
            if call_count >= max_calls:
                # Stop after a few polls
                textual_app._clarification_mode = False
            return []

        with patch.object(textual_app, "write_game_log"):
            with patch.object(
                textual_app, "_fetch_new_clarification_questions", side_effect=mock_fetch
            ):
                # Run polling for a short time
                poll_task = asyncio.create_task(
                    textual_app._poll_clarification_questions_continuously()
                )

                # Wait for task to complete
                try:
                    await asyncio.wait_for(poll_task, timeout=2.0)
                except TimeoutError:
                    poll_task.cancel()

                # Verify multiple polls happened
                assert call_count >= 2, f"Expected at least 2 poll calls, got {call_count}"

    @pytest.mark.asyncio
    async def test_polling_displays_questions_when_found(self, textual_app):
        """Test that polling displays new questions in real-time"""
        import asyncio

        textual_app._clarification_mode = True
        follow_up_questions = [{"agent_id": "agent_alex_001", "question_text": "Are there guards?"}]

        call_count = 0

        def mock_fetch():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                # First poll: return questions
                return follow_up_questions
            else:
                # Subsequent polls: stop
                textual_app._clarification_mode = False
                return []

        with patch.object(textual_app, "write_game_log"):
            with patch.object(
                textual_app, "_fetch_new_clarification_questions", side_effect=mock_fetch
            ):
                with patch.object(textual_app, "show_clarification_questions") as mock_show:
                    # Run polling
                    poll_task = asyncio.create_task(
                        textual_app._poll_clarification_questions_continuously()
                    )

                    try:
                        await asyncio.wait_for(poll_task, timeout=2.0)
                    except TimeoutError:
                        poll_task.cancel()

                    # Verify questions were displayed
                    assert mock_show.called, "Expected show_clarification_questions to be called"

    @pytest.mark.asyncio
    async def test_polling_stops_when_clarification_mode_ends(self, textual_app):
        """Test that polling stops when clarification mode is set to False"""
        import asyncio

        textual_app._clarification_mode = True

        # Start polling
        poll_task = asyncio.create_task(
            textual_app._poll_clarification_questions_continuously()
        )

        # Let it run briefly
        await asyncio.sleep(0.1)

        # End clarification mode
        textual_app._clarification_mode = False

        # Wait for polling to stop
        try:
            await asyncio.wait_for(poll_task, timeout=1.0)
        except TimeoutError:
            poll_task.cancel()
            pytest.fail("Polling did not stop when clarification mode ended")

        # Verify task completed
        assert poll_task.done(), "Expected polling task to be done"

    @pytest.mark.asyncio
    async def test_polling_handles_errors_gracefully(self, textual_app):
        """Test that polling continues after errors"""
        import asyncio

        textual_app._clarification_mode = True
        call_count = 0

        def mock_fetch():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                # First call: error
                raise Exception("Test error")
            else:
                # Second call: stop
                textual_app._clarification_mode = False
                return []

        with patch.object(textual_app, "write_game_log"):
            with patch.object(
                textual_app, "_fetch_new_clarification_questions", side_effect=mock_fetch
            ):
                poll_task = asyncio.create_task(
                    textual_app._poll_clarification_questions_continuously()
                )

                try:
                    await asyncio.wait_for(poll_task, timeout=2.0)
                except TimeoutError:
                    poll_task.cancel()

                # Verify polling continued after error
                assert call_count >= 2, "Expected polling to continue after error"


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


class TestPollingTaskCleanup:
    """Test that polling task is properly cleaned up when exiting clarification mode"""

    @pytest.mark.asyncio
    async def test_polling_stopped_on_finish_command(self, textual_app):
        """Test that polling task is cancelled when 'finish' command is used"""

        # Set up active polling task
        textual_app._clarification_mode = True
        textual_app._polling_task = MagicMock()
        textual_app._polling_task.done.return_value = False

        user_input = "finish"
        mock_input = MagicMock()
        mock_input.id = "dm-input"
        mock_input.value = user_input

        mock_event = MagicMock()
        mock_event.input = mock_input
        mock_event.value = user_input

        with patch.object(textual_app, "write_game_log"):
            with patch.object(textual_app, "_run_blocking_in_background"):
                with patch.object(textual_app, "_stop_clarification_polling") as mock_stop:
                    await textual_app.on_input_submitted(mock_event)

                    # Verify polling was stopped
                    assert mock_stop.called, "Expected _stop_clarification_polling to be called"

    @pytest.mark.asyncio
    async def test_polling_stopped_on_done_with_no_followups(self, textual_app):
        """Test that polling task is cancelled when 'done' finds no follow-ups"""

        # Set up active polling task
        textual_app._clarification_mode = True
        textual_app._polling_task = MagicMock()
        textual_app._polling_task.done.return_value = False

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
                ):
                    with patch.object(
                        textual_app, "_stop_clarification_polling"
                    ) as mock_stop:
                        await textual_app.on_input_submitted(mock_event)

                        # Verify polling was stopped
                        assert mock_stop.called, "Expected _stop_clarification_polling to be called"
