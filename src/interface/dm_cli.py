# ABOUTME: DM Command-Line Interface for interacting with AI TTRPG players.
# ABOUTME: Command parsing, output formatting, session management, and error handling.

import re
import sys
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from enum import Enum

from loguru import logger
from redis import Redis

from src.config.settings import get_settings
from src.models.dice_models import LasersFeelingRollResult
from src.models.game_state import GamePhase
from src.models.messages import MessageChannel, MessageType
from src.orchestration.message_router import MessageRouter
from src.orchestration.turn_orchestrator import TurnOrchestrator
from src.utils.dice import parse_dice_notation, roll_dice, roll_lasers_feelings
from src.utils.logging import setup_logging
from src.utils.redis_cleanup import cleanup_redis_for_new_session

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

            # Allow empty notation for character-suggested roll
            if not notation or not notation.strip():
                return ParsedCommand(
                    command_type=cmd_type,
                    args={},  # No notation = use character's suggestion
                    raw_input=raw_input
                )

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
        violations: list[str] | None = None
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
        expected_command_types: list[str] | None = None,
        current_phase: GamePhase | None = None
    ) -> str:
        """Format prompt awaiting DM input"""
        phase_display = ""
        if current_phase:
            phase_name = self._humanize_phase_name(current_phase)
            phase_display = f"[{phase_name}] "

        if expected_command_types:
            commands = ", ".join(expected_command_types)
            return f"\nAwaiting DM input ({commands})...\n{phase_display}DM > "
        return f"\n{phase_display}DM > "

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
            "SESSION INFO",
            "=" * 50,
            f"Campaign: {campaign_name}",
            f"Session: {session_number}",
            f"Turn: {turn_number}",
            f"Current Phase: {phase_name}",
            "",
            "Active Agents:",
        ]

        for agent in active_agents:
            char_name = agent.get('character_name', 'Unknown')
            agent_id = agent.get('agent_id', 'N/A')
            lines.append(f"  - {char_name} (ID: {agent_id})")

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
        suggestion: str | None = None
    ) -> str:
        """Format error message with optional suggestion"""
        lines = [
            f"\n{self.FAILURE_MARKER} ERROR: {error_type}",
            f"  {message}"
        ]

        if suggestion:
            lines.append(f"\n  Suggestion: {suggestion}")

        return "\n".join(lines)

    def format_dice_suggestion(
        self,
        action_dict: dict,
        character_name_resolver: Callable[[str], str] | None = None
    ) -> str | None:
        """
        Format dice roll suggestion with justifications for DM review.

        Args:
            action_dict: ActionDict containing roll suggestions
            character_name_resolver: Optional function to resolve character_id to name

        Returns:
            Formatted string with roll suggestions, or None if no suggestions
        """
        task_type = action_dict.get("task_type")

        # Return None if no dice suggestion
        if task_type is None:
            return None

        lines = ["  Dice Roll Suggestion:"]

        # Display task type
        task_type_display = task_type.capitalize()
        task_description = (
            "logic/tech" if task_type.lower() == "lasers" else "social/emotion"
        )
        lines.append(f"  - Task Type: {task_type_display} ({task_description})")

        # Track bonus dice count
        bonus_dice = 0

        # Display prepared flag + justification
        is_prepared = action_dict.get("is_prepared", False)
        prepared_just = action_dict.get("prepared_justification", "")
        if is_prepared:
            bonus_dice += 1
            lines.append(f"  - Prepared: {self.SUCCESS_MARKER} \"{prepared_just}\"")

        # Display expert flag + justification
        is_expert = action_dict.get("is_expert", False)
        expert_just = action_dict.get("expert_justification", "")
        if is_expert:
            bonus_dice += 1
            lines.append(f"  - Expert: {self.SUCCESS_MARKER} \"{expert_just}\"")

        # Display helping flag + target + justification
        is_helping = action_dict.get("is_helping", False)
        if is_helping:
            bonus_dice += 1
            helping_char_id = action_dict.get("helping_character_id", "unknown")
            help_just = action_dict.get("help_justification", "")

            # Resolve character name if resolver provided
            helping_char_name = helping_char_id
            if character_name_resolver:
                helping_char_name = character_name_resolver(helping_char_id)

            lines.append(f"  - Helping {helping_char_name}: {self.SUCCESS_MARKER} \"{help_just}\"")

        # Calculate suggested dice count (1 base + bonuses, max 3)
        total_dice = min(1 + bonus_dice, 3)
        roll_formula = f"{total_dice}d6 {task_type_display}"
        lines.append(f"  - Suggested Roll: {roll_formula}")

        return "\n".join(lines)

    def format_character_action_with_directive(
        self,
        character_name: str,
        directive_text: str,
        action_dict: dict,
        character_name_resolver: Callable[[str], str] | None = None
    ) -> str:
        """
        Format character action showing both player directive and character performance.

        Args:
            character_name: Human-readable character name (e.g., "Zara-7")
            directive_text: The strategic goal/instruction from the player
            action_dict: The Action model dict with narrative_text field
            character_name_resolver: Optional function to resolve character_id to name

        Returns:
            Formatted string with labeled sections
        """
        lines = [f"\n{character_name}:"]
        lines.append(f"  Player Directive: {directive_text}")

        narrative = action_dict.get("narrative_text", "")
        lines.append(f"  Character Performance: {narrative}")

        # Append dice suggestion if present
        dice_suggestion = self.format_dice_suggestion(action_dict, character_name_resolver)
        if dice_suggestion:
            lines.append(dice_suggestion)

        return "\n".join(lines)

    def format_character_reaction_detailed(
        self,
        character_name: str,
        reaction_dict: dict
    ) -> str:
        """
        Format character reaction as cohesive narrative.

        Args:
            character_name: Human-readable character name (e.g., "Zara-7")
            reaction_dict: The Reaction model dict with narrative_text field

        Returns:
            Formatted string with labeled sections
        """
        lines = [f"\n{character_name}:"]

        narrative = reaction_dict.get("narrative_text", "")
        lines.append(f"  {narrative}")

        return "\n".join(lines)

    def format_ooc_summary(
        self,
        messages: list,
        turn_number: int,
        agent_names: dict[str, str] | None = None
    ) -> str | None:
        """
        Format OOC strategic discussion summary for post-turn display.

        Args:
            messages: List of OOC messages from this turn
            turn_number: Turn number to display
            agent_names: Optional mapping of agent_id to agent_name

        Returns:
            Formatted string with header and message list, or None if no messages
        """
        if not messages:
            return None

        agent_names = agent_names or {}

        lines = [
            f"\n=== OOC Strategic Discussion (Turn {turn_number}) ==="
        ]

        for message in messages:
            timestamp_str = message.timestamp.strftime("%H:%M:%S")
            agent_name = agent_names.get(message.from_agent, message.from_agent)
            lines.append(f"[{timestamp_str}] {agent_name} (Player): \"{message.content}\"")

        return "\n".join(lines)

    def _humanize_phase_name(self, phase: GamePhase) -> str:
        """Convert GamePhase enum to human-readable name"""
        name_map = {
            GamePhase.DM_NARRATION: "DM Narration",
            GamePhase.MEMORY_QUERY: "Memory Query",
            GamePhase.DM_CLARIFICATION: "DM Clarification",
            GamePhase.STRATEGIC_INTENT: "Strategic Intent",
            GamePhase.OOC_DISCUSSION: "OOC Discussion",
            GamePhase.CONSENSUS_DETECTION: "Consensus Detection",
            GamePhase.CHARACTER_ACTION: "Character Action",
            GamePhase.VALIDATION: "Validation",
            GamePhase.DM_ADJUDICATION: "DM Adjudication",
            GamePhase.DICE_RESOLUTION: "Dice Resolution",
            GamePhase.LASER_FEELINGS_QUESTION: "Laser Feelings Question",
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
        self._current_phase: GamePhase | None = None  # Set to DM_NARRATION when turn starts
        self._turn_number: int = 1
        self._session_number: int = 1
        self._campaign_name: str = ""
        self._active_agents: list[dict] = []
        self._should_exit: bool = False
        # Store current turn state for roll suggestions
        self._current_turn_result: dict | None = None

        # Character ID to name mapping (loaded from config files)
        self._character_names: dict[str, str] = {}
        self._character_configs: dict[str, dict] = {}  # Map character_id -> full config
        self._agent_to_character: dict[str, str] = {}  # Map agent_id -> character_id
        self._load_character_names()
        self._load_agent_to_character_mapping()

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
        notation = parsed.args.get("notation")

        if not notation:
            return {
                "success": False,
                "error": "Roll command requires dice notation or must be used during adjudication",
                "error_type": "MissingDiceNotation"
            }

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
            # Format agent list for display
            if self._active_agents:
                if isinstance(self._active_agents[0], dict):
                    # Legacy format: list of dicts
                    character_list = [
                        agent.get("character_name", "Unknown")
                        for agent in self._active_agents
                    ]
                else:
                    # New format: list of agent IDs
                    character_list = [
                        "Zara-7 (Android Engineer)"  # TODO: Load from config
                    ]
            else:
                character_list = []

            print(self.formatter.format_header(
                campaign_name=self._campaign_name,
                characters=character_list
            ))

        print("\nSession starting...")
        print(self.formatter.format_awaiting_dm_input(current_phase=self._current_phase))

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
                    print(self.formatter.format_awaiting_dm_input(current_phase=self._current_phase))
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
                    print(self.formatter.format_awaiting_dm_input(current_phase=self._current_phase))
                    continue

                # Display command-specific output
                if "output" in result:
                    print(result["output"])

                # Execute turn cycle if needed
                if result.get("should_execute_turn") and self.orchestrator:
                    try:
                        logger.info("Executing turn cycle via orchestrator")
                        turn_result = self.orchestrator.execute_turn_cycle(
                            dm_input=result["args"]["text"],
                            active_agents=self._active_agents,
                            turn_number=self._turn_number,
                            session_number=self._session_number
                        )

                        # Store turn result for roll suggestions
                        self._current_turn_result = turn_result

                        # Handle interrupts - keep prompting DM until turn completes
                        while turn_result.get("awaiting_dm_input"):
                            awaiting_phase = turn_result.get("awaiting_phase")
                            logger.info(
                                f"Turn interrupted at {awaiting_phase}, prompting DM for input"
                            )

                            # Display character actions if available
                            if turn_result.get("character_actions"):
                                print("\nCharacter Actions:")
                                strategic_intents = turn_result.get("strategic_intents", {})
                                character_actions = turn_result["character_actions"]

                                for char_id, action_dict in character_actions.items():
                                    # Get character name
                                    char_name = self._get_character_name(char_id)

                                    # Get directive text from strategic_intents
                                    # Map character_id back to agent_id to get strategic intent
                                    # For now, use a simple heuristic: find matching agent
                                    directive_text = "Unknown directive"
                                    for agent_id, intent_dict in strategic_intents.items():
                                        # Intent dict should have strategic_goal field
                                        if isinstance(intent_dict, dict):
                                            directive_text = intent_dict.get(
                                                "strategic_goal", str(intent_dict)
                                            )
                                        else:
                                            directive_text = str(intent_dict)
                                        break  # For MVP, assume single agent

                                    # Display action with directive using enhanced formatter
                                    formatted_action = (
                                        self.formatter.format_character_action_with_directive(
                                            char_name,
                                            directive_text,
                                            action_dict,
                                            self._get_character_name
                                        )
                                    )
                                    print(formatted_action)

                            # Prompt DM based on awaiting phase
                            # Pass turn_result so phase prompts can access current character actions
                            dm_input_result = self._prompt_for_dm_input_at_phase(
                                awaiting_phase,
                                current_turn_result=turn_result
                            )

                            if not dm_input_result["success"]:
                                print(self.formatter.format_error(
                                    error_type="InvalidInput",
                                    message=dm_input_result.get("error", "Invalid input"),
                                    suggestion=dm_input_result.get("suggestion")
                                ))
                                continue

                            # Resume turn with DM input
                            turn_result = self.orchestrator.resume_turn_with_dm_input(
                                session_number=self._session_number,
                                dm_input_type=dm_input_result["input_type"],
                                dm_input_data=dm_input_result["data"]
                            )

                        # Display final turn results
                        print("\n--- Turn Complete ---")
                        print(f"Final phase: {turn_result['phase_completed']}")

                        # Display character reactions if available
                        if turn_result.get("character_reactions"):
                            print("\nCharacter Reactions:")
                            character_reactions = turn_result["character_reactions"]
                            for char_id, reaction_dict in character_reactions.items():
                                # Extract narrative text from Reaction model dict
                                reaction_text = (
                                    reaction_dict.get("narrative_text", str(reaction_dict))
                                    if reaction_dict
                                    else ""
                                )

                                # Get character name
                                char_name = self._get_character_name(char_id)

                                # Display reaction
                                print(f"\n{char_name}:")
                                print(f"  {reaction_text}")

                        # Display OOC strategic discussion from this turn
                        self._display_ooc_summary(turn_number=self._turn_number)

                        # Update current phase and increment turn counter
                        self._current_phase = GamePhase(turn_result['phase_completed'])
                        self._turn_number += 1
                        self._current_turn_result = None  # Clear for next turn

                    except Exception as e:
                        error_output = self.formatter.format_error(
                            error_type=type(e).__name__,
                            message=f"Turn execution failed: {e}",
                            suggestion="Check logs for details"
                        )
                        print(error_output)

                # Check for exit
                if result.get("should_exit"):
                    print("\nExiting session. Goodbye!")
                    self._should_exit = True
                    break

                # Show next prompt
                print(self.formatter.format_awaiting_dm_input(current_phase=self._current_phase))

            except KeyboardInterrupt:
                print("\n\nReceived interrupt signal. Use /quit to exit gracefully.")
                print(self.formatter.format_awaiting_dm_input(current_phase=self._current_phase))
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
                print(self.formatter.format_awaiting_dm_input(current_phase=self._current_phase))

    def _load_character_names(self) -> None:
        """
        Load character configs to build character_id → character_name mapping.

        Looks for character config files in config/personalities/ directory.
        Populates self._character_names and self._character_configs dicts.
        """
        import json
        from pathlib import Path

        try:
            config_dir = Path("config/personalities")
            if not config_dir.exists():
                logger.warning(f"Character config directory not found: {config_dir}")
                return

            # Load all character config files (char_*_character.json)
            for config_file in config_dir.glob("char_*_character.json"):
                try:
                    with open(config_file) as f:
                        character_config = json.load(f)
                        character_id = character_config.get("character_id")
                        character_name = character_config.get("name")

                        if character_id and character_name:
                            self._character_names[character_id] = character_name
                            self._character_configs[character_id] = character_config
                            logger.debug(
                                f"Loaded character: {character_id} → {character_name}"
                            )
                except Exception as e:
                    logger.warning(f"Failed to load character config {config_file}: {e}")

            logger.info(f"Loaded {len(self._character_names)} character configs")

        except Exception as e:
            logger.error(f"Failed to load character configs: {e}")

    def _load_agent_to_character_mapping(self) -> None:
        """
        Build mapping from agent_id to character_id from config files.

        Reads character config files and creates a lookup dict to resolve
        which character belongs to which agent.
        """
        import json
        from pathlib import Path

        try:
            config_dir = Path("config/personalities")
            if not config_dir.exists():
                logger.warning(f"Character config directory not found: {config_dir}")
                return

            for config_file in config_dir.glob("char_*_character.json"):
                try:
                    with open(config_file) as f:
                        char_config = json.load(f)
                        agent_id = char_config.get("agent_id")
                        character_id = char_config.get("character_id")

                        if agent_id and character_id:
                            self._agent_to_character[agent_id] = character_id
                            logger.debug(f"Mapped agent {agent_id} → character {character_id}")
                except Exception as e:
                    logger.warning(f"Failed to load mapping from {config_file}: {e}")

            logger.info(f"Loaded {len(self._agent_to_character)} agent-to-character mappings")

        except Exception as e:
            logger.error(f"Failed to load agent-to-character mappings: {e}")

    def _get_character_name(self, character_id: str) -> str:
        """
        Get character name from character_id, falling back to ID if not found.

        Args:
            character_id: Character identifier (e.g., "char_zara_001")

        Returns:
            Character name if found, otherwise character_id
        """
        return self._character_names.get(character_id, character_id)

    def _get_agent_name(self, agent_id: str) -> str:
        """
        Get agent name from agent_id, falling back to ID if not found.

        Args:
            agent_id: Agent identifier (e.g., "agent_alex_001")

        Returns:
            Agent name if found, otherwise agent_id
        """
        # Extract player name from agent ID
        # agent_alex_001 → Alex
        if agent_id.startswith("agent_"):
            parts = agent_id.split("_")
            if len(parts) >= 2:
                return parts[1].capitalize()

        return agent_id

    def _get_or_create_router(self) -> MessageRouter:
        """
        Get or create MessageRouter instance.

        Returns:
            MessageRouter instance
        """
        settings = get_settings()
        redis_client = Redis.from_url(settings.redis_url, decode_responses=False)
        return MessageRouter(redis_client)

    def _execute_character_suggested_roll(self, character_actions: dict | None = None) -> dict:
        """
        Execute Lasers & Feelings roll using character's suggested parameters.

        Reads action_dict from provided character_actions or current turn state,
        extracts roll modifiers, loads character sheet for character number,
        and calls roll_lasers_feelings().

        Args:
            character_actions: Optional dict of character actions (if None, uses self._current_turn_result)

        Returns:
            Dict with success: bool, roll_result: LasersFeelingRollResult or error message
        """
        # Get character actions from parameter or current turn state
        if character_actions is None:
            if not self._current_turn_result:
                return {
                    "success": False,
                    "error": "No turn state available",
                    "suggestion": "Character roll suggestions are only available during adjudication"
                }
            character_actions = self._current_turn_result.get("character_actions", {})

        if not character_actions:
            return {
                "success": False,
                "error": "No character actions available",
                "suggestion": "Use /roll <dice> to specify a dice roll"
            }

        # For MVP, assume single character (first in dict)
        # TODO: Support multi-character adjudication
        character_id = list(character_actions.keys())[0]
        action_dict = character_actions[character_id]

        # Extract roll parameters from action_dict
        task_type = action_dict.get("task_type")
        if not task_type:
            return {
                "success": False,
                "error": "No dice roll suggestion available",
                "suggestion": "Use /roll <dice> to specify a dice roll"
            }

        is_prepared = action_dict.get("is_prepared", False)
        is_expert = action_dict.get("is_expert", False)
        is_helping = action_dict.get("is_helping", False)
        gm_question = action_dict.get("gm_question")

        # Load character config to get character number
        character_config = self._character_configs.get(character_id)
        if not character_config:
            return {
                "success": False,
                "error": f"Character config not found for {character_id}",
                "suggestion": "Check character configuration files"
            }

        character_number = character_config.get("number")
        if not character_number:
            return {
                "success": False,
                "error": f"Character number missing in config for {character_id}",
                "suggestion": "Check character configuration files"
            }

        # Calculate dice count for display
        dice_count = 1
        dice_count += 1 if is_prepared else 0
        dice_count += 1 if is_expert else 0
        dice_count += 1 if is_helping else 0
        dice_count = min(dice_count, 3)  # Max 3 dice

        # Display using character suggestion
        character_name = self._get_character_name(character_id)
        print(f"\nUsing {character_name}'s suggested roll: {dice_count}d6 {task_type.capitalize()}")

        # Execute Lasers & Feelings roll
        try:
            roll_result = roll_lasers_feelings(
                character_number=character_number,
                task_type=task_type,
                is_prepared=is_prepared,
                is_expert=is_expert,
                successful_helpers=0,  # TODO(Phase1-Issue2): Will be populated by helper resolution
                gm_question=gm_question
            )

            return {
                "success": True,
                "roll_result": roll_result
            }
        except ValueError as e:
            return {
                "success": False,
                "error": f"Roll execution failed: {e}",
                "suggestion": "Check roll parameters"
            }

    def _display_lasers_feelings_result(self, roll_result: LasersFeelingRollResult) -> None:
        """
        Display Lasers & Feelings roll result in CLI format.

        Args:
            roll_result: LasersFeelingRollResult from roll_lasers_feelings()
        """
        # Build display string
        rolls_str = ", ".join(str(r) for r in roll_result.individual_rolls)
        task_type_display = roll_result.task_type.capitalize()

        lines = [
            f"\n[Lasers & Feelings Roll] {roll_result.dice_count}d6 {task_type_display}",
            f"  Character Number: {roll_result.character_number}",
            f"  Individual Rolls: [{rolls_str}]",
            f"  Successes: {roll_result.total_successes}/{roll_result.dice_count}",
            f"  Outcome: {roll_result.outcome.value.upper()}"
        ]

        # Display LASER FEELINGS if any
        if roll_result.has_laser_feelings:
            lf_indices = ", ".join(str(i+1) for i in roll_result.laser_feelings_indices)
            lines.append(f"  LASER FEELINGS on die #{lf_indices}!")

            # Display GM question if provided
            if roll_result.gm_question:
                lines.append(f"    Suggested Question: \"{roll_result.gm_question}\"")
            else:
                lines.append(
                    "    (No question suggested - ask the character what they want to know)"
                )

        print("\n".join(lines))

    def _prompt_for_laser_feelings_answer(self, roll_result: LasersFeelingRollResult) -> str | None:
        """
        Prompt DM for answer to LASER FEELINGS question.

        Args:
            roll_result: LasersFeelingRollResult with has_laser_feelings=True

        Returns:
            DM's answer as a string, or None if no answer provided
        """
        # Only prompt if LASER FEELINGS occurred
        if not roll_result.has_laser_feelings:
            return None

        # Determine prompt text
        if roll_result.gm_question:
            prompt_text = "\nAnswer: "
        else:
            prompt_text = "\nWhat insight does the character gain? "

        # Read DM's answer
        print(prompt_text, end="", flush=True)
        answer = input().strip()

        # Handle empty answers gracefully
        if not answer:
            return None

        return answer

    def _display_ooc_summary(self, turn_number: int, router: MessageRouter | None = None) -> None:
        """
        Display OOC strategic discussion from the completed turn.

        Fetches OOC messages via MessageRouter and formats for display.

        Args:
            turn_number: Turn number to fetch messages for
            router: Optional MessageRouter instance (creates new if None)
        """
        # Create router if not provided
        if router is None:
            try:
                settings = get_settings()
                redis_client = Redis.from_url(settings.redis_url, decode_responses=False)
                router = MessageRouter(redis_client)
            except Exception as e:
                logger.warning(f"Could not create MessageRouter for OOC summary: {e}")
                return

        # Fetch OOC messages for this turn
        try:
            all_messages = router.get_ooc_messages_for_player(limit=100)

            # Filter to current turn only
            turn_messages = [
                msg for msg in all_messages
                if msg.turn_number == turn_number
            ]

            if not turn_messages:
                # No OOC messages for this turn - don't display section
                return

            # Build agent_id -> agent_name mapping
            # For now, use simple mapping from active_agents
            agent_names = {}
            # TODO: Load from config or use self._character_names mapping

            # Format and display summary
            summary = self.formatter.format_ooc_summary(
                turn_messages,
                turn_number=turn_number,
                agent_names=agent_names
            )

            if summary:
                print(summary)

        except Exception as e:
            logger.warning(f"Failed to display OOC summary: {e}")

    def _get_command_suggestion(self, user_input: str) -> str | None:
        """Get helpful suggestion based on failed command"""
        if "/roll" in user_input.lower():
            return "Try: /roll (use character's suggestion) or /roll 2d6+3 (DM override)"
        elif any(word in user_input.lower() for word in ["success", "fail", "pass"]):
            return "Try: success, fail, or /roll"
        else:
            return "Available commands: narrate text, /roll [dice], success, fail, /info, /quit"

    def _prompt_for_dm_input_at_phase(self, awaiting_phase: str, current_turn_result: dict | None = None) -> dict:
        """
        Prompt DM for input based on which phase is waiting.

        Args:
            awaiting_phase: The phase that's waiting for DM input
            current_turn_result: Optional current turn result dict with character_actions

        Returns:
            Dict with success, input_type, and data fields
        """
        if awaiting_phase == "dm_adjudication":
            # Prompt for adjudication
            print("\n=== DM Adjudication Required ===")
            print("Commands: success, fail, /roll (use suggestion), or /roll <dice> (override)")
            print(self.formatter.format_awaiting_dm_input(
                current_phase=GamePhase.DM_ADJUDICATION,
                expected_command_types=["success", "fail", "/roll"]
            ))

            # Read DM input
            user_input = input().strip()

            if not user_input:
                return {
                    "success": False,
                    "error": "Empty input",
                    "suggestion": "Use: success, fail, /roll, or /roll <dice>"
                }

            # Parse command
            try:
                parsed = self.parser.parse(user_input)
            except InvalidCommandError as e:
                return {
                    "success": False,
                    "error": str(e),
                    "suggestion": "Use: success, fail, /roll, or /roll <dice>"
                }

            # Handle based on command type
            if parsed.command_type == DMCommandType.SUCCESS:
                return {
                    "success": True,
                    "input_type": "adjudication",
                    "data": {
                        "needs_dice": False,
                        "dice_override": None,
                        "manual_success": True  # DM ruled success
                    }
                }

            elif parsed.command_type == DMCommandType.FAIL:
                return {
                    "success": True,
                    "input_type": "adjudication",
                    "data": {
                        "needs_dice": False,
                        "dice_override": None,
                        "manual_success": False  # DM ruled failure
                    }
                }

            elif parsed.command_type == DMCommandType.ROLL:
                # Check if notation was provided (DM override)
                notation = parsed.args.get("notation")

                if notation:
                    # DM provided explicit notation - use it
                    try:
                        dice_result = roll_dice(notation)
                        print(self.formatter.format_dice_roll(
                            notation=dice_result.notation,
                            individual_rolls=dice_result.individual_rolls,
                            total=dice_result.total,
                            modifier=dice_result.modifier
                        ))

                        return {
                            "success": True,
                            "input_type": "adjudication",
                            "data": {
                                "needs_dice": True,
                                "dice_override": dice_result.total
                            }
                        }
                    except ValueError as e:
                        return {
                            "success": False,
                            "error": f"Invalid dice notation: {e}",
                            "suggestion": "Use format like: /roll 1d6, /roll 2d6+3"
                        }
                else:
                    # No notation - use character's suggested roll
                    # Pass character_actions from current_turn_result if available
                    character_actions = None
                    if current_turn_result:
                        character_actions = current_turn_result.get("character_actions")

                    lf_result = self._execute_character_suggested_roll(character_actions=character_actions)

                    if not lf_result["success"]:
                        return lf_result  # Return error

                    # Display Lasers & Feelings roll result
                    roll_result = lf_result["roll_result"]
                    self._display_lasers_feelings_result(roll_result)

                    # Prompt for LASER FEELINGS answer if needed
                    laser_feelings_answer = self._prompt_for_laser_feelings_answer(roll_result)

                    return {
                        "success": True,
                        "input_type": "adjudication",
                        "data": {
                            "needs_dice": True,
                            "lasers_feelings_result": roll_result.model_dump(),
                            "laser_feelings_answer": laser_feelings_answer
                        }
                    }

            else:
                return {
                    "success": False,
                    "error": f"Invalid command for adjudication: {parsed.command_type}",
                    "suggestion": "Use: success, fail, /roll, or /roll <dice>"
                }

        elif awaiting_phase == "dm_clarification_wait":
            # Fetch clarification round from turn state
            turn_result = self._current_turn_result or {}
            round_num = turn_result.get("clarification_round", 1)

            print(f"\n=== Player Clarifying Questions (Round {round_num}) ===")

            # Fetch OOC messages from current turn (dm_clarification phase only)
            router = self._get_or_create_router()
            ooc_messages = router.get_ooc_messages_for_player(limit=100)

            clarification_messages = [
                msg for msg in ooc_messages
                if (msg.phase == "dm_clarification" and
                    msg.turn_number == self._turn_number)
            ]

            if not clarification_messages:
                # No messages found (shouldn't happen, but handle gracefully)
                logger.warning("No clarification messages found but wait node was entered")
                return {
                    "success": True,
                    "input_type": "dm_clarification_answer",
                    "data": {"answers": [], "force_finish": False}
                }

            # Separate questions from answers
            # Questions are from agents (not "dm")
            # Answers are from "dm"
            questions = [msg for msg in clarification_messages if msg.from_agent != "dm"]
            dm_answers = [msg for msg in clarification_messages if msg.from_agent == "dm"]

            # Find questions that haven't been answered yet
            # Compare timestamps: questions after the last DM answer are new
            last_answer_time = datetime.min
            if dm_answers:
                last_answer_time = max(msg.timestamp for msg in dm_answers)

            new_questions = [
                msg for msg in questions
                if msg.timestamp > last_answer_time
            ]

            if not new_questions:
                # All questions already answered (shouldn't happen, but handle gracefully)
                logger.warning("No new questions found but wait node was entered")
                return {
                    "success": True,
                    "input_type": "dm_clarification_answer",
                    "data": {"answers": [], "force_finish": False}
                }

            # Display new questions with agent IDs
            print(f"\nNew questions this round:")
            question_map = {}  # Map question number to agent_id
            for idx, msg in enumerate(new_questions, 1):
                agent_name = self._get_agent_name(msg.from_agent)
                question_map[idx] = msg.from_agent  # Store agent_id
                print(f"  [{idx}] {agent_name}: \"{msg.content}\"")

            print("\nAnswer questions one at a time using format: <number> <answer>")
            print("Examples: '1 About 50 meters', '2 Yes there are'")
            print("Or type 'done' to continue, or 'finish' to skip remaining rounds.")
            print(self.formatter.format_awaiting_dm_input(
                current_phase=GamePhase.DM_CLARIFICATION
            ))

            # Collect answers with agent_id tracking
            answers_dict = {}  # Map agent_id to answer text
            force_finish = False

            while True:
                user_input = input().strip()

                if not user_input:
                    print("Please provide an answer, 'done', or 'finish'")
                    continue

                # Check for commands
                if user_input.lower() == "finish":
                    # DM wants to skip remaining rounds
                    force_finish = True
                    break

                if user_input.lower() in ["done", "continue", "next"]:
                    # DM finished answering this round
                    break

                # Parse numbered answer: "1 answer text"
                parts = user_input.split(maxsplit=1)
                if len(parts) != 2:
                    print("Format: <number> <answer>  (e.g., '1 About 50 meters')")
                    continue

                num_str, answer_text = parts

                try:
                    question_num = int(num_str)
                except ValueError:
                    print(f"Invalid question number: {num_str}. Use format: <number> <answer>")
                    continue

                if question_num not in question_map:
                    print(f"Question {question_num} not found. Available: {list(question_map.keys())}")
                    continue

                # Get agent_id for this question
                agent_id = question_map[question_num]

                # Store answer
                answers_dict[agent_id] = answer_text

                agent_name = self._get_agent_name(agent_id)
                print(f"✓ Answer recorded for {agent_name}")

            if force_finish:
                print(f"\n✓ Skipping remaining clarification rounds. Proceeding to strategy phase...")
            else:
                print(f"\n✓ {len(answers_dict)} answer(s) recorded. Checking for follow-up questions...")

            # Convert answers_dict to list format expected by state machine
            answers_list = [
                {"agent_id": agent_id, "answer": answer_text}
                for agent_id, answer_text in answers_dict.items()
            ]

            return {
                "success": True,
                "input_type": "dm_clarification_answer",
                "data": {
                    "answers": answers_list,
                    "force_finish": force_finish
                }
            }

        elif awaiting_phase == "dm_outcome":
            # Prompt for outcome narration
            print("\n=== DM Outcome Narration Required ===")
            print("Describe what happens as a result of the action.")
            print(self.formatter.format_awaiting_dm_input(
                current_phase=GamePhase.DM_OUTCOME
            ))

            # Read DM narration
            user_input = input().strip()

            if not user_input:
                return {
                    "success": False,
                    "error": "Empty outcome narration",
                    "suggestion": "Describe what happens as a result"
                }

            return {
                "success": True,
                "input_type": "outcome",
                "data": {
                    "outcome_text": user_input
                }
            }

        elif awaiting_phase == "laser_feelings_question":
            # Prompt for LASER FEELINGS answer
            print("\n=== LASER FEELINGS - DM Answer Required ===")
            print("The character rolled LASER FEELINGS and asked a question.")
            print("Provide an honest answer to their question.")
            print(self.formatter.format_awaiting_dm_input(
                current_phase=GamePhase.LASER_FEELINGS_QUESTION
            ))

            # Read DM's answer
            user_input = input().strip()

            if not user_input:
                return {
                    "success": False,
                    "error": "Empty LASER FEELINGS answer",
                    "suggestion": "Provide an honest answer to the character's question"
                }

            return {
                "success": True,
                "input_type": "laser_feelings_answer",
                "data": {
                    "answer": user_input
                }
            }

        else:
            return {
                "success": False,
                "error": f"Unknown phase waiting for input: {awaiting_phase}",
                "suggestion": None
            }


# ============================================================================
# Entry Point (for manual testing)
# ============================================================================


def main():
    """Entry point for running CLI standalone"""
    # Initialize logging
    settings = get_settings()
    setup_logging(log_level=settings.log_level)

    # Initialize Redis connection
    try:
        # Note: decode_responses=False is required for RQ (pickled data)
        # MessageRouter will handle decoding JSON strings manually
        redis_client = Redis.from_url(settings.redis_url)
        redis_client.ping()
        logger.info("Connected to Redis successfully")
    except Exception as e:
        print(f"\nFatal error: Could not connect to Redis: {e}")
        print("Make sure Redis is running via 'docker-compose up -d'")
        sys.exit(1)

    # Clean Redis for fresh session
    cleanup_result = cleanup_redis_for_new_session(redis_client)
    if cleanup_result["success"]:
        print(f"✓ {cleanup_result['message']}")
    else:
        print(f"⚠ Warning: {cleanup_result['message']}")
        print("Continuing with existing Redis data...")

    # Initialize orchestrator
    orchestrator = TurnOrchestrator(redis_client)

    # Initialize CLI with orchestrator
    cli = DMCommandLineInterface(orchestrator=orchestrator)
    cli._campaign_name = "Voyage of the Raptor"
    cli._active_agents = ["agent_alex_001"]  # List of agent IDs, not dicts

    try:
        cli.run()
    except Exception as e:
        print(f"\nFatal error: {e}")
        logger.exception("Fatal error in CLI")
        sys.exit(1)


if __name__ == "__main__":
    main()
