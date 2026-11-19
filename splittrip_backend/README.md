# SplitTrip merged backend

This is one Flask application using **MySQL**. It combines the original user/trip/member/itinerary API with the teammate's expense creation and equal-splitting logic. The teammate's SQLite database (`trip_v2.db`) is not used by this merged version.

## Project structure

```text
splittrip_backend/
├── splittrip/
│   ├── __init__.py
│   ├── app.py
│   └── db.py
├── schema.sql
├── migration_add_expense_splits.sql
├── requirements.txt
└── README.md
```

## Setup

1. Start your local MySQL server.
2. Inspect your existing database before changing it:

   ```sql
   USE trip_planner;
   DESCRIBE users;
   DESCRIBE trips;
   DESCRIBE trip_members;
   DESCRIBE itinerary;
   DESCRIBE expenses;
   ```

   The current app expects `users.username`, `users.email`, `users.password_hash`; `trips.title`, `trips.description`, `trips.created_by`; and `itinerary.activity_time` plus `itinerary.notes`. Do not blindly rerun schema creation to change existing tables.

3. If the existing `expenses` table already exists with `id`, `trip_id`, `paid_by`, `amount`, and `description`, run `migration_add_expense_splits.sql` in MySQL Workbench. If this is a brand-new database, run `schema.sql` instead.
4. In this folder, activate your virtual environment and install dependencies:

   ```bash
   source ../.venv/bin/activate   # if your .venv is in the project root
   pip install -r requirements.txt
   ```

5. Set your MySQL connection variables in the terminal (use your own password; do not commit it):

   ```bash
   export DB_HOST=localhost
   export DB_PORT=3306
   export DB_USER=root
   export DB_PASSWORD='YOUR_MYSQL_PASSWORD'
   export DB_NAME=trip_planner
   ```

6. Start from the `splittrip_backend` directory:

   ```bash
   python -m splittrip.app
   ```

Health check: `GET http://127.0.0.1:5000/health`

## API endpoints

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/health` | Check Flask and MySQL |
| POST | `/api/users` | Register a user |
| POST | `/api/users/login` | Verify login |
| GET | `/api/users/<id>` | Get a user |
| POST | `/api/trips` | Create trip; creator is added as member |
| GET | `/api/trips` | List trips; optional `?user_id=<id>` |
| GET/PATCH/DELETE | `/api/trips/<id>` | Read, update, delete trip |
| GET/POST | `/api/trips/<id>/members` | List/add members |
| DELETE | `/api/trips/<trip_id>/members/<user_id>` | Remove member |
| GET/POST | `/api/trips/<id>/itinerary` | List/add itinerary item |
| PATCH/DELETE | `/api/itinerary/<item_id>` | Update/delete itinerary item |
| POST/GET | `/api/trips/<id>/expenses` | Add/list expenses |
| GET | `/api/expenses/<expense_id>/splits` | List the calculated shares for an expense |

## Expense request example

`POST http://127.0.0.1:5000/api/trips/1/expenses`

Body → raw → JSON:

```json
{
  "paid_by": 1,
  "amount": 100.00,
  "description": "Dinner"
}
```

The backend splits the amount equally among the trip's **current members**, including the payer, because that is how the teammate's submitted code works. Any leftover paise from a split is distributed one paise at a time so the shares add up exactly to the expense total. The payer must be a member of that trip.

Then inspect the shares with:

`GET http://127.0.0.1:5000/api/expenses/1/splits`

## Important integration notes

- Both modules now use the same MySQL database and the same `users`, `trips`, and `trip_members` records.
- The teammate's SQLite `trip_v2.db` is deliberately not connected. Its data is not automatically copied into MySQL.
- Expense creation and equal split records are included. Expense editing/deletion, net balance summaries, payment recording, and settlement workflows are **not** implemented by the teammate's pasted code and remain to be built/tested.
- Login currently verifies passwords but does not issue tokens or enforce authorization. Do not treat this as production-ready authentication.
- Never commit database passwords or real user credentials.
