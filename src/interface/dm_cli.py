# ABOUTME: DM Command-Line Interface for interacting with AI TTRPG players through turn-based commands.
# ABOUTME: Provides command parsing, output formatting, session management, and error handling for DMs.

import sys
import re
from datetime import datetime
from enum import Enum
from typing import Optional
from dataclasses import dataclass

from src.models.messages import DMCommand, DMCommandType as ModelDMCommandType, DiceRoll
from src.models.game_state import GameState, GamePhase
from src.utils.dice import parse_dice_notation, roll_dice


# ============================================================================
# Custom Exceptions
# ============================================================================


class InvalidCommandError(Exception):
    """Raised when a command cannot be parsed or executed"""
    pass


# ============================================================================
# Command Types (CLI-specific)
# ============================================================================


class DMCommandType(str, Enum):
    """
    CLI command types for UI interaction.

    Note: This is a subset of ModelDMCommandType from messages.py.
    The CLI provides a simplified interface, using "fail" instead of "failure"
    for brevity. Commands like PAUSE, RESUME, SAVE, LOAD, STATUS, HELP
    are not yet implemented in the CLI but exist in the model.

    TODO: Implement remaining commands (SAVE, LOAD, HELP) referenced in quickstart.md
    """
    NARRATE = "narrate"
    ROLL = "roll"
    SUCCESS = "success"
    FAIL = "fail"  # Maps to ModelDMCommandType.FAILURE when creating DMCommand
    INFO = "info"  # Maps to ModelDMCommandType.STATUS
    QUIT = "quit"  # No model equivalent - CLI-only


# ============================================================================
# Data Structures
# ============================================================================


@dataclass
class ParsedCommand:
    """Parsed command with type and arguments"""
    command_type: DMCommandType
    args: dict
    raw_input: str


# ============================================================================
# T063: Command Parser
# ============================================================================


class DMCommandParser:
    """
    Parser for DM commands from CLI input.

    Supports:
    - Natural language narration: "The ship drifts..."
    - Slash commands: "/roll 2d6+3", "/success", "/info"
    - Aliases: "success", "fail", "failure"
    """

    # Command patterns
    COMMAND_PATTERNS = {
        DMCommandType.ROLL: r'^/roll(?:\s+(.+))?$',  # Optional notation to catch missing arg
        DMCommandType.SUCCESS: r'^/?success$',
        DMCommandType.FAIL: r'^/?(?:fail|failure)$',
        DMCommandType.INFO: r'^/info$',
        DMCommandType.QUIT: r'^/quit$',
        DMCommandType.NARRATE: r'^/narrate\s+(.+)$',
    }

    def parse(self, user_input: str) -> ParsedCommand:
        """
        Parse user input into structured command.

        Args:
            user_input: Raw input string from DM

        Returns:
            ParsedCommand with type and arguments

        Raises:
            InvalidCommandError: If command cannot be parsed
        """
        # Validate input
        if not user_input or not user_input.strip():
            raise InvalidCommandError("Cannot parse empty command")

        user_input = user_input.strip()

        # Try to match each command pattern
        for cmd_type, pattern in self.COMMAND_PATTERNS.items():
            match = re.match(pattern, user_input, re.IGNORECASE)
            if match:
                return self._parse_matched_command(cmd_type, match, user_input)

        # If no slash command matched, treat as narration
        return ParsedCommand(
            command_type=DMCommandType.NARRATE,
            args={"text": user_input},
            raw_input=user_input
        )

    def _parse_matched_command(
        self,
        cmd_type: DMCommandType,
        match: re.Match,
        raw_input: str
    ) -> ParsedCommand:
        """Parse matched command and extract arguments"""

        if cmd_type == DMCommandType.ROLL:
            notation = match.group(1)
            if not notation or not notation.strip():
                raise InvalidCommandError("Roll command requires dice notation (e.g., /roll 2d6+3)")
            notation = notation.strip()

            # Validate dice notation
            try:
                parse_dice_notation(notation)
            except ValueError as e:
                raise InvalidCommandError(f"Invalid dice notation: {e}")

            return ParsedCommand(
                command_type=cmd_type,
                args={"notation": notation},
                raw_input=raw_input
            )

        elif cmd_type == DMCommandType.NARRATE:
            text = match.group(1).strip()
            return ParsedCommand(
                command_type=cmd_type,
                args={"text": text},
                raw_input=raw_input
            )

        else:
            # Commands without arguments
            return ParsedCommand(
                command_type=cmd_type,
                args={},
                raw_input=raw_input
            )


# ============================================================================
# T067: Output Formatter
# ============================================================================


class CLIFormatter:
    """
    Formats output for display in CLI.

    Handles:
    - Phase transitions
    - Agent responses
    - Validation results
    - Dice rolls
    - Error messages
    - Session info
    """

    # Visual elements
    HEADER_BORDER = "═"
    PHASE_MARKER = "▶"
    SUCCESS_MARKER = "✓"
    FAILURE_MARKER = "✗"

    def format_header(self, campaign_name: str, characters: list[str]) -> str:
        """Format campaign header at session start"""
        width = 70
        lines = [
            "╔" + self.HEADER_BORDER * (width - 2) + "╗",
            "║" + "AI TTRPG Player System - Lasers & Feelings".center(width - 2) + "║",
            "║" + f"Campaign: {campaign_name}".center(width - 2) + "║",
            "╚" + self.HEADER_BORDER * (width - 2) + "╝",
            "",
            f"Loaded {len(characters)} AI player(s):",
        ]

        for char in characters:
            lines.append(f"  - {char}")

        lines.append("")
        return "\n".join(lines)

    def format_phase_transition(self, phase: GamePhase, turn_number: int) -> str:
        """Format phase transition announcement"""
        phase_name = self._humanize_phase_name(phase)
        return f"\n{self.PHASE_MARKER} [Turn {turn_number}] Phase: {phase_name}"

    def format_agent_response(
        self,
        agent_name: str,
        character_name: str,
        response: str,
        phase: GamePhase
    ) -> str:
        """Format agent strategic response"""
        return f"\n{agent_name} (Player): {response}"

    def format_character_action(self, character_name: str, action: str) -> str:
        """Format character in-character action"""
        return f"\n{character_name}: {action}"

    def format_validation_result(
        self,
        valid: bool,
        violations: Optional[list[str]] = None
    ) -> str:
        """Format validation pass/fail"""
        if valid:
            return f"\n[Validation] {self.SUCCESS_MARKER} PASS"
        else:
            lines = [f"\n[Validation] {self.FAILURE_MARKER} FAIL"]
            if violations:
                for v in violations:
                    lines.append(f"  - {v}")
            return "\n".join(lines)

    def format_dice_roll(
        self,
        notation: str,
        individual_rolls: list[int],
        total: int,
        modifier: int
    ) -> str:
        """Format dice roll result"""
        rolls_str = ", ".join(str(r) for r in individual_rolls)
        modifier_str = f" {'+' if modifier >= 0 else ''}{modifier}" if modifier != 0 else ""

        lines = [
            f"\n[Dice Roll] {notation}",
            f"  Individual rolls: [{rolls_str}]",
            f"  Total: {total}{modifier_str}"
        ]
        return "\n".join(lines)

    def format_awaiting_dm_input(
        self,
        expected_command_types: Optional[list[str]] = None
    ) -> str:
        """Format prompt awaiting DM input"""
        if expected_command_types:
            commands = ", ".join(expected_command_types)
            return f"\nAwaiting DM input ({commands})...\nDM > "
        return "\nDM > "

    def format_session_info(
        self,
        campaign_name: str,
        session_number: int,
        turn_number: int,
        current_phase: GamePhase,
        active_agents: list[dict]
    ) -> str:
        """Format session state info for /info command"""
        phase_name = self._humanize_phase_name(current_phase)

        lines = [
            "\n" + "=" * 50,
            f"SESSION INFO",
            "=" * 50,
            f"Campaign: {campaign_name}",
            f"Session: {session_number}",
            f"Turn: {turn_number}",
            f"Current Phase: {phase_name}",
            "",
            "Active Agents:",
        ]

        for agent in active_agents:
            lines.append(f"  - {agent.get('character_name', 'Unknown')} (ID: {agent.get('agent_id', 'N/A')})")

        lines.append("=" * 50)
        return "\n".join(lines)

    def format_character_info(
        self,
        character_name: str,
        style: str,
        role: str,
        number: int
    ) -> str:
        """Format character information"""
        return (
            f"\n{character_name}:\n"
            f"  Style: {style}\n"
            f"  Role: {role}\n"
            f"  Number: {number}"
        )

    def format_error(
        self,
        error_type: str,
        message: str,
        suggestion: Optional[str] = None
    ) -> str:
        """Format error message with optional suggestion"""
        lines = [
            f"\n{self.FAILURE_MARKER} ERROR: {error_type}",
            f"  {message}"
        ]

        if suggestion:
            lines.append(f"\n  Suggestion: {suggestion}")

        return "\n".join(lines)

    def _humanize_phase_name(self, phase: GamePhase) -> str:
        """Convert GamePhase enum to human-readable name"""
        name_map = {
            GamePhase.DM_NARRATION: "DM Narration",
            GamePhase.MEMORY_QUERY: "Memory Query",
            GamePhase.STRATEGIC_INTENT: "Strategic Intent",
            GamePhase.OOC_DISCUSSION: "OOC Discussion",
            GamePhase.CONSENSUS_DETECTION: "Consensus Detection",
            GamePhase.CHARACTER_ACTION: "Character Action",
            GamePhase.VALIDATION: "Validation",
            GamePhase.DM_ADJUDICATION: "DM Adjudication",
            GamePhase.DICE_RESOLUTION: "Dice Resolution",
            GamePhase.DM_OUTCOME: "DM Outcome",
            GamePhase.CHARACTER_REACTION: "Character Reaction",
            GamePhase.MEMORY_STORAGE: "Memory Storage",
        }
        return name_map.get(phase, phase.value)


# ============================================================================
# T064-T066: Command Handlers
# ============================================================================


class DMCommandLineInterface:
    """
    Main CLI interface for DM interaction.

    Handles:
    - Command parsing
    - Command execution
    - Output formatting
    - Session state management
    - Error handling
    """

    def __init__(self, orchestrator=None):
        """
        Initialize CLI interface.

        Args:
            orchestrator: Optional TurnOrchestrator instance (injected for testing)
        """
        self.parser = DMCommandParser()
        self.formatter = CLIFormatter()
        self.orchestrator = orchestrator

        # Session state
        self._current_phase: Optional[GamePhase] = None
        self._turn_number: int = 1
        self._session_number: int = 1
        self._campaign_name: str = ""
        self._active_agents: list[dict] = []
        self._should_exit: bool = False

    def handle_command(self, parsed: ParsedCommand) -> dict:
        """
        Execute parsed command and return result.

        Args:
            parsed: ParsedCommand from parser

        Returns:
            Result dict with success, command_type, args, etc.
        """
        # Check phase compatibility
        if not self._is_command_valid_for_phase(parsed.command_type):
            return {
                "success": False,
                "error": self._get_phase_mismatch_error(parsed.command_type),
                "error_type": "PhaseValidationError"
            }

        # Route to appropriate handler
        if parsed.command_type == DMCommandType.NARRATE:
            return self._handle_narrate(parsed)
        elif parsed.command_type == DMCommandType.ROLL:
            return self._handle_roll(parsed)
        elif parsed.command_type == DMCommandType.SUCCESS:
            return self._handle_success(parsed)
        elif parsed.command_type == DMCommandType.FAIL:
            return self._handle_fail(parsed)
        elif parsed.command_type == DMCommandType.INFO:
            return self._handle_info(parsed)
        elif parsed.command_type == DMCommandType.QUIT:
            return self._handle_quit(parsed)
        else:
            return {
                "success": False,
                "error": f"Unknown command type: {parsed.command_type}",
                "error_type": "UnknownCommandType"
            }

    # T064: Narrate command handler
    def _handle_narrate(self, parsed: ParsedCommand) -> dict:
        """Handle narration command"""
        return {
            "success": True,
            "command_type": DMCommandType.NARRATE,
            "args": parsed.args,
            "should_execute_turn": True
        }

    # T065: Roll command handler
    def _handle_roll(self, parsed: ParsedCommand) -> dict:
        """Handle dice roll command"""
        notation = parsed.args["notation"]

        # Parse and execute dice roll
        try:
            dice_result = roll_dice(notation)
        except ValueError as e:
            return {
                "success": False,
                "error": f"Invalid dice notation: {e}",
                "error_type": "InvalidDiceNotation"
            }

        # Format roll output
        output = self.formatter.format_dice_roll(
            notation=dice_result.notation,
            individual_rolls=dice_result.individual_rolls,
            total=dice_result.total,
            modifier=dice_result.modifier
        )

        return {
            "success": True,
            "command_type": DMCommandType.ROLL,
            "args": {
                "notation": notation,
                "dice_result": dice_result.model_dump()
            },
            "output": output
        }

    # T066: Success command handler
    def _handle_success(self, parsed: ParsedCommand) -> dict:
        """Handle success adjudication"""
        return {
            "success": True,
            "command_type": DMCommandType.SUCCESS,
            "args": {}
        }

    # T066: Fail command handler
    def _handle_fail(self, parsed: ParsedCommand) -> dict:
        """Handle failure adjudication"""
        return {
            "success": True,
            "command_type": DMCommandType.FAIL,
            "args": {}
        }

    # T068: Info command handler
    def _handle_info(self, parsed: ParsedCommand) -> dict:
        """Handle session info display"""
        info_output = self.formatter.format_session_info(
            campaign_name=self._campaign_name or "Unknown Campaign",
            session_number=self._session_number,
            turn_number=self._turn_number,
            current_phase=self._current_phase or GamePhase.DM_NARRATION,
            active_agents=self._active_agents
        )

        return {
            "success": True,
            "command_type": DMCommandType.INFO,
            "output": info_output
        }

    def _handle_quit(self, parsed: ParsedCommand) -> dict:
        """Handle quit command"""
        return {
            "success": True,
            "command_type": DMCommandType.QUIT,
            "should_exit": True
        }

    # T069: Phase validation and error handling
    def _is_command_valid_for_phase(self, command_type: DMCommandType) -> bool:
        """Check if command can be used in current phase"""
        # Info and quit are always valid
        if command_type in (DMCommandType.INFO, DMCommandType.QUIT):
            return True

        # Narrate only valid at DM_NARRATION phase
        if command_type == DMCommandType.NARRATE:
            return (
                self._current_phase is None or
                self._current_phase == GamePhase.DM_NARRATION
            )

        # Success/fail/roll only valid at DM_ADJUDICATION or DICE_RESOLUTION
        if command_type in (DMCommandType.SUCCESS, DMCommandType.FAIL, DMCommandType.ROLL):
            return self._current_phase in (
                GamePhase.DM_ADJUDICATION,
                GamePhase.DICE_RESOLUTION,
                None  # Allow when phase not set (unit testing and manual CLI testing)
            )

        return True

    def _get_phase_mismatch_error(self, command_type: DMCommandType) -> str:
        """Get user-friendly error for phase mismatch"""
        phase_name = self.formatter._humanize_phase_name(
            self._current_phase or GamePhase.DM_NARRATION
        )

        if command_type == DMCommandType.NARRATE:
            return (
                f"Cannot narrate during {phase_name}. "
                f"Wait for the turn to complete and return to narration phase."
            )
        elif command_type in (DMCommandType.SUCCESS, DMCommandType.FAIL, DMCommandType.ROLL):
            return (
                f"Cannot adjudicate during {phase_name}. "
                f"Wait for character actions to complete first."
            )

        return f"Command '{command_type}' not valid during {phase_name}"

    def run(self):
        """
        Main CLI loop.

        Continuously reads DM input, parses commands, executes them,
        and displays output until quit command is received.
        """
        # Display header
        if self._campaign_name:
            print(self.formatter.format_header(
                campaign_name=self._campaign_name,
                characters=[
                    agent.get("character_name", "Unknown")
                    for agent in self._active_agents
                ]
            ))

        print("\nSession starting...")
        print(self.formatter.format_awaiting_dm_input())

        while not self._should_exit:
            try:
                # Read input
                user_input = input().strip()

                if not user_input:
                    continue

                # Parse command
                try:
                    parsed = self.parser.parse(user_input)
                except InvalidCommandError as e:
                    error_output = self.formatter.format_error(
                        error_type="InvalidCommandError",
                        message=str(e),
                        suggestion=self._get_command_suggestion(user_input)
                    )
                    print(error_output)
                    print(self.formatter.format_awaiting_dm_input())
                    continue

                # Execute command
                result = self.handle_command(parsed)

                if not result["success"]:
                    error_output = self.formatter.format_error(
                        error_type=result.get("error_type", "CommandExecutionError"),
                        message=result.get("error", "Unknown error"),
                        suggestion=self._get_command_suggestion(user_input)
                    )
                    print(error_output)
                    print(self.formatter.format_awaiting_dm_input())
                    continue

                # Display command-specific output
                if "output" in result:
                    print(result["output"])

                # Check for exit
                if result.get("should_exit"):
                    print("\nExiting session. Goodbye!")
                    self._should_exit = True
                    break

                # Show next prompt
                print(self.formatter.format_awaiting_dm_input())

            except KeyboardInterrupt:
                print("\n\nReceived interrupt signal. Use /quit to exit gracefully.")
                print(self.formatter.format_awaiting_dm_input())
            except EOFError:
                print("\n\nEnd of input. Exiting.")
                break
            except Exception as e:
                error_output = self.formatter.format_error(
                    error_type=type(e).__name__,
                    message=str(e),
                    suggestion="This is an unexpected error. Check logs for details."
                )
                print(error_output)
                print(self.formatter.format_awaiting_dm_input())

    def _get_command_suggestion(self, user_input: str) -> Optional[str]:
        """Get helpful suggestion based on failed command"""
        if "/roll" in user_input.lower():
            return "Try: /roll 1d20, /roll 2d6+3, or /roll d6"
        elif any(word in user_input.lower() for word in ["success", "fail", "pass"]):
            return "Try: success, fail, or /roll <dice>"
        else:
            return "Available commands: narrate text, /roll <dice>, success, fail, /info, /quit"


# ============================================================================
# Entry Point (for manual testing)
# ============================================================================


def main():
    """Entry point for running CLI standalone"""
    cli = DMCommandLineInterface()
    cli._campaign_name = "Voyage of the Raptor"
    cli._active_agents = [
        {"agent_id": "agent_001", "character_name": "Zara-7 (Android Engineer)"}
    ]

    try:
        cli.run()
    except Exception as e:
        print(f"\nFatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
