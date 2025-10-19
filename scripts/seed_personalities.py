#!/usr/bin/env python3
# ABOUTME: Seeds example AI player personality profiles for the AI TTRPG Player System.
# ABOUTME: Creates diverse personality configurations based on data-model.md specifications.

"""
Personality Seeding Script

This script creates example AI player personality profiles with diverse traits.
The profiles are stored as JSON files in the config/personalities/ directory.

Each personality represents a different play style:
- Analytical Planner: Detail-oriented, cautious, logical
- Bold Improviser: Risk-taking, intuitive, action-oriented
- Team Coordinator: Cooperative, assertive, team-focused
- Balanced Strategist: Even distribution across traits

Usage:
    uv run python scripts/seed_personalities.py

Output:
    config/personalities/*.json
"""

import json
from pathlib import Path
from typing import Any


def create_personality_profiles() -> list[dict[str, Any]]:
    """
    Create diverse personality profiles based on data-model.md §1.1.

    Returns:
        List of personality configuration dictionaries
    """

    profiles = [
        # Profile 1: Analytical Planner (Alex)
        # High analytical_score, detail-oriented, cautious
        # From data-model.md example
        {
            "agent_id": "agent_alex_001",
            "player_name": "Alex",
            "player_goal": "Get character involved in crazy space adventures",
            "analytical_score": 0.85,
            "risk_tolerance": 0.35,
            "detail_oriented": 0.90,
            "emotional_memory": 0.30,
            "assertiveness": 0.60,
            "cooperativeness": 0.75,
            "openness": 0.80,
            "rule_adherence": 0.85,
            "roleplay_intensity": 0.90,
            "base_decay_rate": 0.30
        },

        # Profile 2: Bold Improviser (Morgan)
        # Low analytical_score, high risk_tolerance, action-oriented
        {
            "agent_id": "agent_morgan_002",
            "player_name": "Morgan",
            "player_goal": "Create dramatic moments and take bold risks",
            "analytical_score": 0.25,
            "risk_tolerance": 0.90,
            "detail_oriented": 0.35,
            "emotional_memory": 0.80,
            "assertiveness": 0.85,
            "cooperativeness": 0.40,
            "openness": 0.95,
            "rule_adherence": 0.40,
            "roleplay_intensity": 0.85,
            "base_decay_rate": 0.70
        },

        # Profile 3: Team Coordinator (Sam)
        # High cooperativeness, high assertiveness, team-focused
        {
            "agent_id": "agent_sam_003",
            "player_name": "Sam",
            "player_goal": "Build strong party dynamics and support teammates",
            "analytical_score": 0.60,
            "risk_tolerance": 0.50,
            "detail_oriented": 0.65,
            "emotional_memory": 0.70,
            "assertiveness": 0.75,
            "cooperativeness": 0.95,
            "openness": 0.75,
            "rule_adherence": 0.70,
            "roleplay_intensity": 0.80,
            "base_decay_rate": 0.45
        },

        # Profile 4: Balanced Strategist (Jordan)
        # Medium values across traits, adaptable
        {
            "agent_id": "agent_jordan_004",
            "player_name": "Jordan",
            "player_goal": "Experience rich story and balanced gameplay",
            "analytical_score": 0.55,
            "risk_tolerance": 0.55,
            "detail_oriented": 0.60,
            "emotional_memory": 0.55,
            "assertiveness": 0.60,
            "cooperativeness": 0.65,
            "openness": 0.65,
            "rule_adherence": 0.65,
            "roleplay_intensity": 0.70,
            "base_decay_rate": 0.50
        }
    ]

    return profiles


def create_character_configs() -> list[dict[str, Any]]:
    """
    Create example character sheets paired with personalities.

    Based on Lasers & Feelings mechanics from data-model.md §1.2.

    Returns:
        List of character configuration dictionaries
    """

    characters = [
        # Character for Alex (Analytical Planner) → Android Engineer
        {
            "character_id": "char_zara_001",
            "agent_id": "agent_alex_001",
            "name": "Zara-7",
            "style": "Android",
            "role": "Engineer",
            "number": 2,  # Heavily Lasers-oriented (logical)
            "character_goal": "Understand human emotions through experience",
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
        },

        # Character for Morgan (Bold Improviser) → Hot-Shot Pilot
        {
            "character_id": "char_nova_002",
            "agent_id": "agent_morgan_002",
            "name": "Nova Starfire",
            "style": "Hot-Shot",
            "role": "Pilot",
            "number": 5,  # Heavily Feelings-oriented (intuitive)
            "character_goal": "Become the most legendary pilot in the galaxy",
            "equipment": ["Custom flight jacket", "Lucky dice", "Energy pistol"],
            "speech_patterns": [
                "Uses pilot slang and jargon",
                "Speaks confidently and quickly",
                "Makes pop culture references"
            ],
            "mannerisms": [
                "Fidgets with controls when idle",
                "Grins before risky maneuvers",
                "Points finger guns at people"
            ]
        },

        # Character for Sam (Team Coordinator) → Savvy Envoy
        {
            "character_id": "char_quinn_003",
            "agent_id": "agent_sam_003",
            "name": "Quinn Vel",
            "style": "Savvy",
            "role": "Envoy",
            "number": 4,  # Balanced toward Feelings (diplomatic)
            "character_goal": "Build alliances and prevent unnecessary conflicts",
            "equipment": ["Diplomatic credentials", "Translation device", "Formal attire"],
            "speech_patterns": [
                "Uses diplomatic language",
                "Asks open-ended questions",
                "Mediates conflicts naturally"
            ],
            "mannerisms": [
                "Makes steady eye contact",
                "Uses calming hand gestures",
                "Smiles warmly at strangers"
            ]
        },

        # Character for Jordan (Balanced Strategist) → Intrepid Scientist
        {
            "character_id": "char_kai_004",
            "agent_id": "agent_jordan_004",
            "name": "Dr. Kai Chen",
            "style": "Intrepid",
            "role": "Scientist",
            "number": 3,  # Balanced (analytical + curious)
            "character_goal": "Discover new phenomena and expand scientific knowledge",
            "equipment": ["Tricorder", "Sample containers", "Research journal"],
            "speech_patterns": [
                "Explains concepts enthusiastically",
                "Uses scientific terminology",
                "Asks probing questions"
            ],
            "mannerisms": [
                "Takes notes compulsively",
                "Gets distracted by interesting phenomena",
                "Adjusts glasses when thinking"
            ]
        }
    ]

    return characters


def create_full_character_configs() -> list[dict[str, Any]]:
    """
    Create complete character configs with player personality + character sheet.

    Matches the structure from data-model.md examples.

    Returns:
        List of full character configuration dictionaries
    """

    personalities = create_personality_profiles()
    characters = create_character_configs()

    # Merge personalities and characters by agent_id
    full_configs = []

    for personality in personalities:
        agent_id = personality["agent_id"]

        # Find matching character
        character = next(
            (c for c in characters if c["agent_id"] == agent_id),
            None
        )

        if character:
            full_config = {
                "player": personality,
                "character": character
            }
            full_configs.append(full_config)

    return full_configs


def save_personality_files(output_dir: Path) -> None:
    """
    Save personality configurations as JSON files.

    Args:
        output_dir: Directory to save personality files
    """

    # Create output directory
    output_dir.mkdir(parents=True, exist_ok=True)

    # Create individual personality files
    profiles = create_personality_profiles()

    for profile in profiles:
        agent_id = profile["agent_id"]
        filename = f"{agent_id}_personality.json"
        filepath = output_dir / filename

        with open(filepath, 'w') as f:
            json.dump(profile, f, indent=2)

        print(f"✓ Created {filename}")

    # Create individual character files
    characters = create_character_configs()

    for character in characters:
        character_id = character["character_id"]
        filename = f"{character_id}_character.json"
        filepath = output_dir / filename

        with open(filepath, 'w') as f:
            json.dump(character, f, indent=2)

        print(f"✓ Created {filename}")

    # Create full character configs (player + character pairs)
    full_configs = create_full_character_configs()

    for config in full_configs:
        agent_id = config["player"]["agent_id"]
        filename = f"{agent_id}_full.json"
        filepath = output_dir / filename

        with open(filepath, 'w') as f:
            json.dump(config, f, indent=2)

        print(f"✓ Created {filename} (player + character)")

    # Create campaign config with all characters
    campaign_config = {
        "campaign_name": "Voyage of the Raptor",
        "dm_name": "Ryan",
        "party": {
            "ship_name": "The Raptor",
            "ship_strengths": ["Fast", "Maneuverable", "Well-armed"],
            "ship_problem": "Fuel cells depleting rapidly"
        },
        "corruption_strength": 0.5,
        "characters": full_configs
    }

    campaign_filepath = output_dir / "campaign_config.json"
    with open(campaign_filepath, 'w') as f:
        json.dump(campaign_config, f, indent=2)

    print(f"✓ Created campaign_config.json (full campaign)")


def create_readme(output_dir: Path) -> None:
    """Create README explaining the personality files."""

    readme_content = """# AI Player Personality Configurations

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
"""

    readme_filepath = output_dir / "README.md"
    with open(readme_filepath, 'w') as f:
        f.write(readme_content)

    print(f"✓ Created README.md")


def main() -> None:
    """Main execution function."""

    print("\n" + "="*60)
    print("AI TTRPG Player System - Personality Seeding")
    print("="*60 + "\n")

    # Determine output directory
    project_root = Path(__file__).parent.parent
    output_dir = project_root / "config" / "personalities"

    print(f"Output directory: {output_dir}\n")

    # Create personality files
    save_personality_files(output_dir)

    print()

    # Create README
    create_readme(output_dir)

    print("\n" + "="*60)
    print("✓ Personality Seeding Complete")
    print("="*60)
    print(f"\nCreated files in {output_dir}:")
    print("  - 4 personality profiles (*_personality.json)")
    print("  - 4 character sheets (*_character.json)")
    print("  - 4 full configs (*_full.json)")
    print("  - 1 campaign config (campaign_config.json)")
    print("  - 1 README (README.md)")

    print("\nPersonality profiles:")
    print("  • Alex (Analytical Planner) → Zara-7 (Android Engineer)")
    print("  • Morgan (Bold Improviser) → Nova Starfire (Hot-Shot Pilot)")
    print("  • Sam (Team Coordinator) → Quinn Vel (Savvy Envoy)")
    print("  • Jordan (Balanced Strategist) → Dr. Kai Chen (Intrepid Scientist)")

    print("\nNext steps:")
    print("  1. Review configurations in config/personalities/")
    print("  2. Customize personalities if needed")
    print("  3. Copy .env.example to .env and add OpenAI API key")
    print("  4. Run application: uv run python main.py")
    print()


if __name__ == "__main__":
    main()
