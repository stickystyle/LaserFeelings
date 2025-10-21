# ABOUTME: Unit tests for Textual interface keyboard shortcuts (Ctrl+R/S/F/I).
# ABOUTME: Tests phase validation, command routing, and error handling for keyboard shortcuts.

from unittest.mock import MagicMock, patch

import pytest

from src.interface.dm_textual import DMTextualInterface
from src.models.game_state import GamePhase
from src.orchestration.message_router import MessageRouter
from src.orchestration.turn_orchestrator import TurnOrchestrator


@pytest.fixture
def mock_orchestrator():
    """Create mock TurnOrchestrator"""
    return MagicMock(spec=TurnOrchestrator)


@pytest.fixture
def mock_router():
    """Create mock MessageRouter"""
    return MagicMock(spec=MessageRouter)


@pytest.fixture
def dm_interface(mock_orchestrator, mock_router):
    """Create DMTextualInterface instance with mocked dependencies"""
    interface = DMTextualInterface(orchestrator=mock_orchestrator, router=mock_router)
    return interface


class TestQuickRollShortcut:
    """Tests for Ctrl+R quick roll shortcut"""

    def test_quick_roll_during_adjudication(self, dm_interface):
        """Ctrl+R should work during DM_ADJUDICATION phase"""
        # Set adjudication phase
        dm_interface.current_phase = GamePhase.DM_ADJUDICATION

        # Mock _simulate_user_input to verify it's called
        with patch.object(dm_interface, "_simulate_user_input") as mock_simulate:
            dm_interface.action_quick_roll()

            # Should simulate "accept" command
            mock_simulate.assert_called_once_with("accept")

    def test_quick_roll_during_dice_resolution(self, dm_interface):
        """Ctrl+R should work during DICE_RESOLUTION phase"""
        # Set dice resolution phase
        dm_interface.current_phase = GamePhase.DICE_RESOLUTION

        # Mock _simulate_user_input to verify it's called
        with patch.object(dm_interface, "_simulate_user_input") as mock_simulate:
            dm_interface.action_quick_roll()

            # Should simulate "accept" command
            mock_simulate.assert_called_once_with("accept")

    def test_quick_roll_during_narration_rejected(self, dm_interface):
        """Ctrl+R should be rejected during DM_NARRATION phase"""
        # Set narration phase (not adjudication)
        dm_interface.current_phase = GamePhase.DM_NARRATION

        # Mock write_game_log to verify error message
        with patch.object(dm_interface, "write_game_log") as mock_log:
            with patch.object(dm_interface, "_simulate_user_input") as mock_simulate:
                dm_interface.action_quick_roll()

                # Should display error message
                mock_log.assert_called_once()
                error_msg = mock_log.call_args[0][0]
                assert "only available during adjudication phase" in error_msg

                # Should NOT simulate command
                mock_simulate.assert_not_called()

    def test_quick_roll_during_strategic_intent_rejected(self, dm_interface):
        """Ctrl+R should be rejected during STRATEGIC_INTENT phase"""
        # Set strategic intent phase
        dm_interface.current_phase = GamePhase.STRATEGIC_INTENT

        # Mock write_game_log to verify error message
        with patch.object(dm_interface, "write_game_log") as mock_log:
            with patch.object(dm_interface, "_simulate_user_input") as mock_simulate:
                dm_interface.action_quick_roll()

                # Should display error and not simulate command
                mock_log.assert_called_once()
                mock_simulate.assert_not_called()


class TestSuccessShortcut:
    """Tests for Ctrl+S success shortcut"""

    def test_success_during_adjudication(self, dm_interface):
        """Ctrl+S should work during DM_ADJUDICATION phase"""
        dm_interface.current_phase = GamePhase.DM_ADJUDICATION

        with patch.object(dm_interface, "_simulate_user_input") as mock_simulate:
            dm_interface.action_success()

            # Should simulate "success" command
            mock_simulate.assert_called_once_with("success")

    def test_success_during_dice_resolution(self, dm_interface):
        """Ctrl+S should work during DICE_RESOLUTION phase"""
        dm_interface.current_phase = GamePhase.DICE_RESOLUTION

        with patch.object(dm_interface, "_simulate_user_input") as mock_simulate:
            dm_interface.action_success()

            mock_simulate.assert_called_once_with("success")

    def test_success_during_outcome_rejected(self, dm_interface):
        """Ctrl+S should be rejected during DM_OUTCOME phase"""
        dm_interface.current_phase = GamePhase.DM_OUTCOME

        with patch.object(dm_interface, "write_game_log") as mock_log:
            with patch.object(dm_interface, "_simulate_user_input") as mock_simulate:
                dm_interface.action_success()

                # Should display error message
                mock_log.assert_called_once()
                error_msg = mock_log.call_args[0][0]
                assert "only available during adjudication phase" in error_msg

                # Should NOT simulate command
                mock_simulate.assert_not_called()


class TestFailShortcut:
    """Tests for Ctrl+F fail shortcut"""

    def test_fail_during_adjudication(self, dm_interface):
        """Ctrl+F should work during DM_ADJUDICATION phase"""
        dm_interface.current_phase = GamePhase.DM_ADJUDICATION

        with patch.object(dm_interface, "_simulate_user_input") as mock_simulate:
            dm_interface.action_fail()

            # Should simulate "fail" command
            mock_simulate.assert_called_once_with("fail")

    def test_fail_during_dice_resolution(self, dm_interface):
        """Ctrl+F should work during DICE_RESOLUTION phase"""
        dm_interface.current_phase = GamePhase.DICE_RESOLUTION

        with patch.object(dm_interface, "_simulate_user_input") as mock_simulate:
            dm_interface.action_fail()

            mock_simulate.assert_called_once_with("fail")

    def test_fail_during_character_action_rejected(self, dm_interface):
        """Ctrl+F should be rejected during CHARACTER_ACTION phase"""
        dm_interface.current_phase = GamePhase.CHARACTER_ACTION

        with patch.object(dm_interface, "write_game_log") as mock_log:
            with patch.object(dm_interface, "_simulate_user_input") as mock_simulate:
                dm_interface.action_fail()

                # Should display error and not simulate command
                mock_log.assert_called_once()
                error_msg = mock_log.call_args[0][0]
                assert "only available during adjudication phase" in error_msg
                mock_simulate.assert_not_called()


class TestInfoShortcut:
    """Tests for Ctrl+I info shortcut"""

    def test_info_during_narration(self, dm_interface):
        """Ctrl+I should work during DM_NARRATION phase"""
        dm_interface.current_phase = GamePhase.DM_NARRATION

        with patch.object(dm_interface, "show_session_info") as mock_show_info:
            dm_interface.action_info()

            # Should call show_session_info
            mock_show_info.assert_called_once()

    def test_info_during_adjudication(self, dm_interface):
        """Ctrl+I should work during DM_ADJUDICATION phase"""
        dm_interface.current_phase = GamePhase.DM_ADJUDICATION

        with patch.object(dm_interface, "show_session_info") as mock_show_info:
            dm_interface.action_info()

            mock_show_info.assert_called_once()

    def test_info_during_strategic_intent(self, dm_interface):
        """Ctrl+I should work during STRATEGIC_INTENT phase"""
        dm_interface.current_phase = GamePhase.STRATEGIC_INTENT

        with patch.object(dm_interface, "show_session_info") as mock_show_info:
            dm_interface.action_info()

            mock_show_info.assert_called_once()

    def test_info_during_outcome(self, dm_interface):
        """Ctrl+I should work during DM_OUTCOME phase"""
        dm_interface.current_phase = GamePhase.DM_OUTCOME

        with patch.object(dm_interface, "show_session_info") as mock_show_info:
            dm_interface.action_info()

            mock_show_info.assert_called_once()


class TestIsAdjudicationPhaseHelper:
    """Tests for _is_adjudication_phase() helper method"""

    def test_adjudication_phase_returns_true(self, dm_interface):
        """_is_adjudication_phase should return True for DM_ADJUDICATION"""
        dm_interface.current_phase = GamePhase.DM_ADJUDICATION

        assert dm_interface._is_adjudication_phase() is True

    def test_dice_resolution_returns_true(self, dm_interface):
        """_is_adjudication_phase should return True for DICE_RESOLUTION"""
        dm_interface.current_phase = GamePhase.DICE_RESOLUTION

        assert dm_interface._is_adjudication_phase() is True

    def test_narration_phase_returns_false(self, dm_interface):
        """_is_adjudication_phase should return False for DM_NARRATION"""
        dm_interface.current_phase = GamePhase.DM_NARRATION

        assert dm_interface._is_adjudication_phase() is False

    def test_strategic_intent_returns_false(self, dm_interface):
        """_is_adjudication_phase should return False for STRATEGIC_INTENT"""
        dm_interface.current_phase = GamePhase.STRATEGIC_INTENT

        assert dm_interface._is_adjudication_phase() is False

    def test_outcome_phase_returns_false(self, dm_interface):
        """_is_adjudication_phase should return False for DM_OUTCOME"""
        dm_interface.current_phase = GamePhase.DM_OUTCOME

        assert dm_interface._is_adjudication_phase() is False


class TestSimulateUserInputHelper:
    """Tests for _simulate_user_input() helper method"""

    @patch("src.interface.dm_textual.Input")
    def test_simulate_sets_input_value(self, mock_input_class, dm_interface):
        """_simulate_user_input should set input widget value"""
        # Create mock input widget
        mock_input_widget = MagicMock()
        mock_input_widget.id = "dm-input"

        # Mock query_one to return mock input
        with patch.object(dm_interface, "query_one", return_value=mock_input_widget):
            with patch.object(dm_interface, "post_message"):
                dm_interface._simulate_user_input("test_command")

                # Should set input value
                assert mock_input_widget.value == "test_command"

    @patch("src.interface.dm_textual.Input")
    def test_simulate_posts_submitted_event(self, mock_input_class, dm_interface):
        """_simulate_user_input should post Input.Submitted event"""
        # Create mock input widget
        mock_input_widget = MagicMock()
        mock_input_widget.id = "dm-input"

        # Mock query_one to return mock input
        with patch.object(dm_interface, "query_one", return_value=mock_input_widget):
            with patch.object(dm_interface, "post_message") as mock_post:
                dm_interface._simulate_user_input("accept")

                # Should post Input.Submitted event
                mock_post.assert_called_once()
                # Verify event type (Input.Submitted)
                event = mock_post.call_args[0][0]
                assert hasattr(event, "value")
                assert event.value == "accept"

    @patch("src.interface.dm_textual.Input")
    def test_simulate_different_commands(self, mock_input_class, dm_interface):
        """_simulate_user_input should work with different commands"""
        commands = ["accept", "success", "fail", "override 3"]

        for command in commands:
            mock_input_widget = MagicMock()
            mock_input_widget.id = "dm-input"

            with patch.object(dm_interface, "query_one", return_value=mock_input_widget):
                with patch.object(dm_interface, "post_message") as mock_post:
                    dm_interface._simulate_user_input(command)

                    # Verify command value
                    assert mock_input_widget.value == command
                    event = mock_post.call_args[0][0]
                    assert event.value == command


class TestShortcutIntegration:
    """Integration tests verifying shortcuts route to correct commands"""

    def test_quick_roll_routes_to_accept_handler(self, dm_interface):
        """Ctrl+R should route to 'accept' command handler"""
        dm_interface.current_phase = GamePhase.DM_ADJUDICATION
        dm_interface._current_roll_suggestion = {
            "action_dict": {"task_type": "lasers"},
            "character_name": "Zara-7",
        }

        # Mock query_one to return mock input widget
        mock_input_widget = MagicMock()
        mock_input_widget.id = "dm-input"

        with patch.object(dm_interface, "query_one", return_value=mock_input_widget):
            with patch.object(dm_interface, "post_message"):
                # Trigger shortcut
                dm_interface.action_quick_roll()

                # Verify "accept" was set as input value
                assert mock_input_widget.value == "accept"

    def test_success_routes_to_success_handler(self, dm_interface):
        """Ctrl+S should route to 'success' command handler"""
        dm_interface.current_phase = GamePhase.DM_ADJUDICATION
        dm_interface._current_roll_suggestion = {
            "action_dict": {"task_type": "feelings"},
            "character_name": "Captain Nova",
        }

        # Mock query_one to return mock input widget
        mock_input_widget = MagicMock()
        mock_input_widget.id = "dm-input"

        with patch.object(dm_interface, "query_one", return_value=mock_input_widget):
            with patch.object(dm_interface, "post_message"):
                dm_interface.action_success()

                # Verify "success" was set as input value
                assert mock_input_widget.value == "success"

    def test_fail_routes_to_fail_handler(self, dm_interface):
        """Ctrl+F should route to 'fail' command handler"""
        dm_interface.current_phase = GamePhase.DM_ADJUDICATION
        dm_interface._current_roll_suggestion = {
            "action_dict": {"task_type": "lasers"},
            "character_name": "Dr. Chen",
        }

        # Mock query_one to return mock input widget
        mock_input_widget = MagicMock()
        mock_input_widget.id = "dm-input"

        with patch.object(dm_interface, "query_one", return_value=mock_input_widget):
            with patch.object(dm_interface, "post_message"):
                dm_interface.action_fail()

                # Verify "fail" was set as input value
                assert mock_input_widget.value == "fail"
