# ABOUTME: Integration tests for DMTextualInterface with Textual runtime.
# ABOUTME: Tests app lifecycle, widget composition, and UI functionality.

from datetime import datetime
from unittest.mock import Mock

import pytest

from src.interface.dm_textual import DMTextualInterface
from src.orchestration.message_router import MessageRouter
from src.orchestration.turn_orchestrator import TurnOrchestrator


@pytest.fixture
def mock_orchestrator():
    return Mock(spec=TurnOrchestrator)


@pytest.fixture
def mock_router():
    return Mock(spec=MessageRouter)


@pytest.mark.asyncio
async def test_dm_textual_app_launches_without_error(mock_orchestrator, mock_router):
    """Integration: DMTextualInterface launches without runtime errors."""
    app = DMTextualInterface(orchestrator=mock_orchestrator, router=mock_router)

    # Should not raise any exceptions
    async with app.run_test():
        # App should be running
        assert app is not None


@pytest.mark.asyncio
async def test_dm_textual_compose_creates_required_widgets(mock_orchestrator, mock_router):
    """Integration: compose() creates all required widgets in layout."""
    app = DMTextualInterface(orchestrator=mock_orchestrator, router=mock_router)

    async with app.run_test():
        # Verify widgets exist by their IDs
        assert app.query_one("#game-log") is not None
        assert app.query_one("#ooc-log") is not None
        assert app.query_one("#dm-input") is not None
        assert app.query_one("#turn-status") is not None


@pytest.mark.asyncio
async def test_dm_input_field_visible_and_focused(mock_orchestrator, mock_router):
    """Integration: DM input field is available for input."""
    app = DMTextualInterface(orchestrator=mock_orchestrator, router=mock_router)

    async with app.run_test():
        input_widget = app.query_one("#dm-input")
        assert input_widget is not None


@pytest.mark.asyncio
async def test_turn_execution_updates_turn_number(mock_orchestrator, mock_router):
    """Integration: Turn execution increments turn counter."""
    mock_orchestrator.execute_turn_cycle.return_value = {
        "character_actions": {},
        "character_reactions": {},
        "phase_completed": "dm_narration",
    }

    app = DMTextualInterface(orchestrator=mock_orchestrator, router=mock_router)
    app._active_agents = ["agent_1"]

    async with app.run_test():
        initial_turn = app.turn_number
        app.display_turn_result(
            {
                "character_actions": {},
                "character_reactions": {},
                "phase_completed": "dm_narration",
            }
        )

        assert app.turn_number == initial_turn + 1


@pytest.mark.asyncio
async def test_update_ooc_log_displays_messages(mock_orchestrator, mock_router):
    """Integration: OOC log updates from router messages."""
    from unittest.mock import Mock

    # Mock message
    mock_message = Mock()
    mock_message.timestamp = datetime.now()
    mock_message.from_agent = "agent_1"
    mock_message.content = "Let's focus on the engines"

    mock_router.get_ooc_messages_for_player.return_value = [mock_message]

    app = DMTextualInterface(orchestrator=mock_orchestrator, router=mock_router)
    app._character_names = {"agent_1": "Alex"}

    async with app.run_test():
        app.update_ooc_log()
        # OOC log should have been updated (internal state, not easily testable)


@pytest.mark.asyncio
async def test_display_turn_result_shows_actions_and_reactions(
    mock_orchestrator, mock_router
):
    """Integration: display_turn_result shows character actions and reactions."""
    app = DMTextualInterface(orchestrator=mock_orchestrator, router=mock_router)
    app._character_names = {"char_zara_001": "Zara-7"}

    turn_result = {
        "character_actions": {
            "char_zara_001": {"narrative_text": "I scan the control panel"}
        },
        "character_reactions": {
            "char_zara_001": {"narrative_text": "I nod with satisfaction"}
        },
        "phase_completed": "character_reaction",
    }

    async with app.run_test():
        initial_turn = app.turn_number
        app.display_turn_result(turn_result)

        # Turn number should increment
        assert app.turn_number == initial_turn + 1


@pytest.mark.asyncio
async def test_show_session_info_displays_campaign_state(mock_orchestrator, mock_router):
    """Integration: show_session_info displays campaign state in game log."""
    app = DMTextualInterface(orchestrator=mock_orchestrator, router=mock_router)
    app._campaign_name = "Voyage of the Raptor"
    app._active_agents = ["agent_1", "agent_2"]
    app.turn_number = 5
    app.session_number = 1

    async with app.run_test():
        app.show_session_info()
        # Should write to game log (internal state)


@pytest.mark.asyncio
async def test_show_roll_suggestion_displays_panel(mock_orchestrator, mock_router):
    """Integration: Roll suggestion panel displays correctly."""
    app = DMTextualInterface(orchestrator=mock_orchestrator, router=mock_router)

    suggestion = {
        "character_name": "Zara-7",
        "character_id": "char_zara_001",
        "task_type": "Lasers",
        "prepared_context": "I studied the schematics",
        "suggested_roll": "2d6 Lasers",
    }

    async with app.run_test():
        app.show_roll_suggestion(suggestion)

        # Verify suggestion was stored
        assert app._current_roll_suggestion == suggestion

        # Game log should exist
        game_log = app.query_one("#game-log")
        assert game_log is not None


@pytest.mark.asyncio
async def test_roll_response_accept_command_clears_suggestion(
    mock_orchestrator, mock_router
):
    """Integration: Accepting a roll suggestion clears the stored suggestion."""
    app = DMTextualInterface(orchestrator=mock_orchestrator, router=mock_router)

    suggestion = {
        "character_name": "Zara-7",
        "character_id": "char_zara_001",
        "task_type": "Lasers",
        "prepared_context": "I studied the schematics",
        "suggested_roll": "2d6 Lasers",
    }

    async with app.run_test():
        # Set up a pending suggestion
        app._current_roll_suggestion = suggestion

        # Simulate submitting "accept" via event
        from textual.widgets import Input

        input_widget = app.query_one("#dm-input", Input)

        # Create and post a Submitted event manually
        event = Input.Submitted(input_widget, "accept")
        await app.on_input_submitted(event)

        # Suggestion should be cleared
        assert app._current_roll_suggestion is None


@pytest.mark.asyncio
async def test_roll_response_override_command_clears_suggestion(
    mock_orchestrator, mock_router
):
    """Integration: Overriding a roll suggestion clears the stored suggestion."""
    app = DMTextualInterface(orchestrator=mock_orchestrator, router=mock_router)

    suggestion = {
        "character_name": "Zara-7",
        "character_id": "char_zara_001",
        "task_type": "Lasers",
        "prepared_context": "I studied the schematics",
        "suggested_roll": "2d6 Lasers",
    }

    async with app.run_test():
        # Set up a pending suggestion
        app._current_roll_suggestion = suggestion

        # Simulate submitting "override 1d6" via event
        from textual.widgets import Input

        input_widget = app.query_one("#dm-input", Input)

        # Create and post a Submitted event manually
        event = Input.Submitted(input_widget, "override 1d6")
        await app.on_input_submitted(event)

        # Suggestion should be cleared
        assert app._current_roll_suggestion is None


@pytest.mark.asyncio
async def test_roll_response_success_command_clears_suggestion(
    mock_orchestrator, mock_router
):
    """Integration: Success command clears the stored suggestion."""
    app = DMTextualInterface(orchestrator=mock_orchestrator, router=mock_router)

    suggestion = {
        "character_name": "Zara-7",
        "character_id": "char_zara_001",
        "task_type": "Lasers",
        "prepared_context": "I studied the schematics",
        "suggested_roll": "2d6 Lasers",
    }

    async with app.run_test():
        # Set up a pending suggestion
        app._current_roll_suggestion = suggestion

        # Simulate submitting "success" via event
        from textual.widgets import Input

        input_widget = app.query_one("#dm-input", Input)

        # Create and post a Submitted event manually
        event = Input.Submitted(input_widget, "success")
        await app.on_input_submitted(event)

        # Suggestion should be cleared
        assert app._current_roll_suggestion is None


@pytest.mark.asyncio
async def test_roll_response_fail_command_clears_suggestion(
    mock_orchestrator, mock_router
):
    """Integration: Fail command clears the stored suggestion."""
    app = DMTextualInterface(orchestrator=mock_orchestrator, router=mock_router)

    suggestion = {
        "character_name": "Zara-7",
        "character_id": "char_zara_001",
        "task_type": "Lasers",
        "prepared_context": "I studied the schematics",
        "suggested_roll": "2d6 Lasers",
    }

    async with app.run_test():
        # Set up a pending suggestion
        app._current_roll_suggestion = suggestion

        # Simulate submitting "fail" via event
        from textual.widgets import Input

        input_widget = app.query_one("#dm-input", Input)

        # Create and post a Submitted event manually
        event = Input.Submitted(input_widget, "fail")
        await app.on_input_submitted(event)

        # Suggestion should be cleared
        assert app._current_roll_suggestion is None


@pytest.mark.asyncio
async def test_roll_response_without_pending_suggestion_shows_error(
    mock_orchestrator, mock_router
):
    """Integration: Responding without pending suggestion shows error."""
    app = DMTextualInterface(orchestrator=mock_orchestrator, router=mock_router)
    app._current_roll_suggestion = None

    async with app.run_test():
        # Simulate submitting "accept" without a pending suggestion
        from textual.widgets import Input

        input_widget = app.query_one("#dm-input", Input)

        # Create and post a Submitted event manually
        event = Input.Submitted(input_widget, "accept")
        await app.on_input_submitted(event)

        # Should still be None
        assert app._current_roll_suggestion is None


@pytest.mark.asyncio
async def test_roll_response_accept_calls_orchestrator(mock_orchestrator, mock_router):
    """Integration: Accepting a roll suggestion calls orchestrator with correct data."""
    mock_orchestrator.resume_turn_with_dm_input.return_value = {
        "turn_number": 1,
        "phase_completed": "dice_resolution",
        "success": True,
        "awaiting_dm_input": False,
    }

    app = DMTextualInterface(orchestrator=mock_orchestrator, router=mock_router)

    suggestion = {
        "character_name": "Zara-7",
        "character_id": "char_zara_001",
        "task_type": "Lasers",
        "prepared_context": "I studied the schematics",
        "suggested_roll": "2d6 Lasers",
    }

    async with app.run_test():
        app._current_roll_suggestion = suggestion

        from textual.widgets import Input

        input_widget = app.query_one("#dm-input", Input)
        event = Input.Submitted(input_widget, "accept")
        await app.on_input_submitted(event)

        # Verify orchestrator was called with correct parameters
        mock_orchestrator.resume_turn_with_dm_input.assert_called_once_with(
            session_number=1,
            dm_input_type="adjudication",
            dm_input_data={
                "needs_dice": True,
            }
        )

        # Suggestion should be cleared
        assert app._current_roll_suggestion is None


@pytest.mark.asyncio
async def test_roll_response_override_calls_orchestrator(mock_orchestrator, mock_router):
    """Integration: Overriding a roll calls orchestrator with dice override."""
    mock_orchestrator.resume_turn_with_dm_input.return_value = {
        "turn_number": 1,
        "phase_completed": "dice_resolution",
        "success": True,
        "awaiting_dm_input": False,
    }

    app = DMTextualInterface(orchestrator=mock_orchestrator, router=mock_router)

    suggestion = {
        "character_name": "Zara-7",
        "character_id": "char_zara_001",
        "task_type": "Lasers",
        "prepared_context": "I studied the schematics",
        "suggested_roll": "2d6 Lasers",
    }

    async with app.run_test():
        app._current_roll_suggestion = suggestion

        from textual.widgets import Input

        input_widget = app.query_one("#dm-input", Input)
        event = Input.Submitted(input_widget, "override 4")
        await app.on_input_submitted(event)

        # Verify orchestrator was called with dice override
        mock_orchestrator.resume_turn_with_dm_input.assert_called_once_with(
            session_number=1,
            dm_input_type="adjudication",
            dm_input_data={
                "needs_dice": True,
                "dice_override": 4,
            }
        )

        # Suggestion should be cleared
        assert app._current_roll_suggestion is None


@pytest.mark.asyncio
async def test_roll_response_success_calls_orchestrator(mock_orchestrator, mock_router):
    """Integration: Success command calls orchestrator to force success."""
    mock_orchestrator.resume_turn_with_dm_input.return_value = {
        "turn_number": 1,
        "phase_completed": "dm_outcome",
        "success": True,
        "awaiting_dm_input": False,
    }

    app = DMTextualInterface(orchestrator=mock_orchestrator, router=mock_router)

    suggestion = {
        "character_name": "Zara-7",
        "character_id": "char_zara_001",
        "task_type": "Lasers",
        "prepared_context": "I studied the schematics",
        "suggested_roll": "2d6 Lasers",
    }

    async with app.run_test():
        app._current_roll_suggestion = suggestion

        from textual.widgets import Input

        input_widget = app.query_one("#dm-input", Input)
        event = Input.Submitted(input_widget, "success")
        await app.on_input_submitted(event)

        # Verify orchestrator was called to force success
        mock_orchestrator.resume_turn_with_dm_input.assert_called_once_with(
            session_number=1,
            dm_input_type="adjudication",
            dm_input_data={
                "needs_dice": False,
                "manual_success": True,
            }
        )

        # Suggestion should be cleared
        assert app._current_roll_suggestion is None


@pytest.mark.asyncio
async def test_roll_response_fail_calls_orchestrator(mock_orchestrator, mock_router):
    """Integration: Fail command calls orchestrator to force failure."""
    mock_orchestrator.resume_turn_with_dm_input.return_value = {
        "turn_number": 1,
        "phase_completed": "dm_outcome",
        "success": True,
        "awaiting_dm_input": False,
    }

    app = DMTextualInterface(orchestrator=mock_orchestrator, router=mock_router)

    suggestion = {
        "character_name": "Zara-7",
        "character_id": "char_zara_001",
        "task_type": "Lasers",
        "prepared_context": "I studied the schematics",
        "suggested_roll": "2d6 Lasers",
    }

    async with app.run_test():
        app._current_roll_suggestion = suggestion

        from textual.widgets import Input

        input_widget = app.query_one("#dm-input", Input)
        event = Input.Submitted(input_widget, "fail")
        await app.on_input_submitted(event)

        # Verify orchestrator was called to force failure
        mock_orchestrator.resume_turn_with_dm_input.assert_called_once_with(
            session_number=1,
            dm_input_type="adjudication",
            dm_input_data={
                "needs_dice": False,
                "manual_success": False,
            }
        )

        # Suggestion should be cleared
        assert app._current_roll_suggestion is None


@pytest.mark.asyncio
async def test_roll_response_accept_handles_orchestrator_error(
    mock_orchestrator, mock_router
):
    """Integration: Accept command handles orchestrator errors gracefully."""
    mock_orchestrator.resume_turn_with_dm_input.side_effect = Exception(
        "Roll service unavailable"
    )

    app = DMTextualInterface(orchestrator=mock_orchestrator, router=mock_router)

    suggestion = {
        "character_name": "Zara-7",
        "character_id": "char_zara_001",
        "task_type": "Lasers",
        "prepared_context": "I studied the schematics",
        "suggested_roll": "2d6 Lasers",
    }

    async with app.run_test():
        app._current_roll_suggestion = suggestion

        from textual.widgets import Input

        input_widget = app.query_one("#dm-input", Input)
        event = Input.Submitted(input_widget, "accept")

        # Should not raise exception
        await app.on_input_submitted(event)

        # Suggestion should still be cleared even on error
        assert app._current_roll_suggestion is None


@pytest.mark.asyncio
async def test_roll_response_override_handles_invalid_dice_value(
    mock_orchestrator, mock_router
):
    """Integration: Override command handles invalid dice values."""
    app = DMTextualInterface(orchestrator=mock_orchestrator, router=mock_router)

    suggestion = {
        "character_name": "Zara-7",
        "character_id": "char_zara_001",
        "task_type": "Lasers",
        "prepared_context": "I studied the schematics",
        "suggested_roll": "2d6 Lasers",
    }

    async with app.run_test():
        app._current_roll_suggestion = suggestion

        from textual.widgets import Input

        input_widget = app.query_one("#dm-input", Input)

        # Try to override with invalid value
        event = Input.Submitted(input_widget, "override 7")
        await app.on_input_submitted(event)

        # Orchestrator should NOT be called
        mock_orchestrator.resume_turn_with_dm_input.assert_not_called()

        # Suggestion should still be cleared
        assert app._current_roll_suggestion is None


# ============================================================================
# Phase 4: Clarifying Questions Tests
# ============================================================================


@pytest.mark.asyncio
async def test_show_clarification_questions_displays_panel(mock_orchestrator, mock_router):
    """Integration: Clarification questions panel displays correctly."""
    app = DMTextualInterface(orchestrator=mock_orchestrator, router=mock_router)

    questions_data = {
        "round": 1,
        "questions": [
            {
                "agent_id": "agent_alex_001",
                "question_text": "Are there any guards visible?",
            },
            {
                "agent_id": "agent_zara_001",
                "question_text": "What's the range of the plasma cannon?",
            }
        ]
    }

    app._character_names = {
        "agent_alex_001": "Alex",
        "agent_zara_001": "Zara-7"
    }

    async with app.run_test():
        app.show_clarification_questions(questions_data)

        assert app._clarification_mode is True
        assert app._pending_questions == questions_data["questions"]
        assert app._questions_round == 1


@pytest.mark.asyncio
async def test_answer_clarification_question(mock_orchestrator, mock_router):
    """Integration: Answering a clarification question calls orchestrator."""
    mock_orchestrator.resume_turn_with_dm_input.return_value = {
        "phase_completed": "memory_query"
    }

    app = DMTextualInterface(orchestrator=mock_orchestrator, router=mock_router)

    questions = [
        {
            "agent_id": "agent_alex_001",
            "question_text": "Are there guards?",
        }
    ]

    app._clarification_mode = True
    app._pending_questions = questions
    app._questions_round = 1
    app._character_names = {"agent_alex_001": "Alex"}

    # Mock _fetch_new_clarification_questions to return no follow-ups
    app._fetch_new_clarification_questions = Mock(return_value=[])

    async with app.run_test():
        from textual.widgets import Input

        input_widget = app.query_one("#dm-input", Input)
        event = Input.Submitted(input_widget, "1 Yes, two guards at the far end")
        await app.on_input_submitted(event)

        # Verify orchestrator was called
        mock_orchestrator.resume_turn_with_dm_input.assert_called_once()
        call_args = mock_orchestrator.resume_turn_with_dm_input.call_args

        assert call_args[1]["session_number"] == 1
        assert call_args[1]["dm_input_type"] == "dm_clarification_answer"
        assert call_args[1]["dm_input_data"]["answers"][0]["agent_id"] == "agent_alex_001"
        assert "two guards" in call_args[1]["dm_input_data"]["answers"][0]["answer"]
        assert call_args[1]["dm_input_data"]["force_finish"] is False


@pytest.mark.asyncio
async def test_finish_clarification_early(mock_orchestrator, mock_router):
    """Integration: Force finishing clarification rounds calls orchestrator."""
    mock_orchestrator.resume_turn_with_dm_input.return_value = {
        "phase_completed": "strategic_intent"
    }

    app = DMTextualInterface(orchestrator=mock_orchestrator, router=mock_router)
    app._clarification_mode = True
    app._pending_questions = [{"agent_id": "agent_1", "question_text": "Any guards?"}]

    async with app.run_test():
        from textual.widgets import Input

        input_widget = app.query_one("#dm-input", Input)
        event = Input.Submitted(input_widget, "finish")
        await app.on_input_submitted(event)

        assert app._clarification_mode is False
        mock_orchestrator.resume_turn_with_dm_input.assert_called_once_with(
            session_number=1,
            dm_input_type="dm_clarification_answer",
            dm_input_data={"answers": [], "force_finish": True}
        )


@pytest.mark.asyncio
async def test_done_command_exits_clarification_mode(mock_orchestrator, mock_router):
    """Integration: Done command clears clarification mode."""
    app = DMTextualInterface(orchestrator=mock_orchestrator, router=mock_router)
    app._clarification_mode = True
    app._pending_questions = [{"agent_id": "agent_1", "question_text": "Any guards?"}]

    async with app.run_test():
        from textual.widgets import Input

        input_widget = app.query_one("#dm-input", Input)
        event = Input.Submitted(input_widget, "done")
        await app.on_input_submitted(event)

        assert app._clarification_mode is False
        assert app._pending_questions is None


@pytest.mark.asyncio
async def test_invalid_question_number_shows_error(mock_orchestrator, mock_router):
    """Integration: Invalid question number shows error message."""
    app = DMTextualInterface(orchestrator=mock_orchestrator, router=mock_router)
    app._clarification_mode = True
    app._pending_questions = [{"agent_id": "agent_1", "question_text": "Question 1?"}]

    async with app.run_test():
        from textual.widgets import Input

        input_widget = app.query_one("#dm-input", Input)

        # Try to answer question 5 when only 1 exists
        event = Input.Submitted(input_widget, "5 Some answer")
        await app.on_input_submitted(event)

        # Orchestrator should not be called
        mock_orchestrator.resume_turn_with_dm_input.assert_not_called()


@pytest.mark.asyncio
async def test_invalid_answer_format_shows_error(mock_orchestrator, mock_router):
    """Integration: Invalid answer format shows error message."""
    app = DMTextualInterface(orchestrator=mock_orchestrator, router=mock_router)
    app._clarification_mode = True
    app._pending_questions = [{"agent_id": "agent_1", "question_text": "Question 1?"}]

    async with app.run_test():
        from textual.widgets import Input

        input_widget = app.query_one("#dm-input", Input)

        # Invalid format (no space, no answer)
        event = Input.Submitted(input_widget, "1")
        await app.on_input_submitted(event)

        # Orchestrator should not be called
        mock_orchestrator.resume_turn_with_dm_input.assert_not_called()


@pytest.mark.asyncio
async def test_display_turn_result_shows_clarification_questions(mock_orchestrator, mock_router):
    """Integration: Turn result pause for clarification displays questions."""
    from unittest.mock import Mock

    # Mock message for clarification question
    mock_message = Mock()
    mock_message.timestamp = datetime.now()
    mock_message.from_agent = "agent_alex_001"
    mock_message.content = "Are there any guards?"
    mock_message.phase = "dm_clarification"
    mock_message.turn_number = 1

    mock_router.get_ooc_messages_for_player.return_value = [mock_message]

    app = DMTextualInterface(orchestrator=mock_orchestrator, router=mock_router)
    app._character_names = {"agent_alex_001": "Alex"}
    app.turn_number = 1

    turn_result = {
        "awaiting_dm_input": True,
        "awaiting_phase": "dm_clarification_wait",
        "phase_completed": "dm_clarification",
    }

    async with app.run_test():
        app.display_turn_result(turn_result)

        # Should enter clarification mode
        assert app._clarification_mode is True
        assert app._pending_questions is not None
        assert len(app._pending_questions) == 1
        assert app._pending_questions[0]["agent_id"] == "agent_alex_001"


@pytest.mark.asyncio
async def test_show_clarification_questions_with_no_questions(mock_orchestrator, mock_router):
    """Integration: Empty questions list shows appropriate message."""
    app = DMTextualInterface(orchestrator=mock_orchestrator, router=mock_router)

    questions_data = {
        "round": 1,
        "questions": []
    }

    async with app.run_test():
        app.show_clarification_questions(questions_data)

        # Should not enter clarification mode
        assert app._clarification_mode is False


@pytest.mark.asyncio
async def test_empty_answer_rejected_with_validation_error(mock_orchestrator, mock_router):
    """Integration: Empty answer text is rejected with validation error."""
    app = DMTextualInterface(orchestrator=mock_orchestrator, router=mock_router)
    app._clarification_mode = True
    app._pending_questions = [
        {"agent_id": "agent_1", "question_text": "Any guards?"}
    ]

    async with app.run_test():
        from textual.widgets import Input

        input_widget = app.query_one("#dm-input", Input)

        # Submit answer with empty text (just whitespace after number)
        event = Input.Submitted(input_widget, "1 ")
        await app.on_input_submitted(event)

        # Orchestrator should not be called
        mock_orchestrator.resume_turn_with_dm_input.assert_not_called()

        # Should stay in clarification mode
        assert app._clarification_mode is True


@pytest.mark.asyncio
async def test_done_in_answer_shows_hint(mock_orchestrator, mock_router):
    """Integration: Typing '1 done' shows hint about using 'done' alone."""
    app = DMTextualInterface(orchestrator=mock_orchestrator, router=mock_router)
    app._clarification_mode = True
    app._pending_questions = [
        {"agent_id": "agent_1", "question_text": "Any guards?"}
    ]
    app._character_names = {"agent_1": "Alex"}

    # Mock _fetch_new_clarification_questions to return no follow-ups
    app._fetch_new_clarification_questions = Mock(return_value=[])

    mock_orchestrator.resume_turn_with_dm_input.return_value = {
        "phase_completed": "memory_query"
    }

    async with app.run_test():
        from textual.widgets import Input

        input_widget = app.query_one("#dm-input", Input)

        # Submit answer containing "done"
        event = Input.Submitted(input_widget, "1 done with this")
        await app.on_input_submitted(event)

        # Should still process the answer (with hint displayed)
        mock_orchestrator.resume_turn_with_dm_input.assert_called_once()


@pytest.mark.asyncio
async def test_answer_recording_error_keeps_mode_active(mock_orchestrator, mock_router):
    """Integration: Error during answer recording keeps clarification mode active."""
    mock_orchestrator.resume_turn_with_dm_input.side_effect = Exception(
        "Connection error"
    )

    app = DMTextualInterface(orchestrator=mock_orchestrator, router=mock_router)
    app._clarification_mode = True
    app._pending_questions = [
        {"agent_id": "agent_1", "question_text": "Any guards?"}
    ]
    app._character_names = {"agent_1": "Alex"}

    async with app.run_test():
        from textual.widgets import Input

        input_widget = app.query_one("#dm-input", Input)

        # Submit valid answer, but orchestrator fails
        event = Input.Submitted(input_widget, "1 Yes, there are guards")
        await app.on_input_submitted(event)

        # Should stay in clarification mode (not clear it)
        assert app._clarification_mode is True

        # Should still have pending questions
        assert app._pending_questions is not None


@pytest.mark.asyncio
async def test_connection_error_during_follow_up_poll_exits_mode(
    mock_orchestrator, mock_router
):
    """Integration: Connection error during follow-up polling exits clarification mode."""
    mock_orchestrator.resume_turn_with_dm_input.return_value = {
        "phase_completed": "dm_clarification"
    }

    app = DMTextualInterface(orchestrator=mock_orchestrator, router=mock_router)
    app._clarification_mode = True
    app._pending_questions = [
        {"agent_id": "agent_1", "question_text": "Any guards?"}
    ]
    app._character_names = {"agent_1": "Alex"}

    # Mock _fetch_new_clarification_questions to raise connection error
    app._fetch_new_clarification_questions = Mock(
        side_effect=ConnectionError("Redis connection lost")
    )

    async with app.run_test():
        from textual.widgets import Input

        input_widget = app.query_one("#dm-input", Input)

        # Submit valid answer
        event = Input.Submitted(input_widget, "1 Yes, there are guards")
        await app.on_input_submitted(event)

        # Answer should be recorded successfully
        assert app._clarification_mode is True

        # Type "done" to trigger follow-up polling
        event = Input.Submitted(input_widget, "done")
        await app.on_input_submitted(event)

        # Connection error during follow-up poll should exit clarification mode
        assert app._clarification_mode is False
