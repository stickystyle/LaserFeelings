# AI TTRPG Player System - Quickstart Guide

**Version**: 1.0
**Date**: October 18, 2025
**Estimated Setup Time**: 10 minutes

---

## Prerequisites

Before starting, ensure you have:

- **Python 3.11+** installed (`python --version`)
- **Docker Desktop** installed and running
- **OpenAI API key** with access to GPT-4o
- **macOS or Linux** (Windows with WSL2 also supported)
- **8GB RAM minimum** (for Neo4j + Redis)

---

## Quick Setup (5 Steps)

### 1. Clone and Initialize Project

```bash
# Clone repository
git clone https://github.com/your-org/ttrpg-ai.git
cd ttrpg-ai

# Initialize uv project (if not already initialized)
uv init

# Verify uv installation
uv --version
```

### 2. Install Dependencies

```bash
# Add all required packages via uv
uv add langgraph graphiti-core neo4j redis rq openai pydantic tenacity loguru python-dotenv

# Install development dependencies
uv add --dev pytest pytest-asyncio pytest-mock black ruff

# Verify installation
uv run python -c "import langgraph, graphiti_core, neo4j, redis; print('Dependencies OK')"
```

### 3. Start Infrastructure (Docker Compose)

```bash
# Start Neo4j and Redis
docker-compose up -d

# Verify services are running
docker ps
# Should show: neo4j:5.x and redis:7-alpine

# Wait 10 seconds for Neo4j to fully initialize
sleep 10
```

**Access Neo4j Browser**: Open [http://localhost:7474](http://localhost:7474)
- Username: `neo4j`
- Password: `password` (change in `.env` for production)

### 4. Configure Environment

```bash
# Copy example environment file
cp .env.example .env

# Edit .env with your OpenAI API key
# Use your preferred editor (nano, vim, vscode, etc.)
nano .env
```

**Required `.env` configuration**:
```bash
# LLM Configuration
OPENAI_API_KEY=sk-...  # Your actual API key

# Database Configuration (defaults for Docker Compose)
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=password

# Redis Configuration
REDIS_URL=redis://localhost:6379

# Memory Corruption Settings
CORRUPTION_ENABLED=true
CORRUPTION_STRENGTH=0.3  # Start conservative (0.0-1.0)

# Observability (optional)
LANGSMITH_TRACING_ENABLED=false
```

### 5. Initialize Database and Seed Data

```bash
# Create Neo4j indexes for optimal performance
uv run scripts/setup_neo4j.py

# Create sample agent personalities
uv run scripts/seed_personalities.py

# Verify setup
uv run scripts/verify_setup.py
```

Expected output:
```
✓ Neo4j connection successful
✓ Redis connection successful
✓ Indexes created: agent_session_temporal, valid_at, invalid_at, fact_fulltext
✓ Personalities seeded: Alex (cautious), Blair (aggressive), Casey (diplomatic)
✓ Setup complete!
```

---

## Run Your First Session

### Start RQ Workers (Background Processes)

Open a **new terminal** and run:

```bash
# Start 6 RQ workers (2x 3 agents for parallelism)
uv run rq worker base_persona character validation --url redis://localhost:6379
```

Keep this terminal running during your session.

### Launch DM Interface

In your **original terminal**:

```bash
# Start command-line DM interface
uv run src/interface/dm_cli.py
```

### Example Session Interaction

```
===========================================
AI TTRPG Player System - DM Interface
===========================================
Session 1, Turn 1
Active Agents: Alex (cautious), Blair (aggressive), Casey (diplomatic)

DM> narrate You enter a dark tavern. Three shady figures eye you from the corner.

[System: Memory retrieval in progress...]
[System: OOC discussion starting...]

Alex (OOC): This feels like a trap. I suggest we approach cautiously and gauge their intentions before committing.
Blair (OOC): We should show strength. If they're trouble, better to strike first.
Casey (OOC): Let's try talking first. Maybe they have information or a job offer.

[System: Consensus detected - MAJORITY (Casey+Alex diplomatic, Blair dissents)]
[System: Proceeding to character actions...]

Thrain Ironfoot (Alex's character): *approaches the bar slowly, hand resting on axe hilt* "Barkeep, an ale. And tell me, friend, what brings armed folk to a place like this?"

Kira Swiftblade (Blair's character): *moves to flank the shady figures, trying to position for a quick strike if needed*

Finn Silvertongue (Casey's character): *smiles warmly and waves* "Well met, travelers! Mind if we join you for a drink?"

DM> roll 1d20+3 dc 12
[System: Thrain rolls Perception: 1d20+3 = 17 (success)]

DM> success The bartender nervously whispers "Those three are looking for hired muscle. Dragon problem up north."

Thrain Ironfoot: *nods grimly* "A dragon, eh? That's proper work for proper coin, I'd wager."

[System: Turn complete. Memory consolidating...]
[System: Stored 8 new memories for session 1]

DM> end_session
[System: Session 1 ended. Total turns: 12. Memories: 45 episodic, 12 semantic]
```

---

## DM Command Reference

### Core Commands

| Command | Syntax | Example | Purpose |
|---------|--------|---------|---------|
| `narrate` | `narrate <text>` | `narrate A goblin appears` | Describe scene/situation |
| `roll` | `roll <dice> dc <num>` | `roll 1d20+5 dc 15` | Call for dice roll |
| `success` | `success <text>` | `success Your attack hits!` | Auto-success outcome |
| `fail` | `fail <text>` | `fail You miss the target` | Auto-failure outcome |
| `ask` | `ask <question>` | `ask What do you do?` | Request clarification |
| `end_session` | `end_session` | `end_session` | End current session |

### Dice Notation

- `1d20` - Roll one 20-sided die
- `2d6+3` - Roll two 6-sided dice, add 3
- `1d20+5 advantage` - Roll with advantage (take higher)
- `1d20 disadvantage` - Roll with disadvantage (take lower)

---

## Troubleshooting

### "Neo4j connection failed"

**Solution**:
```bash
# Check if Neo4j is running
docker ps | grep neo4j

# Restart if needed
docker-compose restart neo4j

# Check logs
docker logs ttrpg-ai-neo4j-1
```

### "Redis connection refused"

**Solution**:
```bash
# Check if Redis is running
docker ps | grep redis

# Restart if needed
docker-compose restart redis
```

### "OpenAI API rate limit exceeded"

**Solution**:
```bash
# Reduce concurrent agents in .env
OPENAI_MAX_RETRIES=5
OPENAI_RETRY_DELAY_SECONDS=2

# Or temporarily disable some agents
# Edit scripts/seed_personalities.py to create fewer agents
```

### "RQ workers not processing jobs"

**Solution**:
```bash
# Check worker status
rq info --url redis://localhost:6379

# Restart workers
# Ctrl+C in worker terminal, then re-run:
uv run rq worker base_persona character validation --url redis://localhost:6379
```

### "Validation failures recurring"

AI characters repeatedly narrating outcomes? This is expected during development.

**Solution**:
```bash
# Check validation logs
grep "validation_failed" logs/ttrpg-ai.log

# Temporarily reduce strictness in src/agents/validation.py
# Or increase max retries in .env:
VALIDATION_MAX_ATTEMPTS=5
```

---

## Next Steps

### Inspect Memory Graphs

Open Neo4j Browser ([http://localhost:7474](http://localhost:7474)) and run:

```cypher
// View all memories for Alex
MATCH (e:Edge {agent_id: "agent_alex_001"})
RETURN e
LIMIT 25

// View memories from session 1
MATCH (e:Edge {session_number: 1})
RETURN e.fact, e.days_elapsed, e.confidence

// View corrupted memories
MATCH (e:Edge)
WHERE e.corruption_type IS NOT NULL
RETURN e.fact, e.corruption_type, e.confidence
```

### Review Sample Personalities

```bash
# See default agent personalities
cat scripts/seed_personalities.py

# Customize personalities (edit and re-run)
nano scripts/seed_personalities.py
uv run scripts/seed_personalities.py --overwrite
```

### Run Tests

```bash
# Run all tests
uv run pytest

# Run specific test types
uv run pytest tests/unit/
uv run pytest tests/integration/
uv run pytest tests/contract/

# Run with coverage
uv run pytest --cov=src --cov-report=html
open htmlcov/index.html
```

### Monitor with LangSmith (Optional)

```bash
# Sign up at https://smith.langchain.com
# Get API key and add to .env:
LANGSMITH_API_KEY=ls_...
LANGSMITH_TRACING_ENABLED=true

# Restart system, then view traces at:
# https://smith.langchain.com/your-project
```

---

## Architecture Overview

```
┌─────────────┐
│  Human DM   │ (You)
│  CLI Input  │
└──────┬──────┘
       │
       ▼
┌─────────────────┐
│   LangGraph     │  Turn orchestration
│  State Machine  │  Phase transitions
└────────┬────────┘
         │
    ┌────┴─────┐
    │          │
    ▼          ▼
┌─────────┐  ┌──────────┐
│  Agent  │  │  Agent   │  (RQ Workers)
│  Layer  │  │  Layer   │  3 AI players
└────┬────┘  └────┬─────┘
     │            │
     └────┬───────┘
          ▼
   ┌──────────────┐
   │   Memory     │  Temporal graph
   │  (Graphiti)  │  + corruption
   └──────┬───────┘
          │
     ┌────┴─────┐
     │          │
     ▼          ▼
┌─────────┐  ┌──────┐
│  Neo4j  │  │ Redis│
│  Graph  │  │Queue │
└─────────┘  └──────┘
```

---

## Documentation

- **Architecture**: `docs/architecture.md` - System design deep dive
- **Data Models**: `specs/001-ai-ttrpg-players/data-model.md` - Entity schemas
- **API Contracts**: `specs/001-ai-ttrpg-players/contracts/` - Interface specifications
- **Research Findings**: `specs/001-ai-ttrpg-players/research.md` - Technology choices

---

## Getting Help

- **Issues**: [GitHub Issues](https://github.com/your-org/ttrpg-ai/issues)
- **Discussions**: [GitHub Discussions](https://github.com/your-org/ttrpg-ai/discussions)
- **Research Notes**: See `docs/research-log.md` for development insights

---

## Performance Tips

### For Faster Turn Cycles

```bash
# Increase worker count (if you have >8GB RAM)
uv run rq worker base_persona character validation --burst --workers 12

# Reduce memory retrieval limit in .env
MEMORY_RETRIEVAL_LIMIT=3  # Default 5

# Disable corruption temporarily
CORRUPTION_ENABLED=false
```

### For Longer Sessions

```bash
# Increase Redis memory limit in docker-compose.yml
services:
  redis:
    command: redis-server --maxmemory 2gb --maxmemory-policy allkeys-lru

# Increase message TTL in .env
MESSAGE_CHANNEL_TTL_HOURS=48  # Default 24
```

---

## Clean Shutdown

```bash
# Stop RQ workers
# Press Ctrl+C in worker terminal

# Stop DM interface
# Type 'exit' or press Ctrl+C

# Stop Docker services
docker-compose down

# Preserve data (optional)
docker-compose down -v  # WARNING: Deletes all memories!
```

---

**You're ready to go!** Start your first session with `uv run src/interface/dm_cli.py`

For implementation details, see `specs/001-ai-ttrpg-players/plan.md`.
