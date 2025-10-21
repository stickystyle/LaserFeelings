# ABOUTME: Unit tests for message routing models including channels, types, and visibility rules.
# ABOUTME: Tests Message, DirectiveMessage, ICMessageSummary, and DM command structures.

from datetime import datetime

import pytest
from pydantic import ValidationError

from src.models.messages import (
    MessageChannel,
    MessageType,
    Message,
    DirectiveMessage,
    ICMessageSummary,
    DMCommandType,
    DMCommand,
    DiceRoll,
    VISIBILITY_RULES
)


class TestMessageChannel:
    """Test suite for MessageChannel enum"""

    def test_all_message_channels_exist(self):
        """Test all message channel enum values exist"""
        assert MessageChannel.IC.value == "in_character"
        assert MessageChannel.OOC.value == "out_of_character"
        assert MessageChannel.P2C.value == "player_to_character"

    def test_message_channel_from_string(self):
        """Test creating MessageChannel from string value"""
        assert MessageChannel("in_character") == MessageChannel.IC
        assert MessageChannel("out_of_character") == MessageChannel.OOC
        assert MessageChannel("player_to_character") == MessageChannel.P2C

    def test_invalid_message_channel_raises_error(self):
        """Test invalid channel value raises error"""
        with pytest.raises(ValueError):
            MessageChannel("invalid_channel")


class TestMessageType:
    """Test suite for MessageType enum"""

    def test_all_message_types_exist(self):
        """Test all message type enum values exist"""
        assert MessageType.NARRATION.value == "narration"
        assert MessageType.DIALOGUE.value == "dialogue"
        assert MessageType.ACTION.value == "action"
        assert MessageType.REACTION.value == "reaction"
        assert MessageType.DISCUSSION.value == "discussion"
        assert MessageType.DIRECTIVE.value == "directive"
        assert MessageType.SYSTEM.value == "system"

    def test_message_type_from_string(self):
        """Test creating MessageType from string value"""
        assert MessageType("narration") == MessageType.NARRATION
        assert MessageType("dialogue") == MessageType.DIALOGUE
        assert MessageType("action") == MessageType.ACTION
        assert MessageType("reaction") == MessageType.REACTION
        assert MessageType("discussion") == MessageType.DISCUSSION
        assert MessageType("directive") == MessageType.DIRECTIVE
        assert MessageType("system") == MessageType.SYSTEM

    def test_invalid_message_type_raises_error(self):
        """Test invalid message type raises error"""
        with pytest.raises(ValueError):
            MessageType("invalid_type")


class TestMessage:
    """Test suite for Message model"""

    def test_valid_message_creation(self):
        """Test creating message with valid data"""
        now = datetime.now()
        message = Message(
            message_id="msg_001",
            channel=MessageChannel.IC,
            from_agent="char_001",
            to_agents=None,
            content="I scan the area for threats",
            timestamp=now,
            message_type=MessageType.ACTION,
            phase="character_action",
            turn_number=5,
            session_number=1
        )
        assert message.message_id == "msg_001"
        # use_enum_values=True converts to string
        assert message.channel == "in_character"
        assert message.from_agent == "char_001"
        assert message.to_agents is None
        assert message.content == "I scan the area for threats"
        assert message.timestamp == now
        assert message.message_type == "action"
        assert message.phase == "character_action"
        assert message.turn_number == 5
        assert message.session_number == 1

    def test_message_with_recipients(self):
        """Test message with specific recipients"""
        now = datetime.now()
        message = Message(
            message_id="msg_002",
            channel=MessageChannel.OOC,
            from_agent="agent_001",
            to_agents=["agent_002", "agent_003"],
            content="Should we attack?",
            timestamp=now,
            message_type=MessageType.DISCUSSION,
            phase="ooc_discussion",
            turn_number=3
        )
        assert message.to_agents == ["agent_002", "agent_003"]
        assert len(message.to_agents) == 2

    def test_message_broadcast_none_recipients(self):
        """Test message with None to_agents is broadcast"""
        now = datetime.now()
        message = Message(
            message_id="msg_003",
            channel=MessageChannel.IC,
            from_agent="dm",
            to_agents=None,
            content="The door creaks open",
            timestamp=now,
            message_type=MessageType.NARRATION,
            phase="dm_narration",
            turn_number=1
        )
        assert message.to_agents is None

    def test_message_session_number_optional(self):
        """Test session_number is optional and defaults to None"""
        now = datetime.now()
        message = Message(
            message_id="msg_004",
            channel=MessageChannel.OOC,
            from_agent="agent_001",
            content="Test",
            timestamp=now,
            message_type=MessageType.SYSTEM,
            phase="dm_narration",
            turn_number=1
        )
        assert message.session_number is None

    def test_message_all_channels(self):
        """Test message can be created with all channel types"""
        now = datetime.now()
        for channel in [MessageChannel.IC, MessageChannel.OOC, MessageChannel.P2C]:
            message = Message(
                message_id="msg_test",
                channel=channel,
                from_agent="test",
                content="Test",
                timestamp=now,
                message_type=MessageType.SYSTEM,
                phase="test",
                turn_number=1
            )
            assert isinstance(message.channel, str)

    def test_message_all_types(self):
        """Test message can be created with all message types"""
        now = datetime.now()
        for msg_type in [
            MessageType.NARRATION,
            MessageType.DIALOGUE,
            MessageType.ACTION,
            MessageType.REACTION,
            MessageType.DISCUSSION,
            MessageType.DIRECTIVE,
            MessageType.SYSTEM
        ]:
            message = Message(
                message_id="msg_test",
                channel=MessageChannel.IC,
                from_agent="test",
                content="Test",
                timestamp=now,
                message_type=msg_type,
                phase="test",
                turn_number=1
            )
            assert isinstance(message.message_type, str)

    def test_message_serialization(self):
        """Test message can be serialized to dict"""
        now = datetime.now()
        message = Message(
            message_id="msg_001",
            channel=MessageChannel.IC,
            from_agent="char_001",
            content="Test",
            timestamp=now,
            message_type=MessageType.ACTION,
            phase="character_action",
            turn_number=5
        )
        data = message.model_dump()
        assert isinstance(data, dict)
        assert data["message_id"] == "msg_001"
        assert data["channel"] == "in_character"
        assert data["from_agent"] == "char_001"
        assert data["turn_number"] == 5

    def test_message_required_fields(self):
        """Test all required fields must be provided"""
        with pytest.raises(ValidationError) as exc_info:
            Message()
        error_str = str(exc_info.value)
        assert "message_id" in error_str
        assert "channel" in error_str
        assert "from_agent" in error_str
        assert "content" in error_str
        assert "timestamp" in error_str
        assert "message_type" in error_str
        assert "phase" in error_str
        assert "turn_number" in error_str


class TestDirectiveMessage:
    """Test suite for DirectiveMessage model"""

    def test_valid_directive_creation(self):
        """Test creating directive message with valid data"""
        now = datetime.now()
        directive = DirectiveMessage(
            from_player="agent_001",
            to_character="char_001",
            strategic_directive="Scan the area for threats",
            scene_context="You are in a dark corridor",
            timestamp=now
        )
        assert directive.from_player == "agent_001"
        assert directive.to_character == "char_001"
        assert directive.strategic_directive == "Scan the area for threats"
        assert directive.scene_context == "You are in a dark corridor"
        assert directive.timestamp == now

    def test_directive_interpreted_as_optional(self):
        """Test interpreted_as field is optional and defaults to None"""
        now = datetime.now()
        directive = DirectiveMessage(
            from_player="agent_001",
            to_character="char_001",
            strategic_directive="Test",
            scene_context="Test scene",
            timestamp=now
        )
        assert directive.interpreted_as is None

    def test_directive_with_interpretation(self):
        """Test directive with interpreted_as filled"""
        now = datetime.now()
        directive = DirectiveMessage(
            from_player="agent_001",
            to_character="char_001",
            strategic_directive="Be careful",
            scene_context="Dangerous area",
            timestamp=now,
            interpreted_as="I proceed cautiously, scanning for danger"
        )
        assert directive.interpreted_as == "I proceed cautiously, scanning for danger"

    def test_directive_serialization(self):
        """Test directive can be serialized to dict"""
        now = datetime.now()
        directive = DirectiveMessage(
            from_player="agent_001",
            to_character="char_001",
            strategic_directive="Test directive",
            scene_context="Test scene",
            timestamp=now
        )
        data = directive.model_dump()
        assert isinstance(data, dict)
        assert data["from_player"] == "agent_001"
        assert data["to_character"] == "char_001"

    def test_directive_required_fields(self):
        """Test all required fields must be provided"""
        with pytest.raises(ValidationError) as exc_info:
            DirectiveMessage()
        error_str = str(exc_info.value)
        assert "from_player" in error_str
        assert "to_character" in error_str
        assert "strategic_directive" in error_str
        assert "scene_context" in error_str
        assert "timestamp" in error_str


class TestICMessageSummary:
    """Test suite for ICMessageSummary model"""

    def test_valid_ic_summary_creation(self):
        """Test creating IC message summary with valid data"""
        now = datetime.now()
        summary = ICMessageSummary(
            character_id="char_001",
            action_summary="Scanned the area for threats",
            outcome_summary="Found no immediate dangers",
            turn_number=5,
            timestamp=now
        )
        assert summary.character_id == "char_001"
        assert summary.action_summary == "Scanned the area for threats"
        assert summary.outcome_summary == "Found no immediate dangers"
        assert summary.turn_number == 5
        assert summary.timestamp == now

    def test_ic_summary_outcome_optional(self):
        """Test outcome_summary is optional and defaults to None"""
        now = datetime.now()
        summary = ICMessageSummary(
            character_id="char_001",
            action_summary="Attempted to hack the terminal",
            turn_number=3,
            timestamp=now
        )
        assert summary.outcome_summary is None

    def test_ic_summary_serialization(self):
        """Test IC summary can be serialized to dict"""
        now = datetime.now()
        summary = ICMessageSummary(
            character_id="char_001",
            action_summary="Test action",
            turn_number=1,
            timestamp=now
        )
        data = summary.model_dump()
        assert isinstance(data, dict)
        assert data["character_id"] == "char_001"
        assert data["action_summary"] == "Test action"

    def test_ic_summary_required_fields(self):
        """Test all required fields must be provided"""
        with pytest.raises(ValidationError) as exc_info:
            ICMessageSummary()
        error_str = str(exc_info.value)
        assert "character_id" in error_str
        assert "action_summary" in error_str
        assert "turn_number" in error_str
        assert "timestamp" in error_str


class TestDMCommandType:
    """Test suite for DMCommandType enum"""

    def test_all_dm_command_types_exist(self):
        """Test all DM command type enum values exist"""
        assert DMCommandType.NARRATE.value == "narrate"
        assert DMCommandType.ROLL.value == "roll"
        assert DMCommandType.SUCCESS.value == "success"
        assert DMCommandType.FAILURE.value == "failure"
        assert DMCommandType.PAUSE.value == "pause"
        assert DMCommandType.RESUME.value == "resume"
        assert DMCommandType.SAVE.value == "save"
        assert DMCommandType.LOAD.value == "load"
        assert DMCommandType.STATUS.value == "status"
        assert DMCommandType.HELP.value == "help"

    def test_dm_command_type_from_string(self):
        """Test creating DMCommandType from string value"""
        assert DMCommandType("narrate") == DMCommandType.NARRATE
        assert DMCommandType("roll") == DMCommandType.ROLL


class TestDMCommand:
    """Test suite for DMCommand model"""

    def test_valid_dm_command_creation(self):
        """Test creating DM command with valid data"""
        now = datetime.now()
        command = DMCommand(
            command_type=DMCommandType.NARRATE,
            args={"text": "The door opens"},
            timestamp=now
        )
        assert command.command_type == "narrate"
        assert command.args == {"text": "The door opens"}
        assert command.timestamp == now

    def test_dm_command_empty_args(self):
        """Test DM command with empty args defaults to empty dict"""
        now = datetime.now()
        command = DMCommand(
            command_type=DMCommandType.STATUS,
            timestamp=now
        )
        assert command.args == {}

    def test_dm_command_all_types(self):
        """Test DM command can be created with all command types"""
        now = datetime.now()
        for cmd_type in [
            DMCommandType.NARRATE,
            DMCommandType.ROLL,
            DMCommandType.SUCCESS,
            DMCommandType.FAILURE,
            DMCommandType.PAUSE,
            DMCommandType.RESUME,
            DMCommandType.SAVE,
            DMCommandType.LOAD,
            DMCommandType.STATUS,
            DMCommandType.HELP
        ]:
            command = DMCommand(
                command_type=cmd_type,
                timestamp=now
            )
            assert isinstance(command.command_type, str)

    def test_dm_command_serialization(self):
        """Test DM command can be serialized to dict"""
        now = datetime.now()
        command = DMCommand(
            command_type=DMCommandType.ROLL,
            args={"value": 5},
            timestamp=now
        )
        data = command.model_dump()
        assert isinstance(data, dict)
        assert data["command_type"] == "roll"
        assert data["args"]["value"] == 5

    def test_dm_command_required_fields(self):
        """Test command_type and timestamp are required"""
        with pytest.raises(ValidationError) as exc_info:
            DMCommand()
        error_str = str(exc_info.value)
        assert "command_type" in error_str
        assert "timestamp" in error_str


class TestDiceRoll:
    """Test suite for DiceRoll model"""

    def test_valid_dice_roll_creation(self):
        """Test creating dice roll with valid data"""
        now = datetime.now()
        roll = DiceRoll(
            notation="2d6",
            dice_count=2,
            dice_sides=6,
            modifier=0,
            individual_rolls=[4, 5],
            total=9,
            timestamp=now
        )
        assert roll.notation == "2d6"
        assert roll.dice_count == 2
        assert roll.dice_sides == 6
        assert roll.modifier == 0
        assert roll.individual_rolls == [4, 5]
        assert roll.total == 9
        assert roll.timestamp == now

    def test_dice_roll_with_modifier(self):
        """Test dice roll with positive modifier"""
        now = datetime.now()
        roll = DiceRoll(
            notation="1d20+5",
            dice_count=1,
            dice_sides=20,
            modifier=5,
            individual_rolls=[15],
            total=20,
            timestamp=now
        )
        assert roll.modifier == 5
        assert roll.total == 20

    def test_dice_roll_modifier_default_zero(self):
        """Test modifier defaults to 0"""
        now = datetime.now()
        roll = DiceRoll(
            notation="1d6",
            dice_count=1,
            dice_sides=6,
            individual_rolls=[4],
            total=4,
            timestamp=now
        )
        assert roll.modifier == 0

    def test_dice_roll_rolls_sum_property(self):
        """Test rolls_sum property calculates sum of individual rolls"""
        now = datetime.now()
        roll = DiceRoll(
            notation="3d6",
            dice_count=3,
            dice_sides=6,
            modifier=2,
            individual_rolls=[3, 4, 5],
            total=14,
            timestamp=now
        )
        assert roll.rolls_sum == 12  # 3+4+5, before modifier

    def test_dice_count_validation(self):
        """Test dice_count must be >= 1"""
        now = datetime.now()

        # Valid
        DiceRoll(
            notation="1d6",
            dice_count=1,
            dice_sides=6,
            individual_rolls=[3],
            total=3,
            timestamp=now
        )

        # Invalid
        with pytest.raises(ValidationError) as exc_info:
            DiceRoll(
                notation="0d6",
                dice_count=0,
                dice_sides=6,
                individual_rolls=[],
                total=0,
                timestamp=now
            )
        assert "dice_count" in str(exc_info.value)

    def test_dice_sides_validation(self):
        """Test dice_sides must be >= 2"""
        now = datetime.now()

        # Valid
        DiceRoll(
            notation="1d2",
            dice_count=1,
            dice_sides=2,
            individual_rolls=[1],
            total=1,
            timestamp=now
        )

        # Invalid
        with pytest.raises(ValidationError) as exc_info:
            DiceRoll(
                notation="1d1",
                dice_count=1,
                dice_sides=1,
                individual_rolls=[1],
                total=1,
                timestamp=now
            )
        assert "dice_sides" in str(exc_info.value)

    def test_dice_roll_serialization(self):
        """Test dice roll can be serialized to dict"""
        now = datetime.now()
        roll = DiceRoll(
            notation="2d6",
            dice_count=2,
            dice_sides=6,
            individual_rolls=[3, 4],
            total=7,
            timestamp=now
        )
        data = roll.model_dump()
        assert isinstance(data, dict)
        assert data["notation"] == "2d6"
        assert data["dice_count"] == 2
        assert data["individual_rolls"] == [3, 4]

    def test_dice_roll_required_fields(self):
        """Test all required fields must be provided"""
        with pytest.raises(ValidationError) as exc_info:
            DiceRoll()
        error_str = str(exc_info.value)
        assert "notation" in error_str
        assert "dice_count" in error_str
        assert "dice_sides" in error_str
        assert "individual_rolls" in error_str
        assert "total" in error_str
        assert "timestamp" in error_str


class TestVisibilityRules:
    """Test suite for VISIBILITY_RULES constant"""

    def test_visibility_rules_structure(self):
        """Test VISIBILITY_RULES has correct structure"""
        assert isinstance(VISIBILITY_RULES, dict)
        assert MessageChannel.IC in VISIBILITY_RULES
        assert MessageChannel.OOC in VISIBILITY_RULES
        assert MessageChannel.P2C in VISIBILITY_RULES

    def test_ic_visibility_rules(self):
        """Test IC channel visibility rules"""
        ic_rules = VISIBILITY_RULES[MessageChannel.IC]
        assert ic_rules["characters"] is True
        assert ic_rules["base_personas"] == "summary_only"

    def test_ooc_visibility_rules(self):
        """Test OOC channel visibility rules"""
        ooc_rules = VISIBILITY_RULES[MessageChannel.OOC]
        assert ooc_rules["characters"] is False
        assert ooc_rules["base_personas"] is True

    def test_p2c_visibility_rules(self):
        """Test P2C channel visibility rules"""
        p2c_rules = VISIBILITY_RULES[MessageChannel.P2C]
        assert p2c_rules["characters"] == "recipient_only"
        assert p2c_rules["base_personas"] is False

    def test_all_channels_have_rules(self):
        """Test all message channels have visibility rules defined"""
        for channel in [MessageChannel.IC, MessageChannel.OOC, MessageChannel.P2C]:
            assert channel in VISIBILITY_RULES
            rules = VISIBILITY_RULES[channel]
            assert "characters" in rules
            assert "base_personas" in rules
