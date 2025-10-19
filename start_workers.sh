#!/bin/bash
# Start RQ workers for TTRPG AI system
# This script starts workers for both base_persona and character queues

echo "Starting RQ workers..."
echo "Logs will be written to logs/"

mkdir -p logs

# Set macOS fork safety (required for RQ on macOS)
export OBJC_DISABLE_INITIALIZE_FORK_SAFETY=YES

# Start base_persona worker
echo "Starting base_persona worker..."
uv run rq worker base_persona --url redis://localhost:6379 > logs/worker_base_persona.log 2>&1 &
BASE_PERSONA_PID=$!

# Start character worker
echo "Starting character worker..."
uv run rq worker character --url redis://localhost:6379 > logs/worker_character.log 2>&1 &
CHARACTER_PID=$!

echo "Workers started!"
echo "  base_persona worker PID: $BASE_PERSONA_PID"
echo "  character worker PID: $CHARACTER_PID"
echo ""
echo "To stop workers, run:"
echo "  kill $BASE_PERSONA_PID $CHARACTER_PID"
echo ""
echo "To monitor logs:"
echo "  tail -f logs/worker_base_persona.log"
echo "  tail -f logs/worker_character.log"
