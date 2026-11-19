import os
from flask import Flask, jsonify, request
from werkzeug.security import generate_password_hash, check_password_hash
from mysql.connector import IntegrityError, Error
from .db import get_connection
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

def data():
    return request.get_json(silent=True) or {}

def fail(message, status=400):
    return jsonify({"error": message}), status

def query_one(sql, params=()):
    conn = get_connection()
    cur = conn.cursor(dictionary=True)
    try:
        cur.execute(sql, params)
        return cur.fetchone()
    finally:
        cur.close()
        conn.close()

def query_all(sql, params=()):
    conn = get_connection()
    cur = conn.cursor(dictionary=True)
    try:
        cur.execute(sql, params)
        return cur.fetchall()
    finally:
        cur.close()
        conn.close()

def execute(sql, params=()):
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute(sql, params)
        conn.commit()
        return cur.lastrowid, cur.rowcount
    except Exception:
        conn.rollback()
        raise
    finally:
        cur.close()
        conn.close()

@app.get("/health")
def health():
    try:
        return jsonify({"status": "ok", **query_one("SELECT 1 AS database_connected")})
    except Error as exc:
        return fail(f"Database connection failed: {exc}", 503)

# USER MANAGEMENT
@app.post("/api/users")
def register_user():
    d = data()
    username = str(d.get("username", "")).strip()
    email = str(d.get("email", "")).strip().lower()
    password = str(d.get("password", ""))
    if not username or not email or not password:
        return fail("username, email and password are required")
    if len(password) < 8:
        return fail("password must be at least 8 characters")
    try:
        user_id, _ = execute(
            "INSERT INTO users (username,email,password_hash) VALUES (%s,%s,%s)",
            (username, email, generate_password_hash(password))
        )
        return jsonify({"id": user_id, "username": username, "email": email}), 201
    except IntegrityError:
        return fail("That email is already registered", 409)
    except Error as exc:
        return fail(str(exc), 500)

@app.post("/api/users/login")
def login():
    d = data()
    email, password = str(d.get("email", "")).strip().lower(), str(d.get("password", ""))
    if not email or not password:
        return fail("email and password are required")
    try:
        user = query_one("SELECT * FROM users WHERE email=%s", (email,))
        if not user or not check_password_hash(user["password_hash"], password):
            return fail("Invalid email or password", 401)
        return jsonify({"id": user["id"], "username": user["username"], "email": user["email"]})
    except Error as exc:
        return fail(str(exc), 500)

@app.get("/api/users/<int:user_id>")
def get_user(user_id):
    try:
        user = query_one("SELECT id,username,email,created_at FROM users WHERE id=%s", (user_id,))
        return (jsonify(user), 200) if user else fail("User not found", 404)
    except Error as exc:
        return fail(str(exc), 500)

# TRIP MANAGEMENT
@app.post("/api/trips")
def create_trip():
    d = data()
    title, creator = str(d.get("title", "")).strip(), d.get("created_by")
    description = d.get("description")
    if not title or not isinstance(creator, int):
        return fail("title and integer created_by are required")
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute("INSERT INTO trips (title,description,created_by) VALUES (%s,%s,%s)",
                    (title, description, creator))
        trip_id = cur.lastrowid
        cur.execute("INSERT INTO trip_members (trip_id,user_id) VALUES (%s,%s)", (trip_id, creator))
        conn.commit()
        return jsonify({"id": trip_id, "title": title, "description": description, "created_by": creator}), 201
    except IntegrityError as exc:
        conn.rollback()
        return fail(f"Invalid creator or relationship: {exc}", 400)
    except Error as exc:
        conn.rollback()
        return fail(str(exc), 500)
    finally:
        cur.close()
        conn.close()

@app.get("/api/trips")
def list_trips():
    user_id = request.args.get("user_id", type=int)
    try:
        if user_id is None:
            return jsonify(query_all("SELECT * FROM trips ORDER BY created_at DESC"))
        return jsonify(query_all(
            """SELECT t.* FROM trips t JOIN trip_members m ON m.trip_id=t.id
               WHERE m.user_id=%s ORDER BY t.created_at DESC""", (user_id,)))
    except Error as exc:
        return fail(str(exc), 500)

@app.get("/api/trips/<int:trip_id>")
def get_trip(trip_id):
    try:
        trip = query_one("SELECT * FROM trips WHERE id=%s", (trip_id,))
        return (jsonify(trip), 200) if trip else fail("Trip not found", 404)
    except Error as exc:
        return fail(str(exc), 500)

@app.patch("/api/trips/<int:trip_id>")
def update_trip(trip_id):
    d = data()
    try:
        old = query_one("SELECT * FROM trips WHERE id=%s", (trip_id,))
        if not old:
            return fail("Trip not found", 404)
        title = str(d.get("title", old["title"])).strip()
        description = d.get("description", old["description"])
        if not title:
            return fail("title cannot be empty")
        execute("UPDATE trips SET title=%s,description=%s WHERE id=%s", (title, description, trip_id))
        return jsonify(query_one("SELECT * FROM trips WHERE id=%s", (trip_id,)))
    except Error as exc:
        return fail(str(exc), 500)

@app.delete("/api/trips/<int:trip_id>")
def delete_trip(trip_id):
    try:
        _, count = execute("DELETE FROM trips WHERE id=%s", (trip_id,))
        return (jsonify({"message": "Trip deleted"}), 200) if count else fail("Trip not found", 404)
    except Error as exc:
        return fail(str(exc), 500)

# TRIP PARTICIPANTS
@app.get("/api/trips/<int:trip_id>/members")
def list_members(trip_id):
    try:
        return jsonify(query_all(
            """SELECT u.id,u.username,u.email,m.joined_at
               FROM trip_members m JOIN users u ON u.id=m.user_id
               WHERE m.trip_id=%s ORDER BY m.joined_at""", (trip_id,)))
    except Error as exc:
        return fail(str(exc), 500)

@app.post("/api/trips/<int:trip_id>/members")
def add_member(trip_id):
    user_id = data().get("user_id")
    if not isinstance(user_id, int):
        return fail("integer user_id is required")
    try:
        execute("INSERT INTO trip_members (trip_id,user_id) VALUES (%s,%s)", (trip_id, user_id))
        return jsonify({"message": "Member added", "trip_id": trip_id, "user_id": user_id}), 201
    except IntegrityError:
        return fail("Trip/user does not exist or user is already a member", 409)
    except Error as exc:
        return fail(str(exc), 500)

@app.delete("/api/trips/<int:trip_id>/members/<int:user_id>")
def remove_member(trip_id, user_id):
    try:
        _, count = execute("DELETE FROM trip_members WHERE trip_id=%s AND user_id=%s", (trip_id, user_id))
        return (jsonify({"message": "Member removed"}), 200) if count else fail("Membership not found", 404)
    except Error as exc:
        return fail(str(exc), 500)

# ITINERARY MANAGEMENT
@app.get("/api/trips/<int:trip_id>/itinerary")
def list_itinerary(trip_id):
    try:
        return jsonify(query_all(
            "SELECT * FROM itinerary WHERE trip_id=%s ORDER BY day_number,activity_time,id",
            (trip_id,)))
    except Error as exc:
        return fail(str(exc), 500)

@app.post("/api/trips/<int:trip_id>/itinerary")
def add_itinerary_item(trip_id):
    d = data()
    day, activity = d.get("day_number"), str(d.get("activity", "")).strip()
    if not isinstance(day, int) or day < 1 or not activity:
        return fail("positive integer day_number and activity are required")
    try:
        item_id, _ = execute(
            """INSERT INTO itinerary (trip_id,day_number,activity,activity_time,notes)
               VALUES (%s,%s,%s,%s,%s)""",
            (trip_id, day, activity, d.get("activity_time"), d.get("notes")))
        return jsonify({"id": item_id, "trip_id": trip_id, **d}), 201
    except IntegrityError:
        return fail("Trip does not exist", 404)
    except Error as exc:
        return fail(str(exc), 500)

@app.patch("/api/itinerary/<int:item_id>")
def update_itinerary_item(item_id):
    d = data()
    try:
        old = query_one("SELECT * FROM itinerary WHERE id=%s", (item_id,))
        if not old:
            return fail("Itinerary item not found", 404)
        day = d.get("day_number", old["day_number"])
        activity = str(d.get("activity", old["activity"])).strip()
        if not isinstance(day, int) or day < 1 or not activity:
            return fail("day_number must be positive and activity cannot be empty")
        execute(
            """UPDATE itinerary SET day_number=%s,activity=%s,activity_time=%s,notes=%s
               WHERE id=%s""",
            (day, activity, d.get("activity_time", old["activity_time"]),
             d.get("notes", old["notes"]), item_id))
        return jsonify(query_one("SELECT * FROM itinerary WHERE id=%s", (item_id,)))
    except Error as exc:
        return fail(str(exc), 500)

@app.delete("/api/itinerary/<int:item_id>")
def delete_itinerary_item(item_id):
    try:
        _, count = execute("DELETE FROM itinerary WHERE id=%s", (item_id,))
        return (jsonify({"message": "Itinerary item deleted"}), 200) if count else fail("Item not found", 404)
    except Error as exc:
        return fail(str(exc), 500)


# EXPENSE MANAGEMENT + EQUAL SPLITTING
from decimal import Decimal, InvalidOperation

@app.post("/api/trips/<int:trip_id>/expenses")
def add_expense(trip_id):
    d = data()
    paid_by = d.get("paid_by")
    description = str(d.get("description", "Trip Expense")).strip()

    if not isinstance(paid_by, int) or isinstance(paid_by, bool):
        return fail("integer paid_by is required")
    if not description:
        return fail("description cannot be empty")
    if len(description) > 255:
        return fail("description must be 255 characters or fewer")

    try:
        amount = Decimal(str(d.get("amount", "")))
        if not amount.is_finite() or amount <= 0:
            return fail("amount must be a positive number")
        if amount.as_tuple().exponent < -2:
            return fail("amount can have at most 2 decimal places")
        total_cents = int(amount * 100)
        if total_cents > 9_999_999_999:
            return fail("amount exceeds the supported limit")
    except (InvalidOperation, ValueError):
        return fail("a valid amount is required")

    conn = get_connection()
    cur = conn.cursor()
    try:
        # Every expense is split equally among the trip's current members.
        cur.execute("SELECT user_id FROM trip_members WHERE trip_id=%s ORDER BY user_id", (trip_id,))
        member_ids = [row[0] for row in cur.fetchall()]
        if not member_ids:
            return fail("No members found in this trip to split with", 400)
        if paid_by not in member_ids:
            return fail("paid_by must be a member of this trip", 400)

        cur.execute(
            "INSERT INTO expenses (trip_id, paid_by, amount, description) VALUES (%s,%s,%s,%s)",
            (trip_id, paid_by, amount, description),
        )
        expense_id = cur.lastrowid

        # Split in cents so the shares always add up exactly to the expense.
        base_share, remainder = divmod(total_cents, len(member_ids))
        split_rows = []
        for index, user_id in enumerate(member_ids):
            share_cents = base_share + (1 if index < remainder else 0)
            owed_amount = Decimal(share_cents) / Decimal(100)
            split_rows.append((expense_id, user_id, owed_amount, 0))

        cur.executemany(
            "INSERT INTO expense_splits (expense_id,user_id,owed_amount,is_settled) VALUES (%s,%s,%s,%s)",
            split_rows,
        )
        conn.commit()
        return jsonify({
            "status": "success",
            "expense_id": expense_id,
            "trip_id": trip_id,
            "paid_by": paid_by,
            "amount": format(amount, ".2f"),
            "description": description,
            "split_count": len(split_rows),
            "message": "Expense added and split equally among trip members",
        }), 201
    except Error as exc:
        conn.rollback()
        return fail(f"Database error: {exc}", 500)
    finally:
        cur.close()
        conn.close()

@app.get("/api/trips/<int:trip_id>/expenses")
def get_trip_expenses(trip_id):
    try:
        return jsonify(query_all(
            "SELECT id,trip_id,paid_by,amount,description,created_at FROM expenses WHERE trip_id=%s ORDER BY id DESC",
            (trip_id,),
        )), 200
    except Error as exc:
        return fail(str(exc), 500)

@app.get("/api/expenses/<int:expense_id>/splits")
def get_expense_splits(expense_id):
    try:
        expense = query_one("SELECT id FROM expenses WHERE id=%s", (expense_id,))
        if not expense:
            return fail("Expense not found", 404)
        return jsonify(query_all(
            "SELECT es.id,es.expense_id,es.user_id,u.username,es.owed_amount,es.is_settled "
            "FROM expense_splits es JOIN users u ON u.id=es.user_id "
            "WHERE es.expense_id=%s ORDER BY es.user_id",
            (expense_id,),
        )), 200
    except Error as exc:
        return fail(str(exc), 500)


# BALANCES
@app.get("/api/trips/<int:trip_id>/balances")
def get_trip_balances(trip_id):
    """Return each member's net position: positive = should receive, negative = owes."""
    try:
        trip = query_one("SELECT id FROM trips WHERE id=%s", (trip_id,))
        if not trip:
            return fail("Trip not found", 404)

        members = query_all(
            """SELECT u.id AS user_id, u.username
               FROM trip_members tm JOIN users u ON u.id=tm.user_id
               WHERE tm.trip_id=%s ORDER BY u.id""", (trip_id,))
        balances = {
            m["user_id"]: {
                "user_id": m["user_id"],
                "username": m["username"],
                "total_paid": Decimal("0.00"),
                "total_owed": Decimal("0.00"),
                "net_balance": Decimal("0.00"),
            } for m in members
        }

        expenses = query_all(
            "SELECT id,paid_by,amount FROM expenses WHERE trip_id=%s", (trip_id,))
        for expense in expenses:
            if expense["paid_by"] in balances:
                balances[expense["paid_by"]]["total_paid"] += Decimal(str(expense["amount"]))
            splits = query_all(
                "SELECT user_id,owed_amount FROM expense_splits WHERE expense_id=%s",
                (expense["id"],))
            for split in splits:
                if split["user_id"] in balances:
                    balances[split["user_id"]]["total_owed"] += Decimal(str(split["owed_amount"]))

        settlements = query_all(
            """SELECT paid_by,paid_to,amount FROM settlements
               WHERE trip_id=%s""", (trip_id,))
        for settlement in settlements:
            amount = Decimal(str(settlement["amount"]))
            # A settlement reduces the debtor's outstanding amount and the
            # creditor's amount still waiting to be received.
            if settlement["paid_by"] in balances:
                balances[settlement["paid_by"]]["total_paid"] += amount
            if settlement["paid_to"] in balances:
                balances[settlement["paid_to"]]["total_paid"] -= amount

        result = []
        for item in balances.values():
            item["net_balance"] = item["total_paid"] - item["total_owed"]
            result.append({
                "user_id": item["user_id"],
                "username": item["username"],
                "total_paid": format(item["total_paid"], ".2f"),
                "total_owed": format(item["total_owed"], ".2f"),
                "net_balance": format(item["net_balance"], ".2f"),
                "status": "gets_back" if item["net_balance"] > 0 else
                          "owes" if item["net_balance"] < 0 else "settled",
            })
        return jsonify({"trip_id": trip_id, "balances": result}), 200
    except Error as exc:
        return fail(str(exc), 500)


# EDIT AND DELETE EXPENSES
@app.patch("/api/expenses/<int:expense_id>")
def update_expense(expense_id):
    d = data()
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute(
            "SELECT id,trip_id,paid_by,amount,description FROM expenses WHERE id=%s",
            (expense_id,))
        old = cur.fetchone()
        if not old:
            return fail("Expense not found", 404)

        old_id, trip_id, old_paid_by, old_amount, old_description = old

        cur.execute(
            "SELECT user_id FROM expense_splits WHERE expense_id=%s ORDER BY user_id",
            (expense_id,))
        member_ids = [row[0] for row in cur.fetchall()]
        if not member_ids:
            return fail("Expense has no existing split records", 409)

        paid_by = d.get("paid_by", old_paid_by)
        if not isinstance(paid_by, int) or isinstance(paid_by, bool) or paid_by not in member_ids:
            return fail("paid_by must be one of the members in this expense's split", 400)

        description = str(d.get("description", old_description)).strip()
        if not description or len(description) > 255:
            return fail("description must contain 1 to 255 characters", 400)

        try:
            amount = Decimal(str(d.get("amount", old_amount)))
            if not amount.is_finite() or amount <= 0 or amount.as_tuple().exponent < -2:
                return fail("amount must be positive with at most 2 decimal places", 400)
            total_cents = int(amount * 100)
            if total_cents > 9_999_999_999:
                return fail("amount exceeds the supported limit", 400)
        except (InvalidOperation, ValueError):
            return fail("a valid amount is required", 400)

        base_share, remainder = divmod(total_cents, len(member_ids))
        split_rows = []
        for index, user_id in enumerate(member_ids):
            share_cents = base_share + (1 if index < remainder else 0)
            split_rows.append((expense_id, user_id, Decimal(share_cents) / Decimal(100), 0))

        cur.execute(
            "UPDATE expenses SET paid_by=%s,amount=%s,description=%s WHERE id=%s",
            (paid_by, amount, description, expense_id))
        cur.execute("DELETE FROM expense_splits WHERE expense_id=%s", (expense_id,))
        cur.executemany(
            """INSERT INTO expense_splits
               (expense_id,user_id,owed_amount,is_settled) VALUES (%s,%s,%s,%s)""",
            split_rows)
        conn.commit()
        return jsonify({
            "message": "Expense updated and splits recalculated",
            "expense_id": expense_id,
            "trip_id": trip_id,
            "paid_by": paid_by,
            "amount": format(amount, ".2f"),
            "description": description,
            "split_count": len(split_rows),
        }), 200
    except Error as exc:
        conn.rollback()
        return fail(str(exc), 500)
    finally:
        cur.close()
        conn.close()


@app.delete("/api/expenses/<int:expense_id>")
def delete_expense(expense_id):
    try:
        _, count = execute("DELETE FROM expenses WHERE id=%s", (expense_id,))
        if not count:
            return fail("Expense not found", 404)
        return jsonify({"message": "Expense and its split records deleted"}), 200
    except Error as exc:
        return fail(str(exc), 500)


# SETTLEMENTS
@app.post("/api/trips/<int:trip_id>/settlements")
def add_settlement(trip_id):
    d = data()
    paid_by, paid_to = d.get("paid_by"), d.get("paid_to")
    note = str(d.get("note", "")).strip() or None
    if (not isinstance(paid_by, int) or isinstance(paid_by, bool) or
            not isinstance(paid_to, int) or isinstance(paid_to, bool)):
        return fail("integer paid_by and paid_to are required")
    if paid_by == paid_to:
        return fail("A member cannot settle with themselves")
    try:
        amount = Decimal(str(d.get("amount", "")))
        if not amount.is_finite() or amount <= 0 or amount.as_tuple().exponent < -2:
            return fail("amount must be positive with at most 2 decimal places")
    except (InvalidOperation, ValueError):
        return fail("a valid amount is required")

    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute("SELECT user_id FROM trip_members WHERE trip_id=%s", (trip_id,))
        member_ids = {row[0] for row in cur.fetchall()}
        if paid_by not in member_ids or paid_to not in member_ids:
            return fail("Both users must be members of this trip", 400)
        cur.execute(
            """INSERT INTO settlements (trip_id,paid_by,paid_to,amount,note)
               VALUES (%s,%s,%s,%s,%s)""",
            (trip_id, paid_by, paid_to, amount, note))
        settlement_id = cur.lastrowid
        conn.commit()
        return jsonify({
            "id": settlement_id, "trip_id": trip_id,
            "paid_by": paid_by, "paid_to": paid_to,
            "amount": format(amount, ".2f"), "note": note,
            "message": "Settlement recorded",
        }), 201
    except Error as exc:
        conn.rollback()
        return fail(str(exc), 500)
    finally:
        cur.close()
        conn.close()


@app.get("/api/trips/<int:trip_id>/settlements")
def get_trip_settlements(trip_id):
    try:
        trip = query_one("SELECT id FROM trips WHERE id=%s", (trip_id,))
        if not trip:
            return fail("Trip not found", 404)
        return jsonify(query_all(
            """SELECT s.id,s.trip_id,s.paid_by,p.username AS paid_by_username,
                      s.paid_to,r.username AS paid_to_username,
                      s.amount,s.note,s.created_at
               FROM settlements s
               JOIN users p ON p.id=s.paid_by
               JOIN users r ON r.id=s.paid_to
               WHERE s.trip_id=%s ORDER BY s.created_at DESC,s.id DESC""",
            (trip_id,))), 200
    except Error as exc:
        return fail(str(exc), 500)


@app.delete("/api/settlements/<int:settlement_id>")
def delete_settlement(settlement_id):
    try:
        _, count = execute("DELETE FROM settlements WHERE id=%s", (settlement_id,))
        if not count:
            return fail("Settlement not found", 404)
        return jsonify({"message": "Settlement record deleted"}), 200
    except Error as exc:
        return fail(str(exc), 500)


if __name__ == "__main__":
    app.run(host=os.getenv("FLASK_HOST", "127.0.0.1"),
            port=int(os.getenv("FLASK_PORT", "5000")),
            debug=os.getenv("FLASK_DEBUG", "false").lower() == "true")
