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
        """Test that roll without notation is allowed (uses character suggestion)"""
        parser = DMCommandParser()

        # /roll without notation should now be valid (uses character's suggestion)
        parsed = parser.parse("/roll")
        assert parsed.command_type == DMCommandType.ROLL
        assert parsed.args == {}  # Empty args means use character suggestion
        assert parsed.raw_input == "/roll"


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

    def test_format_dice_suggestion_no_task_type(self):
        """Test that no dice suggestion is returned when task_type is None"""
        formatter = CLIFormatter()
        action_dict = {
            "narrative_text": "I walk to the door",
            "task_type": None
        }

        output = formatter.format_dice_suggestion(action_dict)
        assert output is None

    def test_format_dice_suggestion_lasers_task(self):
        """Test formatting dice suggestion for Lasers task"""
        formatter = CLIFormatter()
        action_dict = {
            "narrative_text": "I repair the fuel cells",
            "task_type": "lasers",
            "is_prepared": False,
            "is_expert": False,
            "is_helping": False
        }

        output = formatter.format_dice_suggestion(action_dict)

        assert output is not None
        assert "Task Type: Lasers (logic/tech)" in output
        assert "Suggested Roll: 1d6 Lasers" in output

    def test_format_dice_suggestion_feelings_task(self):
        """Test formatting dice suggestion for Feelings task"""
        formatter = CLIFormatter()
        action_dict = {
            "narrative_text": "I persuade the captain",
            "task_type": "feelings",
            "is_prepared": False,
            "is_expert": False,
            "is_helping": False
        }

        output = formatter.format_dice_suggestion(action_dict)

        assert output is not None
        assert "Task Type: Feelings (social/emotion)" in output
        assert "Suggested Roll: 1d6 Feelings" in output

    def test_format_dice_suggestion_with_prepared(self):
        """Test dice suggestion with prepared bonus"""
        formatter = CLIFormatter()
        action_dict = {
            "narrative_text": "I repair the fuel cells",
            "task_type": "lasers",
            "is_prepared": True,
            "prepared_justification": "I studied the schematics during our last jump",
            "is_expert": False,
            "is_helping": False
        }

        output = formatter.format_dice_suggestion(action_dict)

        assert output is not None
        assert "Prepared: ✓" in output
        assert "I studied the schematics during our last jump" in output
        assert "Suggested Roll: 2d6 Lasers" in output

    def test_format_dice_suggestion_with_expert(self):
        """Test dice suggestion with expert bonus"""
        formatter = CLIFormatter()
        action_dict = {
            "narrative_text": "I repair the fuel cells",
            "task_type": "lasers",
            "is_prepared": False,
            "is_expert": True,
            "expert_justification": "As the ship's Engineer, fuel cell repair is my specialty",
            "is_helping": False
        }

        output = formatter.format_dice_suggestion(action_dict)

        assert output is not None
        assert "Expert: ✓" in output
        assert "As the ship's Engineer, fuel cell repair is my specialty" in output
        assert "Suggested Roll: 2d6 Lasers" in output

    def test_format_dice_suggestion_with_helping(self):
        """Test dice suggestion with helping bonus"""
        formatter = CLIFormatter()
        action_dict = {
            "narrative_text": "I provide cover fire",
            "task_type": "lasers",
            "is_prepared": False,
            "is_expert": False,
            "is_helping": True,
            "helping_character_id": "char_jordan_002",
            "help_justification": "I'm suppressing enemy positions while Jordan advances"
        }

        # Test with character name resolver
        def resolver(char_id):
            return {"char_jordan_002": "Jordan"}.get(char_id, char_id)

        output = formatter.format_dice_suggestion(action_dict, resolver)

        assert output is not None
        assert "Helping Jordan: ✓" in output
        assert "I'm suppressing enemy positions while Jordan advances" in output
        assert "Suggested Roll: 2d6 Lasers" in output

    def test_format_dice_suggestion_all_bonuses(self):
        """Test dice suggestion with all bonuses (max 3d6)"""
        formatter = CLIFormatter()
        action_dict = {
            "narrative_text": "I repair the fuel cells while coordinating with Jordan",
            "task_type": "lasers",
            "is_prepared": True,
            "prepared_justification": "I gathered all the necessary tools",
            "is_expert": True,
            "expert_justification": "This is my area of expertise",
            "is_helping": True,
            "helping_character_id": "char_jordan_002",
            "help_justification": "Jordan is assisting with the diagnostics"
        }

        output = formatter.format_dice_suggestion(action_dict)

        assert output is not None
        assert "Prepared: ✓" in output
        assert "Expert: ✓" in output
        assert "Helping" in output
        # Should cap at 3d6
        assert "Suggested Roll: 3d6 Lasers" in output

    def test_format_character_action_with_directive_includes_dice_suggestion(self):
        """Test that format_character_action_with_directive includes dice suggestions"""
        formatter = CLIFormatter()
        action_dict = {
            "narrative_text": "Zara-7 approaches the fuel cell bay",
            "task_type": "lasers",
            "is_prepared": True,
            "prepared_justification": "I studied the ship's schematics",
            "is_expert": True,
            "expert_justification": "I'm the ship's Engineer",
            "is_helping": False
        }

        output = formatter.format_character_action_with_directive(
            character_name="Zara-7",
            directive_text="Repair the fuel cells",
            action_dict=action_dict
        )

        assert "Zara-7:" in output
        assert "Player Directive: Repair the fuel cells" in output
        assert "Character Performance: Zara-7 approaches the fuel cell bay" in output
        assert "Dice Roll Suggestion:" in output
        assert "Task Type: Lasers (logic/tech)" in output
        assert "Prepared: ✓" in output
        assert "Expert: ✓" in output
        assert "Suggested Roll: 3d6 Lasers" in output


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


# ============================================================================
# Character Suggested Roll Tests (Fix Validation)
# ============================================================================


class TestCharacterSuggestedRoll:
    """Test that /roll without notation correctly uses character suggestions"""

    def test_execute_suggested_roll_with_character_actions_parameter(self):
        """
        Test that _execute_character_suggested_roll can accept character_actions parameter.

        This validates the fix for the /roll bug where passing character_actions
        from current_turn_result ensures fresh roll data is available during
        adjudication phase.
        """
        cli = DMCommandLineInterface()

        # Prepare mock character config
        cli._character_configs = {
            "char_zara_001": {
                "character_id": "char_zara_001",
                "name": "Zara-7",
                "number": 2
            }
        }

        # Prepare character actions dict (simulating turn result data)
        character_actions = {
            "char_zara_001": {
                "narrative_text": "I analyze the ship's systems",
                "task_type": "lasers",
                "is_prepared": True,
                "prepared_justification": "I'm always ready",
                "is_expert": False,
                "is_helping": False,
                "gm_question": None
            }
        }

        # Execute suggested roll with character_actions parameter
        result = cli._execute_character_suggested_roll(character_actions=character_actions)

        # Verify success
        assert result["success"] is True
        assert "roll_result" in result
        assert result["roll_result"].dice_count == 2  # 1 base + 1 prepared

    def test_execute_suggested_roll_no_character_actions_returns_error(self):
        """Test that missing character actions returns helpful error"""
        cli = DMCommandLineInterface()

        # Call with empty character_actions
        result = cli._execute_character_suggested_roll(character_actions={})

        assert result["success"] is False
        assert "No character actions available" in result["error"]
        assert "Use /roll <dice>" in result["suggestion"]

    def test_prompt_for_dm_input_passes_turn_result(self):
        """
        Test that _prompt_for_dm_input_at_phase can receive current_turn_result.

        This validates the fix: turn_result is passed as parameter so that
        character_actions are available during adjudication prompts.
        """
        cli = DMCommandLineInterface()

        # Prepare character config
        cli._character_configs = {
            "char_zara_001": {
                "character_id": "char_zara_001",
                "name": "Zara-7",
                "number": 2
            }
        }

        # Prepare turn result with character actions
        turn_result = {
            "character_actions": {
                "char_zara_001": {
                    "narrative_text": "I act",
                    "task_type": "feelings",
                    "is_prepared": False,
                    "is_expert": True,
                    "expert_justification": "I'm an expert",
                    "is_helping": False,
                    "gm_question": None
                }
            }
        }

        # Verify that _prompt_for_dm_input_at_phase accepts current_turn_result parameter
        # The method signature now includes this parameter for passing to _execute_character_suggested_roll
        import inspect
        sig = inspect.signature(cli._prompt_for_dm_input_at_phase)
        assert "current_turn_result" in sig.parameters


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
                "char_001": {
                    "character_id": "char_001",
                    "narrative_text": "I attempt to dock with the station",
                    "task_type": None,
                    "is_prepared": False,
                    "prepared_justification": None,
                    "is_expert": False,
                    "expert_justification": None,
                    "is_helping": False,
                    "helping_character_id": None,
                    "help_justification": None
                }
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


# ============================================================================
# Character Suggested Roll Tests
# ============================================================================


class TestCharacterSuggestedRoll:
    """Test /roll without args (uses character's dice suggestion)"""

    def test_execute_character_suggested_roll_success(self):
        """Test executing character suggested roll with valid state"""
        cli = DMCommandLineInterface()

        # Mock turn state with character actions
        cli._current_turn_result = {
            "character_actions": {
                "char_zara_001": {
                    "task_type": "lasers",
                    "is_prepared": True,
                    "is_expert": False,
                    "is_helping": False
                }
            }
        }

        # Mock character config (Zara-7 has number 2)
        cli._character_configs = {
            "char_zara_001": {
                "character_id": "char_zara_001",
                "name": "Zara-7",
                "number": 2
            }
        }
        cli._character_names = {"char_zara_001": "Zara-7"}

        # Execute suggested roll
        result = cli._execute_character_suggested_roll()

        assert result["success"] is True
        assert "roll_result" in result
        roll_result = result["roll_result"]

        # Verify roll parameters
        assert roll_result.character_number == 2
        assert roll_result.task_type == "lasers"
        assert roll_result.is_prepared is True
        assert roll_result.dice_count == 2  # 1 base + 1 prepared

    def test_execute_character_suggested_roll_no_turn_state(self):
        """Test error when no turn state available"""
        cli = DMCommandLineInterface()
        cli._current_turn_result = None

        result = cli._execute_character_suggested_roll()

        assert result["success"] is False
        assert "No turn state available" in result["error"]

    def test_execute_character_suggested_roll_no_character_actions(self):
        """Test error when no character actions in turn state"""
        cli = DMCommandLineInterface()
        cli._current_turn_result = {"character_actions": {}}

        result = cli._execute_character_suggested_roll()

        assert result["success"] is False
        assert "No character actions available" in result["error"]

    def test_execute_character_suggested_roll_no_task_type(self):
        """Test error when action has no task_type (no dice needed)"""
        cli = DMCommandLineInterface()
        cli._current_turn_result = {
            "character_actions": {
                "char_zara_001": {
                    "task_type": None  # No dice roll needed
                }
            }
        }

        result = cli._execute_character_suggested_roll()

        assert result["success"] is False
        assert "No dice roll suggestion available" in result["error"]

    def test_execute_character_suggested_roll_missing_character_config(self):
        """Test error when character config not found"""
        cli = DMCommandLineInterface()
        cli._current_turn_result = {
            "character_actions": {
                "char_unknown_999": {
                    "task_type": "lasers"
                }
            }
        }
        cli._character_configs = {}  # Empty configs

        result = cli._execute_character_suggested_roll()

        assert result["success"] is False
        assert "Character config not found" in result["error"]

    def test_execute_character_suggested_roll_with_all_bonuses(self):
        """Test roll with prepared + expert + helping (max dice)"""
        cli = DMCommandLineInterface()
        cli._current_turn_result = {
            "character_actions": {
                "char_zara_001": {
                    "task_type": "feelings",
                    "is_prepared": True,
                    "is_expert": True,
                    "is_helping": True
                }
            }
        }
        cli._character_configs = {
            "char_zara_001": {
                "character_id": "char_zara_001",
                "name": "Zara-7",
                "number": 2
            }
        }
        cli._character_names = {"char_zara_001": "Zara-7"}

        result = cli._execute_character_suggested_roll()

        assert result["success"] is True
        roll_result = result["roll_result"]

        # Should roll 3d6 (1 base + prepared + expert)
        # Note: is_helping is combined with is_prepared in current implementation
        assert roll_result.dice_count == 3
        assert roll_result.task_type == "feelings"

    def test_display_lasers_feelings_result(self, capsys):
        """Test formatted display of Lasers & Feelings roll result"""
        from datetime import UTC, datetime

        from src.models.dice_models import LasersFeelingRollResult, RollOutcome

        cli = DMCommandLineInterface()

        # Create mock roll result
        roll_result = LasersFeelingRollResult(
            character_number=3,
            task_type="lasers",
            is_prepared=True,
            is_expert=False,
            individual_rolls=[2, 5],
            die_successes=[True, False],
            laser_feelings_indices=[],
            total_successes=1,
            outcome=RollOutcome.BARELY,
            timestamp=datetime.now(UTC)
        )

        # Display result
        cli._display_lasers_feelings_result(roll_result)

        # Capture output
        captured = capsys.readouterr()

        # Verify output contains expected elements
        assert "Lasers & Feelings Roll" in captured.out
        assert "2d6 Lasers" in captured.out
        assert "Character Number: 3" in captured.out
        assert "Individual Rolls: [2, 5]" in captured.out
        assert "Successes: 1/2" in captured.out
        assert "Outcome: BARELY" in captured.out

    def test_display_lasers_feelings_result_with_laser_feelings(self, capsys):
        """Test display when LASER FEELINGS occurs"""
        from datetime import UTC, datetime

        from src.models.dice_models import LasersFeelingRollResult, RollOutcome

        cli = DMCommandLineInterface()

        # Create roll with LASER FEELINGS (die matched character number)
        roll_result = LasersFeelingRollResult(
            character_number=4,
            task_type="feelings",
            is_prepared=False,
            is_expert=False,
            individual_rolls=[4],
            die_successes=[True],
            laser_feelings_indices=[0],  # First die is LASER FEELINGS
            total_successes=1,
            outcome=RollOutcome.BARELY,
            timestamp=datetime.now(UTC)
        )

        cli._display_lasers_feelings_result(roll_result)
        captured = capsys.readouterr()

        # Verify LASER FEELINGS is displayed
        assert "LASER FEELINGS on die #1!" in captured.out

    def test_display_lasers_feelings_result_with_gm_question(self, capsys):
        """Test display when LASER FEELINGS occurs with GM question"""
        from datetime import UTC, datetime

        from src.models.dice_models import LasersFeelingRollResult, RollOutcome

        cli = DMCommandLineInterface()

        # Create roll with LASER FEELINGS and a GM question
        roll_result = LasersFeelingRollResult(
            character_number=3,
            task_type="lasers",
            is_prepared=False,
            is_expert=False,
            individual_rolls=[2, 3],
            die_successes=[True, True],
            laser_feelings_indices=[1],  # Second die is LASER FEELINGS
            total_successes=2,
            outcome=RollOutcome.SUCCESS,
            gm_question="What is the true purpose of this signal?",
            timestamp=datetime.now(UTC)
        )

        cli._display_lasers_feelings_result(roll_result)
        captured = capsys.readouterr()

        # Verify LASER FEELINGS is displayed
        assert "LASER FEELINGS on die #2!" in captured.out
        # Verify the GM question is displayed
        assert "Suggested Question:" in captured.out
        assert "What is the true purpose of this signal?" in captured.out

    def test_display_lasers_feelings_result_with_laser_feelings_no_question(self, capsys):
        """Test display when LASER FEELINGS occurs without GM question"""
        from datetime import UTC, datetime

        from src.models.dice_models import LasersFeelingRollResult, RollOutcome

        cli = DMCommandLineInterface()

        # Create roll with LASER FEELINGS but no question provided
        roll_result = LasersFeelingRollResult(
            character_number=4,
            task_type="feelings",
            is_prepared=False,
            is_expert=False,
            individual_rolls=[4],
            die_successes=[True],
            laser_feelings_indices=[0],
            total_successes=1,
            outcome=RollOutcome.BARELY,
            gm_question=None,  # No question provided
            timestamp=datetime.now(UTC)
        )

        cli._display_lasers_feelings_result(roll_result)
        captured = capsys.readouterr()

        # Verify LASER FEELINGS is displayed
        assert "LASER FEELINGS on die #1!" in captured.out
        # Verify helpful prompt is shown when no question provided
        assert (
            "(No question suggested" in captured.out
            or "ask the character what they want to know" in captured.out
        )

    def test_display_lasers_feelings_result_no_laser_feelings_no_question_display(self, capsys):
        """Test that no question section is displayed when no LASER FEELINGS occurs"""
        from datetime import UTC, datetime

        from src.models.dice_models import LasersFeelingRollResult, RollOutcome

        cli = DMCommandLineInterface()

        # Create roll without LASER FEELINGS
        roll_result = LasersFeelingRollResult(
            character_number=3,
            task_type="lasers",
            is_prepared=False,
            is_expert=False,
            individual_rolls=[2, 5],
            die_successes=[True, False],
            laser_feelings_indices=[],  # No LASER FEELINGS
            total_successes=1,
            outcome=RollOutcome.BARELY,
            timestamp=datetime.now(UTC)
        )

        cli._display_lasers_feelings_result(roll_result)
        captured = capsys.readouterr()

        # Verify no LASER FEELINGS message
        assert "LASER FEELINGS" not in captured.out
        # Verify no question section displayed
        assert "Suggested Question" not in captured.out
        assert "No question suggested" not in captured.out


# ============================================================================
# Agent-to-Character Mapping Tests
# ============================================================================


class TestAgentToCharacterMapping:
    """Test agent-to-character mapping functionality"""

    def test_load_agent_to_character_mapping_success(self, tmp_path, monkeypatch):
        """Test successful loading of agent-to-character mapping from config files"""
        import json

        # Create temporary config directory
        config_dir = tmp_path / "config" / "personalities"
        config_dir.mkdir(parents=True)

        # Create test character config file
        char_config = {
            "character_id": "char_zara_001",
            "agent_id": "agent_alex_001",
            "name": "Zara-7",
            "number": 2
        }
        config_file = config_dir / "char_zara_001_character.json"
        with open(config_file, "w") as f:
            json.dump(char_config, f)

        # Change to tmp_path so config/personalities is found
        monkeypatch.chdir(tmp_path)

        cli = DMCommandLineInterface()

        # Verify mapping was loaded
        assert "agent_alex_001" in cli._agent_to_character
        assert cli._agent_to_character["agent_alex_001"] == "char_zara_001"

    def test_load_agent_to_character_mapping_multiple_characters(self, tmp_path, monkeypatch):
        """Test loading multiple agent-to-character mappings"""
        import json

        # Create temporary config directory
        config_dir = tmp_path / "config" / "personalities"
        config_dir.mkdir(parents=True)

        # Create multiple test character config files
        char_configs = [
            {
                "character_id": "char_zara_001",
                "agent_id": "agent_alex_001",
                "name": "Zara-7",
                "number": 2
            },
            {
                "character_id": "char_nova_002",
                "agent_id": "agent_sam_002",
                "name": "Nova",
                "number": 4
            }
        ]

        for config in char_configs:
            config_file = config_dir / f"{config['character_id']}_character.json"
            with open(config_file, "w") as f:
                json.dump(config, f)

        # Change to tmp_path so config/personalities is found
        monkeypatch.chdir(tmp_path)

        cli = DMCommandLineInterface()

        # Verify both mappings were loaded
        assert len(cli._agent_to_character) == 2
        assert cli._agent_to_character["agent_alex_001"] == "char_zara_001"
        assert cli._agent_to_character["agent_sam_002"] == "char_nova_002"

    def test_load_agent_to_character_mapping_directory_not_found(self, tmp_path, monkeypatch):
        """Test handling when config directory doesn't exist"""
        # Change to tmp_path where there's no config/personalities directory
        monkeypatch.chdir(tmp_path)

        cli = DMCommandLineInterface()

        # Verify empty mapping when directory not found
        assert len(cli._agent_to_character) == 0

    def test_load_agent_to_character_mapping_invalid_json(self, tmp_path, monkeypatch):
        """Test handling when config file has invalid JSON"""

        # Create temporary config directory
        config_dir = tmp_path / "config" / "personalities"
        config_dir.mkdir(parents=True)

        # Create invalid JSON file
        config_file = config_dir / "char_invalid_001_character.json"
        with open(config_file, "w") as f:
            f.write("invalid json {")

        # Change to tmp_path so config/personalities is found
        monkeypatch.chdir(tmp_path)

        cli = DMCommandLineInterface()

        # Verify mapping is empty (invalid file was skipped)
        assert len(cli._agent_to_character) == 0

    def test_execute_character_suggested_roll_uses_correct_character_id(
        self, tmp_path, monkeypatch
    ):
        """Test that suggested roll uses character_id from turn state correctly"""
        import json

        # Create temporary config directory
        config_dir = tmp_path / "config" / "personalities"
        config_dir.mkdir(parents=True)

        # Create test character config file
        char_config = {
            "character_id": "char_zara_001",
            "agent_id": "agent_alex_001",
            "name": "Zara-7",
            "number": 2
        }
        config_file = config_dir / "char_zara_001_character.json"
        with open(config_file, "w") as f:
            json.dump(char_config, f)

        # Change to tmp_path so config/personalities is found
        monkeypatch.chdir(tmp_path)

        cli = DMCommandLineInterface()

        # Set up turn state with character_id that matches config
        cli._current_turn_result = {
            "character_actions": {
                "char_zara_001": {
                    "task_type": "lasers",
                    "is_prepared": True,
                    "is_expert": False,
                    "is_helping": False
                }
            }
        }

        # Execute roll
        result = cli._execute_character_suggested_roll()

        # Should succeed because character_id matches config
        assert result["success"] is True
        assert "roll_result" in result

    def test_execute_character_suggested_roll_with_gm_question(self, tmp_path, monkeypatch):
        """Test that gm_question from action_dict flows through to roll_result"""
        import json

        # Create temporary config directory
        config_dir = tmp_path / "config" / "personalities"
        config_dir.mkdir(parents=True)

        # Create test character config file
        char_config = {
            "character_id": "char_zara_001",
            "agent_id": "agent_alex_001",
            "name": "Zara-7",
            "number": 3
        }
        config_file = config_dir / "char_zara_001_character.json"
        with open(config_file, "w") as f:
            json.dump(char_config, f)

        # Change to tmp_path so config/personalities is found
        monkeypatch.chdir(tmp_path)

        cli = DMCommandLineInterface()

        # Set up turn state with gm_question
        gm_question_text = "What is the true purpose of this signal?"
        cli._current_turn_result = {
            "character_actions": {
                "char_zara_001": {
                    "task_type": "lasers",
                    "is_prepared": False,
                    "is_expert": False,
                    "is_helping": False,
                    "gm_question": gm_question_text
                }
            }
        }

        # Execute roll
        result = cli._execute_character_suggested_roll()

        # Verify success
        assert result["success"] is True
        assert "roll_result" in result

        # Verify gm_question was passed through
        roll_result = result["roll_result"]
        assert roll_result.gm_question == gm_question_text

    def test_execute_character_suggested_roll_without_gm_question(self, tmp_path, monkeypatch):
        """Test that roll works when gm_question is not provided"""
        import json

        # Create temporary config directory
        config_dir = tmp_path / "config" / "personalities"
        config_dir.mkdir(parents=True)

        # Create test character config file
        char_config = {
            "character_id": "char_zara_001",
            "agent_id": "agent_alex_001",
            "name": "Zara-7",
            "number": 2
        }
        config_file = config_dir / "char_zara_001_character.json"
        with open(config_file, "w") as f:
            json.dump(char_config, f)

        # Change to tmp_path so config/personalities is found
        monkeypatch.chdir(tmp_path)

        cli = DMCommandLineInterface()

        # Set up turn state without gm_question
        cli._current_turn_result = {
            "character_actions": {
                "char_zara_001": {
                    "task_type": "lasers",
                    "is_prepared": False,
                    "is_expert": False,
                    "is_helping": False
                }
            }
        }

        # Execute roll
        result = cli._execute_character_suggested_roll()

        # Verify success
        assert result["success"] is True
        assert "roll_result" in result

        # Verify gm_question is None when not provided
        roll_result = result["roll_result"]
        assert roll_result.gm_question is None


# ============================================================================
# LASER FEELINGS Answer Prompt Tests
# ============================================================================


class TestLaserFeelingsAnswerPrompt:
    """Test DM prompt for LASER FEELINGS answers"""

    def test_prompt_for_laser_feelings_answer_with_question(self):
        """Test that DM is prompted for answer when LASER FEELINGS occurs with a question"""
        from datetime import UTC, datetime

        from src.models.dice_models import LasersFeelingRollResult, RollOutcome

        cli = DMCommandLineInterface()

        # Create roll result with LASER FEELINGS and a question
        roll_result = LasersFeelingRollResult(
            character_number=3,
            task_type="lasers",
            is_prepared=False,
            is_expert=False,
            individual_rolls=[2, 3],
            die_successes=[True, True],
            laser_feelings_indices=[1],
            total_successes=2,
            outcome=RollOutcome.SUCCESS,
            gm_question="What is the true purpose of this signal?",
            timestamp=datetime.now(UTC)
        )

        # Mock input() to provide DM answer
        with patch(
            'builtins.input', return_value="It's a distress call from a stranded colony ship"
        ):
            answer = cli._prompt_for_laser_feelings_answer(roll_result)

        assert answer == "It's a distress call from a stranded colony ship"

    def test_prompt_for_laser_feelings_answer_without_question(self):
        """Test that DM is prompted for insight when LASER FEELINGS occurs without a question"""
        from datetime import UTC, datetime

        from src.models.dice_models import LasersFeelingRollResult, RollOutcome

        cli = DMCommandLineInterface()

        # Create roll result with LASER FEELINGS but no question
        roll_result = LasersFeelingRollResult(
            character_number=4,
            task_type="feelings",
            is_prepared=False,
            is_expert=False,
            individual_rolls=[4],
            die_successes=[True],
            laser_feelings_indices=[0],
            total_successes=1,
            outcome=RollOutcome.BARELY,
            gm_question=None,
            timestamp=datetime.now(UTC)
        )

        # Mock input() to provide DM insight
        with patch('builtins.input', return_value="You sense fear in their eyes"):
            answer = cli._prompt_for_laser_feelings_answer(roll_result)

        assert answer == "You sense fear in their eyes"

    def test_prompt_for_laser_feelings_answer_no_laser_feelings(self):
        """Test that no prompt appears when no LASER FEELINGS occurs"""
        from datetime import UTC, datetime

        from src.models.dice_models import LasersFeelingRollResult, RollOutcome

        cli = DMCommandLineInterface()

        # Create roll result WITHOUT LASER FEELINGS
        roll_result = LasersFeelingRollResult(
            character_number=3,
            task_type="lasers",
            is_prepared=False,
            is_expert=False,
            individual_rolls=[2, 5],
            die_successes=[True, False],
            laser_feelings_indices=[],  # No LASER FEELINGS
            total_successes=1,
            outcome=RollOutcome.BARELY,
            timestamp=datetime.now(UTC)
        )

        # Mock input() - should NOT be called
        with patch('builtins.input', return_value="This should not be called") as mock_input:
            answer = cli._prompt_for_laser_feelings_answer(roll_result)

        # Verify input() was NOT called
        mock_input.assert_not_called()
        # Verify return value is None
        assert answer is None

    def test_prompt_for_laser_feelings_answer_empty_answer(self):
        """Test that empty answers are handled gracefully"""
        from datetime import UTC, datetime

        from src.models.dice_models import LasersFeelingRollResult, RollOutcome

        cli = DMCommandLineInterface()

        # Create roll result with LASER FEELINGS
        roll_result = LasersFeelingRollResult(
            character_number=3,
            task_type="lasers",
            is_prepared=False,
            is_expert=False,
            individual_rolls=[3],
            die_successes=[True],
            laser_feelings_indices=[0],
            total_successes=1,
            outcome=RollOutcome.BARELY,
            gm_question="What do you discover?",
            timestamp=datetime.now(UTC)
        )

        # Mock input() to provide empty answer
        with patch('builtins.input', return_value=""):
            answer = cli._prompt_for_laser_feelings_answer(roll_result)

        # Verify None is returned for empty answer
        assert answer is None

    def test_prompt_for_laser_feelings_answer_whitespace_only(self):
        """Test that whitespace-only answers are handled gracefully"""
        from datetime import UTC, datetime

        from src.models.dice_models import LasersFeelingRollResult, RollOutcome

        cli = DMCommandLineInterface()

        # Create roll result with LASER FEELINGS
        roll_result = LasersFeelingRollResult(
            character_number=4,
            task_type="feelings",
            is_prepared=False,
            is_expert=False,
            individual_rolls=[4],
            die_successes=[True],
            laser_feelings_indices=[0],
            total_successes=1,
            outcome=RollOutcome.BARELY,
            timestamp=datetime.now(UTC)
        )

        # Mock input() to provide whitespace-only answer
        with patch('builtins.input', return_value="   "):
            answer = cli._prompt_for_laser_feelings_answer(roll_result)

        # Verify None is returned for whitespace-only answer
        assert answer is None

    def test_prompt_for_laser_feelings_answer_strips_whitespace(self):
        """Test that answers with leading/trailing whitespace are trimmed"""
        from datetime import UTC, datetime

        from src.models.dice_models import LasersFeelingRollResult, RollOutcome

        cli = DMCommandLineInterface()

        # Create roll result with LASER FEELINGS
        roll_result = LasersFeelingRollResult(
            character_number=3,
            task_type="lasers",
            is_prepared=False,
            is_expert=False,
            individual_rolls=[3],
            die_successes=[True],
            laser_feelings_indices=[0],
            total_successes=1,
            outcome=RollOutcome.BARELY,
            gm_question="What do you see?",
            timestamp=datetime.now(UTC)
        )

        # Mock input() to provide answer with whitespace
        with patch('builtins.input', return_value="  A hidden passage  "):
            answer = cli._prompt_for_laser_feelings_answer(roll_result)

        # Verify whitespace was stripped
        assert answer == "A hidden passage"

    def test_prompt_displays_correct_prompt_with_question(self, capsys):
        """Test that correct prompt is displayed when gm_question exists"""
        from datetime import UTC, datetime

        from src.models.dice_models import LasersFeelingRollResult, RollOutcome

        cli = DMCommandLineInterface()

        roll_result = LasersFeelingRollResult(
            character_number=3,
            task_type="lasers",
            is_prepared=False,
            is_expert=False,
            individual_rolls=[3],
            die_successes=[True],
            laser_feelings_indices=[0],
            total_successes=1,
            outcome=RollOutcome.BARELY,
            gm_question="What is behind the door?",
            timestamp=datetime.now(UTC)
        )

        # Mock input()
        with patch('builtins.input', return_value="A dark corridor"):
            cli._prompt_for_laser_feelings_answer(roll_result)

        # Capture output
        captured = capsys.readouterr()

        # Verify "Answer: " prompt was displayed
        assert "Answer:" in captured.out

    def test_prompt_displays_correct_prompt_without_question(self, capsys):
        """Test that correct prompt is displayed when no gm_question"""
        from datetime import UTC, datetime

        from src.models.dice_models import LasersFeelingRollResult, RollOutcome

        cli = DMCommandLineInterface()

        roll_result = LasersFeelingRollResult(
            character_number=4,
            task_type="feelings",
            is_prepared=False,
            is_expert=False,
            individual_rolls=[4],
            die_successes=[True],
            laser_feelings_indices=[0],
            total_successes=1,
            outcome=RollOutcome.BARELY,
            timestamp=datetime.now(UTC)
        )

        # Mock input()
        with patch('builtins.input', return_value="You feel their sincerity"):
            cli._prompt_for_laser_feelings_answer(roll_result)

        # Capture output
        captured = capsys.readouterr()

        # Verify "What insight does the character gain?" prompt was displayed
        assert "What insight does the character gain?" in captured.out

    def test_answer_included_in_adjudication_result(self, tmp_path, monkeypatch):
        """Test LASER FEELINGS answer included in dict from _prompt_for_dm_input_at_phase"""
        import json

        # Create temporary config directory
        config_dir = tmp_path / "config" / "personalities"
        config_dir.mkdir(parents=True)

        # Create test character config file
        char_config = {
            "character_id": "char_zara_001",
            "agent_id": "agent_alex_001",
            "name": "Zara-7",
            "number": 3  # Using number 3 for predictable rolls
        }
        config_file = config_dir / "char_zara_001_character.json"
        with open(config_file, "w") as f:
            json.dump(char_config, f)

        # Change to tmp_path so config/personalities is found
        monkeypatch.chdir(tmp_path)

        cli = DMCommandLineInterface()
        cli._current_phase = GamePhase.DM_ADJUDICATION

        # Set up turn state
        cli._current_turn_result = {
            "character_actions": {
                "char_zara_001": {
                    "task_type": "lasers",
                    "is_prepared": False,
                    "is_expert": False,
                    "is_helping": False,
                    "gm_question": "What is the ship's status?"
                }
            }
        }

        # Mock the dice roll to ensure LASER FEELINGS occurs
        from datetime import UTC, datetime

        from src.models.dice_models import LasersFeelingRollResult, RollOutcome

        mock_roll_result = LasersFeelingRollResult(
            character_number=3,
            task_type="lasers",
            is_prepared=False,
            is_expert=False,
            individual_rolls=[3],
            die_successes=[True],
            laser_feelings_indices=[0],
            total_successes=1,
            outcome=RollOutcome.BARELY,
            gm_question="What is the ship's status?",
            timestamp=datetime.now(UTC)
        )

        # Mock roll_lasers_feelings to return our controlled result
        with patch('src.interface.dm_cli.roll_lasers_feelings', return_value=mock_roll_result):
            # Mock input() for the DM's answer
            with patch('builtins.input', side_effect=["/roll", "The ship is critically damaged"]):
                # First input is for the /roll command, second is for the LASER FEELINGS answer
                result = cli._prompt_for_dm_input_at_phase("dm_adjudication")

        # Verify answer is included in result
        assert result["success"] is True
        assert "data" in result
        assert "laser_feelings_answer" in result["data"]
        assert result["data"]["laser_feelings_answer"] == "The ship is critically damaged"

    def test_no_answer_when_no_laser_feelings(self, tmp_path, monkeypatch):
        """Test that laser_feelings_answer is None when no LASER FEELINGS occurs"""
        import json

        # Create temporary config directory
        config_dir = tmp_path / "config" / "personalities"
        config_dir.mkdir(parents=True)

        # Create test character config file
        char_config = {
            "character_id": "char_zara_001",
            "agent_id": "agent_alex_001",
            "name": "Zara-7",
            "number": 2
        }
        config_file = config_dir / "char_zara_001_character.json"
        with open(config_file, "w") as f:
            json.dump(char_config, f)

        # Change to tmp_path so config/personalities is found
        monkeypatch.chdir(tmp_path)

        cli = DMCommandLineInterface()
        cli._current_phase = GamePhase.DM_ADJUDICATION

        # Set up turn state
        cli._current_turn_result = {
            "character_actions": {
                "char_zara_001": {
                    "task_type": "lasers",
                    "is_prepared": False,
                    "is_expert": False,
                    "is_helping": False
                }
            }
        }

        # Mock the dice roll to ensure NO LASER FEELINGS
        from datetime import UTC, datetime

        from src.models.dice_models import LasersFeelingRollResult, RollOutcome

        mock_roll_result = LasersFeelingRollResult(
            character_number=2,
            task_type="lasers",
            is_prepared=False,
            is_expert=False,
            individual_rolls=[5],
            die_successes=[False],
            laser_feelings_indices=[],  # No LASER FEELINGS
            total_successes=0,
            outcome=RollOutcome.FAILURE,
            timestamp=datetime.now(UTC)
        )

        # Mock roll_lasers_feelings to return our controlled result
        with patch('src.interface.dm_cli.roll_lasers_feelings', return_value=mock_roll_result):
            # Mock input() - should only be called once for the command
            with patch('builtins.input', return_value="/roll"):
                result = cli._prompt_for_dm_input_at_phase("dm_adjudication")

        # Verify laser_feelings_answer is None
        assert result["success"] is True
        assert "data" in result
        assert "laser_feelings_answer" in result["data"]
        assert result["data"]["laser_feelings_answer"] is None
