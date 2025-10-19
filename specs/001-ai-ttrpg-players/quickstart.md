# Quickstart Guide: AI TTRPG Player System

**Last Updated**: October 19, 2025
**Target Audience**: Dungeon Masters and researchers who want to run AI-powered TTRPG sessions locally
**Game System**: Lasers & Feelings (rules-light sci-fi RPG)

This guide will walk you through setting up and running your first AI TTRPG game session in 30 minutes or less.

---

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Installation](#installation)
3. [Infrastructure Setup](#infrastructure-setup)
4. [Configuration](#configuration)
5. [Running Your First Session](#running-your-first-session)
6. [Sample DM Interaction Flow](#sample-dm-interaction-flow)
7. [Troubleshooting](#troubleshooting)
8. [Next Steps](#next-steps)

---

## Prerequisites

Before you begin, ensure you have:

- **macOS or Linux** (Windows users: use WSL2)
- **Python 3.11 or higher** installed
- **Docker Desktop** installed and running (for Neo4j and Redis)
- **OpenAI API key** with GPT-4o access
- **Terminal/shell** access
- **15GB free disk space** (for Docker images and database)

---

## Installation

### Step 1: Install uv (Python Package Manager)

We use `uv` for fast, modern Python package management.

```bash
# Install uv (macOS/Linux)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Verify installation
uv --version
```

Expected output:
```
uv 0.7.4 (or newer)
```

### Step 2: Clone and Setup Project

```bash
# Navigate to your projects directory
cd ~/workingfolder

# Clone the repository (or navigate to existing clone)
cd ttrpg-ai

# Initialize Python project with uv
uv init

# Install project dependencies
uv add langgraph graphiti-core openai pydantic redis rq neo4j pytest pytest-asyncio
```

**Expected output:**
```
Resolved 47 packages in 2.3s
Installed 47 packages in 1.8s
```

---

## Infrastructure Setup

The system requires Neo4j (graph database) and Redis (task queue) running locally via Docker.

### Step 1: Create Docker Compose Configuration

Create a file named `docker-compose.yml` in the project root:

```bash
cd /Volumes/workingfolder/ttrpg-ai
```

Copy and paste this configuration into `docker-compose.yml`:

```yaml
version: '3.8'

services:
  neo4j:
    image: neo4j:5.15-community
    container_name: ttrpg-neo4j
    ports:
      - "7474:7474"  # HTTP
      - "7687:7687"  # Bolt
    environment:
      - NEO4J_AUTH=neo4j/ttrpgpassword
      - NEO4J_PLUGINS=["apoc"]
      - NEO4J_dbms_memory_heap_max__size=2G
      - NEO4J_dbms_memory_pagecache_size=1G
    volumes:
      - neo4j_data:/data
      - neo4j_logs:/logs
    healthcheck:
      test: ["CMD-SHELL", "cypher-shell -u neo4j -p ttrpgpassword 'RETURN 1'"]
      interval: 10s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    container_name: ttrpg-redis
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    command: redis-server --appendonly yes
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 3s
      retries: 5

volumes:
  neo4j_data:
  neo4j_logs:
  redis_data:
```

### Step 2: Start Infrastructure

```bash
# Start Neo4j and Redis in the background
docker-compose up -d

# Wait for services to be healthy (30-60 seconds)
docker-compose ps
```

**Expected output:**
```
NAME                IMAGE                  STATUS
ttrpg-neo4j        neo4j:5.15-community   Up 30 seconds (healthy)
ttrpg-redis        redis:7-alpine         Up 30 seconds (healthy)
```

### Step 3: Verify Neo4j Access

Open your browser and navigate to:
```
http://localhost:7474
```

**Login credentials:**
- Username: `neo4j`
- Password: `ttrpgpassword`

You should see the Neo4j Browser interface. If you see a connection error, wait another minute and refresh.

### Step 4: Verify Redis Access

```bash
# Test Redis connection
docker exec -it ttrpg-redis redis-cli ping
```

**Expected output:**
```
PONG
```

---

## Configuration

### Step 1: Create Environment Configuration

Create a `.env` file in the project root with your API keys and connection details:

```bash
cd /Volumes/workingfolder/ttrpg-ai
```

Create `.env` file with the following content:

```bash
# OpenAI Configuration
OPENAI_API_KEY=sk-your-openai-api-key-here
OPENAI_MODEL=gpt-4o

# Neo4j Configuration
NEO4J_URI=bolt://localhost:7687
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=ttrpgpassword

# Redis Configuration
REDIS_HOST=localhost
REDIS_PORT=6379

# Application Settings
LOG_LEVEL=INFO
CORRUPTION_STRENGTH=0.5
MAX_TURN_TIME_SECONDS=300
```

**Important:** Replace `sk-your-openai-api-key-here` with your actual OpenAI API key.

> **Tip:** Keep your `.env` file secure. Add it to `.gitignore` to prevent accidental commits.

### Step 2: Create Character Configuration

Create a directory for game configurations:

```bash
mkdir -p config
cd config
```

Create `characters.json` with a single AI player for your first session:

```json
{
  "campaign_name": "Voyage of the Raptor",
  "dm_name": "Ryan",
  "party": {
    "ship_name": "The Raptor",
    "ship_strengths": ["Fast", "Maneuverable", "Well-armed"],
    "ship_problem": "Fuel cells depleting rapidly"
  },
  "corruption_strength": 0.3,
  "characters": [
    {
      "player": {
        "agent_id": "agent_alex_001",
        "player_name": "Alex",
        "player_goal": "Get character involved in crazy space adventures",
        "analytical_score": 0.7,
        "risk_tolerance": 0.6,
        "detail_oriented": 0.8,
        "emotional_memory": 0.4,
        "assertiveness": 0.6,
        "cooperativeness": 0.7,
        "openness": 0.8,
        "rule_adherence": 0.7,
        "roleplay_intensity": 0.9
      },
      "character": {
        "character_id": "char_zara_001",
        "name": "Zara-7",
        "style": "Android",
        "role": "Engineer",
        "number": 2,
        "character_goal": "Understand human emotions",
        "equipment": ["Multi-tool", "Diagnostic scanner", "Spare circuits"],
        "speech_patterns": [
          "Speaks formally and precisely",
          "Uses technical jargon",
          "Asks clarifying questions about emotions"
        ],
        "mannerisms": [
          "Tilts head when confused",
          "Pauses before expressing opinions",
          "Observes humans intently"
        ]
      }
    }
  ]
}
```

**Understanding the Configuration:**

- **Player Layer (`player`)**: Defines the strategic personality traits that guide decision-making
  - `analytical_score`: 0.7 = Prefers logical analysis over gut feelings
  - `risk_tolerance`: 0.6 = Moderately cautious
  - `assertiveness`: 0.6 = Sometimes leads, sometimes follows

- **Character Layer (`character`)**: Defines the in-game roleplay personality
  - `number`: 2 = Excellent at "Lasers" (technical/logical) tasks, poor at "Feelings" (social/emotional)
  - `style`: "Android" = Formal, logical, learning about emotions
  - `role`: "Engineer" = Ship repair and technical expertise

> **Note:** The `number` field (2-5) is critical in Lasers & Feelings. Lower numbers excel at technical tasks, higher numbers excel at social tasks.

### Step 3: Create characters.example.json

Copy the configuration for reference:

```bash
cp characters.json characters.example.json
```

---

## Running Your First Session

### Step 1: Start the Game Session

```bash
# From project root
cd /Volumes/workingfolder/ttrpg-ai

# Run the game
uv run python -m src.cli.session --config config/characters.json
```

**Expected output:**
```
╔════════════════════════════════════════════════════════════╗
║        AI TTRPG Player System - Lasers & Feelings         ║
║                  Campaign: Voyage of the Raptor            ║
╚════════════════════════════════════════════════════════════╝

Loaded 1 AI player:
  - Alex playing Zara-7 (Android Engineer)

Ship: The Raptor
  Strengths: Fast, Maneuverable, Well-armed
  Problem: Fuel cells depleting rapidly

Session starting...
[Turn 1] Awaiting DM narration...
```

### Step 2: Provide Initial Narration

You'll see a prompt:

```
DM >
```

Enter your scene description:

```
The Raptor drifts through the debris field of an ancient space station. Your sensors detect faint power readings from the station's docking bay. The fuel gauge reads 12% - enough for one jump, maybe two if you're lucky.
```

Press `Enter`.

### Step 3: Watch the AI Player Respond

The system will now execute the turn cycle:

1. **Memory Query Phase**: AI searches for relevant past experiences
2. **Strategic Intent Phase**: AI player decides what to do
3. **Character Action Phase**: AI character performs in-character roleplay

**Expected output:**
```
[Phase: Memory Query]
Querying memories for context... No previous memories found.

[Phase: Strategic Intent]
Alex (Player): We need fuel badly. Investigating the station is risky but necessary.
Let's be cautious and look for fuel sources while watching for danger.

[Phase: Character Action]
Zara-7: *tilts head, analyzing sensor readouts*
"Captain, I am detecting a 73% probability that the station's fuel reserves
remain intact. I suggest we attempt to dock and investigate. However, I
recommend proceeding with caution - the debris field suggests potential hazards."

*adjusts equipment belt, preparing diagnostic scanner*

[Phase: Validation] ✓ PASS (no outcome narration detected)

Awaiting DM adjudication...
DM >
```

### Step 4: Adjudicate the Action

The AI has stated an *intent* but hasn't narrated an outcome. Now you decide what happens:

```
DM > You successfully dock with the station. As you enter the bay, emergency lighting flickers on. Roll to see if you notice the security turrets activating.
```

### Step 5: Dice Resolution

The system will prompt for task type and automatically roll dice:

```
[Phase: Dice Resolution]
Is this a Lasers (technical/logical) or Feelings (social/emotional) task?
1. Lasers
2. Feelings

Choice > 1

Task Type: Lasers (noticing technical details)
Character Number: 2 (excellent at Lasers tasks)
Rolling 1d6... Result: 1

Success! (rolled 1, needed <2 for Lasers task)

DM > Enter outcome narration:
```

Narrate the result:

```
DM > Zara-7's sensors immediately detect the turrets powering up. You have just enough time to take cover behind some crates before they activate.
```

### Step 6: Character Reaction

The AI character will now react in-character:

```
[Phase: Character Reaction]
Zara-7: *crouches behind crates, scanner still active*
"Acknowledged. Security systems are active - this suggests the station may
not be as abandoned as we hypothesized. I am detecting three turret emplacements.
Perhaps we should attempt to locate a security terminal?"

*pauses, processing*

"Captain, may I ask - do you experience fear in situations such as this?
Your heart rate appears elevated."

[Phase: Memory Storage]
Storing turn events... ✓ Saved to memory.

[Turn 2] Awaiting DM narration...
DM >
```

**Congratulations!** You've completed your first turn. Notice how:
- The AI only stated *intent* ("I suggest we attempt to dock")
- You controlled all *outcomes* (successful docking, turrets activating, time to take cover)
- The AI character stayed in-character with Android mannerisms
- The system tracked everything in memory for future reference

---

## Sample DM Interaction Flow

Here's a typical turn-based interaction pattern:

### Turn Structure

```
┌─────────────────────────────────────────┐
│ 1. DM Narration (You)                  │
│    "A pirate ship appears on sensors"   │
└─────────────────────────────────────────┘
              ↓
┌─────────────────────────────────────────┐
│ 2. AI Strategic Discussion (Automatic) │
│    Alex: "We should try negotiating"    │
└─────────────────────────────────────────┘
              ↓
┌─────────────────────────────────────────┐
│ 3. AI Character Action (Automatic)     │
│    Zara-7: "I attempt to hail them"    │
└─────────────────────────────────────────┘
              ↓
┌─────────────────────────────────────────┐
│ 4. DM Adjudication (You)               │
│    "They respond. Roll for Feelings."   │
└─────────────────────────────────────────┘
              ↓
┌─────────────────────────────────────────┐
│ 5. Dice Roll (Automatic or Override)   │
│    Rolled 4 vs Number 2 = Failure       │
└─────────────────────────────────────────┘
              ↓
┌─────────────────────────────────────────┐
│ 6. DM Outcome (You)                    │
│    "They mock your formal speech"       │
└─────────────────────────────────────────┘
              ↓
┌─────────────────────────────────────────┐
│ 7. AI Character Reaction (Automatic)   │
│    Zara-7: "I do not understand..."     │
└─────────────────────────────────────────┘
```

### DM Commands Reference

While the game is running, you can use these commands:

| Command | Description | Example |
|---------|-------------|---------|
| `[scene text]` | Provide narration | `A door opens ahead` |
| `/override [1-6]` | Override dice roll | `/override 3` |
| `/memory [query]` | Query AI memories | `/memory merchant` |
| `/info` | Show character stats | `/info` |
| `/save` | Save current session | `/save` |
| `/quit` | End session | `/quit` |

### Example: Multi-Turn Session

```
DM > The merchant offers you 50 gold pieces for the data core.

[Strategic Intent]
Alex: That's a reasonable price, but let's see if we can negotiate higher.

[Character Action]
Zara-7: "I appreciate your offer. However, this data core contains
classified research. Would you consider 75 gold pieces?"

DM > The merchant laughs. "You're a tough one. Roll for Feelings to see if
     you can convince them."

[Dice Resolution]
Task Type: Feelings (social negotiation)
Rolling 1d6... Result: 5
Character Number: 2
Outcome: Success! (rolled 5, needed >2)

DM > The merchant grins. "Alright, 75 it is. You drive a hard bargain."

[Character Reaction]
Zara-7: *tilts head* "I was merely stating the objective value. Is this
what humans call 'negotiation'? Fascinating."
```

---

## Troubleshooting

### Issue: "Cannot connect to Neo4j"

**Symptoms:**
```
Error: Unable to connect to bolt://localhost:7687
```

**Solutions:**

1. Check if Neo4j container is running:
   ```bash
   docker-compose ps
   ```

2. If not running, start it:
   ```bash
   docker-compose up -d neo4j
   ```

3. Wait for health check to pass:
   ```bash
   docker-compose logs -f neo4j
   # Wait for "Started."
   ```

4. Verify connection manually:
   ```bash
   docker exec -it ttrpg-neo4j cypher-shell -u neo4j -p ttrpgpassword
   # Should connect successfully
   ```

### Issue: "OpenAI API rate limit exceeded"

**Symptoms:**
```
Error: Rate limit reached for gpt-4o
```

**Solutions:**

1. The system will automatically retry with exponential backoff (2s, 5s, 10s)
2. If persistent, wait 60 seconds and continue
3. Check your OpenAI API quota at https://platform.openai.com/usage
4. Consider using GPT-4o-mini for testing (edit `.env`):
   ```bash
   OPENAI_MODEL=gpt-4o-mini
   ```

### Issue: "Validation failed after 3 attempts"

**Symptoms:**
```
[Validation] ✗ FAILED (attempt 3/3)
Violations: Character narrated outcome
```

**What this means:**
The AI character tried to narrate the result of their action instead of just stating intent. This is expected behavior during early testing.

**Solutions:**

1. The system will auto-correct by removing forbidden language
2. This is logged for research purposes
3. If happening frequently, the AI may need prompt tuning

### Issue: "Memory retrieval timeout"

**Symptoms:**
```
[Memory Query] Timeout after 5 seconds
```

**Solutions:**

1. Check Neo4j is responsive:
   ```bash
   docker-compose logs neo4j | grep -i error
   ```

2. Restart Neo4j if needed:
   ```bash
   docker-compose restart neo4j
   ```

3. Check disk space (Neo4j needs room to grow):
   ```bash
   df -h
   ```

### Issue: "Docker containers won't start"

**Symptoms:**
```
Error: Ports are not available
```

**Solutions:**

1. Check if ports 7474, 7687, or 6379 are already in use:
   ```bash
   lsof -i :7474
   lsof -i :7687
   lsof -i :6379
   ```

2. If another service is using these ports, either:
   - Stop that service, or
   - Edit `docker-compose.yml` to use different ports:
     ```yaml
     ports:
       - "7475:7474"  # Use 7475 instead of 7474
       - "7688:7687"  # Use 7688 instead of 7687
     ```

3. Update `.env` file to match new ports:
   ```bash
   NEO4J_URI=bolt://localhost:7688
   ```

### Issue: "Character personality drifts over time"

**Symptoms:**
The AI character starts acting inconsistently with their established personality after many turns.

**Solutions:**

1. This is a known behavior being tracked for research
2. Save the session and start a new one to reset personality:
   ```
   DM > /save
   DM > /quit
   ```

3. The memory will persist, but personality prompts will be reinforced on restart

### Getting More Help

If you encounter issues not covered here:

1. Check logs:
   ```bash
   docker-compose logs
   ```

2. Check Neo4j Browser (http://localhost:7474) for database issues

3. Enable debug logging in `.env`:
   ```bash
   LOG_LEVEL=DEBUG
   ```

4. Open a GitHub issue with:
   - Error message
   - Relevant logs
   - `characters.json` configuration (remove any sensitive data)

---

## Next Steps

### For DMs: Expanding Your Game

**Add More AI Players** (Multi-Agent Mode)

Edit `config/characters.json` and add 2-3 more character configurations. The system supports up to 4 AI players.

Example second character:
```json
{
  "player": {
    "agent_id": "agent_morgan_002",
    "player_name": "Morgan",
    "player_goal": "Create dramatic moments and character conflicts",
    "analytical_score": 0.3,
    "risk_tolerance": 0.9,
    "assertiveness": 0.8,
    "cooperativeness": 0.5,
    "openness": 0.7,
    "rule_adherence": 0.4,
    "roleplay_intensity": 0.8,
    "detail_oriented": 0.5,
    "emotional_memory": 0.8
  },
  "character": {
    "character_id": "char_rax_002",
    "name": "Rax Stellar",
    "style": "Hot-Shot",
    "role": "Pilot",
    "number": 5,
    "character_goal": "Become the most famous pilot in the galaxy",
    "equipment": ["Lucky dice", "Flight jacket", "Personal shield"],
    "speech_patterns": [
      "Speaks with bravado",
      "Uses pilot jargon",
      "Makes risky boasts"
    ],
    "mannerisms": [
      "Adjusts collar when confident",
      "Smirks at danger",
      "References past exploits"
    ]
  }
}
```

With multiple players, you'll see:
- **Out-of-character discussions** where players debate strategy
- **Consensus detection** (unanimous, majority, or conflicted)
- **Emergent party dynamics** (leadership patterns, inside jokes)

**Customize Memory Settings**

In `characters.json`, adjust `corruption_strength`:
- `0.0` = Perfect memory (unrealistic)
- `0.3` = Minor memory degradation (recommended)
- `0.5` = Moderate memory corruption (realistic)
- `1.0` = Maximum memory corruption (challenging)

**Query Memories Mid-Game**

Use the `/memory` command to see what AI players remember:
```
DM > /memory merchant Galvin
```

This will show:
- All memories related to "merchant Galvin"
- When memories were formed (session, day)
- Confidence scores
- Any corruption detected

### For Developers: Understanding the System

**Explore the Codebase**

Key files to review (once implemented):
```
src/agents/player_agent.py      # Strategic decision-making
src/agents/character_agent.py   # In-character roleplay
src/orchestration/turn_graph.py # LangGraph state machine
src/memory/store.py             # Neo4j memory operations
```

**Run the Test Suite**

```bash
# Unit tests
uv run pytest tests/unit/ -v

# Integration tests
uv run pytest tests/integration/ -v

# End-to-end tests (requires infrastructure running)
uv run pytest tests/e2e/ -v
```

**Inspect the Database**

Open Neo4j Browser (http://localhost:7474) and run queries:

```cypher
// View all memories
MATCH (n)-[e:Edge]-(m)
RETURN n, e, m
LIMIT 25

// Find memories for specific agent
MATCH (n)-[e:Edge]-(m)
WHERE e.agent_id = 'agent_alex_001'
RETURN n, e, m

// View memory by session
MATCH (n)-[e:Edge]-(m)
WHERE e.session_number = 1
RETURN n, e, m
```

**Monitor Redis State**

```bash
# Connect to Redis CLI
docker exec -it ttrpg-redis redis-cli

# View turn state
127.0.0.1:6379> HGETALL turn:state

# View message history
127.0.0.1:6379> LRANGE channel:ic:messages 0 -1
```

### For Researchers: Analyzing Behavior

**Enable Research Logging**

The system logs all agent interactions for analysis. Logs include:
- Strategic decision reasoning
- Consensus patterns
- Validation failures
- Memory queries and retrievals
- Turn execution metrics

**Export Data for Analysis**

```bash
# Export all memories to JSON
uv run python -m src.tools.export_memories --output memories.json

# Export turn logs
uv run python -m src.tools.export_logs --session 1 --output session1_logs.json
```

**Track Emergent Behaviors**

Over 5+ sessions, watch for:
- **Leadership patterns**: Does one AI consistently lead discussions?
- **Party culture**: Do shared strategies emerge?
- **Relationship dynamics**: Do AIs prefer certain teammates?
- **Inside jokes**: Do repeated phrases or references develop?

**Research Questions to Explore**

- How does personality (`analytical_score`, `risk_tolerance`) affect strategic choices?
- Do AI players with high `cooperativeness` defer more often?
- How accurate is memory retrieval after 10+ sessions?
- What consensus patterns emerge in multi-agent discussions?

---

## Appendix: Lasers & Feelings Quick Reference

### Core Mechanic

**Character Number (2-5):**
- **2**: Excellent at Lasers (logic, tech), poor at Feelings (social, emotion)
- **3**: Good at Lasers, weak at Feelings
- **4**: Weak at Lasers, good at Feelings
- **5**: Poor at Lasers, excellent at Feelings

### Rolling Dice

**When attempting a task:**
1. DM determines if it's a "Lasers" or "Feelings" task
2. Roll 1d6
3. **Lasers task**: Roll **under** your number to succeed
4. **Feelings task**: Roll **over** your number to succeed
5. **Exact match**: Success with complication/twist

**Examples:**
- Zara-7 (number 2) repairs a ship: Lasers task, needs to roll 1 = Success!
- Zara-7 (number 2) negotiates with pirates: Feelings task, needs 3-6 = Hard!
- Rax (number 5) pilots through asteroid field: Lasers task, needs 1-4 = Easy!

### Character Archetypes

| Style | Description |
|-------|-------------|
| **Alien** | Strange customs, unique perspective |
| **Android** | Logical, learning emotions |
| **Dangerous** | Intimidating, aggressive |
| **Heroic** | Brave, inspirational |
| **Hot-Shot** | Cocky, skilled |
| **Intrepid** | Curious, bold |
| **Savvy** | Clever, resourceful |

### Character Roles

| Role | Specialty |
|------|-----------|
| **Doctor** | Healing, biology |
| **Envoy** | Diplomacy, languages |
| **Engineer** | Ship repair, gadgets |
| **Explorer** | Navigation, survival |
| **Pilot** | Ship flying, combat |
| **Scientist** | Research, analysis |
| **Soldier** | Combat, tactics |

---

## Summary

You now have:

✅ A working AI TTRPG Player System
✅ Neo4j and Redis infrastructure running
✅ Your first AI player-character pair configured
✅ Experience running a complete turn cycle
✅ Understanding of the DM-AI interaction pattern

**Remember the core principle:** You (the DM) control all outcomes. The AI only states *intent* and reacts to *your* narration. This keeps you firmly in control of the story while the AI provides realistic player behavior.

**Start playing and observe emergent behaviors!** After 5+ sessions, you'll begin to see personality patterns, memory integration, and realistic player-like decision-making.

Have fun exploring space with your AI crew! 🚀

---

**Questions or Issues?** See the [Troubleshooting](#troubleshooting) section or open a GitHub issue.
