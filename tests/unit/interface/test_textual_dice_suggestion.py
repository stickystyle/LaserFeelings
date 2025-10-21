# ABOUTME: Unit tests for Textual UI enhanced dice roll suggestion display.
# ABOUTME: Validates comprehensive roll suggestion formatting matching CLI format.

from src.interface.dm_textual import DMTextualInterface


class TestTextualDiceSuggestion:
    """Test enhanced dice roll suggestion display in Textual UI"""

    def test_build_dice_suggestion_lasers_task(self):
        """Test formatting of Lasers task type with explanation"""
        interface = DMTextualInterface(orchestrator=None, router=None)

        action_dict = {
            "task_type": "lasers",
            "is_prepared": False,
            "is_expert": False,
            "is_helping": False,
        }

        result = interface._build_dice_suggestion_text(action_dict, lambda x: x)

        assert "Task Type: Lasers (logic/tech)" in result

    def test_build_dice_suggestion_feelings_task(self):
        """Test formatting of Feelings task type with explanation"""
        interface = DMTextualInterface(orchestrator=None, router=None)

        action_dict = {
            "task_type": "feelings",
            "is_prepared": False,
            "is_expert": False,
            "is_helping": False,
        }

        result = interface._build_dice_suggestion_text(action_dict, lambda x: x)

        assert "Task Type: Feelings (social/emotion)" in result

    def test_build_dice_suggestion_prepared_with_justification(self):
        """Test that prepared flag with justification is displayed"""
        interface = DMTextualInterface(orchestrator=None, router=None)

        action_dict = {
            "task_type": "lasers",
            "is_prepared": True,
            "prepared_justification": "Found some tools lying around",
            "is_expert": False,
            "is_helping": False,
        }

        result = interface._build_dice_suggestion_text(action_dict, lambda x: x)

        assert "Prepared: ✓" in result
        assert "Found some tools lying around" in result

    def test_build_dice_suggestion_expert_with_justification(self):
        """Test that expert flag with justification is displayed"""
        interface = DMTextualInterface(orchestrator=None, router=None)

        action_dict = {
            "task_type": "lasers",
            "is_prepared": False,
            "is_expert": True,
            "expert_justification": "Studied mechanical systems",
            "is_helping": False,
        }

        result = interface._build_dice_suggestion_text(action_dict, lambda x: x)

        assert "Expert: ✓" in result
        assert "Studied mechanical systems" in result

    def test_build_dice_suggestion_helping_with_character_name_and_justification(self):
        """Test that helping flag with character name and justification is displayed"""
        interface = DMTextualInterface(orchestrator=None, router=None)

        action_dict = {
            "task_type": "lasers",
            "is_prepared": False,
            "is_expert": False,
            "is_helping": True,
            "helping_character_id": "char_zara_001",
            "help_justification": "Can pick the lock while you hold the door",
        }

        # Mock resolver that returns character names
        def mock_resolver(char_id):
            return "Zara-7" if char_id == "char_zara_001" else char_id

        result = interface._build_dice_suggestion_text(action_dict, mock_resolver)

        assert "Helping Zara-7: ✓" in result
        assert "Can pick the lock while you hold the door" in result

    def test_build_dice_suggestion_dice_count_1d6(self):
        """Test dice count calculation for 1d6 (no modifiers)"""
        interface = DMTextualInterface(orchestrator=None, router=None)

        action_dict = {
            "task_type": "lasers",
            "is_prepared": False,
            "is_expert": False,
            "is_helping": False,
        }

        result = interface._build_dice_suggestion_text(action_dict, lambda x: x)

        assert "Suggested Roll: 1d6 Lasers" in result

    def test_build_dice_suggestion_dice_count_2d6(self):
        """Test dice count calculation for 2d6 (one modifier)"""
        interface = DMTextualInterface(orchestrator=None, router=None)

        action_dict = {
            "task_type": "lasers",
            "is_prepared": True,
            "prepared_justification": "Got the right tools",
            "is_expert": False,
            "is_helping": False,
        }

        result = interface._build_dice_suggestion_text(action_dict, lambda x: x)

        assert "Suggested Roll: 2d6 Lasers" in result

    def test_build_dice_suggestion_dice_count_3d6_max(self):
        """Test dice count calculation for 3d6 (max dice with three modifiers)"""
        interface = DMTextualInterface(orchestrator=None, router=None)

        action_dict = {
            "task_type": "lasers",
            "is_prepared": True,
            "prepared_justification": "Got the right tools",
            "is_expert": True,
            "expert_justification": "Expert engineer",
            "is_helping": True,
            "helping_character_id": "char_other_001",
            "help_justification": "Assisting with repairs",
        }

        result = interface._build_dice_suggestion_text(action_dict, lambda x: "Other")

        assert "Suggested Roll: 3d6 Lasers" in result

    def test_build_dice_suggestion_max_dice_is_3d6(self):
        """Test that max dice count is capped at 3d6 even with more modifiers"""
        interface = DMTextualInterface(orchestrator=None, router=None)

        # Even with 3 bonuses, should cap at 3d6
        action_dict = {
            "task_type": "lasers",
            "is_prepared": True,
            "prepared_justification": "Got the right tools",
            "is_expert": True,
            "expert_justification": "Expert engineer",
            "is_helping": True,
            "helping_character_id": "char_other_001",
            "help_justification": "Assisting with repairs",
        }

        result = interface._build_dice_suggestion_text(action_dict, lambda x: "Other")

        # Should be 3d6, not 4d6
        assert "3d6" in result
        assert "4d6" not in result

    def test_build_dice_suggestion_missing_character_name_fallback(self):
        """Test missing character name resolution (fallback to ID)"""
        interface = DMTextualInterface(orchestrator=None, router=None)

        action_dict = {
            "task_type": "lasers",
            "is_prepared": False,
            "is_expert": False,
            "is_helping": True,
            "helping_character_id": "char_unknown_999",
            "help_justification": "Helping out",
        }

        # Resolver returns the ID unchanged for unknown characters
        result = interface._build_dice_suggestion_text(action_dict, lambda x: x)

        assert "Helping char_unknown_999: ✓" in result

    def test_build_dice_suggestion_success_marker_for_active_flags(self):
        """Test that success marker (✓) appears for active flags"""
        interface = DMTextualInterface(orchestrator=None, router=None)

        action_dict = {
            "task_type": "lasers",
            "is_prepared": True,
            "prepared_justification": "Ready",
            "is_expert": True,
            "expert_justification": "Skilled",
            "is_helping": False,
        }

        result = interface._build_dice_suggestion_text(action_dict, lambda x: x)

        # Check for success markers
        assert result.count("✓") == 2  # One for prepared, one for expert

    def test_build_dice_suggestion_some_flags_inactive(self):
        """Test formatting when some flags are inactive (not displayed)"""
        interface = DMTextualInterface(orchestrator=None, router=None)

        action_dict = {
            "task_type": "lasers",
            "is_prepared": True,
            "prepared_justification": "Got tools",
            "is_expert": False,
            "is_helping": False,
        }

        result = interface._build_dice_suggestion_text(action_dict, lambda x: x)

        # Should have prepared but not expert/helping
        assert "Prepared: ✓" in result
        assert "Expert:" not in result
        assert "Helping" not in result

    def test_build_dice_suggestion_all_flags_active(self):
        """Test formatting when all flags are active"""
        interface = DMTextualInterface(orchestrator=None, router=None)

        action_dict = {
            "task_type": "lasers",
            "is_prepared": True,
            "prepared_justification": "Got tools",
            "is_expert": True,
            "expert_justification": "Skilled",
            "is_helping": True,
            "helping_character_id": "char_other_001",
            "help_justification": "Assisting",
        }

        result = interface._build_dice_suggestion_text(action_dict, lambda x: "Other")

        assert "Prepared: ✓" in result
        assert "Expert: ✓" in result
        assert "Helping Other: ✓" in result

    def test_build_dice_suggestion_no_flags_active(self):
        """Test formatting when no flags are active (base 1d6 roll)"""
        interface = DMTextualInterface(orchestrator=None, router=None)

        action_dict = {
            "task_type": "lasers",
            "is_prepared": False,
            "is_expert": False,
            "is_helping": False,
        }

        result = interface._build_dice_suggestion_text(action_dict, lambda x: x)

        # Should have task type and suggested roll but no modifier lines
        assert "Task Type: Lasers (logic/tech)" in result
        assert "Suggested Roll: 1d6 Lasers" in result
        assert "Prepared:" not in result
        assert "Expert:" not in result
        assert "Helping" not in result

    def test_build_dice_suggestion_header_format(self):
        """Test that header matches CLI format"""
        interface = DMTextualInterface(orchestrator=None, router=None)

        action_dict = {
            "task_type": "lasers",
            "is_prepared": False,
            "is_expert": False,
            "is_helping": False,
        }

        result = interface._build_dice_suggestion_text(action_dict, lambda x: x)

        # Should start with header
        assert result.startswith("Dice Roll Suggestion:")

    def test_build_dice_suggestion_line_prefix_format(self):
        """Test that each detail line has '- ' prefix"""
        interface = DMTextualInterface(orchestrator=None, router=None)

        action_dict = {
            "task_type": "lasers",
            "is_prepared": True,
            "prepared_justification": "Got tools",
            "is_expert": False,
            "is_helping": False,
        }

        result = interface._build_dice_suggestion_text(action_dict, lambda x: x)

        lines = result.split("\n")
        # Skip header line (index 0), check remaining lines
        for line in lines[1:]:
            assert line.strip().startswith("- "), f"Line missing '- ' prefix: {line}"

    def test_build_dice_suggestion_case_insensitive_task_type(self):
        """Test task type capitalization works for different cases"""
        interface = DMTextualInterface(orchestrator=None, router=None)

        # Test lowercase
        action_dict = {
            "task_type": "lasers",
            "is_prepared": False,
            "is_expert": False,
            "is_helping": False,
        }
        result = interface._build_dice_suggestion_text(action_dict, lambda x: x)
        assert "Task Type: Lasers (logic/tech)" in result

        # Test uppercase
        action_dict["task_type"] = "FEELINGS"
        result = interface._build_dice_suggestion_text(action_dict, lambda x: x)
        assert "Task Type: Feelings (social/emotion)" in result

        # Test mixed case
        action_dict["task_type"] = "LaSeRs"
        result = interface._build_dice_suggestion_text(action_dict, lambda x: x)
        assert "Task Type: Lasers (logic/tech)" in result
