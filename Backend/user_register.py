"""Standalone user-registration helper matching the current SplitTrip schema.

The Flask API already provides POST /api/users. Prefer that endpoint for
application use. This helper is retained for local scripts and testing.
"""
import os

import mysql.connector
from mysql.connector import IntegrityError
from werkzeug.security import generate_password_hash


def register_user(username, email, password):
    username = str(username).strip()
    email = str(email).strip().lower()
    password = str(password)

    if not username or not email or not password:
        raise ValueError("username, email and password are required")
    if len(password) < 8:
        raise ValueError("password must be at least 8 characters")

    connection = mysql.connector.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=int(os.getenv("DB_PORT", "3306")),
        user=os.getenv("DB_USER", "root"),
        password=os.getenv("DB_PASSWORD", ""),
        database=os.getenv("DB_NAME", "trip_planner"),
    )
    cursor = connection.cursor()
    try:
        cursor.execute(
            """INSERT INTO users (username, email, password_hash)
               VALUES (%s, %s, %s)""",
            (username, email, generate_password_hash(password)),
        )
        connection.commit()
        return cursor.lastrowid
    except IntegrityError as exc:
        connection.rollback()
        raise ValueError("That email is already registered") from exc
    except Exception:
        connection.rollback()
        raise
    finally:
        cursor.close()
        connection.close()


if __name__ == "__main__":
    print("Import register_user(username, email, password) and call it explicitly.")
    print("No test user is inserted automatically.")
