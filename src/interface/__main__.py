# ABOUTME: Entry point for launching the Textual TUI interface.
# ABOUTME: Provides simple command to run: uv run python -m src.interface

import json
import sys

from redis import Redis

from src.config.settings import get_settings
from src.interface.dm_textual import DMTextualInterface
from src.orchestration.message_router import MessageRouter
from src.orchestration.turn_orchestrator import TurnOrchestrator


def main() -> None:
    """Run Textual DM interface with real configuration"""
    # Load settings
    settings = get_settings()

    # Create Redis connection
    try:
        redis_client = Redis.from_url(settings.redis_url, decode_responses=False)
        redis_client.ping()
    except Exception as e:
        print(f"Error: Could not connect to Redis: {e}")
        print("Make sure Redis is running via 'docker-compose up -d'")
        sys.exit(1)

    # Create real orchestrator and router
    orchestrator = TurnOrchestrator(redis_client)
    router = MessageRouter(redis_client)

    # Load campaign config
    try:
        with open("config/personalities/campaign_config.json") as f:
            config = json.load(f)
    except FileNotFoundError:
        print("Error: config/personalities/campaign_config.json not found")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON in campaign_config.json: {e}")
        sys.exit(1)

    # Create app with real dependencies
    app = DMTextualInterface(orchestrator, router)

    # Load campaign and character info
    app._campaign_name = config.get("campaign_name", "Unknown Campaign")
    app.session_number = 1
    app._active_agents = [
        char["player"]["agent_id"] for char in config.get("characters", [])
    ]

    # Build character name mapping (both character_id and agent_id -> name)
    for char in config.get("characters", []):
        character_id = char["character"]["character_id"]
        character_name = char["character"]["name"]
        agent_id = char["player"]["agent_id"]

        app._character_names[character_id] = character_name
        app._character_names[agent_id] = char["player"]["player_name"]

    # Run app
    app.run()


if __name__ == "__main__":
    main()
