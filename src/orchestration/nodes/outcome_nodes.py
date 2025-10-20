# ABOUTME: Dice resolution, helper mechanics, adjudication, and outcome narration node handlers.
# ABOUTME: Contains 5 node functions for dice rolling, LASER FEELINGS, helper resolution, and DM outcome phases.

from datetime import datetime

from loguru import logger

from src.models.game_state import GamePhase, GameState
from src.models.messages import MessageChannel, MessageType
from src.orchestration.message_router import MessageRouter
from src.orchestration.nodes.helpers import _get_character_id_for_agent, _load_character_number
from src.utils.dice import roll_lasers_feelings


def dm_adjudication_node(state: GameState) -> GameState:
    """
    T052: Wait for DM success/fail command.

    Args:
        state: Current game state

    Returns:
        Updated state waiting for DM adjudication
    """
    logger.info(f"[PHASE: DM_ADJUDICATION] Turn {state['turn_number']}")

    # In interactive mode, this pauses execution and waits for DM input
    # For now, we assume DM provides adjudication and continue

    # Check if dice roll is needed
    needs_dice = state.get("dm_adjudication_needed", True)

    if needs_dice and "dice_override" not in state:
        next_phase = GamePhase.DICE_RESOLUTION.value
    else:
        # DM provided direct success/fail, skip dice
        next_phase = GamePhase.DM_OUTCOME.value

    return {**state, "current_phase": next_phase, "phase_start_time": datetime.now()}


def resolve_helpers_node(state: GameState) -> GameState:
    """
    Phase 1 Issue #2: Resolve all helping actions before main action.

    Helper Success Threshold:
    - Helper is "successful" if their roll achieves total_successes >= 1
    - Each successful helper grants +1d6 to the character they're helping
    - Failed helpers (0 successes) provide no bonus and no penalty

    Process:
    1. Identify primary actions (non-helping actions)
    2. For each primary character:
       a. Find all helpers targeting this character
       b. Validate helpers are targeting valid characters
       c. For each valid helper:
          - Load helper's character number from config
          - Build dice pool (helper's own prepared/expert bonuses apply)
          - Roll dice using roll_lasers_feelings() with successful_helpers=0
          - Check if total_successes >= 1 (threshold for successful help)
       d. Count successful helpers
       e. Store count in state.successful_helper_counts dict

    Args:
        state: Current game state with character_actions populated

    Returns:
        Updated state with:
        - successful_helper_counts: dict mapping character_id → helper count
        - current_phase: Set to DICE_RESOLUTION
        - phase_start_time: Updated to current time

    Raises:
        No exceptions - errors are logged and handled gracefully

    Notes:
        - Helpers use their own character_number (loaded from config)
        - Helpers do not receive helper bonuses themselves (successful_helpers=0)
        - Invalid helpers (nonexistent targets, config errors) are skipped with warnings
        - Helper roll failures are treated as 0 successes, not crashes
    """
    logger.info(f"[PHASE: RESOLVE_HELPERS] Turn {state['turn_number']}")

    character_actions = state.get("character_actions", {})

    # Initialize successful_helper_counts dict
    successful_helper_counts: dict[str, int] = {}

    # Identify primary actions (not helping others)
    primary_actions = {
        char_id: action
        for char_id, action in character_actions.items()
        if not action.get("is_helping", False)
    }

    logger.debug(f"Found {len(primary_actions)} primary actions")

    # For each primary action, find and process helpers
    for primary_char_id, primary_action in primary_actions.items():
        # Find all helpers for this primary character
        helpers = [
            action
            for action in character_actions.values()
            if (
                action.get("is_helping", False)
                and action.get("helping_character_id") == primary_char_id
            )
        ]

        if not helpers:
            # No helpers for this character
            successful_helper_counts[primary_char_id] = 0
            logger.debug(f"{primary_char_id} has no helpers")
            continue

        logger.debug(f"{primary_char_id} has {len(helpers)} helper(s)")

        # Validate all helpers before processing
        valid_helpers = []
        for helper_action in helpers:
            helper_char_id = helper_action.get("character_id", "unknown")
            target_char_id = helper_action.get("helping_character_id")

            # Check if target exists in primary actions
            if target_char_id not in primary_actions:
                logger.warning(
                    f"Helper {helper_char_id} targeting nonexistent character "
                    f"{target_char_id} - skipping this helper"
                )
                continue  # Skip invalid helper

            valid_helpers.append(helper_action)

        # Process only valid helpers
        helpers = valid_helpers
        if not helpers:
            successful_helper_counts[primary_char_id] = 0
            logger.debug(f"{primary_char_id} has no valid helpers after validation")
            continue

        logger.info(f"{primary_char_id} has {len(helpers)} valid helper(s)")

        # Roll for each helper and count successes
        successful_count = 0
        for helper_action in helpers:
            helper_char_id = helper_action.get("character_id", "unknown")

            # Extract helper's dice modifiers
            task_type = helper_action.get("task_type", "lasers")
            is_prepared = helper_action.get("is_prepared", False)
            is_expert = helper_action.get("is_expert", False)

            # Load helper's character number from config
            try:
                helper_character_number = _load_character_number(helper_char_id)
            except (FileNotFoundError, ValueError) as e:
                logger.warning(
                    f"Could not load character number for {helper_char_id}: {e}. "
                    f"Using fallback number 3 (balanced character)"
                )
                helper_character_number = 3

            # Roll dice for helper (with their own modifiers, no successful_helpers bonus)
            try:
                helper_roll_result = roll_lasers_feelings(
                    character_number=helper_character_number,
                    task_type=task_type,
                    is_prepared=is_prepared,
                    is_expert=is_expert,
                    successful_helpers=0,  # Helpers don't get helper bonuses
                )

                # Check if helper succeeded (≥1 success)
                if helper_roll_result.total_successes >= 1:
                    successful_count += 1
                    logger.info(
                        f"Helper {helper_char_id} succeeded: "
                        f"{helper_roll_result.individual_rolls} → {helper_roll_result.total_successes} successes"
                    )
                else:
                    logger.info(
                        f"Helper {helper_char_id} failed: "
                        f"{helper_roll_result.individual_rolls} → 0 successes (no bonus)"
                    )
            except Exception as e:
                logger.error(
                    f"Helper {helper_char_id} roll failed with error: {e}. "
                    f"Treating as failed roll (0 successes)"
                )
                # Continue with next helper - don't crash the turn
                continue

        # Store successful helper count for this primary character
        successful_helper_counts[primary_char_id] = successful_count
        logger.info(f"{primary_char_id} has {successful_count} successful helper(s)")

    logger.debug(f"Successful helper counts: {successful_helper_counts}")

    return {
        **state,
        "successful_helper_counts": successful_helper_counts,
        "current_phase": GamePhase.DICE_RESOLUTION.value,
        "phase_start_time": datetime.now(),
    }


def dice_resolution_node(state: GameState) -> GameState:
    """
    T053: Execute dice rolls using Lasers & Feelings multi-die system.

    Phase 2 Issue #3: Detects LASER FEELINGS (exact match) and pauses for GM question.

    Args:
        state: Current game state

    Returns:
        Updated state with dice roll result fields, or LASER_FEELINGS_QUESTION pause
    """
    logger.info(f"[PHASE: DICE_RESOLUTION] Turn {state['turn_number']}")

    # Get character ID from state (first active agent for single-agent MVP)
    character_id = state["active_agents"][0] if state["active_agents"] else None
    if not character_id:
        raise ValueError("No active agents found for dice resolution")

    # Map agent_id to character_id
    character_id = _get_character_id_for_agent(character_id)

    # Get character action to extract dice modifiers
    character_action_dict = state["character_actions"].get(character_id, {})

    # Extract action details
    task_type = character_action_dict.get("task_type", "lasers")
    is_prepared = character_action_dict.get("is_prepared", False)
    is_expert = character_action_dict.get("is_expert", False)
    is_helping = character_action_dict.get("is_helping", False)
    gm_question = character_action_dict.get("gm_question")

    # Get character number from config (MVP hardcoded)
    # TODO: Load from character config in full implementation
    character_number = 2  # Android Engineer (good at Lasers)

    # Get successful helper count from state (Phase 1 Issue #2)
    successful_helper_counts = state.get("successful_helper_counts", {})
    successful_helpers = successful_helper_counts.get(character_id, 0)

    # Perform Lasers & Feelings roll
    roll_result = roll_lasers_feelings(
        character_number=character_number,
        task_type=task_type,
        is_prepared=is_prepared,
        is_expert=is_expert,
        successful_helpers=successful_helpers,  # Phase 1 Issue #2: Use actual helper count
        gm_question=gm_question,
    )

    # Log roll details
    logger.info(
        f"Dice resolution: {roll_result.individual_rolls} "
        f"({roll_result.dice_count}d6, prepared={is_prepared}, expert={is_expert}, helping={is_helping}) "
        f"vs number {character_number} ({task_type}) = "
        f"{roll_result.total_successes} successes → {roll_result.outcome.value.upper()}"
    )

    if roll_result.has_laser_feelings:
        logger.info(
            f"LASER FEELINGS! (rolled exact {character_number} on die(s) {roll_result.laser_feelings_indices})"
        )

    # Phase 2 Issue #3: Check for LASER FEELINGS and pause for GM question
    if len(roll_result.laser_feelings_indices) > 0:
        logger.info(
            f"{character_id} rolled LASER FEELINGS on die {roll_result.laser_feelings_indices[0] + 1}"
        )

        # Map roll result to state fields (same as normal flow for backward compatibility)
        dice_roll_result = {
            "character_number": roll_result.character_number,
            "task_type": roll_result.task_type,
            "is_prepared": roll_result.is_prepared,
            "is_expert": roll_result.is_expert,
            "is_helping": roll_result.is_helping,
            "individual_rolls": roll_result.individual_rolls,
            "die_successes": roll_result.die_successes,
            "laser_feelings_indices": roll_result.laser_feelings_indices,
            "total_successes": roll_result.total_successes,
            "outcome": roll_result.outcome.value,
            "timestamp": roll_result.timestamp,
        }

        # Deprecated fields (backward compatibility)
        dice_result = roll_result.individual_rolls[0] if roll_result.individual_rolls else 0
        dice_success = roll_result.total_successes > 0
        dice_complication = roll_result.has_laser_feelings

        # Store original roll and action for potential modification
        return {
            **state,
            "current_phase": GamePhase.LASER_FEELINGS_QUESTION.value,
            # Store dice results (for backward compatibility with existing tests)
            "dice_roll_result": dice_roll_result,
            "dice_action_character": character_id,
            "dice_result": dice_result,
            "dice_success": dice_success,
            "dice_complication": dice_complication,
            # LASER FEELINGS specific data
            "laser_feelings_data": {
                "character_id": character_id,
                "original_action": character_action_dict,
                "original_roll": {
                    "character_number": roll_result.character_number,
                    "task_type": roll_result.task_type,
                    "is_prepared": roll_result.is_prepared,
                    "is_expert": roll_result.is_expert,
                    "is_helping": roll_result.is_helping,
                    "individual_rolls": roll_result.individual_rolls,
                    "die_successes": roll_result.die_successes,
                    "laser_feelings_indices": roll_result.laser_feelings_indices,
                    "total_successes": roll_result.total_successes,
                    "outcome": roll_result.outcome.value,
                    "timestamp": roll_result.timestamp,
                },
                "gm_question": gm_question,
                "dice_parameters": {
                    "character_number": character_number,
                    "task_type": task_type,
                    "is_prepared": is_prepared,
                    "is_expert": is_expert,
                    "successful_helpers": successful_helpers,
                },
            },
            "phase_start_time": datetime.now(),
        }

    # No LASER FEELINGS - proceed with normal outcome
    # Map LasersFeelingRollResult to GameState fields
    # New fields (primary)
    dice_roll_result = {
        "character_number": roll_result.character_number,
        "task_type": roll_result.task_type,
        "is_prepared": roll_result.is_prepared,
        "is_expert": roll_result.is_expert,
        "is_helping": roll_result.is_helping,
        "individual_rolls": roll_result.individual_rolls,
        "die_successes": roll_result.die_successes,
        "laser_feelings_indices": roll_result.laser_feelings_indices,
        "total_successes": roll_result.total_successes,
        "outcome": roll_result.outcome.value,
        "timestamp": roll_result.timestamp,
    }

    # Deprecated fields (backward compatibility)
    dice_result = roll_result.individual_rolls[0] if roll_result.individual_rolls else 0
    dice_success = roll_result.total_successes > 0
    dice_complication = roll_result.has_laser_feelings

    return {
        **state,
        # New fields (primary)
        "dice_roll_result": dice_roll_result,
        "dice_action_character": character_id,  # Store which character rolled
        # Deprecated fields (backward compatibility)
        "dice_result": dice_result,
        "dice_success": dice_success,
        "dice_complication": dice_complication,
        "current_phase": GamePhase.DM_OUTCOME.value,
        "phase_start_time": datetime.now(),
    }


def laser_feelings_question_node(state: GameState) -> GameState:
    """
    Phase 2 Issue #3: Pause turn and wait for GM to answer character's LASER FEELINGS question.

    This is an interrupt point - the state machine will pause here until
    the DM provides an answer via the CLI.

    Args:
        state: Current game state with laser_feelings_data populated

    Returns:
        State with prompt for DM to answer question
    """
    laser_data = state.get("laser_feelings_data", {})
    character_id = laser_data.get("character_id", "unknown")
    gm_question = laser_data.get("gm_question", "No question provided")

    logger.info(f"LASER FEELINGS: {character_id} asks GM: {gm_question}")

    # This node just waits - the DM will trigger continuation via CLI
    return {**state, "waiting_for_gm_answer": True, "phase_start_time": datetime.now()}


def _create_dm_outcome_node(router: MessageRouter):
    """
    Factory for dm_outcome_node with injected dependencies.

    Args:
        router: MessageRouter for sending IC messages

    Returns:
        Node function with captured router dependency
    """

    def dm_outcome_node(state: GameState) -> GameState:
        """
        T054: Process DM narrated outcome.

        Args:
            state: Current game state

        Returns:
            Updated state with dm_outcome
        """
        logger.info(f"[PHASE: DM_OUTCOME] Turn {state['turn_number']}")

        # In interactive mode, DM provides outcome narration
        # For MVP skeleton, we generate placeholder outcome
        if "dm_outcome" in state and state["dm_outcome"]:
            outcome = state["dm_outcome"]
        else:
            # Generate placeholder based on dice result
            if state.get("dice_success", True):
                outcome = "The action succeeds."
            else:
                outcome = "The action fails."

        logger.debug(f"DM outcome: {outcome[:100]}...")

        # Route outcome as IC message
        router.add_message(
            channel=MessageChannel.IC,
            from_agent="dm",
            content=outcome,
            message_type=MessageType.NARRATION,
            phase=GamePhase.DM_OUTCOME.value,
            turn_number=state["turn_number"],
            session_number=state.get("session_number"),
        )

        # Route LASER FEELINGS answer to player (OOC) if provided
        # LASER FEELINGS insights are for the player strategically, not the character
        laser_feelings_answer = state.get("laser_feelings_answer")
        if laser_feelings_answer:
            # Get agent ID from dice roll result
            agent_id = None
            # Try to find the agent that rolled LASER FEELINGS
            character_id = state.get("dice_action_character")
            if character_id:
                # Map character back to agent
                for active_agent_id in state["active_agents"]:
                    if _get_character_id_for_agent(active_agent_id) == character_id:
                        agent_id = active_agent_id
                        break

            if agent_id:
                logger.info(f"Routing LASER FEELINGS insight to player {agent_id} (OOC)")
                router.add_message(
                    channel=MessageChannel.OOC,
                    from_agent="dm",
                    content=f"[LASER FEELINGS]: {laser_feelings_answer}",
                    message_type=MessageType.NARRATION,
                    phase=GamePhase.DM_OUTCOME.value,
                    turn_number=state["turn_number"],
                    to_agents=[agent_id],
                    session_number=state.get("session_number"),
                )
            else:
                logger.warning("Cannot route LASER FEELINGS answer: no agent_id found")

        return {
            **state,
            "dm_outcome": outcome,
            "current_phase": GamePhase.CHARACTER_REACTION.value,
            "phase_start_time": datetime.now(),
        }

    return dm_outcome_node
