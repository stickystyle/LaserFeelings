# ABOUTME: Textual TUI interface for DM interaction with AI TTRPG players.
# ABOUTME: Provides dual-panel layout with game log and OOC strategic discussion.

import asyncio
from concurrent.futures import ThreadPoolExecutor

from loguru import logger
from textual.app import App, ComposeResult
from textual.containers import Container, Vertical
from textual.reactive import reactive
from textual.widgets import Footer, Header, Input, RichLog, Static

from src.interface.dm_cli import DMCommandParser, DMCommandType, InvalidCommandError
from src.models.dice_models import LasersFeelingRollResult
from src.models.game_state import GamePhase
from src.orchestration.message_router import MessageRouter
from src.orchestration.turn_orchestrator import TurnOrchestrator
from src.utils.dice import roll_dice, roll_lasers_feelings


class DMTextualInterface(App):
    """Textual TUI for DM Interface - dual-panel layout with game log and OOC discussion"""

    # Command prefix constants
    OVERRIDE_PREFIX = "override "
    SUCCESS_MARKER = "✓"

    CSS = """
    #main {
        layout: horizontal;
        height: 1fr;
    }

    .panel {
        border: solid green;
        height: 1fr;
        width: 1fr;
    }

    .panel-title {
        background: green;
        color: white;
        padding: 0 1;
    }

    #game-panel {
        width: 2fr;
    }

    #side-panel {
        width: 1fr;
    }

    #game-log, #ooc-log {
        height: 1fr;
        scrollbar-gutter: stable;
    }

    #dm-input {
        dock: bottom;
        height: 3;
    }

    #turn-status {
        height: 5;
        border: solid blue;
        padding: 1;
    }
    """

    BINDINGS = [
        ("ctrl+q", "quit", "Quit"),
        ("ctrl+r", "quick_roll", "Quick Roll"),
        ("ctrl+s", "success", "Success"),
        ("ctrl+f", "fail", "Fail"),
        ("ctrl+i", "info", "Info"),
    ]

    # Reactive attributes
    turn_number = reactive(1)
    current_phase = reactive(GamePhase.DM_NARRATION)

    def __init__(self, orchestrator: TurnOrchestrator, router: MessageRouter):
        """
        Initialize DM Textual interface.

        Args:
            orchestrator: TurnOrchestrator instance for managing game state
            router: MessageRouter instance for message handling
        """
        super().__init__()
        self.orchestrator = orchestrator
        self.router = router
        self.parser = DMCommandParser()

        # Thread pool for running blocking orchestrator calls
        self._executor = ThreadPoolExecutor(max_workers=2)

        # Session state
        self.session_number = 1
        self._campaign_name = "Unknown Campaign"
        self._active_agents = []
        self._character_names = {}  # Map character_id or agent_id -> name
        self._character_configs = {}  # Map character_id -> full config dict
        self._agent_to_character = {}  # Map agent_id -> character_id
        self._turn_in_progress = False
        self._current_roll_suggestion = None  # Stores pending roll suggestion
        self._current_turn_result = None  # Stores turn state for roll execution

        # Clarification questions state
        self._clarification_mode = False
        self._pending_questions = None  # List of question dicts
        self._questions_round = 1

        # LASER FEELINGS state
        self._laser_feelings_mode = False
        self._pending_laser_feelings_result = None  # LasersFeelingRollResult awaiting answer

        # LASER FEELINGS question state
        self._laser_feelings_question_mode = False
        self._laser_feelings_question_data = None  # Dict with character_id and gm_question

        # Outcome narration state
        self._outcome_narration_mode = False

    async def _run_blocking_call(self, func):
        """
        Run a blocking callable in thread pool without blocking the event loop.

        Args:
            func: Blocking callable to run (use lambda to wrap with args)

        Returns:
            Result from func
        """
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(self._executor, func)

    def _run_blocking_in_background(self, func):
        """
        Start a background task to run a blocking call without awaiting.
        Errors are logged but don't block the UI.

        Args:
            func: Blocking callable to run (use lambda to wrap with args)

        Returns:
            asyncio.Task (you can ignore the return value)
        """

        async def _background_wrapper():
            try:
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(self._executor, func)
            except Exception as e:
                logger.error(f"Background task failed: {e}")

        return asyncio.create_task(_background_wrapper())

    def compose(self) -> ComposeResult:
        """Create layout with dual-panel view"""
        yield Header(show_clock=True, name="AI TTRPG DM Interface")

        with Container(id="main"):
            # Left: Game log and input
            with Vertical(id="game-panel", classes="panel"):
                yield Static("Game Log", classes="panel-title")
                yield RichLog(id="game-log", markup=True, highlight=True)
                yield Input(placeholder="DM > ", id="dm-input")

            # Right: OOC discussion and status
            with Vertical(id="side-panel", classes="panel"):
                yield Static("OOC Strategic Discussion", classes="panel-title")
                yield RichLog(id="ooc-log", markup=True)
                yield Static(id="turn-status")

        yield Footer()

    def on_mount(self) -> None:
        """Called when app is mounted"""
        self.write_game_log("[bold]AI TTRPG DM Interface[/bold]")
        self.write_game_log("[dim]Ready to begin...[/dim]")

        # Load character configurations
        self._load_character_names()
        self._load_agent_to_character_mapping()

        # Set up OOC polling timer (every 2 seconds)
        self.set_interval(2.0, self.update_ooc_log)

        # Update turn status display
        self.update_turn_status()

    def on_unmount(self) -> None:
        """Called when app is unmounted - cleanup resources"""
        logger.debug("Shutting down thread pool executor")
        self._executor.shutdown(wait=True)

    def write_game_log(self, content: str) -> None:
        """
        Write message to game log.

        Args:
            content: Rich markup text to display
        """
        log = self.query_one("#game-log", RichLog)
        log.write(content)

    def show_roll_suggestion(self, action_dict: dict, character_name: str) -> None:
        """
        Display enhanced dice roll suggestion with comprehensive details.

        Args:
            action_dict: ActionDict containing roll suggestions with keys:
                - task_type: str (e.g., "lasers" or "feelings")
                - is_prepared: bool
                - prepared_justification: str
                - is_expert: bool
                - expert_justification: str
                - is_helping: bool
                - helping_character_id: str
                - help_justification: str
            character_name: Name of character making the roll
        """
        # Store for command handlers
        self._current_roll_suggestion = {
            "action_dict": action_dict,
            "character_name": character_name,
        }

        # Build comprehensive suggestion text using helper
        suggestion_text = self._build_dice_suggestion_text(
            action_dict,
            self._get_character_name
        )

        # Display header with character name
        self.write_game_log(f"\n[bold cyan]{character_name}'s Roll Suggestion[/bold cyan]")

        # Display formatted suggestion
        self.write_game_log(suggestion_text)

        # Display response instructions
        self.write_game_log(
            "\n[dim]Respond with:[/dim]\n"
            "  accept    - Accept the suggestion\n"
            "  override <dice> - Override (e.g., 'override 3')\n"
            "  success   - Auto-success\n"
            "  fail      - Auto-failure"
        )

    def action_quick_roll(self) -> None:
        """Quick roll action (Ctrl+R) - accept character-suggested roll"""
        if not self._is_adjudication_phase():
            self.write_game_log(
                "[yellow]⚠ Quick roll only available during adjudication phase[/yellow]"
            )
            logger.debug("Quick roll shortcut rejected: not in adjudication phase")
            return

        logger.info("Quick roll shortcut (Ctrl+R) triggered")
        self._simulate_user_input("accept")

    def action_success(self) -> None:
        """Quick success action (Ctrl+S) - force automatic success"""
        if not self._is_adjudication_phase():
            self.write_game_log(
                "[yellow]⚠ Success only available during adjudication phase[/yellow]"
            )
            logger.debug("Success shortcut rejected: not in adjudication phase")
            return

        logger.info("Success shortcut (Ctrl+S) triggered")
        self._simulate_user_input("success")

    def action_fail(self) -> None:
        """Quick fail action (Ctrl+F) - force automatic failure"""
        if not self._is_adjudication_phase():
            self.write_game_log("[yellow]⚠ Fail only available during adjudication phase[/yellow]")
            logger.debug("Fail shortcut rejected: not in adjudication phase")
            return

        logger.info("Fail shortcut (Ctrl+F) triggered")
        self._simulate_user_input("fail")

    def action_info(self) -> None:
        """Quick info action (Ctrl+I) - show session information"""
        logger.debug("Info shortcut (Ctrl+I) triggered")
        self.show_session_info()

    def update_turn_status(self) -> None:
        """Update turn status panel with current state"""
        status_widget = self.query_one("#turn-status", Static)
        phase_name = self._humanize_phase_name(self.current_phase)

        status_text = (
            f"Campaign: {self._campaign_name}\n"
            f"Session: {self.session_number} | Turn: {self.turn_number}\n"
            f"Phase: {phase_name}\n"
            f"Agents: {len(self._active_agents)}"
        )
        status_widget.update(status_text)

    def show_session_info(self) -> None:
        """Display session info in game log"""
        self.write_game_log("[bold]Session Info:[/bold]")
        self.write_game_log(f"  Campaign: {self._campaign_name}")
        self.write_game_log(f"  Session: {self.session_number}")
        self.write_game_log(f"  Turn: {self.turn_number}")
        phase_name = self._humanize_phase_name(self.current_phase)
        self.write_game_log(f"  Phase: {phase_name}")
        self.write_game_log(f"  Active Agents: {len(self._active_agents)}")

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        """
        Handle DM command input.

        Includes roll responses, clarification answers, and outcome narration.
        """
        if event.input.id != "dm-input":
            return

        user_input = event.value
        event.input.value = ""  # Clear input

        # Check if we're in outcome narration mode first (highest priority)
        if self._outcome_narration_mode:
            outcome_text = user_input.strip()

            # Handle empty outcome
            if not outcome_text:
                self.write_game_log(
                    "[yellow]⚠ Outcome cannot be empty. Please describe what happens.[/yellow]"
                )
                return

            # Display confirmation
            self.write_game_log("[green]✓ Outcome recorded[/green]")

            # Clear outcome mode
            self._outcome_narration_mode = False

            # Resume turn with outcome - fire-and-forget
            self._run_blocking_in_background(
                lambda: self.orchestrator.resume_turn_with_dm_input(
                    session_number=self.session_number,
                    dm_input_type="outcome",
                    dm_input_data={"outcome_text": outcome_text},
                )
            )

            return

        # Check if we're in LASER FEELINGS question mode (second priority)
        # This is the phase where character asks DM a question after rolling LASER FEELINGS
        if self._laser_feelings_question_mode and self._laser_feelings_question_data:
            answer_text = user_input.strip()

            # Handle empty answer
            if not answer_text:
                self.write_game_log(
                    "[yellow]⚠ Answer cannot be empty. Please provide an honest answer.[/yellow]"
                )
                return

            # Display confirmation
            self.write_game_log("[green]✓ Answer recorded[/green]")

            # Clear LASER FEELINGS question mode
            self._laser_feelings_question_mode = False
            self._laser_feelings_question_data = None

            # Resume turn with DM's answer to character's question - fire-and-forget
            self._run_blocking_in_background(
                lambda: self.orchestrator.resume_turn_with_dm_input(
                    session_number=self.session_number,
                    dm_input_type="laser_feelings_answer",
                    dm_input_data={"answer": answer_text},
                )
            )

            return

        # Check if we're in LASER FEELINGS mode (third priority)
        # This is the immediate answer when LASER FEELINGS happens during a roll
        # Don't skip empty input here - we want to show a specific error
        # for empty LASER FEELINGS answers
        if self._laser_feelings_mode and self._pending_laser_feelings_result:
            laser_feelings_answer = user_input.strip()

            # Handle empty answers
            if not laser_feelings_answer:
                self.write_game_log(
                    "[yellow]⚠ Answer cannot be empty. Please provide an answer.[/yellow]"
                )
                return

            # Display confirmation
            self.write_game_log(f"[green]✓ Answer recorded:[/green] {laser_feelings_answer}")

            # Clear LASER FEELINGS mode
            self._laser_feelings_mode = False
            roll_result = self._pending_laser_feelings_result
            self._pending_laser_feelings_result = None

            # Resume turn with roll result + DM's answer - fire-and-forget
            self._run_blocking_in_background(
                lambda: self.orchestrator.resume_turn_with_dm_input(
                    session_number=self.session_number,
                    dm_input_type="adjudication",
                    dm_input_data={
                        "needs_dice": True,
                        "roll_result": roll_result.model_dump(),
                        "laser_feelings_answer": laser_feelings_answer,
                    },
                )
            )

            return

        # Check if we're in clarification mode (second priority)
        if self._clarification_mode and self._pending_questions:
            # Handle "done" command to finish answering questions for this round
            if user_input.lower() == "done":
                self.write_game_log("[green]✓ Done answering questions[/green]")
                self.write_game_log("[dim]Checking for follow-up questions...[/dim]")

                # Poll for follow-up questions after DM finishes current round
                max_wait_time = 5.0  # seconds
                poll_interval = 0.5
                elapsed = 0.0
                new_questions = None

                try:
                    while elapsed < max_wait_time:
                        new_questions = self._fetch_new_clarification_questions()
                        if new_questions:
                            count = len(new_questions)
                            self.write_game_log(
                                f"[yellow]↻ Found {count} follow-up question(s)[/yellow]"
                            )
                            break

                        await asyncio.sleep(poll_interval)
                        elapsed += poll_interval

                    if not new_questions:
                        new_questions = []

                    if new_questions:
                        # Display new round of questions
                        self.show_clarification_questions(
                            {
                                "round": self._questions_round + 1,
                                "questions": new_questions,
                            }
                        )
                    else:
                        self.write_game_log(
                            "[yellow]⤳ No follow-up questions. Clarification complete.[/yellow]"
                        )
                        self._clarification_mode = False
                        self._pending_questions = None

                        # Resume turn with empty answers - signals orchestrator to proceed to
                        # SECOND_MEMORY_QUERY phase (see CLAUDE.md "Clarifying Questions Phase")
                        self._run_blocking_in_background(
                            lambda: self.orchestrator.resume_turn_with_dm_input(
                                session_number=self.session_number,
                                dm_input_type="dm_clarification_answer",
                                dm_input_data={"answers": [], "force_finish": False},
                            )
                        )

                except (ConnectionError, TimeoutError):
                    self.write_game_log(
                        "[red]✗ Cannot continue - connection issue with orchestrator[/red]"
                    )
                    self._clarification_mode = False
                    return

                return

            # Handle "finish" to force end of clarification rounds
            if user_input.lower() == "finish":
                self.write_game_log("[yellow]⊣ Finishing clarification (no more rounds)[/yellow]")
                self._clarification_mode = False
                self._pending_questions = None

                # Signal orchestrator to skip remaining clarification - fire-and-forget
                self._run_blocking_in_background(
                    lambda: self.orchestrator.resume_turn_with_dm_input(
                        session_number=self.session_number,
                        dm_input_type="dm_clarification_answer",
                        dm_input_data={"answers": [], "force_finish": True},
                    )
                )
                return

            # Check for "done" embedded in answer (e.g., "1 done")
            if " done" in user_input.lower():
                self.write_game_log(
                    "[yellow]Hint: Type just 'done' on its own line to exit[/yellow]"
                )

            # Parse answer: "<number> <answer>"
            parts = user_input.split(" ", 1)
            if len(parts) < 2:
                self.write_game_log(
                    "[red]✗ Invalid format.[/red] Use: [green]<number> <answer>[/green]"
                )
                return

            try:
                q_idx = int(parts[0]) - 1
                answer_text = parts[1].strip()

                # Validate answer text is not empty
                if not answer_text:
                    self.write_game_log(
                        "[red]✗ Answer cannot be empty.[/red] [green]Use: <number> <answer>[/green]"
                    )
                    return

                if q_idx < 0 or q_idx >= len(self._pending_questions):
                    self.write_game_log(
                        f"[red]✗ Invalid question number.[/red] "
                        f"Valid range: 1-{len(self._pending_questions)}"
                    )
                    return

                question = self._pending_questions[q_idx]
                agent_id = question.get("agent_id", "unknown")
                char_name = self._get_agent_name(agent_id)

                # Display confirmation immediately before returning to user
                self.write_game_log(
                    f"[green]✓ Answer recorded for {char_name}[/green]"
                )

                # Send answer to orchestrator - fire-and-forget
                # Follow-up questions will be checked when DM types "done"
                try:
                    self._run_blocking_in_background(
                        lambda: self.orchestrator.resume_turn_with_dm_input(
                            session_number=self.session_number,
                            dm_input_type="dm_clarification_answer",
                            dm_input_data={
                                "answers": [{"agent_id": agent_id, "answer": answer_text}],
                                "force_finish": False,
                            },
                        )
                    )
                except Exception as e:
                    logger.error(f"Failed to send answer to orchestrator: {e}")
                    self.write_game_log(
                        f"[red]✗ Failed to send answer: {e}[/red]"
                    )
                    self.write_game_log(
                        "[yellow]⚠ Clarification mode is still active. "
                        "Type 'finish' to exit and continue the game.[/yellow]"
                    )
                    return

                # Return immediately - background polling will show follow-up questions
                return

            except ValueError:
                self.write_game_log(
                    "[red]✗ First part must be a number.[/red] "
                    "Use: [green]<number> <answer>[/green]"
                )
                return

        # Skip empty input for normal commands
        # (LASER FEELINGS and clarification already handled above)
        if not user_input.strip():
            return

        # Check for roll response commands first (before parsing)
        if user_input.lower() in ["accept", "success", "fail"]:
            if not self._current_roll_suggestion:
                self.write_game_log("[red]✗ No pending roll suggestion[/red]")
                return

            suggestion = self._current_roll_suggestion
            self._current_roll_suggestion = None  # Clear after handling

            if user_input.lower() == "accept":
                # Execute the character-suggested roll
                roll_execution = self._execute_character_suggested_roll()

                if not roll_execution.get("success"):
                    # Roll execution failed - display error
                    error_msg = roll_execution.get("error", "Unknown error")
                    suggestion_msg = roll_execution.get("suggestion", "")
                    self.write_game_log(f"[red]✗ Roll failed:[/red] {error_msg}")
                    if suggestion_msg:
                        self.write_game_log(f"[dim]Suggestion: {suggestion_msg}[/dim]")
                    return

                # Roll succeeded - display result
                roll_result = roll_execution["roll_result"]

                # Check if LASER FEELINGS occurred
                if roll_result.has_laser_feelings:
                    # Display special LASER FEELINGS result
                    self._display_lasers_feelings_result(roll_result)

                    # Prompt for DM answer
                    self._prompt_for_laser_feelings_answer(roll_result)

                    # Enter LASER FEELINGS mode and wait for answer
                    self._laser_feelings_mode = True
                    self._pending_laser_feelings_result = roll_result
                    # Input handler will capture the answer and resume turn
                else:
                    # Normal roll - display and resume turn immediately
                    self._display_roll_result(roll_result)

                    # Resume turn with roll result - fire-and-forget
                    self._run_blocking_in_background(
                        lambda: self.orchestrator.resume_turn_with_dm_input(
                            session_number=self.session_number,
                            dm_input_type="adjudication",
                            dm_input_data={
                                "needs_dice": True,
                                "roll_result": roll_result.model_dump(),
                            },
                        )
                    )

            elif user_input.lower() == "success":
                # Force success - bypass dice entirely - fire-and-forget
                self.write_game_log(
                    f"[green]✓ Auto-success:[/green] {suggestion.get('character_name')}"
                )
                self._run_blocking_in_background(
                    lambda: self.orchestrator.resume_turn_with_dm_input(
                        session_number=self.session_number,
                        dm_input_type="adjudication",
                        dm_input_data={
                            "needs_dice": False,
                            "manual_success": True,
                        },
                    )
                )

            elif user_input.lower() == "fail":
                # Force failure - bypass dice entirely - fire-and-forget
                self.write_game_log(
                    f"[red]✗ Auto-failure:[/red] {suggestion.get('character_name')}"
                )
                self._run_blocking_in_background(
                    lambda: self.orchestrator.resume_turn_with_dm_input(
                        session_number=self.session_number,
                        dm_input_type="adjudication",
                        dm_input_data={
                            "needs_dice": False,
                            "manual_success": False,
                        },
                    )
                )

            return

        # Check for override command
        if user_input.lower().startswith(self.OVERRIDE_PREFIX):
            if not self._current_roll_suggestion:
                self.write_game_log("[red]✗ No pending roll suggestion[/red]")
                return

            override_dice = user_input[len(self.OVERRIDE_PREFIX) :].strip()
            suggestion = self._current_roll_suggestion
            self._current_roll_suggestion = None

            char_name = suggestion.get("character_name")

            # Parse override dice value (e.g., "2d6" or just a number)
            try:
                # For Lasers & Feelings, we might get a direct number override
                # The orchestrator expects dice_override as an int (for the single die value)
                # But we also need to validate the format

                # Try to parse as integer first (direct die value override)
                try:
                    dice_value = int(override_dice)
                    if dice_value < 1 or dice_value > 6:
                        raise ValueError("Dice value must be between 1 and 6")

                    # Execute with dice override - fire-and-forget
                    self.write_game_log(
                        f"[yellow]⤺ Overridden:[/yellow] {char_name} rolls {override_dice}"
                    )
                    self._run_blocking_in_background(
                        lambda: self.orchestrator.resume_turn_with_dm_input(
                            session_number=self.session_number,
                            dm_input_type="adjudication",
                            dm_input_data={
                                "needs_dice": True,
                                "dice_override": dice_value,
                            },
                        )
                    )

                except ValueError:
                    # Not a simple integer, might be dice notation like "2d6"
                    # For now, we don't support complex dice notation override
                    # This would require more sophisticated parsing
                    self.write_game_log(
                        f"[red]✗ Invalid override:[/red] Expected single die value (1-6), "
                        f"got '{override_dice}'"
                    )

            except Exception as e:
                self.write_game_log(f"[red]✗ Failed to override roll:[/red] {e}")
                logger.error(f"Roll override failed: {e}")

            return

        # Parse using existing parser
        try:
            parsed = self.parser.parse(user_input)
        except InvalidCommandError as e:
            self.write_game_log(f"[red]✗ Error:[/red] {e}")
            return

        # Validate command for current phase (Task 7)
        is_valid, reason, suggestions = self._is_command_valid_for_phase(parsed.command_type)
        if not is_valid:
            # Display error message with suggestions (Task 8)
            phase_name = self._humanize_phase_name(self.current_phase)
            self.write_game_log(f"[red]✗ Error: Invalid command during {phase_name}[/red]")
            self.write_game_log(f"\n[yellow]ℹ Context: {reason}[/yellow]")

            if suggestions:
                self.write_game_log("\n[cyan]Available commands:[/cyan]")
                for suggestion in suggestions:
                    self.write_game_log(f"  {suggestion}")

            return  # Do not execute invalid command

        # Handle different command types
        if parsed.command_type == DMCommandType.NARRATE:
            if self._turn_in_progress:
                self.write_game_log("[yellow]⟲ Turn already in progress, please wait...[/yellow]")
                return

            self.write_game_log(f"[bold cyan]DM:[/bold cyan] {parsed.args['text']}")
            self._turn_in_progress = True  # SET FLAG
            # Execute turn in background (Phase 2 feature)
            self.run_worker(
                self.execute_turn_worker(parsed.args["text"]),
                name="turn-execution",
                description="Executing turn cycle...",
            )
        elif parsed.command_type == DMCommandType.ROLL:
            # Handle /roll <dice> command - DM override roll
            notation = parsed.args.get("notation")

            if not notation:
                self.write_game_log(
                    "[red]✗ Error:[/red] Roll command requires dice notation (e.g., /roll 2d6+3)"
                )
                return

            # Parse and execute dice roll
            try:
                dice_result = roll_dice(notation)

                # Display roll results
                rolls_str = ", ".join(str(r) for r in dice_result.individual_rolls)
                self.write_game_log(f"[bold]DM Override Roll:[/bold] {notation}")
                self.write_game_log(f"  Rolls: [{rolls_str}]")

                if dice_result.modifier != 0:
                    modifier_str = f"{dice_result.modifier:+d}"
                    self.write_game_log(f"  Modifier: {modifier_str}")

                self.write_game_log(f"  [bold cyan]Total: {dice_result.total}[/bold cyan]")

            except ValueError as e:
                self.write_game_log(f"[red]✗ Invalid dice notation:[/red] {e}")

        elif parsed.command_type == DMCommandType.INFO:
            self.show_session_info()
        elif parsed.command_type == DMCommandType.QUIT:
            self.exit()

    async def execute_turn_worker(self, dm_input: str) -> None:
        """Background worker for turn execution - runs in async context"""
        # Show progress
        self.write_game_log("[dim]▼ AI players are thinking...[/dim]")

        try:
            # Call orchestrator (reuse existing!)
            turn_result = self.orchestrator.execute_turn_cycle(
                dm_input=dm_input,
                active_agents=self._active_agents,
                turn_number=self.turn_number,
                session_number=self.session_number,
            )

            # Update UI directly (we're already in async context with Textual)
            self.display_turn_result(turn_result)

        except Exception as e:
            self.write_game_log(f"[red]✗ Turn execution failed:[/red] {e}")

    def display_turn_result(self, turn_result: dict) -> None:
        """Display results from completed turn or handle pause for DM input"""
        # Store turn result for roll execution
        self._current_turn_result = turn_result

        # Check if graph is paused awaiting DM input
        if turn_result.get("awaiting_dm_input"):
            awaiting_phase = turn_result.get("awaiting_phase")

            # Update phase
            if turn_result.get("phase_completed"):
                phase_str = turn_result["phase_completed"]
                self.current_phase = GamePhase(phase_str)
            self.update_turn_status()

            # Handle different pause types
            if awaiting_phase == "dm_clarification_wait":
                # Fetch and display clarification questions
                self.write_game_log("\n")
                new_questions = self._fetch_new_clarification_questions()
                if new_questions:
                    self.show_clarification_questions(
                        {
                            "round": 1,  # First round when initially pausing
                            "questions": new_questions,
                        }
                    )
                else:
                    self.write_game_log("[dim]Clarification phase but no questions found[/dim]")

            elif awaiting_phase == "dm_adjudication_wait":
                # Display character actions first
                if turn_result.get("character_actions"):
                    self.write_game_log("\n[bold]Character Actions:[/bold]")
                    for char_id, action_dict in turn_result["character_actions"].items():
                        char_name = self._get_character_name(char_id)
                        narrative = action_dict.get("narrative_text", "")
                        self.write_game_log(f"  [yellow]{char_name}:[/yellow] {narrative}")

                        # Show enhanced dice suggestion for this character
                        if action_dict.get("task_type"):
                            self.show_roll_suggestion(action_dict, char_name)

            elif awaiting_phase == "dm_outcome":
                # Display outcome narration prompt
                self._show_outcome_prompt()
                self._outcome_narration_mode = True

            elif awaiting_phase == "laser_feelings_question":
                # Display LASER FEELINGS question prompt
                self._show_laser_feelings_question_prompt(turn_result)
                self._laser_feelings_question_mode = True

            # Keep turn in progress flag set (turn not complete)
            return

        # Display character actions
        if turn_result.get("character_actions"):
            self.write_game_log("[bold]Character Actions:[/bold]")
            for char_id, action_dict in turn_result["character_actions"].items():
                char_name = self._get_character_name(char_id)
                narrative = action_dict.get("narrative_text", "")
                self.write_game_log(f"  [yellow]{char_name}:[/yellow] {narrative}")

        # Display character reactions
        if turn_result.get("character_reactions"):
            self.write_game_log("[bold]Character Reactions:[/bold]")
            for char_id, reaction in turn_result["character_reactions"].items():
                char_name = self._get_character_name(char_id)
                self.write_game_log(f"  [yellow]{char_name}:[/yellow] {reaction}")

        # Update state
        self.turn_number += 1
        if turn_result.get("phase_completed"):
            phase_str = turn_result["phase_completed"]
            self.current_phase = GamePhase(phase_str)
        self.update_turn_status()

        self.write_game_log("[green]✓ Turn complete[/green]\n")
        self._turn_in_progress = False  # CLEAR FLAG
        self._current_turn_result = None  # Clear for next turn

    def update_ooc_log(self) -> None:
        """Poll for new OOC messages and update log"""
        try:
            # Reuse existing router!
            messages = self.router.get_ooc_messages_for_player(limit=50)
            ooc_log = self.query_one("#ooc-log", RichLog)

            # Clear and repopulate
            ooc_log.clear()

            for msg in messages:
                timestamp = msg.timestamp.strftime("%H:%M:%S")
                agent_name = self._get_character_name(msg.from_agent)
                ooc_log.write(f"[dim]{timestamp}[/dim] [bold]{agent_name}:[/bold] {msg.content}")

        except Exception as e:
            # Silently fail for background polling (don't spam error logs)
            logger.debug(f"OOC polling failed: {e}")

    def is_clarification_phase(self) -> bool:
        """Check if we're in a clarification question phase"""
        return self.current_phase == GamePhase.DM_CLARIFICATION

    def _fetch_new_clarification_questions(self) -> list[dict]:
        """
        Fetch new clarification questions from OOC channel.

        Returns:
            List of question dicts with agent_id and question_text
        """
        try:
            # Get recent OOC messages
            ooc_messages = self.router.get_ooc_messages_for_player(limit=100)

            # Filter to clarification phase messages from current turn
            clarification_messages = [
                msg
                for msg in ooc_messages
                if (
                    msg.phase == GamePhase.DM_CLARIFICATION.value
                    and msg.turn_number == self.turn_number
                )
            ]

            if not clarification_messages:
                return []

            # Separate questions from answers
            # Questions are from agents (not "dm")
            # Answers are from "dm"
            questions = [msg for msg in clarification_messages if msg.from_agent != "dm"]
            dm_answers = [msg for msg in clarification_messages if msg.from_agent == "dm"]

            # Find questions that haven't been answered yet
            # Compare timestamps: questions after the last DM answer are new
            from datetime import datetime as dt

            last_answer_time = dt.min
            if dm_answers:
                last_answer_time = max(msg.timestamp for msg in dm_answers)

            new_questions = [msg for msg in questions if msg.timestamp > last_answer_time]

            # Convert to expected format with message_id for tracking
            return [
                {
                    "message_id": msg.message_id,
                    "agent_id": msg.from_agent,
                    "question_text": msg.content,
                }
                for msg in new_questions
            ]

        except (ConnectionError, TimeoutError) as e:
            # These are real connection issues - should fail visibly
            logger.error(f"Connection error fetching questions: {e}")
            self.write_game_log(
                "[red]✗ Connection issue while checking for follow-up questions[/red]"
            )
            raise  # Let caller handle the connection failure
        except KeyError as e:
            # Missing key in OOC message - expected edge case, not an error
            logger.debug(f"Expected key missing in OOC message: {e}")
            return []
        except Exception as e:
            # Unexpected errors - log and fail visibly
            logger.error(f"Unexpected error fetching clarification questions: {e}")
            self.write_game_log(
                "[yellow]⚠ Warning: Unable to check for follow-up questions[/yellow]"
            )
            return []  # Gracefully degrade to "no questions" with visible warning

    def show_clarification_questions(self, questions_data: dict) -> None:
        """
        Display clarifying questions for DM to answer.

        Args:
            questions_data: Dict with:
                - round: int (1, 2, or 3)
                - questions: list of dicts with:
                    - agent_id: str
                    - question_text: str
        """
        round_num = questions_data.get("round", 1)
        questions = questions_data.get("questions", [])

        if not questions:
            self.write_game_log("[dim]No new clarifying questions this round[/dim]")
            return

        # Store questions for answer input handling
        self._pending_questions = questions
        self._questions_round = round_num

        # Display header
        self.write_game_log(
            f"\n[bold cyan]=== Clarifying Questions (Round {round_num}/3) ===[/bold cyan]"
        )

        # List all questions
        self.write_game_log("[dim]New questions this round:[/dim]")
        for idx, q in enumerate(questions, 1):
            agent_id = q.get("agent_id", "unknown")
            char_name = self._get_agent_name(agent_id)
            question_text = q.get("question_text", "")
            self.write_game_log(f"  [{idx}] [yellow]{char_name}:[/yellow] {question_text}")

        # Instructions
        self.write_game_log(
            "\n[dim]Answer questions one at a time using:[/dim]\n"
            "  [green]<number> <answer>[/green] (e.g., '1 Yes, there are guards')\n"
            "  [yellow]done[/yellow] (when finished answering)\n"
            "  [yellow]finish[/yellow] (skip remaining rounds)"
        )

        self._clarification_mode = True

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
            GamePhase.CHARACTER_REFORMULATION: "Character Reformulation",
            GamePhase.DM_ADJUDICATION: "DM Adjudication",
            GamePhase.DICE_RESOLUTION: "Dice Resolution",
            GamePhase.LASER_FEELINGS_QUESTION: "Laser Feelings Question",
            GamePhase.DM_OUTCOME: "DM Outcome",
            GamePhase.CHARACTER_REACTION: "Character Reaction",
            GamePhase.MEMORY_STORAGE: "Memory Storage",
        }
        return name_map.get(phase, phase.value)

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
                            logger.debug(f"Loaded character: {character_id} → {character_name}")
                        else:
                            logger.debug(
                                f"Skipping {config_file.name}: missing required fields "
                                f"(character_id={character_id}, character_name={character_name})"
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
                        else:
                            logger.debug(
                                f"Skipping {config_file.name}: missing required fields "
                                f"(agent_id={agent_id}, character_id={character_id})"
                            )
                except Exception as e:
                    logger.warning(f"Failed to load mapping from {config_file}: {e}")

            logger.info(f"Loaded {len(self._agent_to_character)} agent-to-character mappings")

        except Exception as e:
            logger.error(f"Failed to load agent-to-character mappings: {e}")

    def _display_roll_result(self, roll_result: LasersFeelingRollResult) -> None:
        """
        Display Lasers & Feelings roll result in game log.

        Args:
            roll_result: LasersFeelingRollResult to display
        """
        # Display individual rolls
        rolls_str = ", ".join(str(r) for r in roll_result.individual_rolls)
        self.write_game_log(f"[bold]Rolled {roll_result.dice_count}d6:[/bold] [{rolls_str}]")

        # Display outcome
        outcome_colors = {
            "failure": "red",
            "barely": "yellow",
            "success": "green",
            "critical": "bold green",
        }
        outcome_color = outcome_colors.get(roll_result.outcome.value, "white")
        outcome_text = roll_result.outcome.value.upper()
        self.write_game_log(
            f"[{outcome_color}]Outcome: {outcome_text}[/{outcome_color}] "
            f"({roll_result.total_successes} successes)"
        )

        # Display LASER FEELINGS if applicable
        if roll_result.has_laser_feelings:
            self.write_game_log("[bold magenta]⚡ LASER FEELINGS![/bold magenta]")
            if roll_result.gm_question:
                self.write_game_log(f"[dim]Question: {roll_result.gm_question}[/dim]")

    def _execute_character_suggested_roll(self, character_actions: dict | None = None) -> dict:
        """
        Execute Lasers & Feelings roll using character's suggested parameters.

        Reads action_dict from provided character_actions or current turn state,
        extracts roll modifiers, loads character sheet for character number,
        and calls roll_lasers_feelings().

        Args:
            character_actions: Optional dict of character actions
                (if None, uses self._current_turn_result)

        Returns:
            Dict with success: bool, roll_result: LasersFeelingRollResult or error message
        """
        # Get character actions from parameter or current turn state
        if character_actions is None:
            if not self._current_turn_result:
                return {
                    "success": False,
                    "error": "No turn state available",
                    "suggestion": (
                        "Character roll suggestions are only available during adjudication"
                    ),
                }
            character_actions = self._current_turn_result.get("character_actions", {})

        if not character_actions:
            return {
                "success": False,
                "error": "No character actions available",
                "suggestion": "Use /roll <dice> to specify a dice roll",
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
                "suggestion": "Use /roll <dice> to specify a dice roll",
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
                "suggestion": "Check character configuration files",
            }

        character_number = character_config.get("number")
        if not character_number:
            return {
                "success": False,
                "error": f"Character number missing in config for {character_id}",
                "suggestion": "Check character configuration files",
            }

        # Calculate dice count for display
        dice_count = 1
        dice_count += 1 if is_prepared else 0
        dice_count += 1 if is_expert else 0
        dice_count += 1 if is_helping else 0
        dice_count = min(dice_count, 3)  # Max 3 dice

        # Display using character suggestion
        character_name = self._get_character_name(character_id)
        self.write_game_log(
            f"\n[cyan]Using {character_name}'s suggested roll: "
            f"{dice_count}d6 {task_type.capitalize()}[/cyan]"
        )

        # Execute Lasers & Feelings roll
        try:
            roll_result = roll_lasers_feelings(
                character_number=character_number,
                task_type=task_type,
                is_prepared=is_prepared,
                is_expert=is_expert,
                successful_helpers=0,  # TODO(Phase1-Issue2): Will be populated by helper resolution
                gm_question=gm_question,
            )

            return {"success": True, "roll_result": roll_result}
        except ValueError as e:
            return {
                "success": False,
                "error": f"Roll execution failed: {e}",
                "suggestion": "Check roll parameters",
            }

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
            Agent name (e.g., "Alex") or the agent_id if parsing fails
        """
        if agent_id.startswith("agent_"):
            parts = agent_id.split("_")
            if len(parts) >= 2:
                return parts[1].capitalize()
        return agent_id

    def _display_lasers_feelings_result(self, roll_result: LasersFeelingRollResult) -> None:
        """
        Display Lasers & Feelings roll result with LASER FEELINGS indicator.

        Args:
            roll_result: LasersFeelingRollResult with has_laser_feelings=True
        """
        # Display individual rolls
        rolls_str = ", ".join(str(r) for r in roll_result.individual_rolls)
        task_type_display = roll_result.task_type.capitalize()

        self.write_game_log(
            f"[bold]Lasers & Feelings Roll:[/bold] {roll_result.dice_count}d6 {task_type_display}"
        )
        self.write_game_log(f"  Character Number: {roll_result.character_number}")
        self.write_game_log(f"  Individual Rolls: [{rolls_str}]")
        self.write_game_log(f"  Successes: {roll_result.total_successes}/{roll_result.dice_count}")

        # Display outcome
        outcome_colors = {
            "failure": "red",
            "barely": "yellow",
            "success": "green",
            "critical": "bold green",
        }
        outcome_color = outcome_colors.get(roll_result.outcome.value, "white")
        outcome_text = roll_result.outcome.value.upper()
        self.write_game_log(f"  [{outcome_color}]Outcome: {outcome_text}[/{outcome_color}]")

        # Display LASER FEELINGS if any
        if roll_result.has_laser_feelings:
            lf_indices = ", ".join(str(i + 1) for i in roll_result.laser_feelings_indices)
            self.write_game_log(
                f"  [bold magenta]⚡ LASER FEELINGS on die #{lf_indices}![/bold magenta]"
            )

            # Display GM question if provided
            if roll_result.gm_question:
                self.write_game_log(
                    f'    [dim]Suggested Question: "{roll_result.gm_question}"[/dim]'
                )
            else:
                self.write_game_log(
                    "    [dim](No question suggested - ask the character "
                    "what they want to know)[/dim]"
                )

    def _prompt_for_laser_feelings_answer(self, roll_result: LasersFeelingRollResult) -> str | None:
        """
        Prompt DM for answer to LASER FEELINGS question.

        This method displays the prompt and instructions but doesn't block for input.
        The actual answer will be captured via the normal input handler when DM types it.

        Args:
            roll_result: LasersFeelingRollResult with has_laser_feelings=True

        Returns:
            None (answer will be captured asynchronously via on_input_submitted)
        """
        # Only prompt if LASER FEELINGS occurred
        if not roll_result.has_laser_feelings:
            return None

        # Display prompt based on whether question was suggested
        if roll_result.gm_question:
            self.write_game_log("\n[bold cyan]Answer the character's question:[/bold cyan]")
            self.write_game_log("[dim]Type your answer and press Enter[/dim]")
        else:
            self.write_game_log("\n[bold cyan]What insight does the character gain?[/bold cyan]")
            self.write_game_log("[dim]Type the insight and press Enter[/dim]")

        # Note: We don't actually wait for input here - on_input_submitted will handle it
        return None

    def _show_outcome_prompt(self) -> None:
        """
        Display prompt for DM to provide outcome narration.

        Prompts DM to describe what happens as a result of the action/roll.
        """
        self.write_game_log("\n[bold cyan]=== DM Outcome Narration ===[/bold cyan]")
        self.write_game_log("[dim]Describe what happens based on the roll result:[/dim]")
        self.write_game_log("DM Outcome: ")

    def _show_laser_feelings_question_prompt(self, turn_result: dict) -> None:
        """
        Display prompt for DM to answer character's LASER FEELINGS question.

        This phase occurs after a LASER FEELINGS roll when the character
        asks a question and the DM must provide an honest answer.

        Args:
            turn_result: Turn result containing laser_feelings_data with character_id
                and gm_question
        """
        # Extract character's question from turn result
        laser_feelings_data = turn_result.get("laser_feelings_data", {})
        character_id = laser_feelings_data.get("character_id", "unknown")
        gm_question = laser_feelings_data.get("gm_question")

        # Store for later use in input handler
        self._laser_feelings_question_data = {
            "character_id": character_id,
            "gm_question": gm_question,
        }

        # Get character name for display
        character_name = self._get_character_name(character_id)

        # Display the question prompt
        self.write_game_log("\n[bold cyan]=== LASER FEELINGS Question Response ===[/bold cyan]")

        if gm_question:
            self.write_game_log(f"[yellow]{character_name} asks:[/yellow]")
            self.write_game_log(f'  "{gm_question}"')
            self.write_game_log("\n[dim]Provide your honest answer:[/dim]")
        else:
            self.write_game_log(
                f"[yellow]{character_name}[/yellow] rolled LASER FEELINGS and asked a question."
            )
            self.write_game_log("[dim]Provide your honest answer to their question:[/dim]")

        self.write_game_log("DM Answer: ")

    def _is_command_valid_for_phase(
        self, command_type: DMCommandType
    ) -> tuple[bool, str, list[str]]:
        """
        Check if command is valid for current phase.

        Args:
            command_type: DMCommandType to validate

        Returns:
            Tuple of (is_valid, reason, suggestions):
                - is_valid: True if command can be used in current phase
                - reason: Error message if invalid, empty string if valid
                - suggestions: List of suggested commands if invalid, empty list if valid
        """
        from loguru import logger

        # Info and quit always valid in all phases
        if command_type in (DMCommandType.INFO, DMCommandType.QUIT):
            return (True, "", [])

        # Get current phase (treat None as DM_NARRATION)
        current_phase = self.current_phase or GamePhase.DM_NARRATION

        # Narrate only valid during DM_NARRATION
        if command_type == DMCommandType.NARRATE:
            if current_phase == GamePhase.DM_NARRATION:
                return (True, "", [])
            else:
                phase_name = self._humanize_phase_name(current_phase)
                reason = f"Cannot narrate during {phase_name}. Wait for turn to complete."
                suggestions = self._get_suggestions_for_phase()
                logger.debug(f"Command validation failed: {reason}")
                return (False, reason, suggestions)

        # Roll/Success/Fail only valid during DM_ADJUDICATION or DICE_RESOLUTION
        if command_type in (DMCommandType.ROLL, DMCommandType.SUCCESS, DMCommandType.FAIL):
            if current_phase in (GamePhase.DM_ADJUDICATION, GamePhase.DICE_RESOLUTION):
                return (True, "", [])
            else:
                phase_name = self._humanize_phase_name(current_phase)
                reason = f"Cannot adjudicate during {phase_name}. Wait for character actions first."
                suggestions = self._get_suggestions_for_phase()
                logger.debug(f"Command validation failed: {reason}")
                return (False, reason, suggestions)

        # Unknown command type - allow it (defensive programming)
        logger.warning(f"Unknown command type during validation: {command_type}")
        return (True, "", [])

    def _get_suggestions_for_phase(self) -> list[str]:
        """
        Get helpful command suggestions for current phase.

        Returns:
            List of suggestion strings formatted as bullet points with descriptions
        """
        current_phase = self.current_phase or GamePhase.DM_NARRATION

        # Define suggestions for each phase
        if current_phase == GamePhase.DM_NARRATION:
            return [
                "- narrate <text>  - Describe what happens in the scene",
                "- info  - Show session information",
            ]

        elif current_phase == GamePhase.DM_ADJUDICATION:
            return [
                "- accept  - Accept character's suggested roll",
                "- override <dice>  - Override with specific dice value (1-6)",
                "- success  - Automatic success without rolling",
                "- fail  - Automatic failure without rolling",
                "- /roll <notation>  - Advanced dice roll (e.g., /roll 2d6+3)",
            ]

        elif current_phase == GamePhase.DICE_RESOLUTION:
            return [
                "- accept  - Accept character's suggested roll",
                "- override <dice>  - Override with specific dice value (1-6)",
                "- success  - Automatic success",
                "- fail  - Automatic failure",
            ]

        elif current_phase == GamePhase.DM_OUTCOME:
            return [
                "- <outcome text>  - Describe what happens based on the roll result",
                "- Type outcome and press Enter",
            ]

        elif current_phase == GamePhase.LASER_FEELINGS_QUESTION:
            return [
                "- <answer>  - Provide honest answer to character's question",
                "- Type answer and press Enter",
            ]

        elif current_phase == GamePhase.DM_CLARIFICATION:
            return [
                "- <number> <answer>  - Answer specific question (e.g., '1 Yes, there are guards')",
                "- done  - Finish answering questions for this round",
                "- finish  - Skip remaining clarification rounds",
            ]

        else:
            # Generic suggestions for other phases
            return [
                "- Wait for current phase to complete",
                "- Type 'info' or press Ctrl+I for session information",
            ]

    def _is_adjudication_phase(self) -> bool:
        """
        Check if current phase is an adjudication phase where roll commands are valid.

        Returns:
            True if in DM_ADJUDICATION or DICE_RESOLUTION phase
        """
        return self.current_phase in (GamePhase.DM_ADJUDICATION, GamePhase.DICE_RESOLUTION)

    def _simulate_user_input(self, command: str) -> None:
        """
        Simulate DM typing a command by programmatically triggering input handler.

        This method creates a synthetic input submission event to route keyboard
        shortcuts through the same logic as manual text input.

        Args:
            command: Command string to simulate (e.g., "accept", "success", "fail")
        """
        from textual.widgets import Input

        # Get the input widget
        input_widget = self.query_one("#dm-input", Input)

        # Set the value and trigger submission
        input_widget.value = command
        self.post_message(Input.Submitted(input=input_widget, value=command))

        logger.debug(f"Simulated user input: {command}")

    def _build_dice_suggestion_text(
        self,
        action_dict: dict,
        character_name_resolver
    ) -> str:
        """
        Build formatted dice roll suggestion text matching CLI format.

        Args:
            action_dict: ActionDict containing roll suggestions with keys:
                - task_type: str (e.g., "lasers" or "feelings")
                - is_prepared: bool
                - prepared_justification: str
                - is_expert: bool
                - expert_justification: str
                - is_helping: bool
                - helping_character_id: str
                - help_justification: str
            character_name_resolver: Callable to resolve character_id to name

        Returns:
            Formatted string with comprehensive roll suggestion details
        """
        task_type = action_dict.get("task_type", "")

        lines = ["Dice Roll Suggestion:"]

        # Display task type with explanation
        task_type_display = task_type.capitalize()
        task_description = (
            "logic/tech" if task_type.lower() == "lasers" else "social/emotion"
        )
        lines.append(f"- Task Type: {task_type_display} ({task_description})")

        # Track bonus dice count
        bonus_dice = 0

        # Display prepared flag + justification
        is_prepared = action_dict.get("is_prepared", False)
        prepared_just = action_dict.get("prepared_justification", "")
        if is_prepared:
            bonus_dice += 1
            lines.append(f"- Prepared: {self.SUCCESS_MARKER} \"{prepared_just}\"")

        # Display expert flag + justification
        is_expert = action_dict.get("is_expert", False)
        expert_just = action_dict.get("expert_justification", "")
        if is_expert:
            bonus_dice += 1
            lines.append(f"- Expert: {self.SUCCESS_MARKER} \"{expert_just}\"")

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

            lines.append(f"- Helping {helping_char_name}: {self.SUCCESS_MARKER} \"{help_just}\"")

        # Calculate suggested dice count (1 base + bonuses, max 3)
        total_dice = min(1 + bonus_dice, 3)
        roll_formula = f"{total_dice}d6 {task_type_display}"
        lines.append(f"- Suggested Roll: {roll_formula}")

        return "\n".join(lines)
