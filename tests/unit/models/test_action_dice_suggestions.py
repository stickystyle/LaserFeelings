# ABOUTME: Unit tests for Action model's dice suggestion fields and validation logic.
# ABOUTME: Validates prepared/expert/helping flags and their required justification fields.

import pytest
from pydantic import ValidationError

from src.models.agent_actions import Action


class TestActionValidConstruction:
    """Test suite for valid Action model construction with dice suggestions"""

    def test_valid_action_with_all_dice_suggestions(self):
        """Test creating Action with all dice suggestion fields populated"""
        action = Action(
            character_id="char_zara_001",
            narrative_text="I carefully analyze the alien console while providing technical guidance to Kai.",
            task_type="lasers",
            is_prepared=True,
            prepared_justification="I studied similar alien technology in the academy archives",
            is_expert=True,
            expert_justification="I have extensive training in xenotechnology from my engineering background",
            is_helping=True,
            helping_character_id="char_kai_002",
            help_justification="I'm pointing out critical interface patterns to help Kai avoid triggering security protocols"
        )

        assert action.character_id == "char_zara_001"
        assert action.task_type == "lasers"
        assert action.is_prepared is True
        assert action.prepared_justification == "I studied similar alien technology in the academy archives"
        assert action.is_expert is True
        assert action.expert_justification == "I have extensive training in xenotechnology from my engineering background"
        assert action.is_helping is True
        assert action.helping_character_id == "char_kai_002"
        assert action.help_justification == "I'm pointing out critical interface patterns to help Kai avoid triggering security protocols"

    def test_valid_action_with_only_prepared(self):
        """Test Action with only is_prepared flag and justification"""
        action = Action(
            character_id="char_lyra_003",
            narrative_text="I approach the negotiation with the alien ambassador.",
            task_type="feelings",
            is_prepared=True,
            prepared_justification="I researched this species' diplomatic customs beforehand"
        )

        assert action.is_prepared is True
        assert action.prepared_justification == "I researched this species' diplomatic customs beforehand"
        assert action.is_expert is False
        assert action.expert_justification is None
        assert action.is_helping is False

    def test_valid_action_with_only_expert(self):
        """Test Action with only is_expert flag and justification"""
        action = Action(
            character_id="char_alex_004",
            narrative_text="I pilot the ship through the asteroid field with precision.",
            task_type="lasers",
            is_expert=True,
            expert_justification="I'm a veteran pilot with thousands of hours in hazardous navigation"
        )

        assert action.is_expert is True
        assert action.expert_justification == "I'm a veteran pilot with thousands of hours in hazardous navigation"
        assert action.is_prepared is False
        assert action.prepared_justification is None
        assert action.is_helping is False

    def test_valid_action_with_only_helping(self):
        """Test Action with only is_helping flag and required fields"""
        action = Action(
            character_id="char_trell_005",
            narrative_text="I provide covering fire while the engineer works on the door.",
            task_type="lasers",
            is_helping=True,
            helping_character_id="char_engineer_006",
            help_justification="I'm suppressing enemy fire to give the engineer time to bypass the lock"
        )

        assert action.is_helping is True
        assert action.helping_character_id == "char_engineer_006"
        assert action.help_justification == "I'm suppressing enemy fire to give the engineer time to bypass the lock"
        assert action.is_prepared is False
        assert action.is_expert is False

    def test_valid_action_with_default_values(self):
        """Test simple Action without any dice suggestions uses defaults"""
        action = Action(
            character_id="char_nova_007",
            narrative_text="I scan the area for signs of life."
        )

        assert action.character_id == "char_nova_007"
        assert action.narrative_text == "I scan the area for signs of life."
        assert action.task_type is None
        assert action.is_prepared is False
        assert action.prepared_justification is None
        assert action.is_expert is False
        assert action.expert_justification is None
        assert action.is_helping is False
        assert action.helping_character_id is None
        assert action.help_justification is None

    def test_valid_action_with_lasers_task_type(self):
        """Test Action with task_type='lasers'"""
        action = Action(
            character_id="char_tech_008",
            narrative_text="I attempt to hack into the security system.",
            task_type="lasers"
        )

        assert action.task_type == "lasers"

    def test_valid_action_with_feelings_task_type(self):
        """Test Action with task_type='feelings'"""
        action = Action(
            character_id="char_diplomat_009",
            narrative_text="I try to convince the guard to let us pass peacefully.",
            task_type="feelings"
        )

        assert action.task_type == "feelings"


class TestPreparedJustificationValidation:
    """Test suite for is_prepared and prepared_justification validation"""

    def test_prepared_true_requires_justification(self):
        """Test ValidationError when is_prepared=True but prepared_justification is None"""
        with pytest.raises(ValidationError, match="prepared_justification is required when is_prepared=True"):
            Action(
                character_id="char_test_001",
                narrative_text="I attempt to repair the damaged systems.",
                is_prepared=True,
                prepared_justification=None  # Missing required justification
            )

    def test_prepared_true_with_missing_justification_field(self):
        """Test ValidationError when is_prepared=True but prepared_justification not provided"""
        with pytest.raises(ValidationError, match="prepared_justification is required when is_prepared=True"):
            Action(
                character_id="char_test_002",
                narrative_text="I analyze the alien artifact.",
                is_prepared=True
                # prepared_justification field not provided
            )

    def test_prepared_true_with_empty_string_justification(self):
        """Test that empty string justification is rejected"""
        with pytest.raises(ValidationError, match="prepared_justification is required when is_prepared=True"):
            Action(
                character_id="char_test_003",
                narrative_text="I attempt the complex repair.",
                is_prepared=True,
                prepared_justification=""  # Empty string should be rejected
            )

    def test_prepared_true_with_whitespace_only_justification(self):
        """Test that whitespace-only justification is accepted (current behavior)"""
        # Note: Current validator only checks for None/empty, not whitespace-only
        action = Action(
            character_id="char_test_004",
            narrative_text="I try to decode the message.",
            is_prepared=True,
            prepared_justification="   "  # Whitespace-only passes current validator
        )

        assert action.is_prepared is True
        assert action.prepared_justification == "   "

    def test_prepared_false_with_no_justification_is_valid(self):
        """Test is_prepared=False with no justification is valid"""
        action = Action(
            character_id="char_test_005",
            narrative_text="I improvise a solution.",
            is_prepared=False,
            prepared_justification=None
        )

        assert action.is_prepared is False
        assert action.prepared_justification is None

    def test_prepared_false_with_justification_is_valid(self):
        """Test is_prepared=False can still have justification (though unusual)"""
        action = Action(
            character_id="char_test_006",
            narrative_text="I wing it.",
            is_prepared=False,
            prepared_justification="This shouldn't matter but is allowed"
        )

        assert action.is_prepared is False
        assert action.prepared_justification == "This shouldn't matter but is allowed"


class TestExpertJustificationValidation:
    """Test suite for is_expert and expert_justification validation"""

    def test_expert_true_requires_justification(self):
        """Test ValidationError when is_expert=True but expert_justification is None"""
        with pytest.raises(ValidationError, match="expert_justification is required when is_expert=True"):
            Action(
                character_id="char_test_007",
                narrative_text="I perform expert-level medical treatment.",
                is_expert=True,
                expert_justification=None  # Missing required justification
            )

    def test_expert_true_with_missing_justification_field(self):
        """Test ValidationError when is_expert=True but expert_justification not provided"""
        with pytest.raises(ValidationError, match="expert_justification is required when is_expert=True"):
            Action(
                character_id="char_test_008",
                narrative_text="I demonstrate masterful swordsmanship.",
                is_expert=True
                # expert_justification field not provided
            )

    def test_expert_true_with_empty_string_justification(self):
        """Test that empty string justification is rejected"""
        with pytest.raises(ValidationError, match="expert_justification is required when is_expert=True"):
            Action(
                character_id="char_test_009",
                narrative_text="I use my expert knowledge.",
                is_expert=True,
                expert_justification=""  # Empty string should be rejected
            )

    def test_expert_true_with_whitespace_only_justification(self):
        """Test that whitespace-only justification is accepted (current behavior)"""
        # Note: Current validator only checks for None/empty, not whitespace-only
        action = Action(
            character_id="char_test_010",
            narrative_text="I apply expert techniques.",
            is_expert=True,
            expert_justification="\t\n  "  # Whitespace-only passes current validator
        )

        assert action.is_expert is True
        assert action.expert_justification == "\t\n  "

    def test_expert_false_with_no_justification_is_valid(self):
        """Test is_expert=False with no justification is valid"""
        action = Action(
            character_id="char_test_011",
            narrative_text="I attempt basic first aid.",
            is_expert=False,
            expert_justification=None
        )

        assert action.is_expert is False
        assert action.expert_justification is None

    def test_expert_false_with_justification_is_valid(self):
        """Test is_expert=False can still have justification (though unusual)"""
        action = Action(
            character_id="char_test_012",
            narrative_text="I try my best.",
            is_expert=False,
            expert_justification="Not an expert but here's context"
        )

        assert action.is_expert is False
        assert action.expert_justification == "Not an expert but here's context"


class TestHelpingValidation:
    """Test suite for is_helping, helping_character_id, and help_justification validation"""

    def test_helping_true_requires_character_id(self):
        """Test ValidationError when is_helping=True but helping_character_id is missing"""
        with pytest.raises(ValidationError, match="helping_character_id is required when is_helping=True"):
            Action(
                character_id="char_test_013",
                narrative_text="I assist my teammate.",
                is_helping=True,
                helping_character_id=None,  # Missing required field
                help_justification="I'm providing tactical support"
            )

    def test_helping_true_requires_justification(self):
        """Test ValidationError when is_helping=True but help_justification is missing"""
        with pytest.raises(ValidationError, match="help_justification is required when is_helping=True"):
            Action(
                character_id="char_test_014",
                narrative_text="I help my ally.",
                is_helping=True,
                helping_character_id="char_ally_015",
                help_justification=None  # Missing required field
            )

    def test_helping_true_with_missing_character_id_field(self):
        """Test ValidationError when is_helping=True but helping_character_id not provided"""
        with pytest.raises(ValidationError, match="helping_character_id is required when is_helping=True"):
            Action(
                character_id="char_test_016",
                narrative_text="I provide assistance.",
                is_helping=True,
                help_justification="I'm covering their flank"
                # helping_character_id not provided
            )

    def test_helping_true_with_missing_justification_field(self):
        """Test ValidationError when is_helping=True but help_justification not provided"""
        with pytest.raises(ValidationError, match="help_justification is required when is_helping=True"):
            Action(
                character_id="char_test_017",
                narrative_text="I coordinate with my teammate.",
                is_helping=True,
                helping_character_id="char_teammate_018"
                # help_justification not provided
            )

    def test_helping_true_with_empty_string_justification(self):
        """Test that empty string help_justification is rejected"""
        with pytest.raises(ValidationError, match="help_justification is required when is_helping=True"):
            Action(
                character_id="char_test_019",
                narrative_text="I help out.",
                is_helping=True,
                helping_character_id="char_friend_020",
                help_justification=""  # Empty string should be rejected
            )

    def test_helping_true_with_whitespace_only_justification(self):
        """Test that whitespace-only help_justification is accepted (current behavior)"""
        # Note: Current validator only checks for None/empty, not whitespace-only
        action = Action(
            character_id="char_test_021",
            narrative_text="I lend a hand.",
            is_helping=True,
            helping_character_id="char_companion_022",
            help_justification="  \n\t  "  # Whitespace-only passes current validator
        )

        assert action.is_helping is True
        assert action.help_justification == "  \n\t  "

    def test_helping_true_requires_both_fields(self):
        """Test ValidationError when is_helping=True but both character_id and justification missing"""
        with pytest.raises(ValidationError, match="(helping_character_id|help_justification) is required when is_helping=True"):
            Action(
                character_id="char_test_023",
                narrative_text="I work together with someone.",
                is_helping=True
                # Both helping_character_id and help_justification missing
            )

    def test_helping_false_with_no_fields_is_valid(self):
        """Test is_helping=False with no helping fields is valid"""
        action = Action(
            character_id="char_test_024",
            narrative_text="I work alone.",
            is_helping=False,
            helping_character_id=None,
            help_justification=None
        )

        assert action.is_helping is False
        assert action.helping_character_id is None
        assert action.help_justification is None

    def test_helping_false_with_fields_is_valid(self):
        """Test is_helping=False can still have helping fields (though unusual)"""
        action = Action(
            character_id="char_test_025",
            narrative_text="I act independently.",
            is_helping=False,
            helping_character_id="char_someone_026",
            help_justification="Not actually helping but fields present"
        )

        assert action.is_helping is False
        assert action.helping_character_id == "char_someone_026"
        assert action.help_justification == "Not actually helping but fields present"

    def test_helping_cannot_help_self(self):
        """Test ValidationError when character tries to help themselves"""
        with pytest.raises(ValidationError, match="Characters cannot help themselves"):
            Action(
                character_id="char_zara_001",
                narrative_text="I help myself fix the console.",
                is_helping=True,
                helping_character_id="char_zara_001",  # Same as character_id - not allowed!
                help_justification="I'm providing myself with technical support"
            )


class TestHelpingCharacterIdPattern:
    """Test suite for helping_character_id pattern validation"""

    def test_valid_character_id_patterns(self):
        """Test that valid character_id patterns are accepted"""
        valid_ids = [
            "char_zara_001",
            "char_kai_nova_002",
            "char_test_123",
            "char_a_1",
            "char_long_character_name_with_underscores_999"
        ]

        for char_id in valid_ids:
            action = Action(
                character_id="char_helper_999",
                narrative_text="I assist my ally.",
                is_helping=True,
                helping_character_id=char_id,
                help_justification="Providing support"
            )
            assert action.helping_character_id == char_id

    def test_invalid_character_id_no_prefix(self):
        """Test ValidationError for character_id without 'char_' prefix"""
        with pytest.raises(ValidationError, match="String should match pattern"):
            Action(
                character_id="char_test_027",
                narrative_text="I help someone.",
                is_helping=True,
                helping_character_id="invalid_001",  # Missing 'char_' prefix
                help_justification="Support"
            )

    def test_invalid_character_id_uppercase(self):
        """Test ValidationError for character_id with uppercase letters"""
        with pytest.raises(ValidationError, match="String should match pattern"):
            Action(
                character_id="char_test_028",
                narrative_text="I assist.",
                is_helping=True,
                helping_character_id="char_Zara_001",  # Uppercase 'Z' not allowed
                help_justification="Helping out"
            )

    def test_invalid_character_id_special_chars(self):
        """Test ValidationError for character_id with special characters"""
        with pytest.raises(ValidationError, match="String should match pattern"):
            Action(
                character_id="char_test_029",
                narrative_text="I collaborate.",
                is_helping=True,
                helping_character_id="char_test-001",  # Hyphen not allowed
                help_justification="Team work"
            )

    def test_invalid_character_id_spaces(self):
        """Test ValidationError for character_id with spaces"""
        with pytest.raises(ValidationError, match="String should match pattern"):
            Action(
                character_id="char_test_030",
                narrative_text="I support my team.",
                is_helping=True,
                helping_character_id="char test 001",  # Spaces not allowed
                help_justification="Tactical support"
            )

    def test_invalid_character_id_empty_string(self):
        """Test ValidationError for empty string character_id"""
        with pytest.raises(ValidationError, match="String should match pattern"):
            Action(
                character_id="char_test_031",
                narrative_text="I help.",
                is_helping=True,
                helping_character_id="",  # Empty string
                help_justification="Assistance"
            )

    def test_invalid_character_id_only_prefix(self):
        """Test ValidationError for character_id with only 'char_' prefix"""
        with pytest.raises(ValidationError, match="String should match pattern"):
            Action(
                character_id="char_test_032",
                narrative_text="I coordinate.",
                is_helping=True,
                helping_character_id="char_",  # Only prefix, no identifier
                help_justification="Coordination"
            )


class TestCombinedDiceSuggestions:
    """Test suite for combinations of dice suggestion flags"""

    def test_prepared_and_expert_both_true(self):
        """Test Action with both is_prepared and is_expert flags"""
        action = Action(
            character_id="char_master_033",
            narrative_text="I perform a complex technical procedure.",
            is_prepared=True,
            prepared_justification="I spent hours studying the schematics",
            is_expert=True,
            expert_justification="I'm a certified specialist in this field"
        )

        assert action.is_prepared is True
        assert action.is_expert is True
        assert action.is_helping is False

    def test_prepared_and_helping_both_true(self):
        """Test Action with both is_prepared and is_helping flags"""
        action = Action(
            character_id="char_supporter_034",
            narrative_text="I assist my teammate with the technical challenge.",
            is_prepared=True,
            prepared_justification="I brought the right tools for this",
            is_helping=True,
            helping_character_id="char_teammate_035",
            help_justification="I'm handing them the specialized equipment they need"
        )

        assert action.is_prepared is True
        assert action.is_helping is True
        assert action.is_expert is False

    def test_expert_and_helping_both_true(self):
        """Test Action with both is_expert and is_helping flags"""
        action = Action(
            character_id="char_veteran_036",
            narrative_text="I guide the rookie through the dangerous situation.",
            is_expert=True,
            expert_justification="I've been through this scenario dozens of times",
            is_helping=True,
            helping_character_id="char_rookie_037",
            help_justification="I'm calling out threats and providing tactical guidance"
        )

        assert action.is_expert is True
        assert action.is_helping is True
        assert action.is_prepared is False

    def test_all_three_flags_true(self):
        """Test Action with prepared, expert, and helping all true"""
        action = Action(
            character_id="char_ultimate_038",
            narrative_text="I lead the team through the crisis with expertise and preparation.",
            task_type="lasers",
            is_prepared=True,
            prepared_justification="I anticipated this scenario and brought backup supplies",
            is_expert=True,
            expert_justification="I'm the most experienced crisis manager on the crew",
            is_helping=True,
            helping_character_id="char_team_039",
            help_justification="I'm directing everyone to optimal positions and sharing my equipment"
        )

        assert action.is_prepared is True
        assert action.is_expert is True
        assert action.is_helping is True
        assert action.task_type == "lasers"


class TestTaskTypeValidation:
    """Test suite for task_type field validation"""

    def test_task_type_none_is_valid(self):
        """Test that task_type=None is valid (no dice roll needed)"""
        action = Action(
            character_id="char_test_040",
            narrative_text="I casually examine the room."
        )

        assert action.task_type is None

    def test_task_type_lasers_valid(self):
        """Test task_type='lasers' is valid"""
        action = Action(
            character_id="char_test_041",
            narrative_text="I hack the terminal.",
            task_type="lasers"
        )

        assert action.task_type == "lasers"

    def test_task_type_feelings_valid(self):
        """Test task_type='feelings' is valid"""
        action = Action(
            character_id="char_test_042",
            narrative_text="I persuade the guard.",
            task_type="feelings"
        )

        assert action.task_type == "feelings"

    def test_task_type_invalid_value_rejected(self):
        """Test that invalid task_type values are rejected"""
        with pytest.raises(ValidationError, match="Input should be 'lasers' or 'feelings'"):
            Action(
                character_id="char_test_043",
                narrative_text="I do something.",
                task_type="combat"  # Invalid value
            )

    def test_task_type_case_sensitive(self):
        """Test that task_type is case-sensitive (must be lowercase)"""
        with pytest.raises(ValidationError, match="Input should be 'lasers' or 'feelings'"):
            Action(
                character_id="char_test_044",
                narrative_text="I attempt technical work.",
                task_type="LASERS"  # Uppercase not allowed
            )

        with pytest.raises(ValidationError, match="Input should be 'lasers' or 'feelings'"):
            Action(
                character_id="char_test_045",
                narrative_text="I try diplomacy.",
                task_type="Feelings"  # Mixed case not allowed
            )


class TestGMQuestionField:
    """Test suite for gm_question field (LASER FEELINGS mechanic)"""

    def test_action_with_gm_question(self):
        """Test creating Action with gm_question field"""
        action = Action(
            character_id="char_zara_001",
            narrative_text="I attempt to hack the terminal...",
            task_type="lasers",
            gm_question="What security system is protecting this data?"
        )

        assert action.gm_question == "What security system is protecting this data?"

    def test_action_without_gm_question_defaults_to_none(self):
        """Test that gm_question defaults to None when not provided"""
        action = Action(
            character_id="char_kai_002",
            narrative_text="I scan the area for threats.",
            task_type="lasers"
        )

        assert action.gm_question is None

    def test_action_with_explicit_none_gm_question(self):
        """Test that gm_question can be explicitly set to None"""
        action = Action(
            character_id="char_lyra_003",
            narrative_text="I approach the negotiations.",
            task_type="feelings",
            gm_question=None
        )

        assert action.gm_question is None

    def test_gm_question_included_in_serialization(self):
        """Test that gm_question is included in model serialization"""
        action = Action(
            character_id="char_alex_004",
            narrative_text="I pilot through the asteroid field.",
            task_type="lasers",
            gm_question="What are they really feeling?"
        )

        serialized = action.model_dump()
        assert "gm_question" in serialized
        assert serialized["gm_question"] == "What are they really feeling?"

    def test_gm_question_none_in_serialization(self):
        """Test that gm_question=None is included in serialization"""
        action = Action(
            character_id="char_trell_005",
            narrative_text="I fire at the target.",
            task_type="lasers"
        )

        serialized = action.model_dump()
        assert "gm_question" in serialized
        assert serialized["gm_question"] is None

    def test_gm_question_with_various_question_types(self):
        """Test gm_question accepts various question formats"""
        question_examples = [
            "What are they really feeling?",
            "Who's behind this?",
            "What's the best way to accomplish this mission?",
            "Where is the hidden entrance?",
            "How can I defuse this situation?",
            "What's the truth about their motives?",
            "What do I know about this technology?"
        ]

        for question in question_examples:
            action = Action(
                character_id="char_test_100",
                narrative_text="I attempt the action.",
                task_type="lasers",
                gm_question=question
            )
            assert action.gm_question == question

    def test_gm_question_with_long_text(self):
        """Test that long gm_question strings are accepted"""
        long_question = "What is the complete historical context of this ancient artifact, including its creators, purpose, and the circumstances that led to its abandonment in this location?"

        action = Action(
            character_id="char_test_101",
            narrative_text="I examine the artifact carefully.",
            task_type="lasers",
            gm_question=long_question
        )

        assert action.gm_question == long_question
        assert len(action.gm_question) > 100

    def test_gm_question_with_unicode_characters(self):
        """Test that gm_question handles unicode characters"""
        action = Action(
            character_id="char_test_102",
            narrative_text="I investigate the alien text.",
            task_type="feelings",
            gm_question="What does this symbol mean: αΩ 中文 🔍?"
        )

        assert "αΩ" in action.gm_question
        assert "中文" in action.gm_question
        assert "🔍" in action.gm_question

    def test_gm_question_combined_with_all_dice_suggestions(self):
        """Test gm_question works alongside all dice suggestion fields"""
        action = Action(
            character_id="char_test_103",
            narrative_text="I perform the complex technical procedure with team support.",
            task_type="lasers",
            is_prepared=True,
            prepared_justification="I studied the schematics beforehand",
            is_expert=True,
            expert_justification="I'm a certified specialist",
            is_helping=True,
            helping_character_id="char_test_104",
            help_justification="I'm guiding them through the process",
            gm_question="What's the safest approach to disable this system?"
        )

        assert action.gm_question == "What's the safest approach to disable this system?"
        assert action.is_prepared is True
        assert action.is_expert is True
        assert action.is_helping is True


class TestEdgeCases:
    """Test suite for edge cases and boundary conditions"""

    def test_very_long_justification_strings(self):
        """Test that very long justification strings are accepted"""
        long_justification = "A" * 1000  # 1000 character justification

        action = Action(
            character_id="char_test_046",
            narrative_text="I do something complex.",
            is_prepared=True,
            prepared_justification=long_justification,
            is_expert=True,
            expert_justification=long_justification,
            is_helping=True,
            helping_character_id="char_test_047",
            help_justification=long_justification
        )

        assert len(action.prepared_justification) == 1000
        assert len(action.expert_justification) == 1000
        assert len(action.help_justification) == 1000

    def test_unicode_in_justification_strings(self):
        """Test that unicode characters in justifications are handled correctly"""
        action = Action(
            character_id="char_test_048",
            narrative_text="I navigate the alien ship.",
            is_prepared=True,
            prepared_justification="I studied xenoarchitecture: αβγδε 中文 🚀",
            is_expert=True,
            expert_justification="Expert in alien cultures: café, naïve, résumé",
            is_helping=True,
            helping_character_id="char_test_049",
            help_justification="Guiding through dangerous terrain ⚠️"
        )

        assert "🚀" in action.prepared_justification
        assert "café" in action.expert_justification
        assert "⚠️" in action.help_justification

    def test_narrative_text_can_be_empty_string(self):
        """Test that narrative_text can be empty (though unusual)"""
        # Note: This tests current behavior - in practice, empty narrative_text
        # might not be desirable, but we test what the model currently allows
        action = Action(
            character_id="char_test_050",
            narrative_text=""
        )

        assert action.narrative_text == ""

    def test_multiple_validations_fail_together(self):
        """Test that multiple validation failures are reported"""
        with pytest.raises(ValidationError) as exc_info:
            Action(
                character_id="char_test_051",
                narrative_text="I do everything wrong.",
                is_prepared=True,
                # Missing prepared_justification
                is_expert=True,
                # Missing expert_justification
                is_helping=True,
                # Missing helping_character_id and help_justification
            )

        # Should report multiple validation errors
        error_str = str(exc_info.value)
        assert "prepared_justification" in error_str
        # Note: Pydantic validators run in sequence, so we might only see first error
