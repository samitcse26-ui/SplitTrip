# SplitTrip database files (aligned with SplitTrip_Merged_Backend)

These files replace the teammate's older database scripts.

## What changed

- `database_table.py` now initializes the current schema from `schema.sql`.
- `iternary.py` is retained as a compatibility entry point and delegates to
  `database_table.py`.
- Neither setup script drops tables or deletes records.
- `user_register.py` writes to `users.password_hash`, hashes passwords using
  Werkzeug, reads DB settings from environment variables, and does not
  insert a test account automatically.
- `schema.sql` and `migration_add_expense_splits.sql` are copied from the
  latest merged backend package.

## Important: preserve your current database

The old scripts used `DROP TABLE` and the old user schema used a `password`
column. Do not run the old scripts again. The new schema uses
`users.password_hash`, `trips.created_by`, `trips.created_at`,
`trip_members.joined_at`, `itinerary.activity_time`, `itinerary.notes`,
`expenses.created_at`, and `expense_splits`.

`CREATE TABLE IF NOT EXISTS` creates missing tables but does not modify an
existing table's columns. For an existing database, compare its columns
against `schema.sql` and the current backend README before applying any
ALTER TABLE statements. Do not run a destructive reset.

If the existing backend database already has the required tables and
columns, you do not need to run the initializer at all. The current Flask
app can continue using it.

## Setup

1. Install the backend dependencies from the merged backend's
   `requirements.txt`.
2. Set `DB_HOST`, `DB_PORT`, `DB_USER`, `DB_PASSWORD`, and `DB_NAME` in
   your shell or environment. Never commit a real password.
3. From this folder, run `python database_table.py` only if you need to
   create missing tables.
4. For an existing database missing only `expense_splits`, inspect and run
   `migration_add_expense_splits.sql` in MySQL Workbench.

## User registration

The recommended route is still `POST /api/users` in the Flask app.
`user_register.py` is only a standalone helper; it requires the backend
Python dependencies and environment variables.
