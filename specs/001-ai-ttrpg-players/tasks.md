# Tasks: AI TTRPG Player System

**Input**: Design documents from `/specs/001-ai-ttrpg-players/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/

**Tests**: TDD approach - tests written BEFORE implementation and must FAIL before code is written

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## How to Use This Task List

**Each task includes reference links** to the detailed implementation guidance:

- **research.md §X** → Code examples, patterns, and technology research
- **data-model.md §X** → Pydantic model specifications with complete field definitions
- **contracts/*.yaml** → API interface contracts with behavior requirements and test cases
- **spec.md** → Original user story acceptance criteria
- **quickstart.md** → Setup instructions and command examples
- **plan.md** → Architecture overview and Implementation Guidance Map

**When starting a task**:
1. Read the task description and file path
2. Open the referenced documents (e.g., "research.md §2")
3. Copy/adapt code examples from research.md or data-model.md
4. Verify implementation matches contract specifications
5. Write tests BEFORE implementation (TDD)

**Example workflow**:
```
Task: T034 Implement Graphiti client wrapper in src/memory/graphiti_client.py
Reference: research.md §2 (Graphiti Memory Integration)

Steps:
1. Open research.md, scroll to Section 2
2. Find "Graphiti Memory Integration" heading
3. Copy the code example (Initialize Graphiti client, create_session_episode, etc.)
4. Adapt for src/memory/graphiti_client.py
5. Cross-check with contracts/memory_interface.yaml
6. Write contract tests in tests/contract/test_memory_contracts.py FIRST
```

**Section notation**: §2 = Section 2, §3.1 = Section 3 subsection 1

## Format: `[ID] [P?] [Story] Description`
- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions
- **Reference**: Links to implementation details in documentation

## Path Conventions
- Single Python project structure
- Paths: `src/`, `tests/` at repository root

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and basic structure

- [X] T001 Create project structure per plan.md (src/, tests/, docker/, scripts/, .env.example)
- [X] T002 Initialize Python project with uv init and pyproject.toml configuration
- [X] T003 [P] Add core dependencies via uv: langgraph, graphiti, neo4j, redis, rq, openai, pydantic, pydantic-settings, tenacity, loguru
- [X] T004 [P] Create docker/docker-compose.yml with Neo4j 5.x, Redis 7.x, and app containers
- [X] T005 [P] Create .env.example with all configuration variables per Settings model
- [X] T006 Configure ruff for linting and formatting

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

### Configuration & Settings
- [X] T007 Implement Settings model with Pydantic settings in src/config/settings.py
  - **Reference**: data-model.md §6.1 (Settings), research.md §1-8 for config values
- [X] T008 [P] Create prompt templates structure in src/config/prompts.py
  - **Reference**: research.md §4 (validation prompts), §8 (corruption prompts)

### Core Data Models
- [X] T009 [P] Create GamePhase enum in src/models/game_state.py
  - **Reference**: data-model.md §3.1 (GameState section, GamePhase enum definition)
- [X] T010 [P] Create Channel and MessageType enums in src/models/messages.py
  - **Reference**: data-model.md §4.1 (Message model), research.md §6 (channel definitions)
- [X] T011 [P] Create MemoryType and CorruptionType enums in src/models/memory_edge.py
  - **Reference**: data-model.md §2.1 (MemoryEdge), research.md §8 (corruption types)
- [X] T012 [P] Create PlayStyle enum in src/models/personality.py
  - **Reference**: data-model.md §1.1 (AgentPersonality)
- [X] T013 [P] Implement AgentPersonality model in src/models/personality.py
  - **Reference**: data-model.md §1.1 (complete specification with validation)
- [X] T014 [P] Implement CharacterSheet model in src/models/personality.py
  - **Reference**: data-model.md §1.2 (complete specification with example)
- [X] T015 [P] Implement MemoryEdge model with temporal validation in src/models/memory_edge.py
  - **Reference**: data-model.md §2.1 (includes field_validator for temporal consistency)
- [X] T016 [P] Implement CorruptionConfig model in src/models/memory_edge.py
  - **Reference**: data-model.md §2.2 (CorruptionConfig specification)
- [X] T017 [P] Implement Message model with channel routing in src/models/messages.py
  - **Reference**: data-model.md §4.1 (Message), contracts/agent_interface.yaml (Message schema)
- [X] T018 [P] Implement GameState model in src/models/game_state.py
  - **Reference**: data-model.md §3.1 (GameState with all fields), research.md §1 (LangGraph TypedDict pattern)
- [X] T019 [P] Implement ValidationResult model in src/models/game_state.py
  - **Reference**: data-model.md §3.2 (ValidationResult), research.md §4 (validation structure)
- [X] T020 [P] Implement ConsensusState, Stance, Position, ConsensusResult models in src/models/game_state.py
  - **Reference**: data-model.md §3.2 (Consensus models), research.md §7 (consensus detection)
- [X] T021 [P] Implement DMCommand, DMCommandType, DiceRoll models in src/models/messages.py
  - **Reference**: data-model.md §5.1 (DMCommand), §5.2 (DiceRoll)

### Utilities
- [X] T022 [P] Implement dice roller with D&D 5e notation support in src/utils/dice.py
  - **Reference**: data-model.md §5.2 (DiceRoll model), quickstart.md (roll command examples)
- [X] T023 [P] Setup structured logging with loguru in src/utils/logging.py
  - **Reference**: research.md §3 (structured logging for RQ), plan.md (loguru in tech stack)

### Infrastructure Setup
- [X] T024 Start Docker infrastructure with docker-compose up -d
  - **Reference**: quickstart.md (step 3), research.md §2 (Neo4j config), §3 (Redis config)
- [X] T025 Create Neo4j initialization script with temporal indexes in scripts/setup_neo4j.py
  - **Reference**: research.md §5 (complete index creation Cypher queries)
- [X] T026 Run scripts/setup_neo4j.py to initialize database
  - **Reference**: quickstart.md (step 4)
- [X] T027 Create personality seeding script in scripts/seed_personalities.py
  - **Reference**: data-model.md §1.1 (AgentPersonality examples)

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel

---

## Phase 3: User Story 1 - Single AI Player Completes Full Turn Cycle (Priority: P1) 🎯 MVP

**Goal**: Enable a single AI player to participate in turn-based gameplay with dual-layer architecture (strategic player + roleplay character), maintaining DM narrative control through strict turn phases.

**Independent Test**: Run a complete game turn where the DM narrates a scene, the AI responds strategically and in-character without narrating outcomes, waits for DM adjudication, and stores the memory. Verify the AI expresses intent only and respects phase transitions.

### Contract Tests for User Story 1 (TDD - Write FIRST, Ensure FAIL)

- [X] T028 [P] [US1] Contract test for BasePersonaAgent interface in tests/contract/test_agent_contracts.py
  - **Reference**: contracts/agent_interface.yaml (contract_tests section for BasePersonaAgent)
- [X] T029 [P] [US1] Contract test for CharacterAgent interface in tests/contract/test_agent_contracts.py
  - **Reference**: contracts/agent_interface.yaml (contract_tests section for CharacterAgent)
- [X] T030 [P] [US1] Contract test for CorruptedTemporalMemory interface in tests/contract/test_memory_contracts.py
  - **Reference**: contracts/memory_interface.yaml
- [X] T031 [P] [US1] Contract test for TtrpgOrchestrator interface in tests/contract/test_orchestrator_contracts.py
  - **Reference**: contracts/orchestrator_interface.yaml

### Integration Tests for User Story 1 (TDD - Write FIRST, Ensure FAIL)

- [X] T032 [US1] Integration test for complete turn cycle in tests/integration/test_turn_cycle.py
  - **Reference**: spec.md (US1 acceptance criteria), data-model.md §3.1 (GamePhase transitions)
- [X] T033 [US1] Integration test for memory persistence across sessions in tests/integration/test_memory_persistence.py
  - **Reference**: spec.md (US3 acceptance criteria), research.md §2 (Graphiti episodes)

### Memory Layer Implementation for User Story 1

- [X] T034 [P] [US1] Implement Graphiti client wrapper in src/memory/graphiti_client.py
  - **Reference**: research.md §2 (Graphiti Memory Integration - complete code examples), contracts/memory_interface.yaml
- [X] T035 [US1] Implement CorruptedTemporalMemory base class (no corruption yet) in src/memory/corrupted_temporal.py
  - **Reference**: research.md §2 (Graphiti wrapper pattern), data-model.md §2.1 (MemoryEdge)
- [X] T036 [US1] Add search() method with temporal queries to CorruptedTemporalMemory
  - **Reference**: research.md §2 (query_memories_at_time function), §5 (optimized query patterns)
- [X] T037 [US1] Add add_episode() method for episode storage to CorruptedTemporalMemory
  - **Reference**: research.md §2 (create_session_episode function), contracts/memory_interface.yaml

### Agent Layer Implementation for User Story 1

- [X] T038 [P] [US1] Implement BasePersonaAgent with strategic decision-making in src/agents/base_persona.py
  - **Reference**: contracts/agent_interface.yaml (BasePersonaAgent interface), data-model.md §1.1 (AgentPersonality)
- [X] T039 [P] [US1] Implement CharacterAgent with in-character roleplay in src/agents/character.py
  - **Reference**: contracts/agent_interface.yaml (CharacterAgent interface), data-model.md §1.2 (CharacterSheet)
- [X] T040 [US1] Add participate_in_ooc_discussion() method to BasePersonaAgent
  - **Reference**: contracts/agent_interface.yaml (method spec + behavior requirements), research.md §4 (LLM call pattern)
- [X] T041 [US1] Add formulate_strategic_intent() method to BasePersonaAgent
  - **Reference**: contracts/agent_interface.yaml (Intent output schema), data-model.md §3.2 (Intent model)
- [X] T042 [US1] Add create_character_directive() method to BasePersonaAgent
  - **Reference**: contracts/agent_interface.yaml (Directive output schema), data-model.md §3.2 (Directive model)
- [X] T043 [US1] Add perform_action() method to CharacterAgent
  - **Reference**: contracts/agent_interface.yaml (behavior: intent only, no outcomes), research.md §4 (validation patterns)
- [X] T044 [US1] Add react_to_outcome() method to CharacterAgent
  - **Reference**: contracts/agent_interface.yaml (Reaction schema), data-model.md §1.2 (speech patterns)

### Orchestration Layer Implementation for User Story 1

- [X] T045 [US1] Implement MessageRouter with channel-based visibility in src/orchestration/message_router.py
  - **Reference**: research.md §6 (Three-Channel Message Routing - complete MessageRouter class), data-model.md §4.1 (Message model)
- [X] T046 [US1] Implement LangGraph state machine with GamePhase transitions in src/orchestration/state_machine.py
  - **Reference**: research.md §1 (LangGraph State Machine - workflow build example), data-model.md §3.1 (GameState + GamePhase)
- [X] T047 [US1] Add DM_NARRATION phase handler to state machine
  - **Reference**: research.md §1 (node function pattern), data-model.md §3.1 (phase sequence)
- [X] T048 [US1] Add MEMORY_RETRIEVAL phase handler to state machine
  - **Reference**: research.md §2 (memory query), research.md §1 (node returns new state dict)
- [X] T049 [US1] Add STRATEGIC_INTENT phase handler to state machine
  - **Reference**: contracts/agent_interface.yaml (formulate_strategic_intent), research.md §3 (RQ job dispatch)
- [X] T050 [US1] Add P2C_DIRECTIVE phase handler to state machine
  - **Reference**: contracts/agent_interface.yaml (create_character_directive method)
- [X] T051 [US1] Add CHARACTER_ACTION phase handler to state machine
  - **Reference**: contracts/agent_interface.yaml (perform_action), research.md §3 (worker dispatch + blocking)
- [X] T052 [US1] Add DM_ADJUDICATION phase handler to state machine
  - **Reference**: data-model.md §3.1 (phase transitions), quickstart.md (DM commands)
- [X] T053 [US1] Add DICE_RESOLUTION phase handler to state machine
  - **Reference**: data-model.md §5.2 (DiceRoll), src/utils/dice.py (dice roller)
- [X] T054 [US1] Add DM_OUTCOME phase handler to state machine
  - **Reference**: data-model.md §3.1 (phase flow to CHARACTER_REACTION)
- [X] T055 [US1] Add CHARACTER_REACTION phase handler to state machine
  - **Reference**: contracts/agent_interface.yaml (react_to_outcome method)
- [X] T056 [US1] Add MEMORY_CONSOLIDATION phase handler to state machine
  - **Reference**: research.md §2 (add_episode), data-model.md §2.1 (MemoryEdge creation)
- [X] T057 [US1] Implement phase rollback and retry logic with error recovery
  - **Reference**: research.md §1 (conditional edges for retry), data-model.md §3.2 (ValidationResult)
- [X] T058 [US1] Add LangGraph checkpointing for game state persistence
  - **Reference**: research.md §1 (checkpointer=MemorySaver(), checkpointing best practices)

### Worker Layer Implementation for User Story 1

- [X] T059 [P] [US1] Implement RQ worker for BasePersonaAgent in src/workers/base_persona_worker.py
  - **Reference**: research.md §3 (RQ worker function pattern, must import at module level)
- [X] T060 [P] [US1] Implement RQ worker for CharacterAgent in src/workers/character_worker.py
  - **Reference**: research.md §3 (character_agent_perform_action example)
- [X] T061 [US1] Configure RQ queues with timeout and retry settings
  - **Reference**: research.md §3 (Worker Configuration section, queue creation)
- [X] T062 [US1] Implement exponential backoff for LLM API failures
  - **Reference**: research.md §3 (Exponential Backoff for LLM API Failures - complete @retry decorator)

### DM Interface Implementation for User Story 1

- [X] T063 [US1] Implement DM command parser in src/interface/dm_cli.py
  - **Reference**: data-model.md §5.1 (DMCommand model), quickstart.md (command examples)
- [X] T064 [US1] Add "narrate" command handler to DM CLI
  - **Reference**: quickstart.md (narrate command), data-model.md §5.1 (DMCommandType.NARRATE)
- [X] T065 [US1] Add "roll" command handler with dice notation parsing
  - **Reference**: data-model.md §5.2 (DiceRoll), src/utils/dice.py (D&D 5e notation)
- [X] T066 [US1] Add "success" and "fail" command handlers
  - **Reference**: data-model.md §5.1 (DMCommandType.SUCCESS/FAILURE), research.md §1 (phase transitions)
- [X] T067 [US1] Add turn output formatter displaying agent responses
  - **Reference**: data-model.md §3.1 (GameState fields), contracts/agent_interface.yaml (Message schema)
- [X] T068 [US1] Add session state display showing current phase and turn number
  - **Reference**: data-model.md §3.1 (session_number, turn_number, current_phase)
- [X] T069 [US1] Add error handling and user-friendly error messages
  - **Reference**: contracts/*_interface.yaml (errors sections)

### Unit Tests for User Story 1

- [ ] T070 [P] [US1] Unit tests for AgentPersonality validation in tests/unit/models/test_personality.py
- [ ] T071 [P] [US1] Unit tests for CharacterSheet validation in tests/unit/models/test_character_sheet.py
- [ ] T072 [P] [US1] Unit tests for MemoryEdge temporal validation in tests/unit/models/test_memory_edge.py
- [ ] T073 [P] [US1] Unit tests for GameState transitions in tests/unit/models/test_game_state.py
- [ ] T074 [P] [US1] Unit tests for Message routing rules in tests/unit/models/test_messages.py
- [ ] T075 [P] [US1] Unit tests for dice roller in tests/unit/utils/test_dice.py
- [ ] T076 [P] [US1] Unit tests for BasePersonaAgent logic in tests/unit/agents/test_base_persona.py
- [ ] T077 [P] [US1] Unit tests for CharacterAgent logic in tests/unit/agents/test_character.py
- [ ] T078 [P] [US1] Unit tests for MessageRouter visibility in tests/unit/orchestration/test_message_router.py
- [ ] T079 [P] [US1] Unit tests for state machine transitions in tests/unit/orchestration/test_state_machine.py
- [ ] T080 [P] [US1] Unit tests for Graphiti client in tests/unit/memory/test_graphiti_client.py

### Performance Tests for User Story 1

- [ ] T080.1 [P] [US1] Performance test: verify single AI player turn cycle completes <10s (P95) in tests/integration/test_turn_cycle_performance.py

**Checkpoint**: At this point, User Story 1 should be fully functional - single AI player can complete full turn cycles with DM control maintained

---

## Phase 4: User Story 2 - AI Player Prevents Narrative Overreach (Priority: P1)

**Goal**: Implement validation system that detects and prevents AI players from narrating their own action outcomes, maintaining DM as sole authority on story consequences.

**Independent Test**: Have an AI attempt actions and verify that outcome narration is caught, the AI is prompted to retry with progressively stricter feedback, and persistent violations are auto-corrected or flagged for DM review.

### Contract Tests for User Story 2 (TDD - Write FIRST, Ensure FAIL)

- [ ] T081 [P] [US2] Contract test for ValidationAgent interface in tests/contract/test_validation_contracts.py
  - **Reference**: contracts/agent_interface.yaml (validation behavior requirements)

### Integration Tests for User Story 2 (TDD - Write FIRST, Ensure FAIL)

- [ ] T082 [US2] Integration test for validation retry escalation in tests/integration/test_validation_flow.py
  - **Reference**: research.md §4 (progressive strictness example), data-model.md §3.2 (ValidationResult)
- [ ] T083 [US2] Integration test for auto-fix and DM flagging in tests/integration/test_validation_flow.py
  - **Reference**: spec.md (US2 acceptance criteria), research.md §4 (attempt 3 handling)

### Validation Layer Implementation for User Story 2

- [ ] T084 [US2] Implement ValidationAgent with outcome detection in src/agents/validation.py
  - **Reference**: research.md §4 (validate_action_patterns and validate_action_llm functions)
- [ ] T085 [US2] Add forbidden pattern detection (kills, hits, successfully, manages to, strikes, etc.) to ValidationAgent
  - **Reference**: research.md §4 (FORBIDDEN_PATTERNS list, regex validation)
- [ ] T086 [US2] Add progressive feedback system (attempt 1: gentle, attempt 2: strict, attempt 3: very strict)
  - **Reference**: research.md §4 (build_character_prompt with attempt parameter)
- [ ] T087 [US2] Add auto-correction logic for attempt 3 failures
  - **Reference**: research.md §4 (auto-fix discussion), data-model.md §3.2 (ValidationResult.auto_fixed)
- [ ] T088 [US2] Add DM flagging for persistent violations
  - **Reference**: data-model.md §3.2 (ValidationResult.warning_flag)

### Worker Layer Implementation for User Story 2

- [ ] T089 [US2] Implement RQ worker for ValidationAgent in src/workers/validation_worker.py
  - **Reference**: research.md §3 (RQ worker pattern), contracts/agent_interface.yaml (ValidationAgent integration)

### Orchestration Updates for User Story 2

- [ ] T090 [US2] Add VALIDATION_CHECK phase handler to state machine in src/orchestration/state_machine.py
  - **Reference**: research.md §1 (conditional edge example with should_retry_validation), data-model.md §3.1 (GamePhase)
- [ ] T091 [US2] Implement validation retry loop with 3-attempt limit
  - **Reference**: research.md §1 (retry_with_correction node), research.md §4 (progressive prompts)
- [ ] T092 [US2] Add conditional edge for VALID → DM_ADJUDICATION
  - **Reference**: research.md §1 (conditional_edges example)
- [ ] T093 [US2] Add conditional edge for RETRY → CHARACTER_ACTION
  - **Reference**: research.md §1 (edge predicates with state routing)
- [ ] T094 [US2] Add conditional edge for FAIL → DM_ADJUDICATION with warning flag
  - **Reference**: data-model.md §3.2 (ValidationResult.warning_flag)

### Prompt Engineering for User Story 2

- [ ] T095 [US2] Create validation prompts with progressive strictness in src/config/prompts.py
  - **Reference**: research.md §4 (Progressive Prompt Strictness section - complete prompt templates)
- [ ] T096 [US2] Create character action prompt emphasizing intent-only expression
  - **Reference**: research.md §4 (base_prompt example), contracts/agent_interface.yaml (behavior: MUST express intent only)
- [ ] T097 [US2] Add example valid/invalid actions to prompts
  - **Reference**: research.md §4 (LLM-based validation prompt examples)

### Unit Tests for User Story 2

- [ ] T098 [P] [US2] Unit tests for ValidationAgent pattern detection in tests/unit/agents/test_validation.py
- [ ] T099 [P] [US2] Unit tests for progressive feedback logic in tests/unit/agents/test_validation.py
- [ ] T100 [P] [US2] Unit tests for auto-correction in tests/unit/agents/test_validation.py
- [ ] T101 [P] [US2] Unit tests for ValidationResult model in tests/unit/models/test_validation_result.py

**Checkpoint**: At this point, User Stories 1 AND 2 should both work - single AI player with narrative constraint enforcement

---

## Phase 5: User Story 3 - Memory Persists Across Sessions (Priority: P1)

**Goal**: Enable AI players to remember events, NPCs, and decisions from previous game sessions with temporal context, making long-term campaigns possible.

**Independent Test**: Run a session where specific events occur (e.g., meeting NPC "Galvin"), end the session, start a new session, and verify the AI can query and recall those events accurately with temporal information.

### Integration Tests for User Story 3 (TDD - Write FIRST, Ensure FAIL)

- [ ] T102 [US3] Integration test for cross-session memory recall in tests/integration/test_memory_persistence.py
- [ ] T103 [US3] Integration test for temporal queries (events 20+ sessions ago) in tests/integration/test_memory_persistence.py

### Memory Layer Enhancements for User Story 3

- [ ] T104 [US3] Add temporal indexing to Neo4j setup script in scripts/setup_neo4j.py
- [ ] T105 [US3] Implement session boundary detection in src/memory/corrupted_temporal.py
- [ ] T106 [US3] Add batch memory consolidation at session end
- [ ] T107 [US3] Implement memory retrieval with confidence scores and temporal context
- [ ] T108 [US3] Add "What do we know about [X]?" query interface
- [ ] T109 [US3] Implement entity relationship tracking (NPCs, locations, items)

### Orchestration Updates for User Story 3

- [ ] T110 [US3] Add SESSION_START phase handler with memory loading in src/orchestration/state_machine.py
- [ ] T111 [US3] Add SESSION_END phase handler with memory consolidation
- [ ] T112 [US3] Implement automatic memory storage at critical events (every 10 turns, scene completion)

### DM Interface Updates for User Story 3

- [ ] T113 [US3] Add "end_session" command to DM CLI in src/interface/dm_cli.py
- [ ] T114 [US3] Add session summary display at session end
- [ ] T115 [US3] Add session continuation support with state loading

### Unit Tests for User Story 3

- [ ] T116 [P] [US3] Unit tests for temporal memory queries in tests/unit/memory/test_corrupted_temporal.py
- [ ] T117 [P] [US3] Unit tests for entity relationship tracking in tests/unit/memory/test_graphiti_client.py
- [ ] T118 [P] [US3] Unit tests for session boundary handling in tests/unit/orchestration/test_state_machine.py

**Checkpoint**: At this point, User Stories 1, 2, AND 3 should work - single AI player with validation and persistent memory across sessions (MVP COMPLETE)

---

## Phase 6: User Story 4 - Player-Character Knowledge Separation (Priority: P2)

**Goal**: Enable DM to provide information separately to the AI player (strategic layer) or AI character (roleplay layer), creating realistic knowledge management and secret-keeping scenarios.

**Independent Test**: Provide secret information to one AI player's strategic layer (e.g., "You notice poison on the blade") and verify the character doesn't automatically reveal it, but the player can choose to roleplay the discovery if desired.

### Contract Tests for User Story 4 (TDD - Write FIRST, Ensure FAIL)

- [ ] T119 [US4] Contract test for knowledge separation in tests/contract/test_knowledge_separation.py

### Integration Tests for User Story 4 (TDD - Write FIRST, Ensure FAIL)

- [ ] T120 [US4] Integration test for player-only knowledge in tests/integration/test_knowledge_separation.py
- [ ] T121 [US4] Integration test for character-only knowledge in tests/integration/test_knowledge_separation.py
- [ ] T122 [US4] Integration test for conscious revelation decision in tests/integration/test_knowledge_separation.py

### Memory Layer Enhancements for User Story 4

- [ ] T123 [US4] Add knowledge_layer field to MemoryEdge (player_only, character_only, both) in src/models/memory_edge.py
- [ ] T124 [US4] Implement layer-specific memory filtering in src/memory/corrupted_temporal.py
- [ ] T125 [US4] Update memory query to respect knowledge layer restrictions

### Agent Layer Updates for User Story 4

- [ ] T126 [US4] Add knowledge layer filtering to BasePersonaAgent memory access in src/agents/base_persona.py
- [ ] T127 [US4] Add knowledge layer filtering to CharacterAgent memory access in src/agents/character.py
- [ ] T128 [US4] Implement conscious revelation logic in BasePersonaAgent directive creation

### DM Interface Updates for User Story 4

- [ ] T129 [US4] Add "whisper" command for player-only information in src/interface/dm_cli.py
- [ ] T130 [US4] Add "scene" command for character-only information in src/interface/dm_cli.py
- [ ] T131 [US4] Update command parser to support layer targeting

### Unit Tests for User Story 4

- [ ] T132 [P] [US4] Unit tests for knowledge layer filtering in tests/unit/memory/test_corrupted_temporal.py
- [ ] T133 [P] [US4] Unit tests for conscious revelation logic in tests/unit/agents/test_base_persona.py

**Checkpoint**: User Stories 1-4 complete - single AI player with full knowledge management capabilities

---

## Phase 7: User Story 5 - Multi-Agent Strategic Coordination (Priority: P2)

**Goal**: Enable 3-4 AI players to discuss strategy together out-of-character, reach consensus (unanimous, majority, or timeout vote), and observe emergent party dynamics.

**Independent Test**: Present a decision point to multiple AI players (e.g., "You reach a fork in the tunnel"), observe their strategic discussion, verify consensus detection works (unanimous/majority/conflicted), and confirm characters act according to group decision.

### Contract Tests for User Story 5 (TDD - Write FIRST, Ensure FAIL)

- [ ] T134 [US5] Contract test for ConsensusDetector interface in tests/contract/test_consensus_contracts.py
  - **Reference**: data-model.md §3.2 (ConsensusState, Position, ConsensusResult models)

### Integration Tests for User Story 5 (TDD - Write FIRST, Ensure FAIL)

- [ ] T135 [US5] Integration test for multi-agent coordination in tests/integration/test_multi_agent.py
  - **Reference**: spec.md (US5 acceptance criteria), research.md §7 (consensus detection example)
- [ ] T136 [US5] Integration test for unanimous consensus in tests/integration/test_multi_agent.py
  - **Reference**: research.md §7 (unanimous detection logic)
- [ ] T137 [US5] Integration test for majority consensus with dissent in tests/integration/test_multi_agent.py
  - **Reference**: research.md §7 (majority detection: >50% agree, no disagree)
- [ ] T138 [US5] Integration test for timeout and forced vote in tests/integration/test_multi_agent.py
  - **Reference**: research.md §7 (timeout strategy: 5 rounds OR 2 minutes)

### Orchestration Layer Implementation for User Story 5

- [ ] T139 [US5] Implement ConsensusDetector with stance classification in src/orchestration/consensus_detector.py
  - **Reference**: research.md §7 (Consensus Detection Algorithm - complete extract_positions and detect_consensus functions)
- [ ] T140 [US5] Add LLM-based stance extraction (AGREE/DISAGREE/NEUTRAL/SILENT)
  - **Reference**: research.md §7 (Stance Classification with LLM - complete prompt with JSON mode)
- [ ] T141 [US5] Implement unanimous detection (all explicitly agree)
  - **Reference**: research.md §7 (detect_consensus function, unanimous check)
- [ ] T142 [US5] Implement majority detection (>50% agree, no disagree)
  - **Reference**: research.md §7 (majority consensus logic: agree_count > len/2 and disagree_count == 0)
- [ ] T143 [US5] Implement conflicted detection (no clear majority)
  - **Reference**: research.md §7 (return CONFLICTED state when active disagreement)
- [ ] T144 [US5] Add timeout logic (5 rounds or 2 minutes)
  - **Reference**: research.md §7 (Timeout Strategy Comparison table, hybrid approach)
- [ ] T145 [US5] Implement forced vote mechanism on timeout
  - **Reference**: research.md §7 (should_continue_discussion with TIMEOUT → vote)

### Orchestration Updates for User Story 5

- [ ] T146 [US5] Update OOC_DISCUSSION phase to support multiple agents in src/orchestration/state_machine.py
  - **Reference**: research.md §7 (ooc_discussion_node example), research.md §3 (parallel RQ jobs)
- [ ] T147 [US5] Add consensus detection loop in OOC_DISCUSSION phase
  - **Reference**: research.md §7 (detect_consensus call within node)
- [ ] T148 [US5] Add conditional edges based on consensus state
  - **Reference**: research.md §7 (should_continue_discussion conditional edge), research.md §1 (conditional_edges pattern)
- [ ] T149 [US5] Implement parallel agent invocation for simultaneous discussion
  - **Reference**: research.md §3 (multiple job.enqueue calls), contracts/agent_interface.yaml (participate_in_ooc_discussion)

### Memory Layer Updates for User Story 5

- [ ] T150 [US5] Implement shared party memory layer in src/memory/corrupted_temporal.py
  - **Reference**: research.md §2 (Group ID Strategy: campaign_main for shared, agent_X for personal)
- [ ] T151 [US5] Add personal vs shared memory distinction
  - **Reference**: research.md §2 (group_ids parameter in Graphiti search)
- [ ] T152 [US5] Implement party culture tracking (repeated preferences, leadership patterns)
  - **Reference**: spec.md (US5 emergent behaviors), data-model.md §2.1 (MemoryEdge.memory_type)
- [ ] T152.1 [US5] Implement memory conflict detection algorithm in src/memory/corrupted_temporal.py
  - **Reference**: spec.md (US5 memory conflicts), data-model.md §2.1 (MemoryEdge.confidence)
- [ ] T152.2 [US5] Add precedence resolution (DM > player > character) to conflict handler
  - **Reference**: spec.md (DM authority principle)
- [ ] T152.3 [US5] Add conflict logging with source attribution for researcher review
  - **Reference**: research.md §3 (structured logging), spec.md (research observability)

### Agent Layer Updates for User Story 5

- [ ] T153 [US5] Update BasePersonaAgent to support multi-agent discussion in src/agents/base_persona.py
- [ ] T154 [US5] Add personality-based strategic preferences (cautious vs aggressive)
- [ ] T155 [US5] Add dissent expression for minority opinions

### DM Interface Updates for User Story 5

- [ ] T156 [US5] Add multi-agent session initialization in src/interface/dm_cli.py
- [ ] T157 [US5] Add agent personality selection/configuration
- [ ] T158 [US5] Display consensus state in turn output

### Unit Tests for User Story 5

- [ ] T159 [P] [US5] Unit tests for ConsensusDetector stance classification in tests/unit/orchestration/test_consensus_detector.py
- [ ] T160 [P] [US5] Unit tests for consensus state detection in tests/unit/orchestration/test_consensus_detector.py
- [ ] T161 [P] [US5] Unit tests for timeout logic in tests/unit/orchestration/test_consensus_detector.py
- [ ] T162 [P] [US5] Unit tests for shared party memory in tests/unit/memory/test_corrupted_temporal.py

### Performance Tests for User Story 5

- [ ] T162.1 [US5] Performance test: verify 3-4 AI players maintain <10s turn cycle (P95) with no degradation vs single player in tests/integration/test_multi_agent_performance.py

**Checkpoint**: User Stories 1-5 complete - multi-agent system with strategic coordination

---

## Phase 8: User Story 6 - Character Interprets Player Directives (Priority: P3)

**Goal**: Enable each AI character to interpret high-level strategic directives from their player layer through their unique personality lens, creating an "interpretation gap" for realistic character-driven moments.

**Independent Test**: Give the same strategic directive to characters with different personalities (e.g., "Intimidate the guard carefully" to both cautious and aggressive characters) and verify they execute it differently while maintaining their established speech patterns and mannerisms.

### Integration Tests for User Story 6 (TDD - Write FIRST, Ensure FAIL)

- [ ] T163 [US6] Integration test for personality-based directive interpretation in tests/integration/test_interpretation_gap.py
- [ ] T164 [US6] Integration test for consistent speech patterns across turns in tests/integration/test_interpretation_gap.py

### Agent Layer Enhancements for User Story 6

- [ ] T165 [US6] Enhance CharacterAgent with directive interpretation logic in src/agents/character.py
- [ ] T166 [US6] Add personality trait influence on action execution
- [ ] T167 [US6] Implement speech pattern consistency tracking
- [ ] T168 [US6] Add mannerism injection into character actions
- [ ] T169 [US6] Implement cautious vs aggressive interpretation modes

### Prompt Engineering for User Story 6

- [ ] T170 [US6] Create character-specific prompts emphasizing personality in src/config/prompts.py
- [ ] T171 [US6] Add personality trait examples to character prompts
- [ ] T172 [US6] Create interpretation gap examples (same directive, different personalities)

### Memory Layer Updates for User Story 6

- [ ] T173 [US6] Track character behavioral consistency in memory
- [ ] T174 [US6] Store speech patterns and mannerisms for reinforcement

### Unit Tests for User Story 6

- [ ] T175 [P] [US6] Unit tests for directive interpretation logic in tests/unit/agents/test_character.py
- [ ] T176 [P] [US6] Unit tests for personality trait influence in tests/unit/agents/test_character.py
- [ ] T177 [P] [US6] Unit tests for speech pattern consistency in tests/unit/agents/test_character.py

**Checkpoint**: All user stories (1-6) complete - full system with interpretation gap and personality-driven roleplay

---

## Phase 9: Memory Corruption System (Post-MVP Enhancement)

**Goal**: Implement realistic memory degradation over time based on personality traits, creating more human-like memory recall patterns.

### Integration Tests for Memory Corruption (TDD - Write FIRST, Ensure FAIL)

- [ ] T178 Integration test for memory corruption over time in tests/integration/test_memory_corruption.py
  - **Reference**: research.md §8 (Corruption Probability Benchmarks), spec.md (memory corruption acceptance)
- [ ] T179 Integration test for rehearsal resistance in tests/integration/test_memory_corruption.py
  - **Reference**: research.md §8 (rehearsal_factor in probability calc)

### Memory Corruption Implementation

- [ ] T180 [P] Implement CorruptionEngine with LLM-powered degradation in src/memory/corruption_engine.py
  - **Reference**: research.md §8 (LLM-Powered Natural Corruption - complete llm_corrupt_memory function with detailed prompt)
- [ ] T181 [P] Implement corrupted_temporal decorator in src/memory/corrupted_temporal.py
  - **Reference**: research.md §8 (decorator pattern mentioned), data-model.md §2.1 (MemoryEdge corruption fields)
- [ ] T182 Calculate corruption probability (exponential decay + importance + rehearsal resistance)
  - **Reference**: research.md §8 (Corruption Probability Formula - complete calculate_corruption_probability function)
- [ ] T183 Implement corruption type selection based on personality traits
  - **Reference**: research.md §8 (Corruption Type Selection - complete select_corruption_type function with personality weights)
- [ ] T184 Add detail_drift corruption type
  - **Reference**: research.md §8 (corruption type definitions and examples), data-model.md §2.1 (CorruptionType enum)
- [ ] T185 Add emotional_coloring corruption type
  - **Reference**: research.md §8 (emotional_coloring example: "hostile guard"), data-model.md §1.1 (emotional_memory trait)
- [ ] T186 Add conflation corruption type
  - **Reference**: research.md §8 (conflation example: "tavern—no wait, marketplace")
- [ ] T187 Add simplification corruption type
  - **Reference**: research.md §8 (simplification: "mentioned something" → "mentioned")
- [ ] T188 Add false_confidence corruption type
  - **Reference**: research.md §8 (false_confidence: adding "iron padlock" detail)
- [ ] T189 Implement LLM-based subtle memory alteration
  - **Reference**: research.md §8 (llm_corrupt_memory complete implementation with prompt engineering)
- [ ] T190 Add corruption metadata tracking (original_uuid, corruption_type)
  - **Reference**: research.md §2 (add_corrupted_memory function), data-model.md §2.1 (MemoryEdge.original_uuid)

### Memory Layer Updates for Corruption

- [ ] T191 Update CorruptedTemporalMemory.search() to apply corruption conditionally
  - **Reference**: research.md §8 (probability calculation on query), data-model.md §2.2 (CorruptionConfig.enabled)
- [ ] T192 Add corruption toggle in Settings configuration
  - **Reference**: data-model.md §2.2 (CorruptionConfig.enabled boolean)
- [ ] T193 Implement corruption strength scaling based on personality
  - **Reference**: research.md §8 (personality_modifier calculation: detail_oriented affects decay), data-model.md §1.1 (base_decay_rate)

### Unit Tests for Memory Corruption

- [ ] T194 [P] Unit tests for corruption probability calculation in tests/unit/memory/test_corruption_engine.py
- [ ] T195 [P] Unit tests for corruption type selection in tests/unit/memory/test_corruption_engine.py
- [ ] T196 [P] Unit tests for each corruption type in tests/unit/memory/test_corruption_engine.py
- [ ] T197 [P] Unit tests for corrupted_temporal decorator in tests/unit/memory/test_corrupted_temporal.py

**Checkpoint**: Memory corruption system complete - AI players exhibit realistic memory degradation patterns

---

## Phase 10: Observability & Research Tooling

**Goal**: Implement logging, metrics tracking, and research analysis capabilities for observing emergent behaviors.

### Observability Implementation

- [ ] T198 [P] Configure LangSmith integration for LLM tracing in src/config/settings.py
- [ ] T199 [P] Implement phase transition logging in src/orchestration/state_machine.py
- [ ] T200 [P] Add validation failure rate tracking
- [ ] T201 [P] Add API retry pattern logging
- [ ] T202 [P] Add agent response time metrics
- [ ] T203 [P] Add turn completion metrics
- [ ] T204 [P] Implement relationship development tracking over time
- [ ] T205 [P] Add party dynamics pattern detection
- [ ] T205.1 [P] Performance benchmark: measure actual turns/hour throughput and compare against 30-60 target from plan.md
- [ ] T206 [P] Create unexpected behavior flagging system

### Research Scripts

- [ ] T207 Create simulation script for automated test sessions in scripts/run_simulation.py
- [ ] T208 Add campaign progression tracking
- [ ] T209 Create metrics export for analysis

**Checkpoint**: Full observability and research capabilities enabled

---

## Phase 11: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect multiple user stories

- [ ] T210 [P] Create comprehensive README.md with quickstart, architecture overview, and usage examples
- [ ] T211 [P] Validate and test quickstart.md instructions end-to-end
- [ ] T212 [P] Add ABOUTME comments to all source files (2-line file purpose descriptions)
- [ ] T213 [P] Run ruff check and fix all linting issues
- [ ] T214 [P] Add docstrings to all public classes and methods
- [ ] T215 Code cleanup: remove unused imports, dead code, debug prints
- [ ] T216 Refactor: extract common patterns, reduce duplication
- [ ] T217 [P] Security review: ensure no API keys in logs, validate input sanitization
- [ ] T218 [P] Performance profiling: identify and optimize slow paths
- [ ] T219 Add CLI help text and usage examples
- [ ] T220 Error message audit: ensure all errors are user-friendly
- [ ] T221 Create troubleshooting guide for common issues

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Stories (Phase 3-8)**: All depend on Foundational phase completion
  - US1 (P1): Core single-player functionality - no dependencies on other stories
  - US2 (P1): Depends on US1 (needs agents and orchestration to validate)
  - US3 (P1): Can be built in parallel with US2 after US1 - adds persistence
  - US4 (P2): Depends on US1-US3 - extends memory system
  - US5 (P2): Depends on US1-US3 - adds multi-agent coordination
  - US6 (P3): Depends on US1 - enhances character interpretation
- **Memory Corruption (Phase 9)**: Depends on US3 - enhances memory system
- **Observability (Phase 10)**: Can be built in parallel with user stories
- **Polish (Phase 11)**: Depends on all desired features being complete

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational (Phase 2) - No dependencies on other stories
- **User Story 2 (P1)**: Depends on US1 (requires agents and orchestration to exist)
- **User Story 3 (P1)**: Can start after US1 completes - independently testable
- **User Story 4 (P2)**: Depends on US3 (extends memory system with knowledge layers)
- **User Story 5 (P2)**: Depends on US1-US3 (extends single-player to multi-player)
- **User Story 6 (P3)**: Depends on US1 (enhances character layer only)

### Within Each User Story

- Contract tests FIRST (write tests, ensure they FAIL)
- Integration tests SECOND (write tests, ensure they FAIL)
- Models before services
- Services before orchestration
- Core implementation before integration
- Unit tests alongside implementation
- Story complete before moving to next priority

### Parallel Opportunities

**Phase 1 (Setup)**:
- T003, T004, T005 can run in parallel (dependencies, docker, env)

**Phase 2 (Foundational)**:
- T008 can run in parallel with T007
- T009-T021 (all model enums and classes) can run in parallel
- T022-T023 (utilities) can run in parallel
- T027 can run after T024-T026 complete

**Phase 3 (US1)**:
- Contract tests T028-T031 can all run in parallel (different files)
- T034 (Graphiti client) can run in parallel with T038-T039 (agent base classes)
- T059-T060 (RQ workers) can run in parallel
- Most unit tests T070-T080 can run in parallel (different test files)

**Phase 4 (US2)**:
- T095-T097 (prompt engineering) can run in parallel
- Unit tests T098-T101 can run in parallel

**Phase 5 (US3)**:
- Unit tests T116-T118 can run in parallel

**Phase 6 (US4)**:
- Unit tests T132-T133 can run in parallel

**Phase 7 (US5)**:
- Unit tests T159-T162 can run in parallel

**Phase 8 (US6)**:
- Unit tests T175-T177 can run in parallel

**Phase 9 (Corruption)**:
- T180-T181 can run in parallel (engine and decorator)
- T184-T188 (corruption types) can run in parallel
- Unit tests T194-T197 can run in parallel

**Phase 10 (Observability)**:
- All tasks T198-T209 can run in parallel (different concerns)

**Phase 11 (Polish)**:
- T210-T221 can mostly run in parallel (different files/concerns)

---

## Parallel Example: User Story 1

```bash
# Launch all contract tests for User Story 1 together:
Task: "Contract test for BasePersonaAgent interface in tests/contract/test_agent_contracts.py"
Task: "Contract test for CharacterAgent interface in tests/contract/test_agent_contracts.py"
Task: "Contract test for CorruptedTemporalMemory interface in tests/contract/test_memory_contracts.py"
Task: "Contract test for TtrpgOrchestrator interface in tests/contract/test_orchestrator_contracts.py"

# Launch base implementations together:
Task: "Implement Graphiti client wrapper in src/memory/graphiti_client.py"
Task: "Implement BasePersonaAgent with strategic decision-making in src/agents/base_persona.py"
Task: "Implement CharacterAgent with in-character roleplay in src/agents/character.py"

# Launch RQ workers together:
Task: "Implement RQ worker for BasePersonaAgent in src/workers/base_persona_worker.py"
Task: "Implement RQ worker for CharacterAgent in src/workers/character_worker.py"

# Launch unit tests together (after implementation):
Task: "Unit tests for dice roller in tests/unit/utils/test_dice.py"
Task: "Unit tests for BasePersonaAgent logic in tests/unit/agents/test_base_persona.py"
Task: "Unit tests for CharacterAgent logic in tests/unit/agents/test_character.py"
```

---

## Implementation Strategy

### MVP First (User Stories 1-3 Only)

1. Complete Phase 1: Setup (T001-T006)
2. Complete Phase 2: Foundational (T007-T027) **CRITICAL - blocks all stories**
3. Complete Phase 3: User Story 1 (T028-T080)
4. **STOP and VALIDATE**: Test US1 independently (single AI player turn cycle)
5. Complete Phase 4: User Story 2 (T081-T101)
6. **STOP and VALIDATE**: Test US2 independently (validation enforcement)
7. Complete Phase 5: User Story 3 (T102-T118)
8. **STOP and VALIDATE**: Test US3 independently (memory persistence)
9. **MVP COMPLETE**: System can support single AI player campaigns with memory

### Incremental Delivery

1. Complete Setup + Foundational → Foundation ready
2. Add User Story 1 → Test independently → **Demo single AI player**
3. Add User Story 2 → Test independently → **Demo narrative constraint enforcement**
4. Add User Story 3 → Test independently → **Demo persistent memory** (MVP!)
5. Add User Story 4 → Test independently → **Demo knowledge separation**
6. Add User Story 5 → Test independently → **Demo multi-agent coordination**
7. Add User Story 6 → Test independently → **Demo interpretation gap**
8. Add Phase 9 → Test independently → **Demo memory corruption**
9. Add Phase 10 → **Enable research analysis**
10. Polish (Phase 11) → **Production-ready**

### Parallel Team Strategy

With multiple developers after Foundational phase completes:

**Week 1-2 (Foundation)**:
- Team works together on Setup + Foundational

**Week 3-4 (MVP - P1 Stories)**:
- Developer A: User Story 1 (single player core)
- Developer B: User Story 2 (validation system)
- Developer C: User Story 3 (memory persistence)

**Week 5-6 (P2 Stories)**:
- Developer A: User Story 4 (knowledge separation)
- Developer B: User Story 5 (multi-agent coordination)

**Week 7 (P3 + Enhancements)**:
- Developer A: User Story 6 (interpretation gap)
- Developer B: Memory Corruption (Phase 9)
- Developer C: Observability (Phase 10)

**Week 8 (Polish)**:
- All developers: Phase 11 (polish, docs, testing)

---

## Notes

- [P] tasks = different files, no dependencies within phase
- [Story] label maps task to specific user story for traceability
- Each user story should be independently completable and testable
- TDD enforced: verify tests fail before implementing
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- All tasks include exact file paths for clarity
- MVP = User Stories 1-3 (single AI player with validation and memory)
- Full System = User Stories 1-6 (multi-agent with interpretation gap)
- Research Enhancement = Phase 9 (memory corruption) + Phase 10 (observability)

---

## Task Count Summary

- **Phase 1 (Setup)**: 6 tasks
- **Phase 2 (Foundational)**: 21 tasks ⚠️ BLOCKS ALL STORIES
- **Phase 3 (US1)**: 54 tasks 🎯 MVP START
- **Phase 4 (US2)**: 21 tasks 🎯 MVP
- **Phase 5 (US3)**: 17 tasks 🎯 MVP COMPLETE
- **Phase 6 (US4)**: 15 tasks
- **Phase 7 (US5)**: 33 tasks
- **Phase 8 (US6)**: 15 tasks
- **Phase 9 (Corruption)**: 19 tasks
- **Phase 10 (Observability)**: 13 tasks
- **Phase 11 (Polish)**: 12 tasks

**Total**: 227 tasks

**MVP Scope**: Phases 1-5 (121 tasks) = Single AI player with validation and persistent memory
**Full System**: Phases 1-8 (181 tasks) = Multi-agent system with interpretation gap
**Research Ready**: All phases (227 tasks) = Full system with corruption and observability
