# ABOUTME: Strategic decision-making agent representing the "player" layer in dual architecture.
# ABOUTME: Handles OOC discussion, strategic intent formulation, and directive creation for character layer.

import json
from datetime import datetime
from uuid import uuid4

from openai import AsyncOpenAI

from src.agents.exceptions import (
    CharacterNotFound,
    InvalidCharacterState,
    InvalidMessageFormat,
    LLMCallFailed,
    NoConsensusReached,
)
from src.agents.llm_client import LLMClient
from src.memory.corrupted_temporal import CorruptedTemporalMemory
from src.models.agent_actions import CharacterState, Directive, Intent
from src.models.game_state import GamePhase
from src.models.messages import Message, MessageChannel, MessageType
from src.models.personality import PlayerPersonality


class BasePersonaAgent:
    """
    Strategic decision-making agent (player layer).

    Operates out-of-character to make strategic decisions, participate in
    group discussions, and issue high-level directives to character layer.
    """

    def __init__(
        self,
        agent_id: str,
        personality: PlayerPersonality,
        character_number: int,
        memory: CorruptedTemporalMemory | None = None,
        openai_client: AsyncOpenAI | None = None,
        model: str = "gpt-4o",
        temperature: float = 0.7,
    ):
        """
        Initialize BasePersona agent.

        Args:
            agent_id: Unique identifier for this agent (e.g., 'agent_alex_001')
            personality: Player personality traits affecting decision-making
            character_number: Character's Lasers & Feelings number (2-5) for mechanics awareness
            memory: Memory interface for retrieving past experiences (optional for testing)
            openai_client: AsyncOpenAI client for LLM calls (optional for testing)
            model: OpenAI model to use (default: gpt-4o)
            temperature: LLM temperature for response variation (default: 0.7)
        """
        # Validate character_number
        if not 2 <= character_number <= 5:
            raise ValueError(f"Character number must be 2-5, got {character_number}")

        self.agent_id = agent_id
        self.personality = personality
        self.character_number = character_number
        self._memory = memory
        self._openai_client = openai_client
        self._llm_client = LLMClient(openai_client, model) if openai_client else None
        self.temperature = temperature

    def _build_mechanics_context(self) -> str:
        """
        Build game mechanics section using canonical rules and character's number.

        Returns:
            Formatted string with complete rules plus personalized mechanics context.
        """
        from src.config.prompts import load_game_rules, build_game_mechanics_section

        # Load canonical rules document
        canonical_rules = load_game_rules()

        # Build personalized mechanics section
        personalized_mechanics = build_game_mechanics_section(self.character_number)

        # Combine: Full rules + personalized strategic guidance
        return f"""{canonical_rules}

---

# YOUR CHARACTER'S MECHANICAL PROFILE

{personalized_mechanics}
"""

    async def participate_in_ooc_discussion(
        self,
        dm_narration: str,
        other_messages: list[Message],
    ) -> Message:
        """
        Contribute to out-of-character strategy discussion.

        Behavior:
        - MUST retrieve relevant memories before generating response
        - MUST apply personality traits to decision-making
        - SHOULD reference past experiences in reasoning
        - MUST NOT narrate in-character actions (player layer only)

        Args:
            dm_narration: Current scene from DM
            other_messages: Other players' OOC messages

        Returns:
            Message on out_of_character channel

        Raises:
            RuntimeError: When memory or openai_client not provided to constructor
            LLMCallFailed: When OpenAI API call fails after retries
            InvalidMessageFormat: When generated message doesn't match schema
        """
        # Validate dependencies at runtime
        if not self._memory or not self._llm_client:
            raise RuntimeError(
                "BasePersonaAgent requires memory and openai_client to be initialized. "
                "Provide these dependencies in the constructor."
            )

        # Extract session and turn info from other_messages if available
        session_number = None
        turn_number = None
        if other_messages:
            session_number = other_messages[0].session_number
            turn_number = other_messages[0].turn_number

        # Retrieve relevant memories
        query = f"DM narration: {dm_narration[:200]}"
        memories = await self._memory.search(
            query=query,
            agent_id=self.agent_id,
            session_number=session_number,
            limit=5,
        )

        # Build context from memories
        memory_context = "\n".join([
            f"- {mem.fact} (confidence: {mem.confidence:.2f})"
            for mem in memories[:3]
        ])

        # Build context from other messages
        discussion_context = "\n".join([
            f"{msg.from_agent}: {msg.content}"
            for msg in other_messages[-5:]  # Last 5 messages
        ])

        # Build personality-aware system prompt
        decision_style = self.personality.decision_style
        risk_level = "cautious" if self.personality.risk_tolerance < 0.4 else \
                     "bold" if self.personality.risk_tolerance > 0.7 else "balanced"
        cooperation_style = "collaborative" if self.personality.cooperativeness > 0.6 else "independent"

        # Build mechanics context for strategic awareness
        mechanics_context = self._build_mechanics_context()

        system_prompt = f"""You are a TTRPG player participating in strategic discussion.

Your personality traits:
- Decision style: {decision_style}
- Risk tolerance: {risk_level}
- Cooperation style: {cooperation_style}
- Analytical score: {self.personality.analytical_score:.2f}

{mechanics_context}

You are discussing strategy OUT OF CHARACTER. Do not roleplay your character.
Focus on tactical analysis and strategic planning.
Use your knowledge of game mechanics to inform your strategic suggestions.
"""

        user_prompt = f"""Current situation:
DM: {dm_narration}

Your relevant memories:
{memory_context if memory_context else "No relevant memories found."}

Recent discussion:
{discussion_context if discussion_context else "You are first to speak."}

Provide your strategic input for the group. Consider:
1. What are the risks and opportunities?
2. What approach aligns with your {risk_level} risk tolerance?
3. How can the group work together effectively?

Keep response under 200 words. Be conversational but strategic.
"""

        try:
            content = await self._llm_client.call(
                system_prompt, user_prompt, temperature=self.temperature
            )

            # Validate message length
            if len(content) > 2000:
                content = content[:1997] + "..."

            # Create Message object with required fields
            message = Message(
                message_id=str(uuid4()),
                channel=MessageChannel.OOC,
                from_agent=self.agent_id,
                to_agents=None,  # Broadcast
                content=content,
                timestamp=datetime.now(),
                message_type=MessageType.DISCUSSION,
                phase=GamePhase.OOC_DISCUSSION.value,
                turn_number=turn_number or 1,
                session_number=session_number,
            )

            return message

        except Exception as e:
            raise InvalidMessageFormat(f"Failed to create valid message: {e}") from e

    async def formulate_strategic_intent(
        self,
        discussion_summary: str,
    ) -> Intent:
        """
        Decide high-level strategic goal from OOC discussion.

        Behavior:
        - MUST synthesize discussion into actionable intent
        - MUST include risk assessment
        - SHOULD provide fallback plan
        - MUST align with agent personality traits

        Args:
            discussion_summary: Consensus from OOC discussion

        Returns:
            Intent with strategic_goal, reasoning, risk_assessment

        Raises:
            RuntimeError: When openai_client not provided to constructor
            NoConsensusReached: When discussion lacks clear direction
            LLMCallFailed: When OpenAI API call fails
        """
        # Validate dependencies at runtime
        if not self._llm_client:
            raise RuntimeError(
                "BasePersonaAgent requires openai_client to be initialized. "
                "Provide this dependency in the constructor."
            )

        # If no discussion summary, we lack consensus
        if not discussion_summary or not discussion_summary.strip():
            raise NoConsensusReached("Empty discussion summary provided")

        # Build mechanics context for strategic planning
        mechanics_context = self._build_mechanics_context()

        # Build personality-aware system prompt
        system_prompt = f"""You are a strategic TTRPG player formulating your intent.

Your personality:
- Risk tolerance: {self.personality.risk_tolerance:.2f} (0=cautious, 1=reckless)
- Analytical score: {self.personality.analytical_score:.2f} (0=intuitive, 1=logical)
- Cooperativeness: {self.personality.cooperativeness:.2f}

{mechanics_context}

Based on group discussion, formulate YOUR strategic intent.
Consider game mechanics when assessing risks and choosing approaches.
"""

        user_prompt = f"""Group discussion summary:
{discussion_summary}

Formulate your strategic intent as JSON with:
{{
  "strategic_goal": "High-level objective you want to achieve",
  "reasoning": "Why this approach makes sense",
  "risk_assessment": "Identified risks and mitigation",
  "fallback_plan": "Alternative if primary fails"
}}

Ensure your intent reflects your personality traits.
"""

        try:
            response = await self._llm_client.call(
                system_prompt,
                user_prompt,
                temperature=self.temperature,
                response_format={"type": "json_object"},
            )

            # Parse JSON response
            data = json.loads(response)

            # Handle LLM returning structured risk_assessment (convert to string)
            risk_assessment = data.get("risk_assessment")
            if isinstance(risk_assessment, dict):
                risk_assessment = json.dumps(risk_assessment)

            fallback_plan = data.get("fallback_plan")
            if isinstance(fallback_plan, dict):
                fallback_plan = json.dumps(fallback_plan)

            # Create Intent object
            intent = Intent(
                agent_id=self.agent_id,
                strategic_goal=data.get("strategic_goal", ""),
                reasoning=data.get("reasoning", ""),
                risk_assessment=risk_assessment,
                fallback_plan=fallback_plan,
            )

            # Validate required fields
            if not intent.strategic_goal or not intent.reasoning:
                raise NoConsensusReached("LLM failed to provide complete intent")

            return intent

        except json.JSONDecodeError as e:
            raise LLMCallFailed(f"Failed to parse LLM JSON response: {e}") from e

    async def create_character_directive(
        self,
        intent: Intent,
        character_state: CharacterState,
    ) -> Directive:
        """
        Issue high-level instruction to character agent.

        Behavior:
        - MUST translate strategic intent into actionable directive
        - SHOULD consider character's current emotional/physical state
        - MUST NOT dictate exact dialogue or mannerisms
        - SHOULD provide emotional tone guidance

        Args:
            intent: Strategic intent from player layer
            character_state: Current character state for context

        Returns:
            Directive with instruction, tactical_guidance, emotional_tone

        Raises:
            RuntimeError: When openai_client not provided to constructor
            CharacterNotFound: When character_id doesn't exist
            InvalidCharacterState: When state is corrupted
            LLMCallFailed: When OpenAI API call fails
        """
        # Validate dependencies at runtime
        if not self._llm_client:
            raise RuntimeError(
                "BasePersonaAgent requires openai_client to be initialized. "
                "Provide this dependency in the constructor."
            )

        # Validate character_state is not None and has required fields
        if not character_state:
            raise CharacterNotFound("Character state is None")

        if not character_state.character_id:
            raise InvalidCharacterState("Character state missing character_id")

        # Validate character_state is not corrupted (basic sanity checks)
        if character_state.character_id and not character_state.character_id.startswith("char_"):
            raise InvalidCharacterState(
                f"Invalid character_id format: {character_state.character_id}"
            )

        # Build mechanics context for tactical directive creation
        mechanics_context = self._build_mechanics_context()

        system_prompt = f"""You are a TTRPG player issuing a directive to your character.

Your role: Translate strategic intent into character-level instruction.
- Specify WHAT to do, not HOW to do it
- Do NOT write dialogue or specific mannerisms
- Provide emotional tone/approach guidance
- Trust character layer to interpret appropriately

Your personality:
- Risk tolerance: {self.personality.risk_tolerance:.2f}
- Roleplay intensity: {self.personality.roleplay_intensity:.2f}

{mechanics_context}

Use your understanding of mechanics to guide character toward favorable approaches.
Consider whether LASERS or FEELINGS approaches better suit the situation and your character's strengths.
"""

        user_prompt = f"""Strategic intent:
Goal: {intent.strategic_goal}
Reasoning: {intent.reasoning}
Risks: {intent.risk_assessment or "None identified"}

Character current state:
Location: {character_state.current_location or "Unknown"}
Health: {character_state.health_status or "Normal"}
Emotional state: {character_state.emotional_state or "Neutral"}
Active effects: {', '.join(character_state.active_effects) if character_state.active_effects else "None"}

Create a directive as JSON:
{{
  "instruction": "What character should do (high-level action)",
  "tactical_guidance": "Optional tactical approach suggestions",
  "emotional_tone": "How character should feel/approach this"
}}

Keep instruction abstract - let character layer handle roleplay details.
"""

        try:
            response = await self._llm_client.call(
                system_prompt,
                user_prompt,
                temperature=self.temperature,
                response_format={"type": "json_object"},
            )

            data = json.loads(response)

            directive = Directive(
                from_player=self.agent_id,
                to_character=character_state.character_id,
                instruction=data.get("instruction", ""),
                tactical_guidance=data.get("tactical_guidance"),
                emotional_tone=data.get("emotional_tone"),
            )

            # Validate instruction is present
            if not directive.instruction:
                raise LLMCallFailed("Directive missing required instruction field")

            return directive

        except json.JSONDecodeError as e:
            raise LLMCallFailed(f"Failed to parse directive JSON: {e}") from e

    def _format_memories(self, memories: list[dict]) -> str:
        """
        Format retrieved memories into readable text.

        Args:
            memories: List of memory dicts from graph retrieval

        Returns:
            Formatted string of memories, or "No relevant memories" if empty
        """
        if not memories:
            return "No relevant memories found."

        formatted = []
        for mem in memories:
            # Extract fact and confidence from memory dict
            fact = mem.get("fact", mem.get("content", "Unknown"))
            confidence = mem.get("confidence", 1.0)
            formatted.append(f"- {fact} (confidence: {confidence:.2f})")

        return "\n".join(formatted)

    async def formulate_clarifying_question(
        self,
        dm_narration: str,
        retrieved_memories: list[dict],
        prior_qa: list[Message],
    ) -> dict | None:
        """
        Decide if NEW clarifying question is needed based on narration and context.

        Args:
            dm_narration: The DM's scene description for this turn
            retrieved_memories: Relevant memories from this player's graph
            prior_qa: All OOC messages from dm_clarification phase this turn

        Returns:
            dict with {"question": str, "reasoning": str} if player has a question
            None if player has no new questions

        Raises:
            RuntimeError: When openai_client not provided to constructor
            LLMCallFailed: When OpenAI API call fails after retries
        """
        # Validate dependencies at runtime
        if not self._llm_client:
            raise RuntimeError(
                "BasePersonaAgent requires openai_client to be initialized. "
                "Provide this dependency in the constructor."
            )

        # Format prior Q&A context
        prior_qa_context = ""
        if prior_qa:
            formatted_qa = []
            for msg in prior_qa:
                # Label messages from self as "You", from DM as "DM", others as-is
                if msg.from_agent == self.agent_id:
                    sender = "You"
                elif msg.from_agent == "dm":
                    sender = "DM"
                else:
                    sender = msg.from_agent
                formatted_qa.append(f"{sender}: {msg.content}")
            prior_qa_context = "\n".join(formatted_qa)

        # Format memories
        formatted_memories = self._format_memories(retrieved_memories)

        # Build mechanics context for informed questioning
        mechanics_context = self._build_mechanics_context()

        # Create LLM prompt
        system_prompt = f"""You are {self.agent_id}, a player in a tabletop RPG.

Your personality:
- Analytical score: {self.personality.analytical_score:.2f}
- Risk tolerance: {self.personality.risk_tolerance:.2f}

{mechanics_context}

You are deciding whether to ask the DM a clarifying question based on their narration.
"""

        user_prompt = f"""The DM narrated:
{dm_narration}

Your relevant memories:
{formatted_memories}
"""

        if prior_qa_context:
            user_prompt += f"""
Previous clarifying questions and answers this turn:
{prior_qa_context}
"""

        user_prompt += """
Do you have any NEW clarifying questions based on the narration and prior Q&A?

Guidelines:
- Don't repeat questions already asked
- You can ask follow-ups based on answers
- Only ask if you need factual information for your decision
- If your questions are answered, respond with has_question: false
- Ask about tactical details that affect your strategic planning

Respond with JSON:
{"has_question": true, "question": "...", "reasoning": "why I need this"}
OR
{"has_question": false}
"""

        try:
            response = await self._llm_client.call(
                system_prompt,
                user_prompt,
                temperature=self.temperature,
                response_format={"type": "json_object"},
            )

            # Parse JSON response
            data = json.loads(response)

            # Check if player has a question
            has_question = data.get("has_question", False)

            if has_question:
                question = data.get("question", "").strip()
                reasoning = data.get("reasoning", "").strip()

                # Validate question is present
                if not question:
                    raise LLMCallFailed(
                        "LLM indicated has_question=true but provided no question text"
                    )

                return {
                    "question": question,
                    "reasoning": reasoning or "No reasoning provided"
                }
            else:
                return None

        except json.JSONDecodeError as e:
            raise LLMCallFailed(f"Failed to parse clarifying question JSON: {e}") from e

    async def reformulate_strategy_after_laser_feelings(
        self,
        dm_narration: str,
        original_action: str,
        laser_answer: str,
        memories: list[dict],
    ) -> dict:
        """
        Reformulate strategic intent after receiving LASER FEELINGS answer from DM.

        After rolling LASER FEELINGS (exact match), the player receives an honest answer
        from the DM. This method reconsiders the original strategy in light of this new
        information and formulates a potentially different approach.

        Args:
            dm_narration: Original DM narration that prompted the action
            original_action: The original character action text (before reformulation)
            laser_answer: The DM's honest answer to the LASER FEELINGS question
            memories: List of relevant memories to inform the new strategy

        Returns:
            Dict with keys: {strategic_goal, reasoning, risk_assessment}

        Raises:
            LLMCallFailed: When OpenAI API fails
        """
        llm_client = LLMClient(self.openai_client, model=self.model, temperature=self.temperature)

        memory_context = self._format_memories(memories)

        prompt = f"""You are {self.agent_id}, a strategic tabletop RPG player.

SITUATION:
{dm_narration}

LASER FEELINGS:
Your character just rolled LASER FEELINGS (exact match) and asked a question. The DM just answered:
"{laser_answer}"

ORIGINAL ACTION:
Your character's original action was: "{original_action}"

YOUR TASK:
Given this new information from the DM's honest answer, reconsider your strategy. Do you want to:
1. Proceed with your original action as planned?
2. Modify your approach based on this new insight?
3. Completely pivot to a different tactic?

Remember:
- You're making a STRATEGIC decision (out-of-character), not a character action
- Your goal is to accomplish your character's goal effectively
- Use the new information wisely

{memory_context}

Respond with JSON:
{{
  "strategic_goal": "What you're now trying to accomplish after learning this",
  "reasoning": "Why you chose this approach",
  "risk_assessment": "What could go wrong with this new plan"
}}"""

        response = await llm_client.call_llm(prompt)

        try:
            # Try to parse JSON from response
            result = json.loads(response)
            return {
                "strategic_goal": result.get("strategic_goal", ""),
                "reasoning": result.get("reasoning", ""),
                "risk_assessment": result.get("risk_assessment", ""),
            }
        except json.JSONDecodeError:
            # If not JSON, return as-is
            return {
                "strategic_goal": response,
                "reasoning": "Direct text response from agent",
                "risk_assessment": "N/A",
            }
