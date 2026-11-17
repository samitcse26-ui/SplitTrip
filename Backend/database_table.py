"""Create missing SplitTrip tables using the schema from the current backend.

Safe to rerun: the schema uses CREATE TABLE IF NOT EXISTS.
This script never drops tables or deletes existing records.
"""
import os
from pathlib import Path

import mysql.connector


def get_connection():
    return mysql.connector.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=int(os.getenv("DB_PORT", "3306")),
        user=os.getenv("DB_USER", "root"),
        password=os.getenv("DB_PASSWORD", ""),
        database=os.getenv("DB_NAME", "trip_planner"),
    )


def initialize_database():
    schema_path = Path(__file__).with_name("schema.sql")
    sql_text = schema_path.read_text(encoding="utf-8")

    # The connection already selects DB_NAME, so skip CREATE DATABASE and USE.
    statements = []
    for raw in sql_text.split(";"):
        lines = [
            line for line in raw.splitlines()
            if line.strip() and not line.lstrip().startswith("--")
        ]
        statement = "\\n".join(lines).strip()
        if statement and not statement.upper().startswith(("CREATE DATABASE", "USE ")):
            statements.append(statement)

    conn = get_connection()
    cursor = conn.cursor()
    try:
        for statement in statements:
            cursor.execute(statement)
        conn.commit()
        print("SplitTrip schema checked/initialized. Existing data was not deleted.")
    except Exception:
        conn.rollback()
        raise
    finally:
        cursor.close()
        conn.close()


if __name__ == "__main__":
    initialize_database()
