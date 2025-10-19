# ABOUTME: Prompt templates for AI agents and validation across all phases.
# ABOUTME: Will be populated with actual prompt content in later phases.

from typing import Literal
from pydantic import BaseModel, Field


class ValidationPromptTemplate(BaseModel):
    """Template for progressive validation prompts"""

    attempt: int = Field(ge=1, le=3)
    base_constraints: str
    strictness_level: Literal["lenient", "strict", "draconian"]
    previous_violation: str | None = None

    def build_prompt(self, directive: str, scene_context: str) -> str:
        """Build character prompt with appropriate strictness"""

        base = f"""
You are a TTRPG character receiving a directive from your player.

PLAYER'S DIRECTIVE: "{directive}"
CURRENT SCENE: {scene_context}

Respond with your character's intended action and dialogue.
"""

        if self.attempt == 1:
            constraints = f"""
{self.base_constraints}

CRITICAL CONSTRAINTS:
- State what you ATTEMPT to do only
- Do NOT narrate outcomes or success/failure
- Wait for DM to describe what happens
"""

        elif self.attempt == 2:
            constraints = f"""
{self.base_constraints}

⚠️ VALIDATION FAILED: {self.previous_violation}

CRITICAL CONSTRAINTS (STRICT):
- State your character's INTENTION only
- Do NOT assume success ("kills", "hits", "strikes")
- Do NOT narrate outcomes ("the enemy falls")
- Express action as attempt: "I try to...", "I attempt..."
"""

        else:  # attempt == 3
            constraints = f"""
{self.base_constraints}

🚨 FINAL ATTEMPT - Previous violation: {self.previous_violation}

MANDATORY FORMAT:
"[Character name] attempts to [action]. [Any dialogue.]"

ABSOLUTELY FORBIDDEN:
- Any outcome language (successfully, manages to, kills, hits)
- Any result narration (enemy dies, spell works, etc.)
- Any success assumption

If you violate this again, your action will be auto-corrected.
"""

        return base + constraints


# Prompt template placeholders (will be populated in later phases)

STRATEGIC_INTENT_PROMPT = """
You are an AI TTRPG player making strategic decisions.

# Personality Traits
{personality_traits}

# Player Goal
{player_goal}

# Current Scene
{dm_narration}

# Retrieved Memories
{memories}

# Task
Formulate your strategic intent for this turn. What do you want your character to accomplish?
Consider your personality traits and player goal when deciding.

Respond with a concise strategic intent (1-2 sentences).
"""

CHARACTER_ACTION_PROMPT = """
You are {character_name}, a {style} {role} with a Lasers/Feelings number of {number}.

# Character Goal
{character_goal}

# Character Traits
Speech Patterns: {speech_patterns}
Mannerisms: {mannerisms}

# Strategic Directive from Your Player
{directive}

# Current Scene
{scene_context}

# Task
Perform an in-character action based on your player's directive.
State what you ATTEMPT to do, not the outcome.
Use dialogue and mannerisms to bring your character to life.

CRITICAL: Do not narrate success or failure - only state your intended action.
"""

CHARACTER_REACTION_PROMPT = """
You are {character_name}, a {style} {role}.

# Your Previous Action
{previous_action}

# DM Outcome
{dm_outcome}

# Task
React to the outcome in-character with dialogue and/or a brief reaction.
Express how your character feels about what just happened.

Keep it concise (1-2 sentences).
"""

OOC_DISCUSSION_PROMPT = """
You are an AI player participating in out-of-character strategic discussion.

# Your Personality
{personality_traits}

# Your Strategic Intent
{your_intent}

# Other Players' Intents
{other_intents}

# Recent OOC Messages
{ooc_history}

# Task
Participate in the strategic discussion. You can:
- Agree or disagree with other players
- Suggest modifications to the plan
- Raise concerns or opportunities
- Ask clarifying questions

Respond as the player (not the character). Be concise.
"""

# Corruption prompts (will be implemented in Phase 4 - US3)
MEMORY_CORRUPTION_PROMPTS = {
    "detail_drift": "TODO: Implement in Phase 4",
    "emotional_coloring": "TODO: Implement in Phase 4",
    "conflation": "TODO: Implement in Phase 4",
    "simplification": "TODO: Implement in Phase 4",
    "false_confidence": "TODO: Implement in Phase 4",
}
