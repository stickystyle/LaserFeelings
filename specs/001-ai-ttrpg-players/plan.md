# Implementation Plan: AI TTRPG Player System

**Branch**: `001-ai-ttrpg-players` | **Date**: 2025-10-18 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/001-ai-ttrpg-players/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/commands/plan.md` for the execution workflow.

## Summary

Build a multi-agent AI system where AI agents play as realistic tabletop RPG players in a game run by a human Dungeon Master. The system uses a dual-layer architecture separating strategic decision-making (the "player") from in-character roleplay (the "character"), mimicking how real people play TTRPGs. The primary goal is to observe emergent social behaviors and party dynamics that arise when multiple AI agents interact over extended gameplay sessions.

**Technical Approach**: LangGraph-based multi-agent orchestration with Neo4j graph memory for relationship tracking, OpenAI GPT-4o for agent intelligence, and turn-based CLI interface. MVP focuses on single AI player with strict narrative control validation, followed by multi-agent coordination features.

## Technical Context

**Language/Version**: Python 3.11+ (for performance and typing improvements)
**Primary Dependencies**: LangGraph 0.2.x (agent orchestration), Graphiti (latest - graph-based memory), OpenAI GPT-4o API (agent intelligence), Pydantic 2.x (data validation)
**Storage**: Neo4j 5.x (graph database for memory relationships and temporal tracking), Redis 7.x (task queue state), local JSON files (character configurations)
**Testing**: pytest (unit/integration), pytest-asyncio (async test support), contract testing for LangGraph node interfaces
**Target Platform**: Local development machine (macOS/Linux), Python CLI application
**Project Type**: Single project (CLI tool with agent orchestration backend)
**Performance Goals**:
- Turn execution <10s P95 when LLM APIs responsive (not critical for research)
- Memory retrieval <2s for queries
- Context window management at 80% token threshold
**Constraints**:
- LLM API retry: 2s, 5s, 10s exponential backoff (max 5 attempts in ~35s)
- Target token budget: <5000 tokens per turn cycle
- Session length: 2-4 hours typical
- Concurrent AI players: 3-4 maximum
**Scale/Scope**:
- Single DM, single game instance
- 100+ turn cycles per session
- 10+ sessions per campaign
- Memory store growing over months

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Core Principles Compliance

**I. Code Quality & Maintainability**: ✅ PASS
- All code files will include ABOUTME comments
- Simple, maintainable solutions prioritized over clever abstractions
- LangGraph provides structure without custom complexity
- Clear naming for player/character layers prevents confusion

**II. Testing Standards (TDD)**: ✅ PASS
- TDD workflow enforced for all implementation
- Unit tests: Individual agent nodes, validation logic, memory queries
- Integration tests: Turn phase sequences, multi-agent coordination
- End-to-end tests: Complete game sessions from DM input to AI response
- Contract tests: LangGraph node interfaces, LLM API interactions

**III. User Experience Consistency**: ✅ PASS
- Turn-based prompts provide consistent DM interaction pattern
- Error messages standardized across validation failures
- Clear phase transitions visible to DM
- Edge cases documented with explicit handling strategies

**IV. Performance & Scalability**: ⚠️ CONSIDERATION
- Performance targets documented but marked "not critical for research"
- LLM API latency dominates response time (acceptable for research goals)
- Memory retrieval performance tracked but not optimized prematurely
- **Justification**: Research focus allows flexible timing; optimize only if experiments are blocked by latency

### Quality Gates Readiness

**GATE 1 (Constitution Check)**: ✅ Ready for Phase 0 research
**GATE 2 (Test Completeness)**: Pending implementation
**GATE 3 (User Story Validation)**: Pending implementation
**GATE 4 (Feature Completion)**: Pending implementation

### Violations & Justifications

None. All constitutional principles are satisfied or explicitly addressed.

## Project Structure

### Documentation (this feature)

```
specs/001-ai-ttrpg-players/
├── spec.md              # Feature specification (completed)
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (in progress)
├── data-model.md        # Phase 1 output (pending)
├── quickstart.md        # Phase 1 output (pending)
├── contracts/           # Phase 1 output (pending)
└── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
```

### Source Code (repository root)

```
src/
├── agents/              # LangGraph agent definitions
│   ├── player_agent.py      # Strategic decision-making layer
│   ├── character_agent.py   # In-character roleplay layer
│   └── validation_agent.py  # Narrative overreach detection
├── orchestration/       # Turn phase state machines
│   ├── turn_graph.py        # LangGraph turn cycle definition
│   ├── phases.py            # Individual phase implementations
│   └── consensus.py         # Multi-agent coordination logic
├── memory/              # Graphiti memory integration
│   ├── store.py             # Neo4j graph memory operations
│   ├── queries.py           # Memory retrieval patterns
│   └── compression.py       # Context window management
├── game/                # Game mechanics
│   ├── dice.py              # 1d6 roller with DM override
│   ├── character.py         # Lasers & Feelings character state
│   └── validation.py        # Outcome language detection
├── cli/                 # Command-line interface
│   ├── prompts.py           # Turn-based prompt system
│   ├── session.py           # Session management
│   └── commands.py          # DM command handlers
└── config/              # Configuration management
    ├── loader.py            # characters.json parser
    └── schemas.py           # Pydantic models for validation

tests/
├── unit/                # Isolated component tests
│   ├── test_agents.py
│   ├── test_validation.py
│   ├── test_memory.py
│   └── test_dice.py
├── integration/         # Multi-component interaction tests
│   ├── test_turn_cycle.py
│   ├── test_consensus.py
│   └── test_memory_integration.py
├── contract/            # LangGraph node contract tests
│   ├── test_agent_contracts.py
│   └── test_phase_contracts.py
└── e2e/                 # Full session tests
    ├── test_single_player.py
    └── test_multi_agent.py

config/
└── characters.example.json  # Example character configuration

docs/
└── lasers_and_feelings_rpg.pdf  # Game rules reference
```

**Structure Decision**: Single project structure chosen because:
- Unified Python codebase with clear separation of concerns
- No frontend/backend split (CLI-only interface)
- Agent, orchestration, memory, game mechanics, and CLI layers cleanly separated
- Tests mirror source structure for discoverability
- Configuration externalized to JSON for DM accessibility

## Complexity Tracking

*No constitutional violations requiring justification*

---

## Phase 0: Research & Unknowns Resolution

**Status**: Complete ✅

The following unknowns need research to resolve NEEDS CLARIFICATION items:

### Research Tasks

1. **LangGraph Agent Orchestration Patterns**
   - How to structure dual-layer (player/character) agents in LangGraph?
   - Best practices for turn-based state machine with rollback/retry?
   - How to implement validation loops with retry limits?

2. **Graphiti Memory Integration**
   - How does Graphiti integrate with Neo4j for temporal graph memory?
   - Best practices for separating player vs character knowledge stores?
   - Query patterns for relationship-aware memory retrieval?

3. **OpenAI GPT-4o for Consistent Personas**
   - Prompt engineering patterns for stable character personalities?
   - How to prevent LLM "narrative overreach" (generating outcomes)?
   - Token budget management strategies for long sessions?

4. **Neo4j Schema Design for TTRPG Memory**
   - Node types for NPCs, events, locations, relationships?
   - How to model temporal context (session numbers, in-game time)?
   - Indexing strategy for memory queries at 80% token threshold?

5. **Redis Queue Management with RQ**
   - How to persist turn phase state for crash recovery?
   - Retry logic integration with exponential backoff?
   - Worker management for async LLM API calls?

**Output**: ✅ research.md created with decisions, rationale, and alternatives for each research task

---

## Phase 1: Design & Contracts

**Status**: Complete ✅

### Delivered Artifacts ✅

1. **data-model.md**: ✅ Entity definitions complete
   - AIPlayer (base persona with personality traits)
   - AICharacter (performer with in-game personality)
   - Memory (episodic/semantic/procedural with confidence scores)
   - TurnPhase (state machine nodes)
   - ConsensusState (unanimous/majority/conflicted)
   - Directive (player→character communication)
   - KnowledgeSeparation (player-only vs character-only knowledge)

2. **contracts/**: ✅ LangGraph node interface specifications complete
   - `player_agent_contract.yaml`: Input/output schema for strategic decision node
   - `character_agent_contract.yaml`: Input/output schema for roleplay node
   - `validation_contract.yaml`: Input/output schema for outcome detection
   - `memory_query_contract.yaml`: Input/output schema for retrieval operations

3. **quickstart.md**: ✅ Getting started guide complete
   - Installation (uv, Neo4j, Redis setup)
   - Create characters.json from example
   - Start session with single AI player
   - Sample DM interaction flow

4. **Agent Context Update**: ✅ Complete
   - Ran `.specify/scripts/bash/update-agent-context.sh claude`
   - Added LangGraph, Graphiti, Neo4j, Redis/RQ to CLAUDE.md technology list

---

## Next Steps

1. Execute Phase 0 research (generate research.md)
2. Execute Phase 1 design (generate data-model.md, contracts/, quickstart.md)
3. Update agent context with new technologies
4. Re-run Constitution Check post-design
5. Proceed to `/speckit.tasks` for Phase 2 task breakdown
