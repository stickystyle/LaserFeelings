# ABOUTME: Unit tests for DM Command-Line Interface (dm_cli.py).
# ABOUTME: Tests command parsing, handlers, formatting, and error handling for the DM interface.

from datetime import datetime
from unittest.mock import Mock, patch

import pytest

from src.interface.dm_cli import (
    CLIFormatter,
    DMCommandLineInterface,
    DMCommandParser,
    DMCommandType,
    InvalidCommandError,
    ParsedCommand,
)
from src.models.game_state import GamePhase

# ============================================================================
# T063: Command Parser Tests
# ============================================================================


class TestDMCommandParser:
    """Test command parsing with various formats"""

    def test_parse_narrate_command(self):
        """Test parsing narrate command"""
        parser = DMCommandParser()
        result = parser.parse("The ship drifts through space")

        assert result.command_type == DMCommandType.NARRATE
        assert result.args["text"] == "The ship drifts through space"

    def test_parse_narrate_with_slash(self):
        """Test parsing narrate with explicit /narrate"""
        parser = DMCommandParser()
        result = parser.parse("/narrate A door opens")

        assert result.command_type == DMCommandType.NARRATE
        assert result.args["text"] == "A door opens"

    def test_parse_roll_command_simple(self):
        """Test parsing simple roll command"""
        parser = DMCommandParser()
        result = parser.parse("/roll 1d20")

        assert result.command_type == DMCommandType.ROLL
        assert result.args["notation"] == "1d20"

    def test_parse_roll_command_with_modifier(self):
        """Test parsing roll command with modifier"""
        parser = DMCommandParser()
        result = parser.parse("/roll 2d6+3")

        assert result.command_type == DMCommandType.ROLL
        assert result.args["notation"] == "2d6+3"

    def test_parse_roll_command_negative_modifier(self):
        """Test parsing roll command with negative modifier"""
        parser = DMCommandParser()
        result = parser.parse("/roll 3d8-2")

        assert result.command_type == DMCommandType.ROLL
        assert result.args["notation"] == "3d8-2"

    def test_parse_success_command(self):
        """Test parsing success command"""
        parser = DMCommandParser()
        result = parser.parse("success")

        assert result.command_type == DMCommandType.SUCCESS
        assert result.args == {}

    def test_parse_success_command_with_slash(self):
        """Test parsing success command with slash"""
        parser = DMCommandParser()
        result = parser.parse("/success")

        assert result.command_type == DMCommandType.SUCCESS

    def test_parse_fail_command(self):
        """Test parsing fail command"""
        parser = DMCommandParser()
        result = parser.parse("fail")

        assert result.command_type == DMCommandType.FAIL
        assert result.args == {}

    def test_parse_failure_command(self):
        """Test parsing failure command (alias for fail)"""
        parser = DMCommandParser()
        result = parser.parse("failure")

        assert result.command_type == DMCommandType.FAIL

    def test_parse_info_command(self):
        """Test parsing info command"""
        parser = DMCommandParser()
        result = parser.parse("/info")

        assert result.command_type == DMCommandType.INFO

    def test_parse_quit_command(self):
        """Test parsing quit command"""
        parser = DMCommandParser()
        result = parser.parse("/quit")

        assert result.command_type == DMCommandType.QUIT

    def test_parse_empty_input_raises_error(self):
        """Test that empty input raises error"""
        parser = DMCommandParser()

        with pytest.raises(InvalidCommandError, match="Cannot parse empty command"):
            parser.parse("")

    def test_parse_whitespace_only_raises_error(self):
        """Test that whitespace-only input raises error"""
        parser = DMCommandParser()

        with pytest.raises(InvalidCommandError, match="Cannot parse empty command"):
            parser.parse("   ")

    def test_parse_invalid_roll_notation(self):
        """Test that invalid dice notation raises error"""
        parser = DMCommandParser()

        with pytest.raises(InvalidCommandError, match="Invalid dice notation"):
            parser.parse("/roll xyz")

    def test_parse_roll_missing_notation(self):
        """Test that roll without notation raises error"""
        parser = DMCommandParser()

        with pytest.raises(InvalidCommandError, match="Roll command requires dice notation"):
            parser.parse("/roll")


# ============================================================================
# T064-T066: Command Handler Tests
# ============================================================================


class TestCommandHandlers:
    """Test command execution handlers"""

    def test_handle_narrate_command(self):
        """Test narrate command creates DMCommand"""
        cli = DMCommandLineInterface()
        parsed = ParsedCommand(
            command_type=DMCommandType.NARRATE,
            args={"text": "The ship arrives at station"},
            raw_input="The ship arrives at station"
        )

        result = cli.handle_command(parsed)

        assert result["success"] is True
        assert result["command_type"] == DMCommandType.NARRATE
        assert result["args"]["text"] == "The ship arrives at station"

    def test_handle_roll_command(self):
        """Test roll command executes dice roll and returns formatted output"""
        cli = DMCommandLineInterface()
        parsed = ParsedCommand(
            command_type=DMCommandType.ROLL,
            args={"notation": "2d6+3"},
            raw_input="/roll 2d6+3"
        )

        result = cli.handle_command(parsed)

        assert result["success"] is True
        assert result["command_type"] == DMCommandType.ROLL
        assert "notation" in result["args"]
        assert result["args"]["notation"] == "2d6+3"

        # Check that dice were actually rolled
        assert "dice_result" in result["args"]
        dice_result = result["args"]["dice_result"]
        assert dice_result["dice_count"] == 2
        assert dice_result["dice_sides"] == 6
        assert dice_result["modifier"] == 3
        assert len(dice_result["individual_rolls"]) == 2
        assert "total" in dice_result

        # Check that output was formatted
        assert "output" in result
        assert "Dice Roll" in result["output"]

    def test_handle_success_command(self):
        """Test success command creates DMCommand"""
        cli = DMCommandLineInterface()
        parsed = ParsedCommand(
            command_type=DMCommandType.SUCCESS,
            args={},
            raw_input="success"
        )

        result = cli.handle_command(parsed)

        assert result["success"] is True
        assert result["command_type"] == DMCommandType.SUCCESS

    def test_handle_fail_command(self):
        """Test fail command creates DMCommand"""
        cli = DMCommandLineInterface()
        parsed = ParsedCommand(
            command_type=DMCommandType.FAIL,
            args={},
            raw_input="fail"
        )

        result = cli.handle_command(parsed)

        assert result["success"] is True
        assert result["command_type"] == DMCommandType.FAIL


# ============================================================================
# T067: Turn Output Formatter Tests
# ============================================================================


class TestCLIFormatter:
    """Test output formatting for various phases and results"""

    def test_format_header(self):
        """Test formatting campaign header"""
        formatter = CLIFormatter()
        header = formatter.format_header(
            campaign_name="Voyage of the Raptor",
            characters=["Zara-7 (Android Engineer)"]
        )

        assert "Voyage of the Raptor" in header
        assert "Zara-7" in header
        assert "═" in header  # Box drawing chars

    def test_format_phase_transition(self):
        """Test formatting phase transition"""
        formatter = CLIFormatter()
        output = formatter.format_phase_transition(
            phase=GamePhase.MEMORY_QUERY,
            turn_number=1
        )

        assert "Memory Query" in output or "MEMORY_QUERY" in output
        assert "Turn 1" in output or "1" in output

    def test_format_agent_response(self):
        """Test formatting agent strategic intent"""
        formatter = CLIFormatter()
        output = formatter.format_agent_response(
            agent_name="Alex",
            character_name="Zara-7",
            response="We should investigate cautiously",
            phase=GamePhase.STRATEGIC_INTENT
        )

        assert "Alex" in output
        assert "We should investigate cautiously" in output

    def test_format_character_action(self):
        """Test formatting character action"""
        formatter = CLIFormatter()
        output = formatter.format_character_action(
            character_name="Zara-7",
            action='*tilts head* "I suggest we dock"'
        )

        assert "Zara-7" in output
        assert "tilts head" in output
        assert "I suggest we dock" in output

    def test_format_validation_pass(self):
        """Test formatting validation pass"""
        formatter = CLIFormatter()
        output = formatter.format_validation_result(valid=True)

        assert "✓" in output or "PASS" in output

    def test_format_validation_fail(self):
        """Test formatting validation fail"""
        formatter = CLIFormatter()
        output = formatter.format_validation_result(
            valid=False,
            violations=["Character narrated outcome"]
        )

        assert "✗" in output or "FAIL" in output
        assert "Character narrated outcome" in output

    def test_format_dice_roll(self):
        """Test formatting dice roll result"""
        formatter = CLIFormatter()
        output = formatter.format_dice_roll(
            notation="1d20+5",
            individual_rolls=[15],
            total=20,
            modifier=5
        )

        assert "1d20+5" in output
        assert "15" in output
        assert "20" in output

    def test_format_awaiting_dm_input(self):
        """Test formatting awaiting DM prompt"""
        formatter = CLIFormatter()
        output = formatter.format_awaiting_dm_input(
            expected_command_types=["success", "fail", "roll"]
        )

        assert "DM" in output
        assert "success" in output.lower() or "fail" in output.lower()


# ============================================================================
# T068: Session State Display Tests
# ============================================================================


class TestSessionStateDisplay:
    """Test session state information display"""

    def test_format_session_info(self):
        """Test formatting session info output"""
        formatter = CLIFormatter()
        output = formatter.format_session_info(
            campaign_name="Voyage of the Raptor",
            session_number=1,
            turn_number=5,
            current_phase=GamePhase.DM_ADJUDICATION,
            active_agents=[
                {"agent_id": "agent_001", "character_name": "Zara-7"}
            ]
        )

        assert "Voyage of the Raptor" in output
        assert "Session 1" in output or "1" in output
        assert "Turn 5" in output or "5" in output
        assert "Zara-7" in output
        assert "DM_ADJUDICATION" in output or "Adjudication" in output

    def test_format_character_info(self):
        """Test formatting character information"""
        formatter = CLIFormatter()
        output = formatter.format_character_info(
            character_name="Zara-7",
            style="Android",
            role="Engineer",
            number=2
        )

        assert "Zara-7" in output
        assert "Android" in output
        assert "Engineer" in output
        assert "2" in output


# ============================================================================
# T069: Error Handling Tests
# ============================================================================


class TestErrorHandling:
    """Test error handling and user-friendly messages"""

    def test_invalid_command_at_wrong_phase(self):
        """Test error when command used at wrong phase"""
        cli = DMCommandLineInterface()
        cli._current_phase = GamePhase.MEMORY_QUERY

        # Try to use success command during memory query
        parsed = ParsedCommand(
            command_type=DMCommandType.SUCCESS,
            args={},
            raw_input="success"
        )

        result = cli.handle_command(parsed)

        assert result["success"] is False
        assert "error" in result
        assert "memory query" in result["error"].lower() or "not valid" in result["error"].lower()

    def test_invalid_dice_notation_error_message(self):
        """Test user-friendly error for invalid dice notation"""
        parser = DMCommandParser()

        with pytest.raises(InvalidCommandError) as exc_info:
            parser.parse("/roll 2d6d8")

        assert "Invalid dice notation" in str(exc_info.value)
        assert "expected format" in str(exc_info.value).lower() or "XdY" in str(exc_info.value)

    def test_format_error_message(self):
        """Test formatting error messages"""
        formatter = CLIFormatter()
        output = formatter.format_error(
            error_type="InvalidCommandError",
            message="Roll command requires dice notation",
            suggestion="Try: /roll 1d20 or /roll 2d6+3"
        )

        assert "error" in output.lower()
        assert "Roll command requires dice notation" in output
        assert "/roll 1d20" in output

    def test_network_error_handling(self):
        """Test handling network/API errors gracefully"""
        formatter = CLIFormatter()
        output = formatter.format_error(
            error_type="NetworkError",
            message="OpenAI API timeout",
            suggestion="The request timed out. Press Enter to retry or /quit to exit."
        )

        assert "timeout" in output.lower()
        assert "retry" in output.lower()


# ============================================================================
# Integration Tests
# ============================================================================


class TestOOCSummaryFormatting:
    """Test OOC summary display in CLI"""

    def test_format_ooc_summary_with_messages(self):
        """Test formatting OOC summary with multiple messages"""
        from src.models.messages import Message, MessageChannel, MessageType

        formatter = CLIFormatter()

        messages = [
            Message(
                message_id="msg_001",
                channel=MessageChannel.OOC,
                from_agent="agent_alex_001",
                content="We should investigate the fuel readings first",
                timestamp=datetime(2025, 10, 19, 14, 32, 15),
                message_type=MessageType.DISCUSSION,
                phase="strategic_intent",
                turn_number=3,
                session_number=1
            ),
            Message(
                message_id="msg_002",
                channel=MessageChannel.OOC,
                from_agent="agent_jordan_002",
                content="Agreed. Zara-7 should run diagnostics",
                timestamp=datetime(2025, 10, 19, 14, 32, 18),
                message_type=MessageType.DISCUSSION,
                phase="strategic_intent",
                turn_number=3,
                session_number=1
            )
        ]

        # Map agent IDs to names
        agent_names = {
            "agent_alex_001": "Alex",
            "agent_jordan_002": "Jordan"
        }

        output = formatter.format_ooc_summary(messages, turn_number=3, agent_names=agent_names)

        assert "OOC Strategic Discussion" in output
        assert "Turn 3" in output
        assert "Alex (Player):" in output
        assert "Jordan (Player):" in output
        assert "We should investigate the fuel readings first" in output
        assert "Agreed. Zara-7 should run diagnostics" in output

    def test_format_ooc_summary_empty_messages(self):
        """Test formatting OOC summary with no messages returns None"""
        formatter = CLIFormatter()

        output = formatter.format_ooc_summary([], turn_number=3, agent_names={})

        # Should return None when no messages
        assert output is None

    def test_format_ooc_summary_without_agent_names(self):
        """Test formatting OOC summary without agent name mapping"""
        from src.models.messages import Message, MessageChannel, MessageType

        formatter = CLIFormatter()

        messages = [
            Message(
                message_id="msg_001",
                channel=MessageChannel.OOC,
                from_agent="agent_unknown_001",
                content="Unknown agent message",
                timestamp=datetime(2025, 10, 19, 14, 30, 00),
                message_type=MessageType.DISCUSSION,
                phase="strategic_intent",
                turn_number=1,
                session_number=1
            )
        ]

        output = formatter.format_ooc_summary(messages, turn_number=1, agent_names={})

        # Should fall back to agent_id
        assert "agent_unknown_001 (Player):" in output


class TestDMCLIOOCIntegration:
    """Test DM CLI integration with OOC display"""

    @patch('src.interface.dm_cli.MessageRouter')
    def test_display_ooc_summary_fetches_messages(self, mock_router_class):
        """Test _display_ooc_summary fetches and displays messages"""
        from src.models.messages import Message, MessageChannel, MessageType

        # Mock message router
        mock_router = Mock()
        mock_router_class.return_value = mock_router

        # Mock OOC messages
        messages = [
            Message(
                message_id="msg_001",
                channel=MessageChannel.OOC,
                from_agent="agent_alex_001",
                content="Let's be cautious",
                timestamp=datetime(2025, 10, 19, 14, 30, 00),
                message_type=MessageType.DISCUSSION,
                phase="strategic_intent",
                turn_number=3,
                session_number=1
            )
        ]

        mock_router.get_ooc_messages_for_player.return_value = messages

        cli = DMCommandLineInterface()
        cli._turn_number = 3

        # Capture printed output
        with patch('builtins.print') as mock_print:
            cli._display_ooc_summary(turn_number=3, router=mock_router)

            # Verify output was printed
            assert mock_print.called
            # Find the call that contains OOC summary
            printed_output = " ".join([str(call[0][0]) for call in mock_print.call_args_list])
            assert "OOC Strategic Discussion" in printed_output

    @patch('src.interface.dm_cli.MessageRouter')
    def test_display_ooc_summary_no_messages(self, mock_router_class):
        """Test _display_ooc_summary handles no messages gracefully"""
        # Mock message router returning empty list
        mock_router = Mock()
        mock_router_class.return_value = mock_router
        mock_router.get_ooc_messages_for_player.return_value = []

        cli = DMCommandLineInterface()

        # Should not print anything when no messages
        with patch('builtins.print') as mock_print:
            cli._display_ooc_summary(turn_number=1, router=mock_router)

            # Should not have printed OOC summary section
            if mock_print.called:
                printed_output = " ".join([str(call[0][0]) for call in mock_print.call_args_list])
                assert "OOC Strategic Discussion" not in printed_output


class TestDMCLIIntegration:
    """Test CLI integration with orchestrator (mocked)"""

    def test_full_turn_cycle(self):
        """Test complete turn cycle through CLI"""
        # Create mock orchestrator
        mock_orchestrator = Mock()
        mock_orchestrator.execute_turn_cycle.return_value = {
            "success": True,
            "turn_number": 1,
            "phase_completed": GamePhase.MEMORY_STORAGE.value,
            "character_actions": {
                "char_001": "I attempt to dock with the station"
            }
        }

        # Inject mock orchestrator
        cli = DMCommandLineInterface(orchestrator=mock_orchestrator)

        # Parse and execute narrate command
        parsed = cli.parser.parse("The ship approaches the station")
        result = cli.handle_command(parsed)

        assert result["success"] is True

    def test_quit_command_exits_gracefully(self):
        """Test quit command sets exit flag"""
        cli = DMCommandLineInterface()

        parsed = cli.parser.parse("/quit")
        result = cli.handle_command(parsed)

        assert result["success"] is True
        assert result["should_exit"] is True
