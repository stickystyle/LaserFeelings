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
from src.models.game_state import GamePhase
from src.orchestration.message_router import MessageRouter
from src.orchestration.turn_orchestrator import TurnOrchestrator


class DMTextualInterface(App):
    """Textual TUI for DM Interface - dual-panel layout with game log and OOC discussion"""

    # Command prefix constants
    OVERRIDE_PREFIX = "override "

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
        self._turn_in_progress = False
        self._current_roll_suggestion = None  # Stores pending roll suggestion

        # Clarification questions state
        self._clarification_mode = False
        self._pending_questions = None  # List of question dicts
        self._questions_round = 1

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

        # Set up OOC polling timer (every 2 seconds)
        self.set_interval(2.0, self.update_ooc_log)

        # Update turn status display
        self.update_turn_status()

    def write_game_log(self, content: str) -> None:
        """
        Write message to game log.

        Args:
            content: Rich markup text to display
        """
        log = self.query_one("#game-log", RichLog)
        log.write(content)

    def show_roll_suggestion(self, suggestion: dict) -> None:
        """
        Display interactive dice roll suggestion as a panel with text instructions.

        Args:
            suggestion: Dict with keys:
                - task_type: str (e.g., "Lasers" or "Feelings")
                - prepared_context: str (why player is prepared)
                - suggested_roll: str (e.g., "2d6 Lasers")
                - character_name: str (who's rolling)
                - character_id: str (for routing commands back)
        """
        # Store the current suggestion for button handlers to reference
        self._current_roll_suggestion = suggestion

        # Build the suggestion panel content
        char_name = suggestion.get("character_name", "Unknown")
        task_type = suggestion.get("task_type", "Unknown")
        prepared = suggestion.get("prepared_context", "No context")
        suggested = suggestion.get("suggested_roll", "1d6")

        # Display as interactive panel
        panel_content = (
            f"[bold cyan]{char_name}'s Suggested Roll[/bold cyan]\n"
            f"Task: {task_type}\n"
            f"Prepared: {prepared}\n"
            f"Dice: {suggested}\n"
            f"\n"
            f"[dim]Respond with:[/dim]\n"
            f"  accept    - Accept the suggestion\n"
            f"  override <dice> - Override (e.g., 'override 1d6')\n"
            f"  success   - Auto-success\n"
            f"  fail      - Auto-failure"
        )

        self.write_game_log(panel_content)

    def action_quick_roll(self) -> None:
        """Quick roll action (Ctrl+R)"""
        pass  # Placeholder for Phase 3

    def action_success(self) -> None:
        """Quick success action (Ctrl+S)"""
        pass  # Placeholder for Phase 3

    def action_fail(self) -> None:
        """Quick fail action (Ctrl+F)"""
        pass  # Placeholder for Phase 3

    def action_info(self) -> None:
        """Quick info action (Ctrl+I)"""
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
        """Handle DM command input - includes roll responses and clarification answers"""
        if event.input.id != "dm-input":
            return

        user_input = event.value
        event.input.value = ""  # Clear input

        if not user_input.strip():
            return

        # Check if we're in clarification mode first (highest priority)
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

                # Call orchestrator to skip remaining clarification (run in background thread)
                try:
                    result = await self._run_blocking_call(
                        lambda: self.orchestrator.resume_turn_with_dm_input(
                            session_number=self.session_number,
                            dm_input_type="dm_clarification_answer",
                            dm_input_data={"answers": [], "force_finish": True},
                        )
                    )
                    if result and "phase_completed" in result:
                        self.current_phase = GamePhase(result["phase_completed"])
                except Exception as e:
                    self.write_game_log(f"[red]✗ Error:[/red] {e}")
                    logger.error(f"Force finish clarification failed: {e}")
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
                char_name = self._character_names.get(agent_id, "Unknown")

                # Display confirmation
                self.write_game_log(
                    f"[green]✓ Answer recorded:[/green] {char_name} - {answer_text}"
                )

                # Call orchestrator to record answer (single answer at a time)
                # Run in background thread to keep UI responsive
                try:
                    result = await self._run_blocking_call(
                        lambda: self.orchestrator.resume_turn_with_dm_input(
                            session_number=self.session_number,
                            dm_input_type="dm_clarification_answer",
                            dm_input_data={
                                "answers": [{"agent_id": agent_id, "answer": answer_text}],
                                "force_finish": False,
                            },
                        )
                    )

                    # Simply show success - don't poll for new questions yet
                    # Follow-up questions only appear after user types "done" for current round
                    # This allows the DM to answer multiple questions from the same round
                    self.write_game_log(f"[green]✓ Answer recorded for {char_name}[/green]")

                    if result and "phase_completed" in result:
                        self.current_phase = GamePhase(result["phase_completed"])

                except Exception as e:
                    self.write_game_log(f"[red]✗ Failed to record answer:[/red] {e}")
                    self.write_game_log(
                        "[yellow]Type 'done' or 'finish' to exit clarification mode[/yellow]"
                    )
                    logger.error(f"Answer recording failed: {e}")
                    # Keep mode active so user can retry or exit manually
                    # Don't recurse - let user make next decision
                    return

                return

            except ValueError:
                self.write_game_log(
                    "[red]✗ First part must be a number.[/red] "
                    "Use: [green]<number> <answer>[/green]"
                )
                return

        # Check for roll response commands first (before parsing)
        if user_input.lower() in ["accept", "success", "fail"]:
            if not self._current_roll_suggestion:
                self.write_game_log("[red]✗ No pending roll suggestion[/red]")
                return

            suggestion = self._current_roll_suggestion
            self._current_roll_suggestion = None  # Clear after handling

            if user_input.lower() == "accept":
                # Accept the suggested roll - let dice resolution proceed (run in background)
                try:
                    result = await self._run_blocking_call(
                        lambda: self.orchestrator.resume_turn_with_dm_input(
                            session_number=self.session_number,
                            dm_input_type="adjudication",
                            dm_input_data={
                                "needs_dice": True,
                                # No dice_override - use natural roll
                            },
                        )
                    )

                    self.write_game_log(
                        f"[green]✓ Roll accepted:[/green] {suggestion.get('suggested_roll')}"
                    )

                    # Update turn state if result indicates new phase
                    if result and "phase_completed" in result:
                        self.current_phase = GamePhase(result["phase_completed"])

                except Exception as e:
                    self.write_game_log(f"[red]✗ Failed to execute roll:[/red] {e}")
                    logger.error(f"Roll execution failed: {e}")

            elif user_input.lower() == "success":
                # Force success - bypass dice entirely (run in background)
                try:
                    result = await self._run_blocking_call(
                        lambda: self.orchestrator.resume_turn_with_dm_input(
                            session_number=self.session_number,
                            dm_input_type="adjudication",
                            dm_input_data={
                                "needs_dice": False,
                                "manual_success": True,
                            },
                        )
                    )

                    self.write_game_log(
                        f"[green]✓ Auto-success:[/green] {suggestion.get('character_name')}"
                    )

                    # Update turn state if result indicates new phase
                    if result and "phase_completed" in result:
                        self.current_phase = GamePhase(result["phase_completed"])

                except Exception as e:
                    self.write_game_log(f"[red]✗ Failed to mark success:[/red] {e}")
                    logger.error(f"Force success failed: {e}")

            elif user_input.lower() == "fail":
                # Force failure - bypass dice entirely (run in background)
                try:
                    result = await self._run_blocking_call(
                        lambda: self.orchestrator.resume_turn_with_dm_input(
                            session_number=self.session_number,
                            dm_input_type="adjudication",
                            dm_input_data={
                                "needs_dice": False,
                                "manual_success": False,
                            },
                        )
                    )

                    self.write_game_log(
                        f"[red]✗ Auto-failure:[/red] {suggestion.get('character_name')}"
                    )

                    # Update turn state if result indicates new phase
                    if result and "phase_completed" in result:
                        self.current_phase = GamePhase(result["phase_completed"])

                except Exception as e:
                    self.write_game_log(f"[red]✗ Failed to mark failure:[/red] {e}")
                    logger.error(f"Force failure failed: {e}")

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

                    # Execute with dice override (run in background)
                    result = await self._run_blocking_call(
                        lambda: self.orchestrator.resume_turn_with_dm_input(
                            session_number=self.session_number,
                            dm_input_type="adjudication",
                            dm_input_data={
                                "needs_dice": True,
                                "dice_override": dice_value,
                            },
                        )
                    )

                    self.write_game_log(
                        f"[yellow]⤺ Overridden:[/yellow] {char_name} rolls {override_dice}"
                    )

                    # Update turn state if result indicates new phase
                    if result and "phase_completed" in result:
                        self.current_phase = GamePhase(result["phase_completed"])

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
            # Handle /roll command - show suggestion (Phase 3 feature)
            # For now, show a placeholder message
            self.write_game_log("[dim]Roll suggestions coming soon...[/dim]")
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

            # Keep turn in progress flag set (turn not complete)
            return

        # Display character actions
        if turn_result.get("character_actions"):
            self.write_game_log("[bold]Character Actions:[/bold]")
            for char_id, action_dict in turn_result["character_actions"].items():
                char_name = self._character_names.get(char_id, char_id)
                narrative = action_dict.get("narrative_text", "")
                self.write_game_log(f"  [yellow]{char_name}:[/yellow] {narrative}")

        # Display character reactions
        if turn_result.get("character_reactions"):
            self.write_game_log("[bold]Character Reactions:[/bold]")
            for char_id, reaction in turn_result["character_reactions"].items():
                char_name = self._character_names.get(char_id, char_id)
                self.write_game_log(f"  [yellow]{char_name}:[/yellow] {reaction}")

        # Update state
        self.turn_number += 1
        if turn_result.get("phase_completed"):
            phase_str = turn_result["phase_completed"]
            self.current_phase = GamePhase(phase_str)
        self.update_turn_status()

        self.write_game_log("[green]✓ Turn complete[/green]\n")
        self._turn_in_progress = False  # CLEAR FLAG

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
                agent_name = self._character_names.get(msg.from_agent, msg.from_agent)
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

            # Convert to expected format
            return [
                {
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
            char_name = self._character_names.get(agent_id, "Unknown")
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
