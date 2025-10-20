# Feature Specification: AI TTRPG Player System

**Feature Branch**: `001-ai-ttrpg-players`
**Created**: October 18, 2025
**Status**: Draft
**Input**: Multi-agent AI system where AI agents play as realistic tabletop RPG players in a game run by a human Dungeon Master, using dual-layer architecture (strategic "player" + roleplay "character")

## Clarifications

### Session 2025-10-18

- Q: How should the system behave when a turn phase fails or times out mid-execution? → A: Rollback to last stable phase and retry once, then flag for DM intervention
- Q: Should the system integrate with existing virtual tabletop platforms (Roll20, Foundry VTT) or operate as standalone command-line tool? → A: Standalone command-line tool with no VTT integration
- Q: Should dice rolling be handled by external dice bot/roller or built into the system? → A: Built-in dice roller with DM override capability
- Q: Which database technology should be used for memory storage? → A: Neo4j graph database for relationship-heavy queries and temporal tracking
- Q: How should the system handle LLM API failures, rate limits, or timeouts? → A: Retry multiple times with longer waits between attempts
- Q: What specific exponential backoff parameters should be used for LLM API retries? → A: Standard: 2s, 5s, 10s max retries = 5 attempts within ~35 seconds
- Q: How should the DM interact with the standalone command-line tool? → A: Turn-based prompts: System prompts DM at each phase (e.g., "Enter narration:", "Override roll? [y/n]:")
- Q: Should the dice roller support full D&D 5e notation or only Lasers & Feelings dice mechanics? → A: Lasers & Feelings only: Support 1d6 rolls exclusively (minimal implementation)
- Q: At what token usage threshold should the system trigger context window compression? → A: Balanced: Trigger at 80% of token limit (reasonable safety margin)
- Q: How should the DM create and configure AI player-character pairs at session start? → A: JSON configuration file: DM creates `characters.json` with all player/character attributes before starting

### Session 2025-10-19

- Q: How should AI player personality traits (analytical score, risk tolerance, detail orientation, emotional memory, assertiveness, cooperativeness, openness, rule adherence, roleplay intensity) be numerically represented? → A: Normalized 0.0-1.0 floating point scale for all personality traits (standard ML approach, allows easy mathematical operations, integrates naturally with LLM prompt engineering)
- Q: After 3 failed validation attempts, should the system auto-correct or flag for DM intervention, and how should auto-correction work? → A: Auto-correct by filtering forbidden outcome words (removes "kills", "successfully", etc.), flag for DM review if meaning becomes unclear after filtering
- Q: What qualifies as a "critical event" that should trigger memory storage? → A: NPC introductions, combat outcomes, major party decisions, quest status changes (concrete, objectively detectable events with high retrieval value)
- Q: What format should be used for logging agent interactions, phase transitions, validation failures, memory queries, and consensus outcomes? → A: Structured JSON logs with event_type, timestamp, session_id, turn_number, and event-specific fields (enables programmatic analysis, time-series research, filtering by event type)
- Q: How should memory confidence scores be calculated and represented? → A: 0.0-1.0 score based on recency decay and source authority (DM narration = 1.0, player observations = 0.7-0.9 decaying with time, character interpretations = 0.5-0.7 decaying faster)

## Game System

**Lasers & Feelings** is the core TTRPG system for this project. It is an extremely rules-light, one-page game designed by John Harper.

**Source Documents:**
- `lasers_and_feelings_rpg.pdf` - Complete game rules
- `56udLX.png` - Character sheet template

### Core Mechanics

**The Number (1-6 scale):**
- Players choose a single number from 2-5 that represents their character's balance between "Lasers" (logic, technology, cold rationality) and "Feelings" (intuition, emotion, passion)
- Lower numbers = better at Lasers (technical/logical tasks)
- Higher numbers = better at Feelings (social/emotional tasks)
- To succeed at a task: roll 1d6. If attempting a Lasers task, roll UNDER your number. If attempting a Feelings task, roll OVER your number.
- Rolling exactly your number triggers LASER FEELINGS: you succeed AND get to ask the GM a question which they must answer honestly. This grants special insight into the situation.

**Character Definition:**
Characters are defined by extremely simple attributes:
- **STYLE**: Character archetype (Alien, Android, Dangerous, Heroic, Hot-Shot, Intrepid, Savvy)
- **ROLE**: Character job/function (Doctor, Envoy, Engineer, Explorer, Pilot, Scientist, Soldier)
- **PLAYER GOAL**: What the player wants to do (e.g., "Get your character involved in crazy space adventures")
- **CHARACTER GOAL**: What the character wants (e.g., "Become Captain", "Meet New Aliens", "Prove Yourself")
- **YOUR NUMBER**: The 2-5 value representing Lasers/Feelings balance
- **EQUIPMENT**: A few items the character carries

**Ship State:**
The party shares a ship ("The Raptor" in the template) with:
- **Strengths**: What the ship is good at
- **Problem**: Current ship malfunction or issue

### Mapping to AI Agent State

The character sheet structure directly maps to AI agent state management:

**Character Layer State:**
- `name`: Character name
- `style`: One of the canonical styles from the game
- `role`: One of the canonical roles from the game
- `character_goal`: In-character motivation
- `number`: Integer 2-5 representing Lasers/Feelings balance
- `equipment`: List of items
- `speech_patterns`: Derived from STYLE and ROLE (e.g., Android might speak formally)
- `mannerisms`: Personality quirks consistent with STYLE

**Player Layer State:**
- `player_goal`: Out-of-character objective for this character
- `risk_tolerance`: Derived from chosen NUMBER (low numbers = cautious/logical, high numbers = bold/emotional)
- `decision_style`: Strategic preferences based on character archetype

**Shared Party State:**
- `ship_name`: "The Raptor" (default) or custom name
- `ship_strengths`: List of ship capabilities
- `ship_problem`: Current ship malfunction or issue that may influence decisions

**Critical Design Implications:**

1. **Decision Making**: When an AI player must make a choice, their NUMBER should influence whether they analyze logically (low number) or trust their gut (high number)

2. **Character Interpretation**: The STYLE and ROLE combination creates the character's personality lens through which they interpret player directives

3. **Simplicity**: Unlike D&D, there are no complex stats, skills, or inventory systems - just NUMBER, STYLE, ROLE, and GOALS. This simplicity is intentional and should be preserved.

4. **Ship as Shared Context**: The ship's PROBLEM can create party-wide strategic pressures (e.g., "We need to find fuel before we can leave this planet")

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Single AI Player Completes Full Turn Cycle (Priority: P1)

As a human Dungeon Master, I want a single AI player to participate in a turn-based game session where the AI makes strategic decisions and performs in-character roleplay without narrating outcomes, so that I can validate the core dual-layer architecture works and I maintain full narrative control.

**Why this priority**: This is the foundational capability. Without a working single AI player that respects turn structure and DM authority, the multi-agent system cannot exist. This represents the minimum viable product.

**Independent Test**: Can be fully tested by running a complete game turn where the DM narrates, the AI responds strategically and in-character, waits for DM adjudication, and stores the memory. Delivers immediate value: a functional AI player for solo DM playtesting.

**Acceptance Scenarios**:

1. **Given** DM narrates "A goblin jumps from behind a tree", **When** AI player processes this narration, **Then** AI discusses strategy internally, directs their character to take action expressing intent only (e.g., "I charge at the goblin with my sword raised"), and waits for DM to call for dice roll
2. **Given** AI player's character attempts an action, **When** AI generates the action description, **Then** the description contains no outcome language (no "kills", "hits", "successfully", etc.) and only expresses intent
3. **Given** DM narrates outcome "Your blade strikes the goblin's shoulder", **When** AI receives this outcome, **Then** AI character reacts in-character with emotional response but does not initiate new actions
4. **Given** a complete turn cycle finishes, **When** turn ends, **Then** system stores relevant events in memory for future retrieval

---

### User Story 2 - AI Player Prevents Narrative Overreach (Priority: P1)

As a human Dungeon Master, I want the system to detect and prevent AI players from narrating their own action outcomes, so that I remain the sole authority on story consequences and game flow is not disrupted.

**Why this priority**: Critical for maintaining DM control. If AI players can narrate outcomes, they effectively become co-DMs and undermine the entire system's purpose. Must be proven before adding complexity.

**Independent Test**: Can be tested by having an AI attempt actions and verifying that any outcome narration is caught, the AI is prompted to retry, and persistent violations are either auto-corrected or flagged for DM review.

**Acceptance Scenarios**:

1. **Given** AI player generates response containing outcome language (e.g., "I strike the goblin and kill it"), **When** system validates the response, **Then** system detects the violation, provides feedback, and requests a retry expressing intent only
2. **Given** AI player fails validation on second attempt, **When** third attempt is made, **Then** system provides stronger warning about expressing intent only
3. **Given** AI player fails validation after 3 attempts, **When** final attempt fails, **Then** system auto-corrects by filtering forbidden outcome words (kills, successfully, strikes, etc.), or flags for DM manual review if filtered result is unclear
4. **Given** AI player successfully expresses intent without outcomes, **When** validation runs, **Then** validation passes and turn proceeds to DM adjudication phase

---

### User Story 3 - Memory Persists Across Sessions (Priority: P1)

As a human Dungeon Master, I want AI players to remember events, NPCs, and decisions from previous game sessions, so that the campaign feels continuous and AI players can reference past experiences naturally.

**Why this priority**: Memory is essential for emergent behavior and realistic player simulation. Without persistent memory, each session starts from scratch, making long-term campaigns impossible and eliminating the research goal of observing party dynamics over time.

**Independent Test**: Can be tested by running a session where specific events occur (e.g., meeting an NPC, finding a quest item), ending the session, starting a new session, and verifying the AI can query and recall those events accurately.

**Acceptance Scenarios**:

1. **Given** session ends after AI player interacts with merchant NPC "Galvin", **When** session memory is stored, **Then** system records the interaction with NPC name, relationship context, and temporal information
2. **Given** new session starts 3 in-game days later, **When** DM narrates "You return to the merchant's shop", **Then** AI player queries memory for "merchant Galvin" and retrieves previous interaction details
3. **Given** AI player recalls previous interaction, **When** AI directs character, **Then** character responds appropriately based on past relationship (e.g., friendly if merchant helped before)
4. **Given** AI player queries memory for event 20+ sessions ago, **When** retrieval occurs, **Then** system returns relevant facts with temporal context indicating when memory was formed

---

### User Story 4 - Player-Character Knowledge Separation (Priority: P2)

As a human Dungeon Master, I want to provide information separately to the AI player (strategic layer) or the AI character (roleplay layer), so that the AI player can decide whether to reveal information in-character and create realistic knowledge management scenarios.

**Why this priority**: Enables sophisticated roleplay dynamics like keeping secrets, discovering information gradually, and creating trust/tension between party members. Not required for MVP but significantly enhances realism.

**Independent Test**: Can be tested by providing secret information to one AI player's strategic layer and verifying that the character doesn't automatically reveal it, but the player can choose to roleplay the discovery if desired.

**Acceptance Scenarios**:

1. **Given** DM whispers "You notice poison on the blade" to one AI player only, **When** player layer receives this information, **Then** information is marked as player-knowledge-only and not automatically shared with character layer
2. **Given** player layer knows about poison, **When** other AI players discuss whether to trust the NPC, **Then** informed player must consciously decide whether to share information in-character
3. **Given** informed player decides to reveal poison knowledge, **When** character acts, **Then** character must roleplay discovering or noticing the poison (cannot simply state it as known fact)
4. **Given** informed player decides to keep secret, **When** character acts normally, **Then** character shows no awareness of the poison in their responses

---

### User Story 5 - Multi-Agent Strategic Coordination (Priority: P2)

As a human Dungeon Master, I want 3-4 AI players to discuss strategy together out-of-character and reach consensus before their characters act, so that I can observe emergent party dynamics and coordination patterns.

**Why this priority**: Core research goal to observe social dynamics. Requires stable single-player implementation first, but is essential for the "Full System" phase and studying emergent behaviors like leadership and inside jokes.

**Independent Test**: Can be tested by presenting a decision point to multiple AI players, observing their strategic discussion, verifying consensus detection works, and confirming characters act according to group decision.

**Acceptance Scenarios**:

1. **Given** DM narrates "You reach a fork in the tunnel", **When** multiple AI players discuss options, **Then** each player expresses their strategic preference based on their personality (cautious vs aggressive)
2. **Given** players discuss and all explicitly agree on one option, **When** consensus detection runs, **Then** system recognizes unanimous consensus and proceeds immediately to character actions
3. **Given** players discuss and >50% agree but minority disagrees, **When** consensus detection runs, **Then** system recognizes majority consensus, notes dissent in memory, and proceeds with majority decision
4. **Given** players discuss but no clear majority emerges after reasonable time, **When** timeout triggers, **Then** system forces decision by vote and allows minority players to express frustration

---

### User Story 6 - Character Interprets Player Directives (Priority: P3)

As a human Dungeon Master, I want each AI character to interpret high-level strategic directives from their player layer through the lens of their unique personality, so that an "interpretation gap" creates realistic character-driven moments.

**Why this priority**: Enhances roleplay realism and creates the "my character went too far" moments that mirror real TTRPG play. Nice-to-have for richness but not essential for core functionality.

**Independent Test**: Can be tested by giving the same strategic directive to characters with different personalities and verifying they execute it differently while staying in character.

**Acceptance Scenarios**:

1. **Given** cautious player directs aggressive character "Intimidate the guard carefully", **When** character interprets directive, **Then** character shows intimidation through personality (e.g., "Do ye REALLY want to block our path, friend?") - threatening but not violent
2. **Given** aggressive player directs cautious character "Attack immediately", **When** character interprets directive, **Then** character attacks but shows hesitation through personality (e.g., "F-forgive me..." while reluctantly raising weapon)
3. **Given** player directs character to perform creative solution, **When** character acts, **Then** character adds their own flavor and mannerisms consistent with their established personality
4. **Given** character consistently acts over multiple turns, **When** reviewing turn history, **Then** character maintains consistent speech patterns, emotional responses, and behavioral quirks

---

### Edge Cases

- What happens when AI player repeatedly fails validation after 3 retry attempts? (System auto-corrects by filtering forbidden outcome words; if filtered result is unclear or broken, flags for DM manual review instead)
- How does system handle memory queries that return no results? (System should indicate no prior knowledge exists rather than inventing false information)
- What happens when multiple AI players reach stalemate with no consensus? (System must timeout and force decision by vote after reasonable discussion period - 5 rounds or 2 minutes)
- How does system handle AI player disconnection or phase failure mid-turn? (System rolls back to last stable phase, retries once, then flags for DM intervention if retry fails)
- What happens when DM provides information that contradicts stored memory? (System should update memory with DM's version as canonical truth)
- How does system handle context window approaching token limits? (System must swap recent messages for relevant memory summaries when usage reaches 80% of token limit to prevent overflow)
- What happens when AI character personality drifts over long session? (System may need to reinforce personality prompts periodically or reset between sessions)

## Requirements *(mandatory)*

### Functional Requirements

**MVP Requirements (Single AI Player):**

- **FR-001**: System MUST implement separate player and character layers for each AI, where player layer makes strategic out-of-character decisions and character layer performs in-character roleplay only
- **FR-001a**: System MUST load AI player-character configurations from a `characters.json` file at session start, containing all required attributes (name, style, role, number, goals, equipment, player personality traits)
- **FR-002**: System MUST enforce strict turn phase sequencing: DM Narration → Memory Query → Strategic Intent → Character Action → Validation → DM Adjudication → Dice Resolution (auto-rolled with DM override option) → DM Outcome → Character Reaction → Memory Storage. If a phase fails or times out, system MUST rollback to the last stable phase, retry once, and flag for DM intervention if retry fails
- **FR-003**: System MUST detect when AI generates outcome language (kills, hits, successfully, manages to, strikes, "The X falls", future narration) and prevent it from reaching DM
- **FR-004**: System MUST retry failed validation responses up to 3 times with progressively stricter prompting. After 3 failures, system MUST auto-correct by filtering forbidden outcome words (kills, hits, successfully, manages to, strikes, falls, dies, defeats, wins, etc.). If filtered result is unclear or grammatically broken, system MUST flag for DM manual review instead
- **FR-005**: System MUST store game events, character relationships, and strategic decisions in persistent memory at: every 10 turns, scene completion, critical events (NPC introductions, combat outcomes, major party decisions, quest status changes), and session end
- **FR-006**: System MUST retrieve relevant memories at: session start, strategic decision points, context window full, and explicit player queries
- **FR-007**: System MUST support memory queries like "What do we know about [NPC/location/event]?" and return facts with confidence scores (0.0-1.0 calculated from recency decay and source authority: DM narration = 1.0, player observations = 0.7-0.9 decaying with time, character interpretations = 0.5-0.7 decaying faster), temporal context, and source information
- **FR-008**: System MUST maintain separate knowledge stores for player layer (strategic knowledge) and character layer (in-character knowledge) for each AI
- **FR-009**: System MUST allow DM to provide information to player layer only, character layer only, or both, with enforcement that characters cannot use player-only knowledge
- **FR-010**: System SHOULD complete turn execution within 10 seconds (P95) when LLM APIs are responsive, but timing is not critical for MVP (research focus allows flexible pacing beyond this target)
- **FR-011**: System MUST preserve game state on unexpected errors and be recoverable from any phase without data loss
- **FR-012**: System MUST include built-in dice roller supporting 1d6 rolls (Lasers & Feelings mechanics only) that auto-rolls by default, with DM ability to manually override any result before resolution
- **FR-013**: System MUST handle LLM API failures, rate limits, and timeouts by retrying with exponential backoff (2s, 5s, 10s delays for maximum 5 attempts within ~35 seconds), then trigger phase rollback and DM flag if all retries exhausted

**Full System Requirements (3-4 AI Players):**

- **FR-014**: System MUST support 3-4 simultaneous AI player-character pairs without performance degradation
- **FR-015**: System MUST provide communication channel for player layers to discuss strategy together out-of-character, not visible to character layers
- **FR-016**: System MUST detect when consensus is reached among players using three states: unanimous (all agree explicitly), majority (>50% agree), or conflicted (no clear majority)
- **FR-017**: System MUST timeout strategic debates after reasonable discussion period (5 rounds of discussion or 2 minutes) and force decision by vote when conflicted
- **FR-018**: System MUST maintain shared party memory layer containing group consensus facts, shared experiences, and party culture, separate from personal memories
- **FR-019**: System MUST distinguish personal memories (per AI) from shared memories (party-wide) and handle conflicting memories using precedence rules: DM narration (canonical truth) > player layer memory > character layer memory. System MUST log all detected conflicts with source attribution for researcher review.
- **FR-020**: System MUST allow multiple players to discuss simultaneously (asynchronously) and multiple characters to declare actions in parallel
- **FR-021**: System MUST log all agent interactions, phase transitions, validation failures, memory queries, and consensus outcomes as structured JSON entries containing: event_type, timestamp (ISO 8601), session_id, turn_number, and event-specific fields. Logs must be appendable and support filtering by event type for research analysis

**Observability & Research Requirements:**

- **FR-022**: System MUST track validation failure rates, API retry patterns, agent response times, and turn completion metrics
- **FR-023**: System MUST record relationship development over time between AI players and track party dynamics patterns
- **FR-024**: System MUST enable researcher to inspect original agent reasoning, memory formation, and decision-making processes
- **FR-025**: System MUST flag unexpected behaviors for researcher review (e.g., novel coordination patterns, emergent social dynamics)

### Key Entities

- **AI Player (Base Persona)**: Strategic decision-maker operating out-of-character. Has personality traits represented as normalized floating-point values (0.0-1.0 scale): analytical score, risk tolerance, detail orientation, emotional memory, assertiveness, cooperativeness, openness, rule adherence, roleplay intensity. Makes high-level strategic decisions, discusses with other players, provides directives to their character.

- **AI Character (Performer)**: In-character roleplay performer. Has in-game personality (class, background, bonds, ideals, flaws, speech patterns, mannerisms). Receives directives from player layer, interprets through personality lens, performs roleplay expressing intent only, never narrates outcomes.

- **Memory**: Persistent knowledge stored across sessions. Types include: Episodic (session-based conversation threads and events with temporal context), Semantic (NPC personalities, world facts, quest status, party norms), Procedural (combat strategies, negotiation patterns, coordination tactics). Contains confidence scores (0.0-1.0 based on recency decay and source authority: DM narration = 1.0, player observations = 0.7-0.9 decaying over time, character interpretations = 0.5-0.7 decaying faster), temporal context, source attribution, and relationship information.

- **Turn Phase**: Discrete step in turn-based gameplay cycle. Enforces strict sequencing to prevent chaos and ensure DM authority. Phases must be atomic (complete or rollback to maintain state consistency). On failure or timeout, system rolls back to last stable phase, retries once, then flags for DM intervention if retry fails.

- **Consensus State**: Agreement level among multiple AI players during strategic discussion. Three types: Unanimous (all explicitly agree, proceed immediately), Majority (>50% agree, note dissent, proceed with majority), Conflicted (no majority, timeout after 5 rounds or 2 minutes, force vote).

- **Directive**: High-level instruction from player layer to character layer. One-way communication providing strategic guidance that character interprets through their personality (creates "interpretation gap" for realistic roleplay).

- **Knowledge Separation**: Distinction between what player layer knows versus what character layer knows. Enables scenarios where player has meta-knowledge but character must roleplay discovering information.

## Success Criteria *(mandatory)*

### Measurable Outcomes

**MVP Success (Single AI Player):**

- **SC-001**: Single AI player completes full turn cycles without breaking game flow, maintaining character consistency across 100+ consecutive turns
- **SC-002**: System prevents over 95% of narrative overreach attempts on first validation pass
- **SC-003**: Memories persist correctly across sessions, with accurate recall when queried by DM or AI after 10+ sessions
- **SC-004**: System handles LLM API failures gracefully with exponential backoff, successfully recovering from transient errors in 90% of retry attempts
- **SC-005**: DM subjective rating: "I feel in control of the story" scores 8 or higher out of 10 after 5+ session campaign
- **SC-006**: DM subjective rating: "The AI feels like a real player" scores 7 or higher out of 10 after 5+ session campaign
- **SC-007**: System achieves over 95% uptime during gameplay sessions with no stuck states requiring manual intervention

**Full System Success (Multi-Agent):**

- **SC-008**: 3-4 AI players coordinate successfully during strategic discussions, reaching consensus (unanimous, majority, or vote) within reasonable time for 90% of decisions
- **SC-009**: Emergent party dynamics become observable within 5 gameplay sessions: leadership patterns emerge (one agent becomes de facto leader), repeated strategic preferences develop (party culture), or relationship dynamics appear (preference for certain teammates' suggestions)
- **SC-010**: AI players spontaneously reference shared experiences from previous sessions without prompting, demonstrating memory integration
- **SC-011**: System maintains stable performance with 3-4 players over 2-hour sessions with no degradation in response quality or memory accuracy

**Research & Quality:**

- **SC-012**: System logs 100% of phase transitions, agent interactions, and validation failures as structured JSON entries without missing data points, enabling programmatic research analysis
- **SC-013**: Memory retrieval returns accurate, relevant results consistently without performance degradation as memory store grows
- **SC-014**: Validation retry mechanism succeeds in correcting narrative overreach within 3 attempts for 90% of violations
- **SC-015**: DM can operate the system without technical knowledge, with intuitive commands and helpful error messages (validated through usability testing with target DM)

## Assumptions

- Human DM is present and engaged throughout each session, providing timely input (system does not run autonomously)
- Game sessions are discrete events with clear start/end boundaries, typically lasting 2-4 hours
- Campaigns consist of multiple sessions conducted over weeks or months, creating opportunities for long-term memory and dynamics
- Large language models (GPT-4 or equivalent) are available and capable of following complex instructions while maintaining personality consistency
- Primary goal is research and observation of emergent behavior; production-ready polish is not required, and rough edges are acceptable if core functionality works
- Timing flexibility: Turn execution speed is not critical for research purposes; system can wait for LLM API responses with exponential backoff retry logic
- This is a single-instance system for one DM; no concurrent games or multi-user support required
- Development and operation occur on local machine with local Neo4j database; no cloud deployment or API access for third parties needed
- Focus is exclusively on "Lasers and Feelings" mechanics; support for Dungeon World in future version
- Target token budget is under 5000 tokens per turn cycle, requiring efficient memory compression and context management
- Session structure follows traditional TTRPG pacing with discrete turns, clear DM narration points, and player response opportunities

## Out of Scope

The following capabilities are explicitly **not** included in this feature:

**Automated DMing:**
- No AI Dungeon Master functionality
- No automated NPC generation or dialogue
- No procedural world generation or automatic story creation
- Human DM provides all narration, adjudication, and world simulation

**Advanced User Interfaces:**
- No voice or audio interface for interactions
- No visual character sheets, dashboards, or graphical displays
- No real-time memory visualization tools (researcher inspects database directly)
- No web UI; command-line interface is sufficient
- No integration with virtual tabletop platforms (Roll20, Foundry VTT, etc.)

**Multi-Campaign Features:**
- No character progression or persistence across different campaigns
- No world state persistence between separate campaigns
- No campaign library, organization system, or campaign management tools

**Commercial & Multi-User:**
- No user authentication or account management
- No multi-user support or concurrent DMs
- No cloud hosting or deployment infrastructure
- No public API or third-party integration capabilities

**Game System Variety:**
- No support for TTRPG systems other than Lasers and Feelings & Dungeon World
- No custom rule systems or homebrew mechanics

**Future Memory Features (Post-MVP):**
- No realistic memory degradation or corruption based on time (planned for post-MVP)
- No personality-specific memory drift patterns
- No rehearsal tracking or importance scoring for memory retention
- No temporal queries like "What did we know at Session 10?" in MVP phase

## Dependencies

- Large language model API access (GPT-4 or equivalent) for AI player and character agent implementation
- Neo4j graph database (local instance) for memory storage supporting relationship traversal, temporal tracking, and complex queries on NPC relationships, events, and party dynamics
- Command-line interface framework using turn-based prompts (system prompts DM at each phase: "Enter narration:", "Override roll? [y/n]:", etc.)
- Built-in dice rolling functionality supporting 1d6 rolls (Lasers & Feelings mechanics only) with DM override capability
- JSON configuration file (`characters.json`) for defining AI player-character pairs with all required attributes (name, style, role, number, goals, equipment, player personality traits)
