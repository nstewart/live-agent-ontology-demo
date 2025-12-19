#!/usr/bin/env python3
"""Initialize LangGraph checkpointer tables in PostgreSQL."""

import sys

import psycopg
from langgraph.checkpoint.postgres import PostgresSaver

from src.config import get_settings


def init_checkpointer():
    """Initialize checkpointer tables in PostgreSQL."""
    settings = get_settings()

    print(f"Initializing LangGraph checkpointer tables...")
    print(f"  Database: {settings.pg_host}:{settings.pg_port}/{settings.pg_database}")

    try:
        # First, drop any existing checkpoint tables to ensure clean state
        print("  Dropping existing checkpoint tables if present...")
        with psycopg.connect(settings.pg_dsn) as conn:
            with conn.cursor() as cur:
                cur.execute("DROP TABLE IF EXISTS checkpoint_blobs CASCADE")
                cur.execute("DROP TABLE IF EXISTS checkpoint_writes CASCADE")
                cur.execute("DROP TABLE IF EXISTS checkpoints CASCADE")
                cur.execute("DROP TABLE IF EXISTS checkpoint_migrations CASCADE")
            conn.commit()
        print("  ✓ Existing tables dropped")

        # Create checkpointer and setup tables with correct schema
        print("  Creating fresh checkpoint tables...")
        with PostgresSaver.from_conn_string(settings.pg_dsn) as checkpointer:
            checkpointer.setup()

        print("✓ Checkpointer tables created successfully!")
        return 0

    except Exception as e:
        print(f"✗ Error initializing checkpointer: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(init_checkpointer())
