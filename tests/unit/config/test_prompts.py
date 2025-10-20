# ABOUTME: Unit tests for prompt template generation functions.
# ABOUTME: Tests game mechanics section generation with different character numbers.

import pytest

from src.config.prompts import build_game_mechanics_section


class TestBuildGameMechanicsSection:
    """Test game mechanics section generation for different character numbers"""

    def test_number_2_lasers_specialist(self):
        """Number 2 should emphasize LASERS strengths"""
        result = build_game_mechanics_section(2)

        # Should indicate LASERS strength
        assert "LASERS (technical/logical actions)" in result
        assert "excel at technology, science, and rational analysis" in result

        # Should indicate FEELINGS weakness
        assert "struggle with intuition, diplomacy, and emotional approaches" in result

        # Should show correct probabilities (16.7% LASERS, 66.7% FEELINGS)
        assert "17%" in result or "16%" in result  # LASERS success rate
        assert "67%" in result or "66%" in result  # FEELINGS success rate

        # Should show character number
        assert "Your character's number: 2" in result

    def test_number_5_feelings_specialist(self):
        """Number 5 should emphasize FEELINGS strengths"""
        result = build_game_mechanics_section(5)

        # Should indicate FEELINGS strength
        assert "FEELINGS (social/emotional actions)" in result
        assert "excel at intuition, diplomacy, and passionate actions" in result

        # Should indicate LASERS weakness
        assert "struggle with technology, science, and cold rationality" in result

        # Should show correct probabilities (66.7% LASERS, 16.7% FEELINGS)
        assert "67%" in result or "66%" in result  # LASERS success rate
        assert "17%" in result or "16%" in result  # FEELINGS success rate

        # Should show character number
        assert "Your character's number: 5" in result

    def test_number_3_balanced_lasers_advantage(self):
        """Number 3 should be balanced with slight LASERS advantage"""
        result = build_game_mechanics_section(3)

        # Should indicate balanced with LASERS lean
        assert "balanced (slight LASERS advantage)" in result
        assert "competent at both approaches, slightly better with logic" in result

        # Should NOT indicate specific weakness
        assert "struggle" not in result

        # Should show probabilities (33% LASERS, 50% FEELINGS)
        assert "33%" in result  # LASERS success rate
        assert "50%" in result  # FEELINGS success rate

        # Should show character number
        assert "Your character's number: 3" in result

    def test_number_4_balanced_feelings_advantage(self):
        """Number 4 should be balanced with slight FEELINGS advantage"""
        result = build_game_mechanics_section(4)

        # Should indicate balanced with FEELINGS lean
        assert "balanced (slight FEELINGS advantage)" in result
        assert "competent at both approaches, slightly better with emotion" in result

        # Should NOT indicate specific weakness
        assert "struggle" not in result

        # Should show probabilities (50% LASERS, 33% FEELINGS)
        assert "50%" in result  # LASERS success rate
        assert "33%" in result  # FEELINGS success rate

        # Should show character number
        assert "Your character's number: 4" in result

    def test_invalid_number_too_low(self):
        """Should raise ValueError for number below 2"""
        with pytest.raises(ValueError, match="Character number must be 2-5, got 1"):
            build_game_mechanics_section(1)

    def test_invalid_number_too_high(self):
        """Should raise ValueError for number above 5"""
        with pytest.raises(ValueError, match="Character number must be 2-5, got 6"):
            build_game_mechanics_section(6)

    def test_invalid_number_zero(self):
        """Should raise ValueError for zero"""
        with pytest.raises(ValueError, match="Character number must be 2-5, got 0"):
            build_game_mechanics_section(0)

    def test_invalid_number_negative(self):
        """Should raise ValueError for negative numbers"""
        with pytest.raises(ValueError, match="Character number must be 2-5, got -1"):
            build_game_mechanics_section(-1)

    def test_includes_all_required_sections(self):
        """All numbers should include standard mechanics sections"""
        for number in range(2, 6):
            result = build_game_mechanics_section(number)

            # Should include all major sections
            assert "## LASERS & FEELINGS GAME MECHANICS" in result
            assert "### How Actions Work:" in result
            assert "### Success Levels" in result
            assert "### Tactical Advantages" in result
            assert "### Strategic Implications" in result
            assert "### Examples of Each Approach:" in result

    def test_includes_dice_mechanics(self):
        """Should explain dice rolling mechanics"""
        result = build_game_mechanics_section(3)

        # Should explain dice mechanics
        assert "1d6" in result
        assert "+1d" in result
        assert "Roll UNDER your number" in result
        assert "Roll OVER your number" in result

    def test_includes_success_levels(self):
        """Should explain all success levels"""
        result = build_game_mechanics_section(3)

        assert "0 dice succeed" in result
        assert "1 die succeeds" in result
        assert "2 dice succeed" in result
        assert "3+ dice succeed" in result

    def test_includes_laser_feelings_special(self):
        """Should explain LASER FEELINGS special insight for exact roll"""
        result = build_game_mechanics_section(3)

        assert "Roll exactly 3" in result or "exactly 3" in result
        assert "LASER FEELINGS" in result
        assert "special insight" in result
        assert "ask the DM a" in result

    def test_includes_tactical_advantages(self):
        """Should list all tactical advantage types"""
        result = build_game_mechanics_section(3)

        assert "Prepared" in result
        assert "Expert" in result
        assert "Helped" in result

    def test_includes_strategic_guidance(self):
        """Should provide strategic decision-making guidance"""
        result = build_game_mechanics_section(3)

        assert "Strategic Implications" in result
        assert "Play to your strengths" in result
        assert "Coordinate with allies" in result

    def test_includes_action_examples(self):
        """Should provide examples of LASERS and FEELINGS actions"""
        result = build_game_mechanics_section(3)

        # LASERS examples
        assert "Hacking" in result or "analyzing" in result

        # FEELINGS examples
        assert "Reading emotions" in result or "seducing" in result

    def test_probability_calculations_are_correct(self):
        """Verify probability calculations are mathematically correct"""
        # Number 2: LASERS=(2-1)/6=1/6≈16.7%, FEELINGS=(6-2)/6=4/6≈66.7%
        result_2 = build_game_mechanics_section(2)
        assert "17%" in result_2 or "16%" in result_2  # LASERS
        assert "67%" in result_2 or "66%" in result_2  # FEELINGS

        # Number 3: LASERS=(3-1)/6=2/6≈33.3%, FEELINGS=(6-3)/6=3/6=50%
        result_3 = build_game_mechanics_section(3)
        assert "33%" in result_3  # LASERS
        assert "50%" in result_3  # FEELINGS

        # Number 4: LASERS=(4-1)/6=3/6=50%, FEELINGS=(6-4)/6=2/6≈33.3%
        result_4 = build_game_mechanics_section(4)
        assert "50%" in result_4  # LASERS
        assert "33%" in result_4  # FEELINGS

        # Number 5: LASERS=(5-1)/6=4/6≈66.7%, FEELINGS=(6-5)/6=1/6≈16.7%
        result_5 = build_game_mechanics_section(5)
        assert "67%" in result_5 or "66%" in result_5  # LASERS
        assert "17%" in result_5 or "16%" in result_5  # FEELINGS
