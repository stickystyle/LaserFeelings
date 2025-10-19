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


def build_game_mechanics_section(character_number: int) -> str:
    """
    Build comprehensive Lasers & Feelings mechanics explanation personalized to character.

    Args:
        character_number: Character's L&F number (2-5)

    Returns:
        Formatted string explaining game mechanics with personalized strengths/weaknesses
    """
    # Validate number is in valid range
    if not 2 <= character_number <= 5:
        raise ValueError(f"Character number must be 2-5, got {character_number}")

    # Calculate success probabilities
    lasers_chance = ((character_number - 1) / 6) * 100  # Roll under number
    feelings_chance = ((6 - character_number) / 6) * 100  # Roll over number

    # Determine character's mechanical strengths/weaknesses
    if character_number == 2:
        strength = "LASERS (technical/logical actions)"
        weakness = "FEELINGS (social/emotional actions)"
        strength_detail = "You excel at technology, science, and rational analysis"
        weakness_detail = "You struggle with intuition, diplomacy, and emotional approaches"
    elif character_number == 5:
        strength = "FEELINGS (social/emotional actions)"
        weakness = "LASERS (technical/logical actions)"
        strength_detail = "You excel at intuition, diplomacy, and passionate actions"
        weakness_detail = "You struggle with technology, science, and cold rationality"
    elif character_number == 3:
        strength = "balanced (slight LASERS advantage)"
        weakness = None
        strength_detail = "You are competent at both approaches, slightly better with logic"
        weakness_detail = None
    else:  # character_number == 4
        strength = "balanced (slight FEELINGS advantage)"
        weakness = None
        strength_detail = "You are competent at both approaches, slightly better with emotion"
        weakness_detail = None

    mechanics = f"""
## LASERS & FEELINGS GAME MECHANICS

**Your character's number: {character_number}**
You are {strength}.
{strength_detail}
{weakness_detail if weakness_detail else ""}

### How Actions Work:
When your character attempts risky actions, the DM calls for a dice roll:
- Roll 1d6 (base die) + bonuses for being prepared (+1d) or expert (+1d)
- Compare each die result to your number ({character_number})

**LASERS actions** (technology, science, rational analysis, calm precision):
- Roll UNDER your number to succeed
- Your success chance: {lasers_chance:.0f}% per die

**FEELINGS actions** (intuition, diplomacy, passion, wild emotion):
- Roll OVER your number to succeed
- Your success chance: {feelings_chance:.0f}% per die

### Success Levels (based on how many dice succeed):
- **0 dice succeed**: Failure - things get worse, new complications arise
- **1 die succeeds**: Partial success - you accomplish the goal but with a complication, cost, or harm
- **2 dice succeed**: Clean success - you do it well with no complications
- **3+ dice succeed**: Critical success - you get bonus effects or advantages beyond your intent
- **Roll exactly {character_number}**: LASER FEELINGS - special insight! You succeed AND can ask the DM a revealing question about the situation

### Tactical Advantages (add extra dice):
- **Prepared** (+1d): You planned ahead, have the right tools, or set up the situation favorably
- **Expert** (+1d): This action directly relates to your role, background, or specialty
- **Helped** (+1d): An ally successfully assists you with their own roll

### Strategic Implications for Decision-Making:
- **Play to your strengths**: Choose {strength} approaches when possible
{f"- **Avoid your weaknesses**: Minimize {weakness} approaches or seek help/preparation to offset disadvantage" if weakness else "- **Leverage versatility**: You can tackle most problems with either approach"}
- **Seek tactical advantages**: Look for opportunities to be prepared or use expertise (can stack for 3d6 total)
- **Coordinate with allies**: Request help actions to boost critical rolls
- **Fish for insights**: Rolling exactly {character_number} gives you LASER FEELINGS - use this to ask strategic questions:
  - "What are they really feeling?"
  - "Who's behind this?"
  - "What's the best way to accomplish X?"
  - "What should I be on the lookout for?"

### Examples of Each Approach:
**LASERS** (roll under {character_number}): Hacking systems, analyzing data, repairing equipment, precise shooting, logical persuasion
**FEELINGS** (roll over {character_number}): Reading emotions, seducing, inspiring crew, trusting instincts, passionate speeches
"""

    return mechanics.strip()


# Corruption prompts (will be implemented in Phase 4 - US3)
MEMORY_CORRUPTION_PROMPTS = {
    "detail_drift": "TODO: Implement in Phase 4",
    "emotional_coloring": "TODO: Implement in Phase 4",
    "conflation": "TODO: Implement in Phase 4",
    "simplification": "TODO: Implement in Phase 4",
    "false_confidence": "TODO: Implement in Phase 4",
}
