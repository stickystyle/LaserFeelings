# ABOUTME: Scripts package for AI TTRPG Player System infrastructure setup.
# ABOUTME: Contains database initialization and configuration seeding utilities.

"""
Infrastructure setup scripts for the AI TTRPG Player System.

Available scripts:
- setup_neo4j.py: Initialize Neo4j database with indexes and constraints
- seed_personalities.py: Create example AI player personality configurations
- setup.sh: Convenience script to run all setup steps
"""

__all__ = ['setup_neo4j', 'seed_personalities']
