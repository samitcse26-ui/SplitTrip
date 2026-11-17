"""Compatibility entry point for the old itinerary/database setup filename.

The previous version dropped and recreated tables, which could erase data.
Database setup is now centralized in database_table.py and schema.sql.
"""
from database_table import initialize_database


if __name__ == "__main__":
    initialize_database()
