# Textual TUI Framework Research

**Date**: 2025-10-20
**Purpose**: Evaluate Textual Python TUI framework for enhancing DM CLI interface

---

## Executive Summary

**Textual** is a mature, well-designed Python TUI framework that would integrate **very easily** with the existing API. The current architecture has excellent separation of concerns - the `TurnOrchestrator` and `MessageRouter` are UI-agnostic, meaning Textual could be adopted with minimal changes to core logic. **Approximately 80% of existing code could be reused**, with only the presentation layer needing adaptation.

**Bottom Line**: Textual would provide significant UX improvements but requires 2-4 days of development time. Whether it's worth the investment depends on how much time will be spent DMing sessions and whether the project will be demonstrated to others.

---

## Textual Framework Overview (2025)

### What is Textual?

Textual is a Rapid Application Development framework for Python that lets you build sophisticated user interfaces with a simple Python API. Apps run in the terminal or a web browser.

**Repository**: https://github.com/Textualize/textual
**Documentation**: https://textual.textualize.io/
**Maintained by**: Textualize.io (creators of Rich)

### Core Features

- **Rich Widget Library**: Buttons, inputs, text areas, panels, tables, progress bars, spinners, tree controls
- **Layout System**: Vertical, horizontal, and grid layouts with CSS-like styling
- **AsyncIO Native**: Built on `asyncio`, perfect for existing architecture
- **Event-Driven**: Message passing between widgets, reactive programming support
- **Worker API**: Background tasks with progress tracking (perfect for LLM API calls)
- **Testing Support**: Full pytest integration with snapshot testing
- **Cross-Platform**: Linux, macOS, Windows; works over SSH
- **Modern Terminal Features**: 16.7 million colors, mouse support, smooth flicker-free animations
- **Web Deployment**: Can run in browser as well as terminal
- **Built on Rich**: Inherits Rich's capabilities for beautiful text formatting and syntax highlighting

### Installation

```bash
uv add textual
```

---

## Key Widgets for DM CLI Use Case

### 1. RichLog
Scrollable log widget with Rich markup support - perfect for game log and OOC discussion.

```python
from textual.widgets import RichLog

log = RichLog(markup=True, highlight=True)
log.write("[bold cyan]DM:[/bold cyan] The ship shudders violently")
log.write("[green]✓[/green] Roll succeeded!")
```

### 2. Input/TextArea
Command input with event handling.

```python
from textual.widgets import Input

input_widget = Input(placeholder="DM > ")

@on(Input.Submitted, "#dm-input")
async def handle_input(self, event: Input.Submitted):
    command = event.value
    # Process command
```

### 3. Panels/Containers
Multi-column layouts for simultaneous IC/OOC views.

```python
from textual.containers import Vertical, Horizontal

with Horizontal():
    with Vertical(id="left"):
        yield RichLog(id="game-log")
    with Vertical(id="right"):
        yield RichLog(id="ooc-log")
```

### 4. Progress/Spinner
Show LLM API progress instead of blocking waits.

```python
from textual.widgets import ProgressBar

progress = ProgressBar(total=100)
progress.advance(25)  # 25% complete
```

### 5. Command Palette
Built-in command launcher (Ctrl+P style) for quick access to commands.

---

## Benefits for DM CLI Interface

### 1. Multi-Panel Layout ⭐⭐⭐

**Current**: OOC summary only shown at end of turn
**Textual**: Live OOC panel updating as agents strategize

```
┌─────────────────────────────────────┬────────────────────────┐
│ Game Log (IC)                       │ OOC Strategy           │
│                                     │                        │
│ Zara-7: "I'll repair the engines"  │ Alex: "Focus on tech   │
│ [Roll: 1d6 Lasers] → Success!      │ tasks, Zara is our     │
│                                     │ best bet"              │
│ DM: The engines roar back to life  │                        │
│                                     │ ────────────────────── │
│                                     │ Turn 3 │ Narration    │
│                                     │ Phase  │ Phase        │
└─────────────────────────────────────┴────────────────────────┘
DM > _
```

This would give **real-time visibility** into AI player strategic thinking, valuable for research goals.

### 2. Visual Phase Tracking

**Current**: Text line `[Turn 1] Phase: Character Action`
**Textual**: Color-coded progress bar through turn phases with current phase highlighted

### 3. Character Status Dashboard

Display all characters simultaneously:
- Character names, Lasers/Feelings numbers
- Current goals
- Equipment
- Memory corruption state

### 4. Interactive Dice Roll Suggestions

**Current**:
```
Dice Roll Suggestion:
- Task Type: Lasers (logic/tech)
- Prepared: ✓ "I studied the engine schematics"
- Suggested Roll: 2d6 Lasers
```

**Textual**:
```
┌─ Zara-7's Suggested Roll ──────────────────┐
│ Task: Lasers (logic/tech)                  │
│ ✓ Prepared: "I studied the schematics"     │
│ Dice: 2d6                                  │
│                                            │
│ [Accept] [Override] [Auto-Success] [Fail] │
└────────────────────────────────────────────┘
```

Click buttons instead of typing commands.

### 5. Streaming LLM Responses

**Current**: Blocking wait with no feedback
**Textual**: Show spinner/progress while OpenAI processes

```
▼ Alex is thinking... [====------] 40%
```

### 6. Command Palette

Built-in quick launcher (Ctrl+P):
- `/roll` → Roll Dice
- `/success` → Mark Success
- `/fail` → Mark Failure
- `/info` → Show Session Info

---

## Integration Analysis

### Current Architecture ✓

The existing design has **excellent separation of concerns**:

```
┌──────────────────────┐
│ DMCommandLineInterface│  ← Only this layer needs changes
└──────────────────────┘
          ↓
┌──────────────────────┐
│  TurnOrchestrator    │  ← No changes needed
│  MessageRouter       │  ← No changes needed
│  DMCommandParser     │  ← Reusable as-is!
│  CLIFormatter        │  ← Adaptable (return Rich markup)
└──────────────────────┘
```

### Reusable Components (80%)

- ✓ `TurnOrchestrator` - No changes
- ✓ `MessageRouter` - No changes
- ✓ `DMCommandParser` - Reuse as-is
- ✓ `CLIFormatter` - Adapt methods to return Rich markup strings
- ✓ All game logic, state management, Redis operations

### New Code Required (20%)

- ✗ Textual App class (compose method, event handlers)
- ✗ Widget layout and styling
- ✗ Worker functions for async operations
- ✗ Tests for Textual components

### API Compatibility

The orchestrator exposes clean interfaces that work perfectly with Textual's async model:

```python
# These calls work without modification
turn_result = orchestrator.execute_turn_cycle(
    dm_input=text,
    active_agents=agents,
    turn_number=turn,
    session_number=session
)

turn_result = orchestrator.resume_turn_with_dm_input(
    session_number=session,
    dm_input_type=type,
    dm_input_data=data
)

messages = router.get_ooc_messages_for_player(limit=100)
```

All of these can be called from Textual event handlers or workers without modification.

---

## Example Integration Code

### Basic Textual App Structure

```python
from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, RichLog, Input, Static
from textual.containers import Container, Vertical, Horizontal
from textual.reactive import reactive

from src.orchestration.state_machine import TurnOrchestrator
from src.orchestration.message_router import MessageRouter
from src.interface.dm_cli import DMCommandParser, InvalidCommandError, DMCommandType
from src.models.game_state import GamePhase


class DMTextualInterface(App):
    """Textual TUI for DM Interface"""

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
        super().__init__()
        self.orchestrator = orchestrator
        self.router = router
        self.parser = DMCommandParser()  # Reuse existing!
        self.session_number = 1
        self._active_agents = []
        self._campaign_name = "Voyage of the Raptor"
        self._character_names = {}

    def compose(self) -> ComposeResult:
        """Create layout"""
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
        self.write_game_log(f"[bold]Campaign:[/bold] {self._campaign_name}")
        self.write_game_log("[dim]Session starting...[/dim]")
        self.update_turn_status()

        # Start background task to poll OOC messages
        self.set_interval(2.0, self.update_ooc_log)

    @on(Input.Submitted, "#dm-input")
    async def handle_dm_input(self, event: Input.Submitted):
        """Handle DM command input"""
        user_input = event.value
        event.input.value = ""  # Clear input

        if not user_input.strip():
            return

        # Parse using existing parser!
        try:
            parsed = self.parser.parse(user_input)
        except InvalidCommandError as e:
            self.write_game_log(f"[red]✗ Error:[/red] {e}")
            return

        # Handle different command types
        if parsed.command_type == DMCommandType.NARRATE:
            self.write_game_log(f"[bold cyan]DM:[/bold cyan] {parsed.args['text']}")

            # Execute turn in background worker (non-blocking!)
            self.run_worker(
                self.execute_turn_worker(parsed.args['text']),
                name="turn-execution",
                description="Executing turn cycle..."
            )

        elif parsed.command_type == DMCommandType.INFO:
            self.show_session_info()

        elif parsed.command_type == DMCommandType.QUIT:
            self.exit()

    async def execute_turn_worker(self, dm_input: str):
        """Background worker for turn execution"""
        # Show progress
        self.write_game_log("[dim]▼ AI players are thinking...[/dim]")

        try:
            # Call orchestrator (reuse existing!)
            turn_result = self.orchestrator.execute_turn_cycle(
                dm_input=dm_input,
                active_agents=self._active_agents,
                turn_number=self.turn_number,
                session_number=self.session_number
            )

            # Update UI from worker thread safely
            self.call_from_thread(self.display_turn_result, turn_result)

        except Exception as e:
            self.call_from_thread(
                self.write_game_log,
                f"[red]✗ Turn execution failed:[/red] {e}"
            )

    def display_turn_result(self, turn_result: dict):
        """Display results from completed turn"""
        # Display character actions
        if turn_result.get("character_actions"):
            self.write_game_log("\n[bold]Character Actions:[/bold]")
            for char_id, action_dict in turn_result["character_actions"].items():
                char_name = self._character_names.get(char_id, char_id)
                narrative = action_dict.get("narrative_text", "")
                self.write_game_log(f"  [yellow]{char_name}:[/yellow] {narrative}")

        # Display character reactions
        if turn_result.get("character_reactions"):
            self.write_game_log("\n[bold]Character Reactions:[/bold]")
            for char_id, reaction_dict in turn_result["character_reactions"].items():
                char_name = self._character_names.get(char_id, char_id)
                reaction = reaction_dict.get("narrative_text", "")
                self.write_game_log(f"  [yellow]{char_name}:[/yellow] {reaction}")

        # Update state
        self.turn_number += 1
        self.current_phase = GamePhase(turn_result['phase_completed'])
        self.update_turn_status()

        self.write_game_log("[green]✓ Turn complete[/green]\n")

    def write_game_log(self, content: str):
        """Write to game log"""
        log = self.query_one("#game-log", RichLog)
        log.write(content)

    def update_ooc_log(self):
        """Poll for new OOC messages and update log"""
        try:
            # Reuse existing router!
            messages = self.router.get_ooc_messages_for_player(limit=50)
            ooc_log = self.query_one("#ooc-log", RichLog)

            # Clear and repopulate (simple approach)
            ooc_log.clear()

            for msg in messages:
                timestamp = msg.timestamp.strftime("%H:%M:%S")
                agent_name = self._character_names.get(msg.from_agent, msg.from_agent)
                ooc_log.write(
                    f"[dim]{timestamp}[/dim] [bold]{agent_name}:[/bold] {msg.content}"
                )

        except Exception as e:
            # Silently fail for background polling
            pass

    def update_turn_status(self):
        """Update turn status display"""
        status = self.query_one("#turn-status", Static)
        phase_name = self.current_phase.value.replace("_", " ").title()

        status.update(
            f"[bold]Turn:[/bold] {self.turn_number}\n"
            f"[bold]Session:[/bold] {self.session_number}\n"
            f"[bold]Phase:[/bold] {phase_name}"
        )

    def show_session_info(self):
        """Display session information"""
        info = (
            f"[bold cyan]Session Information[/bold cyan]\n"
            f"Campaign: {self._campaign_name}\n"
            f"Session: {self.session_number}\n"
            f"Turn: {self.turn_number}\n"
            f"Phase: {self.current_phase.value}\n"
            f"Active Agents: {len(self._active_agents)}"
        )
        self.write_game_log(info)

    def action_quick_roll(self):
        """Quick roll action (Ctrl+R)"""
        self.query_one("#dm-input", Input).value = "/roll "
        self.query_one("#dm-input", Input).focus()

    def action_success(self):
        """Quick success action (Ctrl+S)"""
        self.query_one("#dm-input", Input).value = "success"
        self.query_one("#dm-input", Input).action_submit()

    def action_fail(self):
        """Quick fail action (Ctrl+F)"""
        self.query_one("#dm-input", Input).value = "fail"
        self.query_one("#dm-input", Input).action_submit()

    def action_info(self):
        """Quick info action (Ctrl+I)"""
        self.show_session_info()


# Entry point
def main():
    """Run Textual DM interface"""
    from src.config.settings import get_settings
    from redis import Redis

    settings = get_settings()
    redis_client = Redis.from_url(settings.redis_url)

    orchestrator = TurnOrchestrator(redis_client)
    router = MessageRouter(redis_client)

    app = DMTextualInterface(orchestrator, router)
    app._active_agents = ["agent_alex_001"]
    app.run()


if __name__ == "__main__":
    main()
```

### CSS Styling Example

Textual uses CSS-like syntax for styling:

```css
/* Save as dm_textual.tcss */

Screen {
    background: $surface;
}

#main {
    layout: horizontal;
    height: 1fr;
}

.panel {
    border: solid $accent;
    height: 1fr;
    width: 1fr;
}

.panel-title {
    background: $accent;
    color: $text;
    padding: 0 1;
    text-style: bold;
}

#game-panel {
    width: 2fr;  /* 2/3 of screen */
}

#side-panel {
    width: 1fr;  /* 1/3 of screen */
}

#game-log, #ooc-log {
    height: 1fr;
    scrollbar-gutter: stable;
    border: solid $primary;
}

#dm-input {
    dock: bottom;
    height: 3;
    border: solid $success;
}

#turn-status {
    height: 8;
    border: solid $secondary;
    padding: 1;
}
```

---

## Testing with Textual

Textual has excellent pytest integration:

```python
import pytest
from textual.pilot import Pilot

from src.interface.dm_textual import DMTextualInterface


@pytest.mark.asyncio
async def test_dm_input_narration(mock_orchestrator, mock_router):
    """Test narration command through Textual interface"""
    app = DMTextualInterface(mock_orchestrator, mock_router)

    async with app.run_test() as pilot:
        # Type narration
        await pilot.press("T", "h", "e", " ", "s", "h", "i", "p", " ", "s", "h", "a", "k", "e", "s")
        await pilot.press("enter")

        # Verify it was logged
        game_log = app.query_one("#game-log", RichLog)
        assert "The ship shakes" in game_log.lines


@pytest.mark.asyncio
async def test_keyboard_shortcuts(mock_orchestrator, mock_router):
    """Test keyboard shortcuts work"""
    app = DMTextualInterface(mock_orchestrator, mock_router)

    async with app.run_test() as pilot:
        # Press Ctrl+R for quick roll
        await pilot.press("ctrl+r")

        # Verify input field has /roll
        dm_input = app.query_one("#dm-input", Input)
        assert dm_input.value == "/roll "


async def test_snapshot(snap_compare):
    """Snapshot test for visual regression"""
    app = DMTextualInterface(mock_orchestrator, mock_router)
    assert await snap_compare(app)
```

---

## Drawbacks & Considerations

### 1. Development Time Investment

2-4 days to implement and test. For a research project, this might not be justified unless planning extensive DM sessions.

### 2. Added Dependency

`textual` becomes a required dependency. However, it's mature, actively maintained (recent tutorials published May 2025), and has no major known issues.

### 3. Testing Complexity

Textual apps are more complex to test than simple CLI:
- Need to use `textual.testing` utilities
- Snapshot testing adds complexity
- More integration test surface area

However, Textual has **good pytest support** and testing tools.

### 4. Learning Curve

Need to learn Textual's API:
- Widget composition
- Event handling
- CSS-like styling
- Worker API

However, the API is well-documented with many examples.

### 5. Current CLI Works Fine

The current implementation is functional, simple, and aligns with the "rules-light" philosophy of Lasers & Feelings. The print/input approach is battle-tested and easy to reason about.

### 6. Maintenance Overhead

More code = more to maintain. The Textual version would be ~300-400 lines vs current ~1400 lines, but those 300-400 lines are denser and require understanding Textual's lifecycle.

---

## Migration Complexity

### Complexity: Low-Medium 🟢

**Time Estimate**:
- **Basic migration** (feature parity): **2 days**
  - Day 1: Set up Textual app, basic layout, input handling
  - Day 2: Integrate orchestrator, test turn cycle

- **Enhanced UX** (multi-panel, buttons, progress): **+1-2 days**
  - OOC live panel
  - Character status dashboard
  - Interactive dice roll buttons
  - Progress indicators

**Total**: 2-4 days depending on desired feature set

---

## Recommendation

### Short Answer

Textual would be a **nice upgrade** but **not essential**.

### Decision Framework

**Choose Textual if**:
- ✓ Planning to run many DM sessions (>10 hours total)
- ✓ Will be demonstrating this project to others
- ✓ Real-time OOC visibility would enhance research insights
- ✓ Want to learn Textual as a skill
- ✓ Value polish and UX

**Stick with current CLI if**:
- ✓ Want to ship quickly and focus on AI behavior research
- ✓ The simple interface aligns with minimalist philosophy
- ✓ Testing complexity is a concern
- ✓ Prefer explicit, linear code flow
- ✓ 2-4 days feels like too much time investment

### Middle-Ground Option 🎯

Build Textual as an **optional alternative interface**:

```
src/interface/
├── dm_cli.py          # Keep existing (default)
├── dm_textual.py      # New Textual version (opt-in)
└── __init__.py

# Usage:
uv run ttrpg-dm --interface=cli      # Current
uv run ttrpg-dm --interface=textual  # New
```

This gives:
- ✓ Flexibility to choose based on session needs
- ✓ Learning opportunity without full commitment
- ✓ Ability to compare UX in real sessions
- ✓ Gradual migration path

---

## Next Steps

If proceeding with Textual:

### 1. Quick Prototype (2 hours)

```bash
uv add textual

# Create minimal proof-of-concept
cat > src/interface/dm_textual_prototype.py << 'EOF'
from textual.app import App
from textual.widgets import Header, Footer, RichLog, Input

class DMPrototype(App):
    def compose(self):
        yield Header()
        yield RichLog(markup=True)
        yield Input(placeholder="DM > ")
        yield Footer()

    def on_input_submitted(self, event):
        log = self.query_one(RichLog)
        log.write(f"[cyan]You typed:[/cyan] {event.value}")
        event.input.value = ""

if __name__ == "__main__":
    DMPrototype().run()
EOF

uv run python src/interface/dm_textual_prototype.py
```

### 2. Validate Workflow (1 hour)

- Run a single turn through Textual interface
- Verify orchestrator integration works smoothly
- Test keyboard shortcuts and widgets

### 3. Decide (5 minutes)

- Does the UX improvement justify the time?
- If yes → proceed with full migration
- If no → stick with current CLI

---

## Resources

### Official Documentation

- **Main Site**: https://textual.textualize.io/
- **GitHub**: https://github.com/Textualize/textual
- **Tutorial**: https://textual.textualize.io/tutorial/
- **Widget Gallery**: https://textual.textualize.io/widget_gallery/
- **Testing Guide**: https://textual.textualize.io/guide/testing/
- **Workers API**: https://textual.textualize.io/guide/workers/

### Tutorials and Examples

- **Real Python Tutorial (March 2025)**: https://realpython.com/python-textual/
- **Chat Application Example**: https://arjancodes.com/blog/textual-python-library-for-creating-interactive-terminal-applications/
- **ArjanCodes Guide**: https://arjancodes.com/blog/textual-python-library-for-creating-interactive-terminal-applications/

### Related Tools

- **Rich** (underlying library): https://github.com/Textualize/rich
- **pytest-textual**: Testing utilities
- **textual-inputs**: Extended input widgets

---

## Conclusion

Textual is a powerful, well-designed framework that would integrate smoothly with the existing DM CLI architecture. The clean separation of concerns in the current codebase means ~80% of code is reusable. However, the 2-4 day investment should be weighed against project priorities.

**Recommended approach**: Start with a 2-hour prototype to validate the UX improvement justifies the time investment, then decide whether to proceed with full migration or keep the existing simple CLI.
