# ABOUTME: In-character roleplay agent representing the "character" layer in dual architecture.
# ABOUTME: Interprets player directives through personality lens, expresses intent only (no outcome narration).

import json
import re

from openai import AsyncOpenAI

from src.agents.exceptions import ValidationFailed
from src.agents.llm_client import LLMClient
from src.memory.corrupted_temporal import CorruptedTemporalMemory
from src.models.agent_actions import Action, Directive, EmotionalState, Reaction
from src.models.personality import CharacterSheet, PlayerPersonality


class CharacterAgent:
    """
    In-character roleplay agent (character layer).

    Interprets player directives and expresses them through character's unique
    voice, personality, and mannerisms. MUST express intent only, never narrate
    outcomes (that's the DM's role).
    """

    def __init__(
        self,
        character_id: str,
        character_sheet: CharacterSheet,
        personality: PlayerPersonality | None = None,
        memory: CorruptedTemporalMemory | None = None,
        openai_client: AsyncOpenAI | None = None,
        model: str = "gpt-4o",
        temperature: float = 0.8,
    ):
        """
        Initialize Character agent.

        Args:
            character_id: Unique identifier for this character (e.g., 'char_zara_001')
            character_sheet: Lasers & Feelings character sheet with roleplay traits
            personality: Player personality (affects interpretation style, optional for testing)
            memory: Memory interface for character-specific memories (optional for testing)
            openai_client: AsyncOpenAI client for LLM calls (optional for testing)
            model: OpenAI model to use (default: gpt-4o)
            temperature: LLM temperature for roleplay variation (default: 0.8)
        """
        self.character_id = character_id
        self.character_sheet = character_sheet
        self.personality = personality
        self._memory = memory
        self._openai_client = openai_client
        self._llm_client = LLMClient(openai_client, model) if openai_client else None
        self.temperature = temperature

    def _build_character_system_prompt(self) -> str:
        """Build system prompt incorporating character traits and speech patterns."""
        speech_patterns = "\n".join([
            f"- {pattern}" for pattern in self.character_sheet.speech_patterns
        ]) if self.character_sheet.speech_patterns else "- Speaks naturally"

        mannerisms = "\n".join([
            f"- {manner}" for manner in self.character_sheet.mannerisms
        ]) if self.character_sheet.mannerisms else "- No specific mannerisms"

        approach = self.character_sheet.approach_bias
        approach_desc = {
            "lasers": "logical, technical, and analytical",
            "feelings": "intuitive, emotional, and empathetic",
            "balanced": "balanced between logic and emotion"
        }.get(approach, "balanced")

        # Handle enums that may be already converted to values (use_enum_values=True)
        style_str = self.character_sheet.style.value if hasattr(self.character_sheet.style, 'value') else self.character_sheet.style
        role_str = self.character_sheet.role.value if hasattr(self.character_sheet.role, 'value') else self.character_sheet.role

        return f"""You are roleplaying as {self.character_sheet.name}, a {style_str} {role_str}.

Character traits:
- Goal: {self.character_sheet.character_goal}
- Approach: {approach_desc} (number: {self.character_sheet.number})
- Equipment: {', '.join(self.character_sheet.equipment) if self.character_sheet.equipment else 'None'}

Speech patterns:
{speech_patterns}

Mannerisms:
{mannerisms}

CRITICAL RULES:
1. You express INTENT only, never outcomes
2. Use "attempt", "try", "aim to" - never "successfully", "hits", "kills"
3. Do NOT narrate results - that's the DM's job
4. Stay in character voice at all times
5. Interpret player directives through YOUR personality lens

You are performing IN CHARACTER. Bring this character to life!
"""

    async def perform_action(
        self,
        directive: Directive,
        scene_context: str,
    ) -> Action:
        """
        Execute in-character action based on player directive.

        CRITICAL BEHAVIOR:
        - MUST express intent only, never narrate outcomes
        - MUST interpret directive through character personality
        - MUST use character speech patterns and mannerisms
        - MUST NOT use forbidden language (successfully, kills, hits, etc.)
        - SHOULD add character flavor to directive execution

        Args:
            directive: High-level instruction from player layer
            scene_context: Current scene from DM

        Returns:
            Action with action_text, optional dialogue, mannerisms

        Raises:
            RuntimeError: When openai_client not provided to constructor
            ValidationFailed: When action contains narrative overreach
            LLMCallFailed: When OpenAI API call fails
        """
        # Validate dependencies at runtime
        if not self._llm_client:
            raise RuntimeError(
                "CharacterAgent requires openai_client to be initialized. "
                "Provide this dependency in the constructor."
            )

        system_prompt = self._build_character_system_prompt()

        user_prompt = f"""Scene:
{scene_context}

Player directive:
{directive.instruction}

{f"Tactical guidance: {directive.tactical_guidance}" if directive.tactical_guidance else ""}
{f"Emotional tone: {directive.emotional_tone}" if directive.emotional_tone else ""}

Perform this action IN CHARACTER as JSON:
{{
  "action_text": "What you ATTEMPT to do (intent only, no outcomes)",
  "dialogue": "What you say (if anything)",
  "mannerisms": "Physical actions, body language, gestures"
}}

REMEMBER:
- Use "I attempt to...", "I try to...", "I aim to..."
- NEVER say "I successfully...", "I hit...", "I kill..."
- Express your intent, let the DM narrate what actually happens
"""

        try:
            response = await self._llm_client.call(
                system_prompt,
                user_prompt,
                temperature=self.temperature,
                response_format={"type": "json_object"},
            )

            data = json.loads(response)

            action = Action(
                character_id=self.character_id,
                action_text=data.get("action_text", ""),
                dialogue=data.get("dialogue"),
                mannerisms=data.get("mannerisms"),
            )

            # Validate action_text is present
            if not action.action_text:
                raise ValidationFailed("Action missing required action_text field")

            # Context-aware validation for forbidden patterns using regex
            forbidden_patterns = [
                (r"\bsuccessfully\b", "successfully"),
                (r"\bmanages?\s+to\b", "manages to"),
                (r"\b(kills?|defeats?)\s+\w+", "outcome narration (kills/defeats target)"),
                (r"\b(hits?|strikes?)\s+(the|a|an)\s+\w+", "outcome narration (hits/strikes target)"),
                (r"\bthe\s+\w+\s+(falls?|dies?|collapses?)\b", "outcome narration (enemy falls/dies)"),
                (r"\b(he|she|it|they)\s+(die|dies|fall|falls|collapse|collapses)\b", "outcome narration (entity dies/falls)"),
            ]

            action_text = action.action_text
            for pattern, description in forbidden_patterns:
                if re.search(pattern, action_text, re.IGNORECASE):
                    raise ValidationFailed(
                        f"Action contains forbidden outcome language: '{description}'. "
                        f"Matched pattern in: '{action_text}'. "
                        f"Express intent only, not results."
                    )

            return action

        except json.JSONDecodeError as e:
            raise ValidationFailed(f"Failed to parse action JSON: {e}") from e

    async def react_to_outcome(
        self,
        dm_narration: str,
        emotional_state: EmotionalState,
    ) -> Reaction:
        """
        Respond in-character to DM's outcome narration.

        Behavior:
        - MUST respond with character voice
        - MUST reflect emotional state in response
        - SHOULD indicate next desired action if relevant
        - MUST NOT initiate new actions (reaction only)

        Args:
            dm_narration: DM's outcome description
            emotional_state: Character's current emotional state

        Returns:
            Reaction with reaction_text, optional dialogue, next_intent

        Raises:
            RuntimeError: When openai_client not provided to constructor
            LLMCallFailed: When OpenAI API call fails
        """
        # Validate dependencies at runtime
        if not self._llm_client:
            raise RuntimeError(
                "CharacterAgent requires openai_client to be initialized. "
                "Provide this dependency in the constructor."
            )

        system_prompt = self._build_character_system_prompt()

        user_prompt = f"""DM narration (what happened):
{dm_narration}

Your current emotional state:
- Primary emotion: {emotional_state.primary_emotion}
- Intensity: {emotional_state.intensity:.2f}
{f"- Secondary emotions: {', '.join(emotional_state.secondary_emotions)}" if emotional_state.secondary_emotions else ""}

React to this outcome IN CHARACTER as JSON:
{{
  "reaction_text": "Your emotional/physical response to what happened",
  "dialogue": "What you say in reaction (if anything)",
  "next_intent": "What you want to do next (if relevant)"
}}

React authentically to the outcome. Show emotion, personality, and character voice.
This is a REACTION, not a new action - respond to what happened.
"""

        try:
            response = await self._llm_client.call(
                system_prompt,
                user_prompt,
                temperature=self.temperature,
                response_format={"type": "json_object"},
            )

            data = json.loads(response)

            reaction = Reaction(
                character_id=self.character_id,
                reaction_text=data.get("reaction_text", ""),
                dialogue=data.get("dialogue"),
                next_intent=data.get("next_intent"),
            )

            # Validate reaction_text is present
            if not reaction.reaction_text:
                raise ValidationFailed("Reaction missing required reaction_text field")

            return reaction

        except json.JSONDecodeError as e:
            raise ValidationFailed(f"Failed to parse reaction JSON: {e}") from e
