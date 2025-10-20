"""Configuration module for AI TTRPG Player System"""

from .prompts import (
    CHARACTER_ACTION_PROMPT,
    CHARACTER_REACTION_PROMPT,
    MEMORY_CORRUPTION_PROMPTS,
    OOC_DISCUSSION_PROMPT,
    STRATEGIC_INTENT_PROMPT,
    ValidationPromptTemplate,
)
from .settings import Settings, get_settings

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
