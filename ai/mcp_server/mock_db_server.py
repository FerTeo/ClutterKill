"""
Mock Database MCP Server

A FastMCP server that exposes CRUD tools on a SQLite database.
It runs as a subprocess, communicating over stdio transport.

The database file persists in the OS temp directory for the duration
of the session, so state is preserved between agent calls.
"""
import os
import sqlite3
import tempfile

from mcp.server.fastmcp import FastMCP

# ── Server setup ──────────────────────────────────────────────────────────────
mcp = FastMCP("MockDatabase")

# Persistent SQLite file in temp dir so state survives between agent calls
DB_PATH = os.path.join(tempfile.gettempdir(), "agents_mock_db.sqlite")
conn = sqlite3.connect(DB_PATH, check_same_thread=False)
conn.execute(
    "CREATE TABLE IF NOT EXISTS records (key TEXT PRIMARY KEY, value TEXT)"
)
conn.commit()


# ── CRUD Tools ────────────────────────────────────────────────────────────────

@mcp.tool()
def create_record(key: str, value: str) -> str:
    """Create a new record in the database with the given key and value."""
    try:
        conn.execute("INSERT INTO records VALUES (?, ?)", (key, value))
        conn.commit()
        return f"Created: {key} = {value}"
    except sqlite3.IntegrityError:
        return f"Error: key '{key}' already exists. Use update_record to change it."


@mcp.tool()
def read_record(key: str) -> str:
    """Read the value of a record by its key."""
    cursor = conn.execute("SELECT value FROM records WHERE key = ?", (key,))
    row = cursor.fetchone()
    return f"{key} = {row[0]}" if row else f"No record found for key '{key}'."


@mcp.tool()
def update_record(key: str, new_value: str) -> str:
    """Update the value of an existing record."""
    cursor = conn.execute(
        "UPDATE records SET value = ? WHERE key = ?", (new_value, key)
    )
    conn.commit()
    if cursor.rowcount > 0:
        return f"Updated: {key} = {new_value}"
    return f"No record found for key '{key}'."


@mcp.tool()
def delete_record(key: str) -> str:
    """Delete a record from the database by its key."""
    cursor = conn.execute("DELETE FROM records WHERE key = ?", (key,))
    conn.commit()
    if cursor.rowcount > 0:
        return f"Deleted record '{key}'."
    return f"No record found for key '{key}'."


@mcp.tool()
def list_all_records() -> str:
    """List all records currently stored in the database."""
    cursor = conn.execute("SELECT key, value FROM records ORDER BY key")
    rows = cursor.fetchall()
    if not rows:
        return "The database is empty."
    return "\n".join(f"  {key} = {value}" for key, value in rows)


# ── Entry point ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    mcp.run()
