#!/bin/bash
# ABOUTME: Convenience script to set up the AI TTRPG Player System infrastructure.
# ABOUTME: Starts Docker containers, initializes Neo4j database, and seeds personality data.

set -e  # Exit on error

echo "================================================================"
echo "AI TTRPG Player System - Infrastructure Setup"
echo "================================================================"
echo ""

# Check if docker-compose is available
if ! command -v docker-compose &> /dev/null; then
    echo "✗ docker-compose not found"
    echo "  Please install Docker Desktop or docker-compose"
    exit 1
fi

# Check if uv is available
if ! command -v uv &> /dev/null; then
    echo "✗ uv not found"
    echo "  Please install uv: curl -LsSf https://astral.sh/uv/install.sh | sh"
    exit 1
fi

echo "Step 1: Starting Docker containers..."
echo "----------------------------------------"
cd "$(dirname "$0")/.."
docker-compose -f docker/docker-compose.yml up -d

echo ""
echo "Step 2: Waiting for services to be healthy..."
echo "----------------------------------------"
echo "This may take 30-60 seconds for Neo4j to fully initialize..."
sleep 10

# Wait for Neo4j health check
max_attempts=12
attempt=0
while [ $attempt -lt $max_attempts ]; do
    if docker exec ttrpg-neo4j cypher-shell -u neo4j -p password123 'RETURN 1;' &> /dev/null; then
        echo "✓ Neo4j is ready"
        break
    fi
    attempt=$((attempt + 1))
    echo "  Waiting for Neo4j... (attempt $attempt/$max_attempts)"
    sleep 5
done

if [ $attempt -eq $max_attempts ]; then
    echo "✗ Neo4j failed to start within timeout"
    echo "  Check logs: docker logs ttrpg-neo4j"
    exit 1
fi

# Wait for Redis
if docker exec ttrpg-redis redis-cli ping &> /dev/null; then
    echo "✓ Redis is ready"
else
    echo "✗ Redis is not responding"
    exit 1
fi

echo ""
echo "Step 3: Initializing Neo4j database..."
echo "----------------------------------------"
uv run python scripts/setup_neo4j.py

echo ""
echo "Step 4: Seeding personality configurations..."
echo "----------------------------------------"
uv run python scripts/seed_personalities.py

echo ""
echo "================================================================"
echo "✓ Setup Complete!"
echo "================================================================"
echo ""
echo "Next steps:"
echo "  1. Review personalities in config/personalities/"
echo "  2. Copy .env.example to .env and add your OpenAI API key"
echo "  3. Run the application: uv run python main.py"
echo ""
echo "Useful commands:"
echo "  - View Neo4j browser: http://localhost:7474"
echo "  - Check container status: docker-compose -f docker/docker-compose.yml ps"
echo "  - View logs: docker-compose -f docker/docker-compose.yml logs -f"
echo "  - Stop services: docker-compose -f docker/docker-compose.yml down"
echo ""
