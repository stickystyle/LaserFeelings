# ABOUTME: Helper utility functions for state machine nodes (character ID mapping, job polling, config loading).
# ABOUTME: Provides reusable functions for agent-character mapping, RQ job polling, and configuration file loading.

import json
import time
from pathlib import Path

from loguru import logger
from rq.job import Job

from src.orchestration.exceptions import JobFailedError


def _load_agent_character_mapping() -> dict[str, str]:
    """
    Load agent_id → character_id mapping from config files.

    Returns:
        Dict mapping agent IDs to character IDs
    """
    mapping = {}
    config_dir = Path("config/personalities")

    if not config_dir.exists():
        logger.warning(f"Config directory not found: {config_dir}")
        return mapping

    for config_file in config_dir.glob("char_*_character.json"):
        try:
            with open(config_file) as f:
                char_config = json.load(f)
                agent_id = char_config.get("agent_id")
                character_id = char_config.get("character_id")

                if agent_id and character_id:
                    mapping[agent_id] = character_id
        except Exception as e:
            logger.warning(f"Failed to load {config_file}: {e}")

    logger.info(f"Loaded agent-to-character mappings: {mapping}")
    return mapping


# Load mapping once at module level
_AGENT_CHARACTER_MAPPING = _load_agent_character_mapping()


def _get_character_id_for_agent(agent_id: str) -> str:
    """
    Map agent ID to character ID using config files.

    Args:
        agent_id: Agent identifier (e.g., "agent_alex_001")

    Returns:
        Character identifier (e.g., "char_zara_001")

    Raises:
        ValueError: If agent_id not found in mapping
    """
    character_id = _AGENT_CHARACTER_MAPPING.get(agent_id)

    if not character_id:
        raise ValueError(
            f"No character mapping found for agent {agent_id}. "
            f"Available agents: {list(_AGENT_CHARACTER_MAPPING.keys())}"
        )

    return character_id


def _poll_job_with_backoff(job: Job, timeout: float) -> None:
    """
    Poll RQ job with exponential backoff.

    Args:
        job: RQ Job to poll
        timeout: Maximum time to wait in seconds

    Raises:
        JobFailedError: If job times out or fails

    Note:
        Uses exponential backoff capped at 2s to reduce CPU usage
    """
    sleep_time = 0.5
    max_sleep = 2.0
    start_time = time.time()

    while job.result is None and not job.is_failed:
        if time.time() - start_time > timeout:
            raise JobFailedError(f"Job timeout after {timeout}s")
        time.sleep(sleep_time)
        job.refresh()
        sleep_time = min(sleep_time * 1.3, max_sleep)  # Exponential backoff capped at 2s


def _load_character_number(character_id: str) -> int:
    """
    Load character number from config file.

    Args:
        character_id: Character ID (e.g., 'char_zara_001')

    Returns:
        Character number (2-5) from config file

    Raises:
        FileNotFoundError: If config file doesn't exist
        ValueError: If number is invalid or missing
    """
    config_path = Path(f"config/personalities/{character_id}_character.json")

    if not config_path.exists():
        raise FileNotFoundError(f"No config found for {character_id} at {config_path}")

    with open(config_path) as f:
        config = json.load(f)
        number = config.get("number")

        if number is None:
            raise ValueError(f"Missing 'number' field in config for {character_id}")

        if not isinstance(number, int) or not (2 <= number <= 5):
            raise ValueError(f"Invalid number {number} for {character_id} (must be 2-5)")

        return number
