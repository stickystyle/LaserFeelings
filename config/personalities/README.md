# AI Player Personality Configurations

This directory contains personality profiles for AI players in the TTRPG system.

## File Structure

### Individual Files
- `agent_*_personality.json` - Player layer personality traits
- `char_*_character.json` - Character layer roleplay configuration
- `agent_*_full.json` - Combined player + character configuration

### Campaign Configuration
- `campaign_config.json` - Complete campaign with all player-character pairs

## Personality Profiles

### agent_alex_001 (Analytical Planner)
- **Character**: Zara-7 (Android Engineer)
- **Style**: Detail-oriented, cautious, logical
- **Decision-making**: Analytical, high rule adherence
- **Memory**: Low decay rate (detail_oriented: 0.90)

### agent_morgan_002 (Bold Improviser)
- **Character**: Nova Starfire (Hot-Shot Pilot)
- **Style**: Risk-taking, intuitive, action-oriented
- **Decision-making**: Impulsive, creative interpretation
- **Memory**: High decay rate (detail_oriented: 0.35)

### agent_sam_003 (Team Coordinator)
- **Character**: Quinn Vel (Savvy Envoy)
- **Style**: Cooperative, assertive, diplomatic
- **Decision-making**: Team-focused, consensus-building
- **Memory**: Moderate decay rate (detail_oriented: 0.65)

### agent_jordan_004 (Balanced Strategist)
- **Character**: Dr. Kai Chen (Intrepid Scientist)
- **Style**: Adaptable, balanced across traits
- **Decision-making**: Context-dependent, strategic
- **Memory**: Moderate decay rate (detail_oriented: 0.60)

## Usage

### Load Individual Personality
```python
import json
from pathlib import Path

personality_file = Path("config/personalities/agent_alex_001_personality.json")
with open(personality_file) as f:
    personality = json.load(f)
```

### Load Campaign Configuration
```python
campaign_file = Path("config/personalities/campaign_config.json")
with open(campaign_file) as f:
    campaign = json.load(f)
```

## Customization

To create custom personalities:
1. Copy an existing personality file
2. Modify traits (all values 0.0-1.0)
3. Update character details (name, style, role, etc.)
4. Update agent_id and character_id to be unique

## Trait Reference

See `data-model.md` for complete trait definitions:
- `analytical_score`: Logic vs intuition (0=gut, 1=logic)
- `risk_tolerance`: Caution vs boldness (0=cautious, 1=reckless)
- `detail_oriented`: Affects memory decay rate
- `emotional_memory`: How emotions color memories
- `assertiveness`: Leadership tendency
- `cooperativeness`: Teamwork vs solo preference
- `openness`: Traditional vs innovative
- `rule_adherence`: Respect for game rules
- `roleplay_intensity`: In-character vs metagaming
- `base_decay_rate`: Base memory corruption rate
