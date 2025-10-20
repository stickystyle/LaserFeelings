#!/usr/bin/env python3
# ABOUTME: Initializes Neo4j database with temporal indexes and constraints for the AI TTRPG player system.
# ABOUTME: Creates composite indexes for agent-temporal queries and full-text indexes for semantic search.

"""
Neo4j Database Initialization Script

This script sets up the required indexes and constraints for the AI TTRPG Player System.
It creates temporal indexes for efficient memory queries, entity constraints for data integrity,
and full-text indexes for semantic search.

Usage:
    uv run python scripts/setup_neo4j.py

Requirements:
    - Docker containers must be running (docker-compose up -d)
    - Neo4j must be accessible at the configured URI
    - Credentials from .env file must be correct
"""

import os
import sys
from pathlib import Path

# Add project root to path to import src modules
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv
from neo4j import Driver, GraphDatabase, Session
from neo4j.exceptions import AuthError, ServiceUnavailable


def load_configuration() -> tuple[str, str, str]:
    """Load configuration from .env file."""
    env_file = project_root / ".env"

    # Try .env first, fall back to .env.example
    if env_file.exists():
        load_dotenv(env_file)
        print(f"✓ Loaded configuration from {env_file}")
    else:
        example_file = project_root / ".env.example"
        load_dotenv(example_file)
        print(f"⚠ No .env file found, using {example_file}")

    neo4j_uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    neo4j_user = os.getenv("NEO4J_USER", "neo4j")
    neo4j_password = os.getenv("NEO4J_PASSWORD", "password123")

    return neo4j_uri, neo4j_user, neo4j_password


def create_indexes(session: Session) -> int:
    """
    Create all required indexes for the TTRPG memory system.

    Based on research.md §5 (Neo4j Temporal Indexing Strategy).
    All index creation uses IF NOT EXISTS for idempotent execution.
    """

    indexes = [
        # Composite index for agent-temporal queries
        # Optimizes queries filtering by agent_id + session_number + days_elapsed
        # Provides 3-6x speedup for typical queries (800ms → 120ms)
        (
            "agent_session_temporal",
            """
            CREATE INDEX agent_session_temporal IF NOT EXISTS
            FOR (e:Edge)
            ON (e.agent_id, e.session_number, e.days_elapsed)
            """
        ),

        # Temporal range indexes for validity windows
        # Enables efficient "memories valid at time T" queries
        (
            "edge_valid_at",
            """
            CREATE INDEX edge_valid_at IF NOT EXISTS
            FOR (e:Edge)
            ON (e.valid_at)
            """
        ),
        (
            "edge_invalid_at",
            """
            CREATE INDEX edge_invalid_at IF NOT EXISTS
            FOR (e:Edge)
            ON (e.invalid_at)
            """
        ),

        # Full-text index for semantic content search
        # Required for "what do we know about X?" style queries
        (
            "edge_fact_fulltext",
            """
            CREATE FULLTEXT INDEX edge_fact_fulltext IF NOT EXISTS
            FOR (e:Edge)
            ON EACH [e.fact]
            """
        ),

        # Index on corruption metadata for analytics
        # Enables fast corruption statistics and debugging
        (
            "corruption_type",
            """
            CREATE INDEX corruption_type IF NOT EXISTS
            FOR (e:Edge)
            ON (e.corruption_type)
            """
        ),

        # Index for importance-based retrieval
        # Supports queries that prioritize important memories
        (
            "edge_importance",
            """
            CREATE INDEX edge_importance IF NOT EXISTS
            FOR (e:Edge)
            ON (e.importance)
            """
        ),

        # Index for rehearsal count tracking
        # Supports queries about memory access patterns
        (
            "edge_rehearsal",
            """
            CREATE INDEX edge_rehearsal IF NOT EXISTS
            FOR (e:Edge)
            ON (e.rehearsal_count)
            """
        ),

        # Composite index for memory type filtering
        # Optimizes queries by memory type + agent
        (
            "memory_type_agent",
            """
            CREATE INDEX memory_type_agent IF NOT EXISTS
            FOR (e:Edge)
            ON (e.memory_type, e.agent_id)
            """
        ),
    ]

    print("\n" + "="*60)
    print("Creating Neo4j Indexes")
    print("="*60 + "\n")

    for index_name, query in indexes:
        try:
            session.run(query)
            print(f"✓ Created index: {index_name}")
        except Exception as e:
            print(f"✗ Error creating index {index_name}: {e}")
            raise

    return len(indexes)


def create_constraints(session: Session) -> int:
    """
    Create constraints for data integrity.

    Ensures unique identifiers and prevents duplicate entities.
    """

    constraints = [
        # Unique agent_id on nodes (if we create Agent nodes in future)
        (
            "unique_agent_id",
            """
            CREATE CONSTRAINT unique_agent_id IF NOT EXISTS
            FOR (a:Agent)
            REQUIRE a.agent_id IS UNIQUE
            """
        ),

        # Unique UUID on Edge nodes (Graphiti uses this)
        (
            "unique_edge_uuid",
            """
            CREATE CONSTRAINT unique_edge_uuid IF NOT EXISTS
            FOR (e:Edge)
            REQUIRE e.uuid IS UNIQUE
            """
        ),

        # Unique UUID on Entity nodes (Graphiti uses this)
        (
            "unique_entity_uuid",
            """
            CREATE CONSTRAINT unique_entity_uuid IF NOT EXISTS
            FOR (n:Entity)
            REQUIRE n.uuid IS UNIQUE
            """
        ),
    ]

    print("\n" + "="*60)
    print("Creating Neo4j Constraints")
    print("="*60 + "\n")

    for constraint_name, query in constraints:
        try:
            session.run(query)
            print(f"✓ Created constraint: {constraint_name}")
        except Exception as e:
            # Constraints might already exist, which is fine
            if "already exists" in str(e).lower() or "equivalent" in str(e).lower():
                print(f"⚠ Constraint {constraint_name} already exists (OK)")
            else:
                print(f"✗ Error creating constraint {constraint_name}: {e}")
                raise

    return len(constraints)


def verify_connection(driver: Driver) -> bool:
    """Verify connection to Neo4j and print version info."""
    try:
        with driver.session() as session:
            result = session.run("CALL dbms.components() YIELD name, versions, edition")
            record = result.single()
            if record is None:
                print("\n✗ Connection failed: No response from database")
                return False
            print("\n✓ Connected to Neo4j")
            print(f"  Version: {record['versions'][0]}")
            print(f"  Edition: {record['edition']}")
            return True
    except Exception as e:
        print(f"\n✗ Connection failed: {e}")
        return False


def verify_indexes(session: Session) -> int:
    """Verify all indexes were created successfully."""
    result = session.run("SHOW INDEXES")
    indexes = list(result)

    print("\n" + "="*60)
    print(f"Verification: {len(indexes)} indexes exist in database")
    print("="*60 + "\n")

    for idx in indexes:
        print(f"  • {idx['name']} ({idx['type']})")

    return len(indexes)


def main() -> None:
    """Main execution function."""
    print("\n" + "="*60)
    print("Neo4j Database Initialization for AI TTRPG Player System")
    print("="*60)

    # Load configuration
    neo4j_uri, neo4j_user, neo4j_password = load_configuration()

    print(f"\nConnecting to Neo4j at {neo4j_uri}...")
    print(f"User: {neo4j_user}")

    # Create driver
    try:
        driver = GraphDatabase.driver(
            neo4j_uri,
            auth=(neo4j_user, neo4j_password),
            max_connection_lifetime=3600,
            connection_timeout=10
        )
    except Exception as e:
        print(f"\n✗ Failed to create driver: {e}")
        print("\nTroubleshooting:")
        print("  1. Ensure Docker containers are running: docker-compose up -d")
        print("  2. Check Neo4j logs: docker logs ttrpg-neo4j")
        print("  3. Verify credentials in .env file")
        sys.exit(1)

    # Verify connection
    if not verify_connection(driver):
        print("\nTroubleshooting:")
        print("  1. Check if Neo4j container is healthy: docker ps")
        print("  2. Verify credentials match docker-compose.yml")
        print("  3. Wait for Neo4j to fully start (may take 30-60 seconds)")
        driver.close()
        sys.exit(1)

    # Create indexes and constraints
    try:
        with driver.session() as session:
            index_count = create_indexes(session)
            constraint_count = create_constraints(session)

            # Verify creation
            verify_indexes(session)

            print("\n" + "="*60)
            print("✓ Initialization Complete")
            print("="*60)
            print(f"  Created {index_count} indexes")
            print(f"  Created {constraint_count} constraints")
            print("\nNeo4j database is ready for the AI TTRPG Player System.")
            print("\nNext steps:")
            print("  1. Run personality seeding: uv run python scripts/seed_personalities.py")
            print("  2. Start the application: uv run python main.py")

    except ServiceUnavailable as e:
        print(f"\n✗ Neo4j service unavailable: {e}")
        print("\nCheck if containers are running: docker-compose ps")
        sys.exit(1)
    except AuthError as e:
        print(f"\n✗ Authentication failed: {e}")
        print("\nVerify credentials in .env match docker-compose.yml")
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ Setup failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        driver.close()


if __name__ == "__main__":
    main()
