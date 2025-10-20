#!/usr/bin/env python3
# ABOUTME: Demo script showing DM CLI parsing and formatting capabilities.
# ABOUTME: Demonstrates command parsing, output formatting, and error handling without orchestrator.

"""
Demo of DM CLI Interface

This script demonstrates the command parsing and output formatting
capabilities of the DM CLI without requiring a full orchestrator setup.
"""

from src.interface.dm_cli import (
    CLIFormatter,
    DMCommandLineInterface,
    DMCommandParser,
    InvalidCommandError,
)
from src.models.game_state import GamePhase


def demo_command_parsing():
    """Demonstrate command parsing"""
    print("\n" + "=" * 70)
    print("DEMO: Command Parsing")
    print("=" * 70)

    parser = DMCommandParser()

    test_inputs = [
        "The ship drifts through space",
        "/narrate A door opens ahead",
        "/roll 2d6+3",
        "/roll 1d20",
        "success",
        "fail",
        "/info",
        "/quit",
    ]

    for user_input in test_inputs:
        print(f"\nInput: {user_input}")
        try:
            parsed = parser.parse(user_input)
            print(f"  Type: {parsed.command_type}")
            print(f"  Args: {parsed.args}")
        except InvalidCommandError as e:
            print(f"  ERROR: {e}")


def demo_output_formatting():
    """Demonstrate output formatting"""
    print("\n" + "=" * 70)
    print("DEMO: Output Formatting")
    print("=" * 70)

    formatter = CLIFormatter()

    # Header
    print("\n1. Campaign Header:")
    print(formatter.format_header(
        campaign_name="Voyage of the Raptor",
        characters=["Zara-7 (Android Engineer)", "Rax Stellar (Hot-Shot Pilot)"]
    ))

    # Phase transition
    print("\n2. Phase Transition:")
    print(formatter.format_phase_transition(
        phase=GamePhase.STRATEGIC_INTENT,
        turn_number=3
    ))

    # Agent response
    print("\n3. Agent Strategic Response:")
    print(formatter.format_agent_response(
        agent_name="Alex",
        character_name="Zara-7",
        response="We should investigate the station cautiously while scanning for threats.",
        phase=GamePhase.STRATEGIC_INTENT
    ))

    # Character action
    print("\n4. Character Action:")
    print(formatter.format_character_action(
        character_name="Zara-7",
        action='*tilts head, analyzing sensor readouts* "Captain, I detect '
               'a 73% probability that the station\'s fuel reserves remain intact. '
               'I suggest we attempt to dock."'
    ))

    # Validation results
    print("\n5. Validation Pass:")
    print(formatter.format_validation_result(valid=True))

    print("\n6. Validation Fail:")
    print(formatter.format_validation_result(
        valid=False,
        violations=["Character narrated outcome", "Used forbidden pattern 'successfully'"]
    ))

    # Dice roll
    print("\n7. Dice Roll:")
    print(formatter.format_dice_roll(
        notation="2d6+3",
        individual_rolls=[4, 5],
        total=12,
        modifier=3
    ))

    # Session info
    print("\n8. Session Info:")
    print(formatter.format_session_info(
        campaign_name="Voyage of the Raptor",
        session_number=2,
        turn_number=15,
        current_phase=GamePhase.DM_ADJUDICATION,
        active_agents=[
            {"agent_id": "agent_001", "character_name": "Zara-7"},
            {"agent_id": "agent_002", "character_name": "Rax Stellar"}
        ]
    ))

    # Error message
    print("\n9. Error Message:")
    print(formatter.format_error(
        error_type="InvalidCommandError",
        message="Roll command requires dice notation",
        suggestion="Try: /roll 1d20 or /roll 2d6+3"
    ))


def demo_command_handlers():
    """Demonstrate command execution"""
    print("\n" + "=" * 70)
    print("DEMO: Command Execution")
    print("=" * 70)

    cli = DMCommandLineInterface()

    test_commands = [
        "The ship approaches the derelict station",
        "/roll 1d20+5",
        "success",
        "/info",
    ]

    for cmd_input in test_commands:
        print(f"\n> {cmd_input}")
        try:
            parsed = cli.parser.parse(cmd_input)
            result = cli.handle_command(parsed)

            if result["success"]:
                print(f"✓ Success: {result['command_type']}")
                if "output" in result:
                    print(result["output"])
            else:
                print(f"✗ Failed: {result.get('error', 'Unknown error')}")
        except InvalidCommandError as e:
            print(f"✗ Parse Error: {e}")


def demo_error_handling():
    """Demonstrate error handling"""
    print("\n" + "=" * 70)
    print("DEMO: Error Handling")
    print("=" * 70)

    cli = DMCommandLineInterface()
    formatter = CLIFormatter()

    # Test invalid commands
    test_cases = [
        ("", "Empty input"),
        ("/roll", "Missing dice notation"),
        ("/roll xyz", "Invalid dice notation"),
        ("/roll 2d6d8", "Malformed dice notation"),
    ]

    for cmd_input, description in test_cases:
        print(f"\nTest: {description}")
        print(f"Input: '{cmd_input}'")
        try:
            if cmd_input:
                parsed = cli.parser.parse(cmd_input)
                result = cli.handle_command(parsed)
                if not result["success"]:
                    print(formatter.format_error(
                        error_type="CommandError",
                        message=result.get("error", "Unknown error")
                    ))
        except InvalidCommandError as e:
            print(formatter.format_error(
                error_type="InvalidCommandError",
                message=str(e),
                suggestion="Check command format and try again"
            ))


def main():
    """Run all demos"""
    print("\n" + "=" * 70)
    print(" DM CLI INTERFACE DEMO")
    print("=" * 70)
    print("\nThis demo shows the command parsing, output formatting,")
    print("and error handling capabilities of the DM CLI interface.")

    demo_command_parsing()
    demo_output_formatting()
    demo_command_handlers()
    demo_error_handling()

    print("\n" + "=" * 70)
    print(" DEMO COMPLETE")
    print("=" * 70)
    print("\nTo run the interactive CLI:")
    print("  python -m src.interface.dm_cli")
    print()


if __name__ == "__main__":
    main()
