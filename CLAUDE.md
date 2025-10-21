# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**ttrpg-ai** is a multi-agent AI system where AI agents play as realistic tabletop RPG players in a game run by a human Dungeon Master. The system uses a **dual-layer architecture** that separates strategic decision-making (the "player") from in-character roleplay (the "character"), mimicking how real people play TTRPGs.

**Game System**: Lasers & Feelings (rules-light sci-fi RPG)
**Primary Goal**: Observe emergent social behaviors and party dynamics over extended gameplay sessions

## Core Architecture

### Dual-Layer Agent Design

Each AI participant consists of two layers:

1. **Player Layer** (`BasePersonaAgent`): Strategic decision-making operating out-of-character
   - Makes tactical decisions based on personality traits (analytical_score, risk_tolerance, etc.)
   - Communicates with other players via OOC (out-of-character) channel
   - Sends private directives to their character via P2C (player-to-character) channel
   - Located in: `src/agents/base_persona.py`

2. **Character Layer** (`CharacterAgent`): In-character roleplay and performance
   - Receives directives from their player
   - Performs actions and reactions in-character via IC (in-character) channel
   - Cannot narrate outcomes (only intents) - DM controls all outcomes
   - Located in: `src/agents/character.py`

### Three-Channel Communication

The system enforces strict message routing via `MessageRouter` (`src/orchestration/message_router.py`):

- **IC (in_character)**: Character dialogue and actions - visible to all characters, summarized for players
- **OOC (out_of_character)**: Player strategy discussions - only players see this
- **P2C (player_to_character)**: Private directives from player to their character - only target character sees

### Clarifying Questions Phase

The system allows AI players to ask the DM clarifying questions after narration before formulating strategy. This mimics real TTRPG gameplay where players ask "How far away is the door?" or "Do I see any guards?"

**Turn Flow with Clarification**:
```
DM_NARRATION → Initial narration
  ↓
MEMORY_QUERY → Players query memories based on narration
  ↓
DM_CLARIFICATION_COLLECT → Players formulate questions (no interrupt)
  ├─ No questions → skip to SECOND_MEMORY_QUERY
  └─ Questions exist → route to DM_CLARIFICATION_WAIT
      ↓
DM_CLARIFICATION_WAIT → Pause for DM to answer (interrupt)
  ├─ DM answers → loop back to COLLECT (for follow-ups)
  └─ Max 3 rounds or DM types "finish" → proceed
  ↓
SECOND_MEMORY_QUERY → Re-query memories with narration + clarifications
  ↓
STRATEGIC_INTENT → Players formulate strategy (now fully informed)
```

**Key Features**:
- **Automatic**: Players automatically decide if they need clarification via LLM
- **Multi-round**: Up to 3 rounds of Q&A to allow follow-up questions
- **Optional**: If no players have questions, phase is skipped automatically
- **Public**: All questions and answers visible on OOC channel to all players
- **DM Control**: DM can force finish to skip remaining rounds

### Memory System (Graphiti + Neo4j)

Memory is graph-based using Graphiti library with Neo4j backend:

- `GraphitiClient` (`src/memory/graphiti_client.py`) wraps Graphiti operations
- Episodes are created per turn with session_number and turn_number metadata
- Queries filter by temporal context and agent_id
- Memory edges have corruption types tracked via `MemoryEdge` model (`src/models/memory_edge.py`)

## Development Commands

### Running Tests

```bash
# All tests
uv run pytest

# Specific test types
uv run pytest tests/unit/ -v           # Unit tests only
uv run pytest tests/contract/ -v       # Contract tests (interface validation)
uv run pytest tests/integration/ -v    # Integration tests (requires infrastructure)

# Run single test
uv run pytest tests/unit/utils/test_dice.py::test_roll_d6 -v

# Show stdout/stderr
uv run pytest -s

# Short traceback
uv run pytest --tb=short
```

### Linting and Formatting

```bash
# Check code style
uv run ruff check .

# Auto-fix issues
uv run ruff check --fix .

# Check specific paths
uv run ruff check src/agents/ tests/

# Auto-fix formatting
uv run ruff format
```

### Infrastructure

The system requires Neo4j and Redis running locally:

**Connection details** (from `.env`):
- Neo4j: `bolt://localhost:7687` (user: neo4j, pass: ttrpgpassword)
- Neo4j Browser: `http://localhost:7474`
- Redis: `localhost:6379`

### Running the CLI

```bash
# Start DM interface (when implemented)
uv run ttrpg-dm --config config/characters.json

# Or via Python module
uv run python -m src.interface.dm_cli --config config/characters.json
```

**Note**: The CLI automatically cleans Redis on startup to ensure a fresh session. This clears all messages, queues, and turn state while preserving Neo4j graph memory.

## Code Organization

```
src/
├── agents/           # Agent implementations (BasePersona, Character)
│   ├── base_persona.py      # Strategic decision-making layer
│   ├── character.py         # In-character roleplay layer
│   ├── llm_client.py        # OpenAI API wrapper
│   └── exceptions.py        # Agent-specific errors
├── config/           # Configuration and prompt templates
│   ├── settings.py          # Pydantic Settings (env vars)
│   └── prompts.py           # LLM prompt templates
├── interface/        # User interfaces
│   └── dm_cli.py            # DM command-line interface
├── memory/           # Memory storage and retrieval
│   ├── graphiti_client.py   # Graphiti/Neo4j wrapper
│   ├── corrupted_temporal.py  # Memory corruption logic
│   └── exceptions.py        # Memory-specific errors
├── models/           # Pydantic data models
│   ├── agent_actions.py     # Action, Reaction, Directive models
│   ├── game_state.py        # Turn state tracking
│   ├── memory_edge.py       # Memory metadata and corruption types
│   ├── messages.py          # Message models and channel routing
│   └── personality.py       # PlayerPersonality, CharacterSheet
├── orchestration/    # Turn coordination and message routing
│   ├── message_router.py    # Three-channel message routing
│   ├── state_machine.py     # Turn cycle state machine (LangGraph)
│   └── exceptions.py        # Orchestration errors
├── utils/            # Shared utilities
│   ├── dice.py              # Lasers & Feelings dice roller
│   ├── logging.py           # Structured logging setup
│   └── redis_cleanup.py     # Redis database cleanup for session initialization
└── workers/          # RQ worker functions
    ├── base_persona_worker.py  # Player decision workers
    ├── character_worker.py     # Character action/reaction workers
    ├── llm_retry.py            # LLM retry decorator
    └── queue_config.py         # RQ queue configuration

tests/
├── conftest.py       # Shared pytest fixtures
├── contract/         # Interface contracts (verify method signatures)
├── integration/      # Cross-component tests (requires infrastructure)
└── unit/             # Isolated component tests (mocked dependencies)

config/               # Runtime configurations
└── personalities/    # Character JSON configurations

specs/001-ai-ttrpg-players/  # Feature specifications
├── spec.md           # Full feature specification
├── plan.md           # Implementation plan
├── tasks.md          # Task tracking
├── data-model.md     # Complete data model reference
└── quickstart.md     # DM quickstart guide
```

## Important Patterns and Rules

### File Headers

All source files MUST start with a 2-line comment explaining the file's purpose:
```python
# ABOUTME: Brief description of what this file does (first line).
# ABOUTME: Additional context or key responsibilities (second line).
```

### Testing Requirements

This project follows **Test-Driven Development (TDD)**:

1. Write failing test first
2. Implement minimal code to pass test
3. Refactor while keeping tests green

**Test Coverage Requirements**:
- **Unit tests**: Test individual functions/methods with mocked dependencies
- **Contract tests**: Verify interface signatures match expected contracts (no implementation testing)
- **Integration tests**: Test cross-component interactions with real infrastructure

All three test types are mandatory. Do not skip any test category.

## Common Workflows

### Adding a New Personality Trait

1. Update `PlayerPersonality` model in `src/models/personality.py`
2. Add trait to fixture in `tests/conftest.py`
3. Update character config schema in `specs/001-ai-ttrpg-players/data-model.md`
4. Add validation tests in `tests/unit/models/`

### Adding a New Message Channel

1. Add enum value to `MessageChannel` in `src/models/messages.py`
2. Add visibility rules to `VISIBILITY_RULES` dict
3. Update `MessageRouter.route_message()` in `src/orchestration/message_router.py`
4. Add contract tests in `tests/contract/test_message_contracts.py`

## References

- Full specification: `specs/001-ai-ttrpg-players/spec.md`
- Data models: `specs/001-ai-ttrpg-players/data-model.md`
- DM quickstart guide: `specs/001-ai-ttrpg-players/quickstart.md`
- Implementation plan: `specs/001-ai-ttrpg-players/plan.md`
- Task tracking: `specs/001-ai-ttrpg-players/tasks.md`
- Game rules: `docs/lasers_and_feelings_rules.md`
