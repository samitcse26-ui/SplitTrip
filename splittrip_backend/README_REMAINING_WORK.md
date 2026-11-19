# SplitTrip backend: remaining features

This package is based on the current `SplitTrip_Merged_Backend.zip`. It preserves the existing Flask/MySQL structure and adds:

- Net balance calculation for each trip member.
- Recording and listing settlements.
- Deleting a settlement record.
- Editing an expense and recalculating its equal split.
- Deleting an expense (its split rows are removed by the existing foreign key cascade).

## Install / replace

1. Back up your current project folder.
2. Replace the contents of your existing `splittrip_backend` folder with this package's `splittrip_backend` folder.
3. Keep your existing `.env` file. Do not upload it to GitHub.
4. Install dependencies if needed: `pip install -r requirements.txt`.
5. Run `migration_add_settlements.sql` once in MySQL Workbench, using the `trip_planner` database.
6. Start Flask as you normally do and test `/health`.

Do not run `schema.sql` over an existing database as a reset operation. It uses `CREATE TABLE IF NOT EXISTS`, but it does not migrate every older table layout. The settlement migration is the only new migration in this package.

## New / updated endpoints

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/api/trips/<trip_id>/balances` | Net balance for each member |
| POST | `/api/trips/<trip_id>/settlements` | Record a payment from one member to another |
| GET | `/api/trips/<trip_id>/settlements` | List recorded settlements |
| DELETE | `/api/settlements/<settlement_id>` | Remove a settlement record |
| PATCH | `/api/expenses/<expense_id>` | Edit expense and recalculate its split |
| DELETE | `/api/expenses/<expense_id>` | Delete expense and its split rows |

### Balance interpretation

- `net_balance` greater than zero: member should receive money.
- `net_balance` less than zero: member owes money.
- `net_balance` equal to zero: member is settled.

Settlements are recorded as `paid_by` (the member paying) and `paid_to` (the member receiving). The balance endpoint accounts for those records.

### Example requests

Record a settlement:
```json
{
  "paid_by": 2,
  "paid_to": 1,
  "amount": "300.00",
  "note": "Dinner repayment"
}
```

Edit an expense:
```json
{
  "amount": "1500.00",
  "description": "Updated dinner bill",
  "paid_by": 1
}
```

Get balances:
`GET http://127.0.0.1:5000/api/trips/1/balances`

Get settlements:
`GET http://127.0.0.1:5000/api/trips/1/settlements`

## Important behavior / scope

- Editing an expense recalculates shares among the users who were in that expense's existing split. It does not silently add newly joined trip members to an old expense.
- Settlement records are manual records; this project does not move real money or verify bank/UPI payments.
- Authentication is not yet enforced on these routes. Do not treat this mini-project backend as production-ready.
- Test with a copy of your database first. Keep a database backup before applying migrations.
