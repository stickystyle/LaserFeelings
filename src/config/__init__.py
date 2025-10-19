"""Configuration module for AI TTRPG Player System"""

from .settings import Settings, get_settings
from .prompts import (
    ValidationPromptTemplate,
    STRATEGIC_INTENT_PROMPT,
    CHARACTER_ACTION_PROMPT,
    CHARACTER_REACTION_PROMPT,
    OOC_DISCUSSION_PROMPT,
    MEMORY_CORRUPTION_PROMPTS,
)

__all__ = [
    "Settings",
    "get_settings",
    "ValidationPromptTemplate",
    "STRATEGIC_INTENT_PROMPT",
    "CHARACTER_ACTION_PROMPT",
    "CHARACTER_REACTION_PROMPT",
    "OOC_DISCUSSION_PROMPT",
    "MEMORY_CORRUPTION_PROMPTS",
]
