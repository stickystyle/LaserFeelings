# ABOUTME: Unit tests for LASER FEELINGS outcome handling in Textual DM interface.
# ABOUTME: Tests display, prompting, and turn flow for critical success events.

from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

import pytest
from textual.widgets import RichLog

from src.interface.dm_textual import DMTextualInterface
from src.models.dice_models import LasersFeelingRollResult, RollOutcome


@pytest.fixture
def mock_orchestrator():
    """Mock TurnOrchestrator"""
    return MagicMock()


@pytest.fixture
def mock_router():
    """Mock MessageRouter"""
    return MagicMock()


@pytest.fixture
def textual_interface(mock_orchestrator, mock_router):
    """Create DMTextualInterface instance"""
    interface = DMTextualInterface(orchestrator=mock_orchestrator, router=mock_router)
    # Mock the query_one method to return a fake RichLog with a write method
    # Make sure the same mock is returned each time query_one is called
    mock_log = MagicMock(spec=RichLog)
    mock_log.write = MagicMock()

    def query_one_side_effect(*args, **kwargs):
        # Always return the same mock log
        return mock_log

    interface.query_one = MagicMock(side_effect=query_one_side_effect)
    # Store reference to mock_log for test access
    interface._test_mock_log = mock_log
    return interface


@pytest.fixture
def laser_feelings_roll_with_question():
    """LasersFeelingRollResult with LASER FEELINGS and a question"""
    return LasersFeelingRollResult(
        character_number=3,
        task_type="lasers",
        is_prepared=True,
        is_expert=False,
        is_helping=False,
        individual_rolls=[3, 5],
        die_successes=[True, True],
        laser_feelings_indices=[0],  # First die rolled 3 (exact match)
        total_successes=2,
        outcome=RollOutcome.SUCCESS,
        gm_question="What security measures do I notice?",
        timestamp=datetime.now(UTC),
    )


@pytest.fixture
def laser_feelings_roll_without_question():
    """LasersFeelingRollResult with LASER FEELINGS but no question"""
    return LasersFeelingRollResult(
        character_number=2,
        task_type="feelings",
        is_prepared=False,
        is_expert=True,
        is_helping=False,
        individual_rolls=[2, 4],
        die_successes=[True, True],
        laser_feelings_indices=[0],  # First die rolled 2 (exact match)
        total_successes=2,
        outcome=RollOutcome.SUCCESS,
        gm_question=None,  # No question suggested
        timestamp=datetime.now(UTC),
    )


@pytest.fixture
def normal_roll_result():
    """LasersFeelingRollResult without LASER FEELINGS"""
    return LasersFeelingRollResult(
        character_number=4,
        task_type="lasers",
        is_prepared=False,
        is_expert=False,
        is_helping=False,
        individual_rolls=[2],
        die_successes=[True],
        laser_feelings_indices=[],  # No exact matches
        total_successes=1,
        outcome=RollOutcome.BARELY,
        gm_question=None,
        timestamp=datetime.now(UTC),
    )


class TestDisplayLaserFeelingsResult:
    """Test _display_lasers_feelings_result() method"""

    def test_displays_roll_with_laser_feelings_indicator(
        self, textual_interface, laser_feelings_roll_with_question
    ):
        """Should display roll details with LASER FEELINGS indicator"""
        textual_interface._display_lasers_feelings_result(laser_feelings_roll_with_question)

        # Verify write_game_log was called
        game_log = textual_interface._test_mock_log
        assert game_log.write.call_count > 0

        # Check that LASER FEELINGS indicator was displayed
        all_calls = [str(call) for call in game_log.write.call_args_list]
        laser_feelings_displayed = any("LASER FEELINGS" in str(call) for call in all_calls)
        assert laser_feelings_displayed, "LASER FEELINGS indicator should be displayed"

    def test_displays_character_suggested_question(
        self, textual_interface, laser_feelings_roll_with_question
    ):
        """Should display character's suggested question if provided"""
        textual_interface._display_lasers_feelings_result(laser_feelings_roll_with_question)

        game_log = textual_interface._test_mock_log
        all_calls = [str(call) for call in game_log.write.call_args_list]

        # Check that the question text appears
        question_displayed = any(
            laser_feelings_roll_with_question.gm_question in str(call) for call in all_calls
        )
        assert question_displayed, "Character's question should be displayed"

    def test_displays_no_question_message_when_missing(
        self, textual_interface, laser_feelings_roll_without_question
    ):
        """Should display message when no question was suggested"""
        textual_interface._display_lasers_feelings_result(laser_feelings_roll_without_question)

        game_log = textual_interface._test_mock_log
        all_calls = [str(call) for call in game_log.write.call_args_list]

        # Check for "No question suggested" message
        no_question_msg = any(
            "No question suggested" in str(call) or "want to know" in str(call)
            for call in all_calls
        )
        assert no_question_msg, "Should display message when no question provided"

    def test_displays_die_number_for_laser_feelings(
        self, textual_interface, laser_feelings_roll_with_question
    ):
        """Should display which die showed LASER FEELINGS"""
        textual_interface._display_lasers_feelings_result(laser_feelings_roll_with_question)

        game_log = textual_interface._test_mock_log
        all_calls = [str(call) for call in game_log.write.call_args_list]

        # Should show "die #1" (since laser_feelings_indices=[0], displayed as 1-indexed)
        die_number_shown = any("die #1" in str(call) for call in all_calls)
        assert die_number_shown, "Should display which die showed LASER FEELINGS"

    def test_displays_roll_outcome(self, textual_interface, laser_feelings_roll_with_question):
        """Should display roll outcome (always success for LASER FEELINGS)"""
        textual_interface._display_lasers_feelings_result(laser_feelings_roll_with_question)

        game_log = textual_interface._test_mock_log
        all_calls = [str(call) for call in game_log.write.call_args_list]

        # Should show outcome
        outcome_shown = any("SUCCESS" in str(call).upper() for call in all_calls)
        assert outcome_shown, "Should display roll outcome"

    def test_displays_individual_rolls(self, textual_interface, laser_feelings_roll_with_question):
        """Should display individual die results"""
        textual_interface._display_lasers_feelings_result(laser_feelings_roll_with_question)

        game_log = textual_interface._test_mock_log
        all_calls = [str(call) for call in game_log.write.call_args_list]

        # Should show the rolls [3, 5]
        rolls_shown = any("[3, 5]" in str(call) for call in all_calls)
        assert rolls_shown, "Should display individual die rolls"


class TestPromptForLaserFeelingsAnswer:
    """Test _prompt_for_laser_feelings_answer() method"""

    def test_displays_prompt_for_suggested_question(
        self, textual_interface, laser_feelings_roll_with_question
    ):
        """Should display prompt to answer character's question"""
        textual_interface._prompt_for_laser_feelings_answer(laser_feelings_roll_with_question)

        game_log = textual_interface._test_mock_log
        all_calls = [str(call) for call in game_log.write.call_args_list]

        # Should show "Answer" prompt
        answer_prompt = any("answer" in str(call).lower() for call in all_calls)
        assert answer_prompt, "Should display answer prompt"

    def test_displays_insight_prompt_when_no_question(
        self, textual_interface, laser_feelings_roll_without_question
    ):
        """Should display generic insight prompt when no question provided"""
        textual_interface._prompt_for_laser_feelings_answer(laser_feelings_roll_without_question)

        game_log = textual_interface._test_mock_log
        all_calls = [str(call) for call in game_log.write.call_args_list]

        # Should show "insight" prompt
        insight_prompt = any("insight" in str(call).lower() for call in all_calls)
        assert insight_prompt, "Should display insight prompt when no question"

    def test_returns_none_when_no_laser_feelings(self, textual_interface, normal_roll_result):
        """Should return None and not prompt when no LASER FEELINGS occurred"""
        result = textual_interface._prompt_for_laser_feelings_answer(normal_roll_result)

        assert result is None, "Should return None for normal rolls"

        # Should not write any prompts
        game_log = textual_interface._test_mock_log
        assert game_log.write.call_count == 0, "Should not display prompts for normal rolls"


class TestLaserFeelingsIntegration:
    """Test integration of LASER FEELINGS into turn flow"""

    @pytest.mark.asyncio
    async def test_laser_feelings_triggers_special_phase(
        self, textual_interface, laser_feelings_roll_with_question
    ):
        """Should enter LASER FEELINGS mode when roll has exact match"""
        # Simulate accepting a roll suggestion that results in LASER FEELINGS
        textual_interface._current_roll_suggestion = {
            "character_name": "Zara",
            "character_id": "char_zara_001",
            "task_type": "lasers",
            "suggested_roll": "2d6 Lasers",
        }

        # Mock roll execution to return LASER FEELINGS
        with patch.object(
            textual_interface,
            "_execute_character_suggested_roll",
            return_value={"success": True, "roll_result": laser_feelings_roll_with_question},
        ):
            # Simulate input event for "accept"
            from textual.widgets import Input

            mock_input = MagicMock(spec=Input)
            mock_input.id = "dm-input"

            event = Input.Submitted(mock_input, "accept")
            await textual_interface.on_input_submitted(event)

            # Should enter LASER FEELINGS mode
            assert textual_interface._laser_feelings_mode is True, (
                "Should enter LASER FEELINGS mode"
            )
            assert (
                textual_interface._pending_laser_feelings_result
                == laser_feelings_roll_with_question
            )

    @pytest.mark.asyncio
    async def test_dm_answer_captured_and_sent_to_orchestrator(
        self, textual_interface, laser_feelings_roll_with_question
    ):
        """Should capture DM's answer and send to orchestrator"""
        # Set up LASER FEELINGS mode
        textual_interface._laser_feelings_mode = True
        textual_interface._pending_laser_feelings_result = laser_feelings_roll_with_question

        # Mock the background task runner
        with patch.object(textual_interface, "_run_blocking_in_background") as mock_bg:
            # Simulate DM typing answer
            from textual.widgets import Input

            mock_input = MagicMock(spec=Input)
            mock_input.id = "dm-input"

            event = Input.Submitted(mock_input, "You notice a hidden camera in the corner")
            await textual_interface.on_input_submitted(event)

            # Should exit LASER FEELINGS mode
            assert textual_interface._laser_feelings_mode is False
            assert textual_interface._pending_laser_feelings_result is None

            # Should call orchestrator with answer
            assert mock_bg.called
            # Extract the lambda that was passed
            call_args = mock_bg.call_args
            assert call_args is not None

    @pytest.mark.asyncio
    async def test_empty_answer_rejected(
        self, textual_interface, laser_feelings_roll_with_question
    ):
        """Should reject empty answers and keep waiting"""
        # Set up LASER FEELINGS mode
        textual_interface._laser_feelings_mode = True
        textual_interface._pending_laser_feelings_result = laser_feelings_roll_with_question

        # Simulate empty input
        from textual.widgets import Input

        mock_input = MagicMock(spec=Input)
        mock_input.id = "dm-input"

        event = Input.Submitted(mock_input, "   ")  # Just whitespace
        await textual_interface.on_input_submitted(event)

        # Should stay in LASER FEELINGS mode
        assert textual_interface._laser_feelings_mode is True
        assert textual_interface._pending_laser_feelings_result is not None

        # Should display error message
        game_log = textual_interface._test_mock_log
        all_calls = [str(call) for call in game_log.write.call_args_list]

        error_shown = any(
            "cannot be empty" in str(call).lower() or "provide an answer" in str(call).lower()
            for call in all_calls
        )
        assert error_shown, f"Should display error for empty answer. Got calls: {all_calls}"

    @pytest.mark.asyncio
    async def test_normal_roll_skips_laser_feelings_phase(
        self, textual_interface, normal_roll_result
    ):
        """Should skip LASER FEELINGS phase for normal rolls"""
        # Simulate accepting a roll suggestion with normal result
        textual_interface._current_roll_suggestion = {
            "character_name": "Zara",
            "character_id": "char_zara_001",
            "task_type": "lasers",
            "suggested_roll": "1d6 Lasers",
        }

        # Mock roll execution to return normal roll
        with patch.object(
            textual_interface,
            "_execute_character_suggested_roll",
            return_value={"success": True, "roll_result": normal_roll_result},
        ):
            with patch.object(textual_interface, "_run_blocking_in_background"):
                # Simulate input event for "accept"
                from textual.widgets import Input

                mock_input = MagicMock(spec=Input)
                mock_input.id = "dm-input"

                event = Input.Submitted(mock_input, "accept")
                await textual_interface.on_input_submitted(event)

                # Should NOT enter LASER FEELINGS mode
                assert textual_interface._laser_feelings_mode is False
                assert textual_interface._pending_laser_feelings_result is None

    @pytest.mark.asyncio
    async def test_laser_feelings_has_priority_over_clarification(
        self, textual_interface, laser_feelings_roll_with_question
    ):
        """LASER FEELINGS mode should take priority over clarification mode"""
        # Set up both modes (edge case)
        textual_interface._laser_feelings_mode = True
        textual_interface._pending_laser_feelings_result = laser_feelings_roll_with_question
        textual_interface._clarification_mode = True
        textual_interface._pending_questions = [
            {"agent_id": "agent_alex_001", "question_text": "Test?"}
        ]

        # Mock the background task runner
        with patch.object(textual_interface, "_run_blocking_in_background"):
            # Simulate DM typing answer
            from textual.widgets import Input

            mock_input = MagicMock(spec=Input)
            mock_input.id = "dm-input"

            event = Input.Submitted(mock_input, "You see guards")
            await textual_interface.on_input_submitted(event)

            # LASER FEELINGS mode should be cleared (it was handled)
            assert textual_interface._laser_feelings_mode is False

            # Clarification mode should still be active (wasn't processed)
            assert textual_interface._clarification_mode is True


class TestLaserFeelingsErrorHandling:
    """Test error handling for LASER FEELINGS"""

    def test_display_handles_missing_question_gracefully(self, textual_interface):
        """Should handle roll result with no question gracefully"""
        roll = LasersFeelingRollResult(
            character_number=3,
            task_type="lasers",
            is_prepared=False,
            is_expert=False,
            is_helping=False,
            individual_rolls=[3],
            die_successes=[True],
            laser_feelings_indices=[0],
            total_successes=1,
            outcome=RollOutcome.BARELY,
            gm_question=None,  # Explicitly None
            timestamp=datetime.now(UTC),
        )

        # Should not raise exception
        textual_interface._display_lasers_feelings_result(roll)

        # Should display fallback message
        game_log = textual_interface._test_mock_log
        assert game_log.write.called

    def test_prompt_only_shows_for_laser_feelings_rolls(
        self, textual_interface, normal_roll_result
    ):
        """Should not prompt when has_laser_feelings=False"""
        result = textual_interface._prompt_for_laser_feelings_answer(normal_roll_result)

        assert result is None
        game_log = textual_interface._test_mock_log
        assert game_log.write.call_count == 0, (
            "Should not display anything for non-LASER FEELINGS rolls"
        )
