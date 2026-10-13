from flask import Flask, render_template, request, redirect, url_for, flash
import sqlite3
import os
from pathlib import Path
from datetime import date

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "legal-case-demo")
DB = Path(__file__).with_name("legal_management.db")


def db():
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys=ON")
    return con


def init_db():
    with db() as con:
        con.executescript("""
        CREATE TABLE IF NOT EXISTS clients(
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          name TEXT NOT NULL, phone TEXT, email TEXT, address TEXT
        );

        CREATE TABLE IF NOT EXISTS lawyers(
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          name TEXT NOT NULL, specialization TEXT NOT NULL,
          email TEXT,
          hourly_rate REAL NOT NULL DEFAULT 1000 CHECK(hourly_rate>=0)
        );

        CREATE TABLE IF NOT EXISTS case_types(
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          type_name TEXT NOT NULL UNIQUE
        );

        CREATE TABLE IF NOT EXISTS courts(
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          court_name TEXT NOT NULL, location TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS cases(
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          case_number TEXT NOT NULL UNIQUE,
          title TEXT NOT NULL,
          client_id INTEGER NOT NULL,
          case_type_id INTEGER NOT NULL,
          court_id INTEGER,
          status TEXT NOT NULL DEFAULT 'Open',
          opened_on TEXT NOT NULL,
          description TEXT,
          FOREIGN KEY(client_id) REFERENCES clients(id),
          FOREIGN KEY(case_type_id) REFERENCES case_types(id),
          FOREIGN KEY(court_id) REFERENCES courts(id)
        );

        CREATE TABLE IF NOT EXISTS assignments(
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          case_id INTEGER NOT NULL,
          lawyer_id INTEGER NOT NULL,
          assigned_on TEXT NOT NULL,
          UNIQUE(case_id,lawyer_id),
          FOREIGN KEY(case_id) REFERENCES cases(id) ON DELETE CASCADE,
          FOREIGN KEY(lawyer_id) REFERENCES lawyers(id)
        );

        CREATE TABLE IF NOT EXISTS hearings(
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          case_id INTEGER NOT NULL,
          lawyer_id INTEGER NOT NULL,
          court_room TEXT,
          hearing_date TEXT NOT NULL,
          start_time TEXT NOT NULL,
          end_time TEXT NOT NULL,
          notes TEXT,
          FOREIGN KEY(case_id) REFERENCES cases(id) ON DELETE CASCADE,
          FOREIGN KEY(lawyer_id) REFERENCES lawyers(id),
          CHECK(end_time>start_time)
        );

        CREATE TABLE IF NOT EXISTS tasks(
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          case_id INTEGER NOT NULL,
          title TEXT NOT NULL,
          due_date TEXT NOT NULL,
          status TEXT NOT NULL DEFAULT 'Pending',
          priority TEXT NOT NULL DEFAULT 'Medium',
          FOREIGN KEY(case_id) REFERENCES cases(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS documents(
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          case_id INTEGER NOT NULL,
          document_name TEXT NOT NULL,
          document_type TEXT NOT NULL,
          uploaded_on TEXT NOT NULL,
          FOREIGN KEY(case_id) REFERENCES cases(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS time_entries(
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          case_id INTEGER NOT NULL,
          lawyer_id INTEGER NOT NULL,
          work_date TEXT NOT NULL,
          hours REAL NOT NULL CHECK(hours>0),
          description TEXT NOT NULL,
          billable INTEGER NOT NULL DEFAULT 1 CHECK(billable IN (0,1)),
          FOREIGN KEY(case_id) REFERENCES cases(id) ON DELETE CASCADE,
          FOREIGN KEY(lawyer_id) REFERENCES lawyers(id)
        );

        CREATE TABLE IF NOT EXISTS expenses(
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          case_id INTEGER NOT NULL,
          expense_date TEXT NOT NULL,
          category TEXT NOT NULL,
          amount REAL NOT NULL CHECK(amount>=0),
          notes TEXT,
          FOREIGN KEY(case_id) REFERENCES cases(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS invoices(
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          invoice_number TEXT NOT NULL UNIQUE,
          case_id INTEGER NOT NULL,
          issued_on TEXT NOT NULL,
          due_date TEXT NOT NULL,
          amount REAL NOT NULL CHECK(amount>=0),
          status TEXT NOT NULL DEFAULT 'Unpaid',
          FOREIGN KEY(case_id) REFERENCES cases(id)
        );

        CREATE TABLE IF NOT EXISTS payments(
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          invoice_id INTEGER NOT NULL,
          paid_on TEXT NOT NULL,
          amount REAL NOT NULL CHECK(amount>0),
          method TEXT NOT NULL,
          FOREIGN KEY(invoice_id) REFERENCES invoices(id) ON DELETE CASCADE
        );
        """)

        if con.execute("SELECT COUNT(*) FROM case_types").fetchone()[0] == 0:
            con.executemany(
                "INSERT INTO case_types(type_name) VALUES(?)",
                [
                    ("Civil",), ("Criminal",), ("Corporate",),
                    ("Family",), ("Property",)
                ]
            )

        if con.execute("SELECT COUNT(*) FROM courts").fetchone()[0] == 0:
            con.executemany(
                "INSERT INTO courts(court_name,location) VALUES(?,?)",
                [
                    ("District Court", "Hyderabad"),
                    ("High Court", "Hyderabad"),
                    ("Family Court", "Hyderabad")
                ]
            )

        if con.execute("SELECT COUNT(*) FROM clients").fetchone()[0] == 0:
            con.executemany(
                "INSERT INTO clients(name,phone,email,address) VALUES(?,?,?,?)",
                [
                    ("Aarav Mehta", "9876501234",
                     "aarav@example.com", "Hyderabad"),
                    ("Meera Reddy", "9876502345",
                     "meera@example.com", "Secunderabad"),
                    ("Northstar Traders", "9876503456",
                     "legal@northstar.example", "Hyderabad")
                ]
            )

        if con.execute("SELECT COUNT(*) FROM lawyers").fetchone()[0] == 0:
            con.executemany(
                """INSERT INTO lawyers(name,specialization,email,hourly_rate)
                   VALUES(?,?,?,?)""",
                [
                    ("Adv. Kavya Rao", "Civil Litigation",
                     "kavya@example.com", 2500),
                    ("Adv. Arjun Shah", "Corporate Law",
                     "arjun@example.com", 3000),
                    ("Adv. Nisha Menon", "Family Law",
                     "nisha@example.com", 2200)
                ]
            )

        if con.execute("SELECT COUNT(*) FROM cases").fetchone()[0] == 0:
            con.executemany(
                """INSERT INTO cases(
                    case_number,title,client_id,case_type_id,court_id,
                    status,opened_on,description
                ) VALUES(?,?,?,?,?,?,?,?)""",
                [
                    ("LC-2026-001", "Property boundary dispute",
                     1, 5, 1, "Open", "2026-09-10",
                     "Property boundary and title review."),
                    ("LC-2026-002", "Commercial supply agreement",
                     3, 3, 2, "In Progress", "2026-09-18",
                     "Contract interpretation and supply dispute."),
                    ("LC-2026-003", "Family settlement petition",
                     2, 4, 3, "Open", "2026-10-01",
                     "Settlement and petition preparation.")
                ]
            )

        if con.execute("SELECT COUNT(*) FROM assignments").fetchone()[0] == 0:
            con.executemany(
                "INSERT INTO assignments(case_id,lawyer_id,assigned_on) VALUES(?,?,?)",
                [
                    (1, 1, "2026-09-10"),
                    (2, 2, "2026-09-18"),
                    (3, 3, "2026-10-01")
                ]
            )

        if con.execute("SELECT COUNT(*) FROM hearings").fetchone()[0] == 0:
            con.executemany(
                """INSERT INTO hearings(
                    case_id,lawyer_id,court_room,hearing_date,
                    start_time,end_time,notes
                ) VALUES(?,?,?,?,?,?,?)""",
                [
                    (1, 1, "Courtroom 4", "2026-10-20",
                     "10:00", "10:45", "Submit title documents."),
                    (2, 2, "Courtroom 2", "2026-10-22",
                     "11:00", "11:45", "Contract hearing.")
                ]
            )

        if con.execute("SELECT COUNT(*) FROM tasks").fetchone()[0] == 0:
            con.executemany(
                """INSERT INTO tasks(case_id,title,due_date,status,priority)
                   VALUES(?,?,?,?,?)""",
                [
                    (1, "Collect property records", "2026-10-16",
                     "Pending", "High"),
                    (2, "Review contract clauses", "2026-10-18",
                     "In Progress", "High"),
                    (3, "Prepare petition draft", "2026-10-19",
                     "Pending", "Medium")
                ]
            )

        if con.execute("SELECT COUNT(*) FROM time_entries").fetchone()[0] == 0:
            con.executemany(
                """INSERT INTO time_entries(
                    case_id,lawyer_id,work_date,hours,description,billable
                ) VALUES(?,?,?,?,?,?)""",
                [
                    (1, 1, "2026-10-05", 2.5,
                     "Review of title documents", 1),
                    (2, 2, "2026-10-06", 1.5,
                     "Contract review", 1)
                ]
            )

        if con.execute("SELECT COUNT(*) FROM expenses").fetchone()[0] == 0:
            con.executemany(
                """INSERT INTO expenses(
                    case_id,expense_date,category,amount,notes
                ) VALUES(?,?,?,?,?)""",
                [
                    (1, "2026-10-05", "Document copies",
                     450, "Certified copies"),
                    (2, "2026-10-06", "Travel", 800, "Court visit")
                ]
            )

        if con.execute("SELECT COUNT(*) FROM invoices").fetchone()[0] == 0:
            con.executemany(
                """INSERT INTO invoices(
                    invoice_number,case_id,issued_on,due_date,amount,status
                ) VALUES(?,?,?,?,?,?)""",
                [
                    ("INV-2026-001", 1, "2026-10-06",
                     "2026-10-20", 6700, "Unpaid"),
                    ("INV-2026-002", 2, "2026-10-07",
                     "2026-10-21", 4500, "Partially Paid")
                ]
            )

        if con.execute("SELECT COUNT(*) FROM payments").fetchone()[0] == 0:
            con.execute(
                """INSERT INTO payments(invoice_id,paid_on,amount,method)
                   VALUES(2,'2026-10-10',1500,'UPI')"""
            )


init_db()


@app.route("/")
def dashboard():
    with db() as con:
        stats = {
            "clients": con.execute(
                "SELECT COUNT(*) FROM clients"
            ).fetchone()[0],
            "cases": con.execute(
                "SELECT COUNT(*) FROM cases"
            ).fetchone()[0],
            "hearings": con.execute(
                "SELECT COUNT(*) FROM hearings WHERE hearing_date>=?",
                (date.today().isoformat(),)
            ).fetchone()[0],
            "unpaid": con.execute("""
                SELECT COALESCE(
                    SUM(i.amount-COALESCE(p.paid,0)),0
                )
                FROM invoices i
                LEFT JOIN (
                    SELECT invoice_id,SUM(amount) paid
                    FROM payments GROUP BY invoice_id
                ) p ON p.invoice_id=i.id
            """).fetchone()[0]
        }

        cases = con.execute("""
            SELECT c.*, cl.name client, ct.type_name case_type, l.name lawyer
            FROM cases c
            JOIN clients cl ON cl.id=c.client_id
            JOIN case_types ct ON ct.id=c.case_type_id
            LEFT JOIN assignments a ON a.case_id=c.id
            LEFT JOIN lawyers l ON l.id=a.lawyer_id
            ORDER BY c.id DESC LIMIT 6
        """).fetchall()

        hearings = con.execute("""
            SELECT h.*, c.case_number, c.title, l.name lawyer
            FROM hearings h
            JOIN cases c ON c.id=h.case_id
            JOIN lawyers l ON l.id=h.lawyer_id
            WHERE h.hearing_date>=?
            ORDER BY h.hearing_date,h.start_time LIMIT 5
        """, (date.today().isoformat(),)).fetchall()

    return render_template(
        "dashboard.html",
        stats=stats,
        cases=cases,
        hearings=hearings
    )


@app.route("/clients", methods=["GET", "POST"])
def clients():
    with db() as con:
        if request.method == "POST":
            con.execute(
                """INSERT INTO clients(name,phone,email,address)
                   VALUES(?,?,?,?)""",
                (
                    request.form["name"].strip(),
                    request.form.get("phone", "").strip(),
                    request.form.get("email", "").strip(),
                    request.form.get("address", "").strip()
                )
            )
            flash("Client registered.", "success")
            return redirect(url_for("clients"))

        rows = con.execute(
            "SELECT * FROM clients ORDER BY name"
        ).fetchall()

    return render_template("clients.html", rows=rows)


@app.route("/lawyers", methods=["GET", "POST"])
def lawyers():
    with db() as con:
        if request.method == "POST":
            con.execute(
                """INSERT INTO lawyers(name,specialization,email,hourly_rate)
                   VALUES(?,?,?,?)""",
                (
                    request.form["name"].strip(),
                    request.form["specialization"].strip(),
                    request.form.get("email", "").strip(),
                    float(request.form["hourly_rate"])
                )
            )
            flash("Lawyer added.", "success")
            return redirect(url_for("lawyers"))

        rows = con.execute("""
            SELECT l.*, COUNT(DISTINCT a.case_id) case_count
            FROM lawyers l
            LEFT JOIN assignments a ON a.lawyer_id=l.id
            GROUP BY l.id
            ORDER BY l.name
        """).fetchall()

    return render_template("lawyers.html", rows=rows)


@app.route("/cases", methods=["GET", "POST"])
def cases():
    with db() as con:
        if request.method == "POST":
            try:
                con.execute("""
                    INSERT INTO cases(
                        case_number,title,client_id,case_type_id,court_id,
                        status,opened_on,description
                    ) VALUES(?,?,?,?,?,?,?,?)
                """, (
                    request.form["case_number"].strip().upper(),
                    request.form["title"].strip(),
                    int(request.form["client_id"]),
                    int(request.form["case_type_id"]),
                    int(request.form["court_id"])
                    if request.form.get("court_id") else None,
                    request.form["status"],
                    request.form["opened_on"],
                    request.form.get("description", "").strip()
                ))
                flash("Case registered.", "success")
            except sqlite3.IntegrityError:
                flash(
                    "Could not register case. Check that the case number "
                    "is unique and required fields are valid.",
                    "error"
                )
            return redirect(url_for("cases"))

        rows = con.execute("""
            SELECT c.*, cl.name client, ct.type_name case_type,
                   co.court_name
            FROM cases c
            JOIN clients cl ON cl.id=c.client_id
            JOIN case_types ct ON ct.id=c.case_type_id
            LEFT JOIN courts co ON co.id=c.court_id
            ORDER BY c.id DESC
        """).fetchall()

        client_list = con.execute(
            "SELECT * FROM clients ORDER BY name"
        ).fetchall()
        types = con.execute(
            "SELECT * FROM case_types ORDER BY type_name"
        ).fetchall()
        courts = con.execute(
            "SELECT * FROM courts ORDER BY court_name"
        ).fetchall()

    return render_template(
        "cases.html",
        rows=rows,
        clients=client_list,
        types=types,
        courts=courts,
        today=date.today().isoformat()
    )


@app.route("/assignments", methods=["GET", "POST"])
def assignments():
    with db() as con:
        if request.method == "POST":
            try:
                con.execute(
                    """INSERT INTO assignments(case_id,lawyer_id,assigned_on)
                       VALUES(?,?,?)""",
                    (
                        int(request.form["case_id"]),
                        int(request.form["lawyer_id"]),
                        date.today().isoformat()
                    )
                )
                flash("Lawyer assigned to case.", "success")
            except sqlite3.IntegrityError:
                flash("That lawyer is already assigned to this case.", "error")
            return redirect(url_for("assignments"))

        cases_list = con.execute(
            "SELECT id,case_number,title FROM cases ORDER BY case_number"
        ).fetchall()
        lawyers_list = con.execute(
            "SELECT * FROM lawyers ORDER BY name"
        ).fetchall()

        rows = con.execute("""
            SELECT a.id, c.case_number, c.title, l.name lawyer,
                   l.specialization, a.assigned_on
            FROM assignments a
            JOIN cases c ON c.id=a.case_id
            JOIN lawyers l ON l.id=a.lawyer_id
            ORDER BY a.id DESC
        """).fetchall()

    return render_template(
        "assignments.html",
        cases=cases_list,
        lawyers=lawyers_list,
        rows=rows
    )


@app.route("/hearings", methods=["GET", "POST"])
def hearings():
    with db() as con:
        if request.method == "POST":
            start = request.form["start_time"]
            end = request.form["end_time"]
            day = request.form["hearing_date"]
            lawyer_id = int(request.form["lawyer_id"])

            if end <= start:
                flash("End time must be after start time.", "error")
            else:
                clash = con.execute("""
                    SELECT 1 FROM hearings
                    WHERE lawyer_id=? AND hearing_date=?
                    AND start_time < ? AND end_time > ?
                """, (lawyer_id, day, end, start)).fetchone()

                if clash:
                    flash(
                        "Scheduling conflict: this lawyer already has "
                        "an overlapping hearing.",
                        "error"
                    )
                else:
                    con.execute("""
                        INSERT INTO hearings(
                            case_id,lawyer_id,court_room,hearing_date,
                            start_time,end_time,notes
                        ) VALUES(?,?,?,?,?,?,?)
                    """, (
                        int(request.form["case_id"]),
                        lawyer_id,
                        request.form.get("court_room", "").strip(),
                        day,
                        start,
                        end,
                        request.form.get("notes", "").strip()
                    ))
                    flash("Hearing scheduled.", "success")

            return redirect(url_for("hearings"))

        rows = con.execute("""
            SELECT h.*, c.case_number, c.title, l.name lawyer
            FROM hearings h
            JOIN cases c ON c.id=h.case_id
            JOIN lawyers l ON l.id=h.lawyer_id
            ORDER BY h.hearing_date,h.start_time
        """).fetchall()

        cases_list = con.execute(
            "SELECT id,case_number,title FROM cases ORDER BY case_number"
        ).fetchall()
        lawyers_list = con.execute(
            "SELECT * FROM lawyers ORDER BY name"
        ).fetchall()

    return render_template(
        "hearings.html",
        rows=rows,
        cases=cases_list,
        lawyers=lawyers_list
    )


@app.route("/tasks", methods=["GET", "POST"])
def tasks():
    with db() as con:
        if request.method == "POST":
            con.execute(
                """INSERT INTO tasks(case_id,title,due_date,status,priority)
                   VALUES(?,?,?,?,?)""",
                (
                    int(request.form["case_id"]),
                    request.form["title"].strip(),
                    request.form["due_date"],
                    request.form["status"],
                    request.form["priority"]
                )
            )
            flash("Task saved.", "success")
            return redirect(url_for("tasks"))

        rows = con.execute("""
            SELECT t.*, c.case_number, c.title case_title
            FROM tasks t
            JOIN cases c ON c.id=t.case_id
            ORDER BY
                CASE t.status
                    WHEN 'Pending' THEN 0
                    WHEN 'In Progress' THEN 1
                    ELSE 2
                END,
                t.due_date
        """).fetchall()

        cases_list = con.execute(
            "SELECT id,case_number,title FROM cases ORDER BY case_number"
        ).fetchall()

    return render_template(
        "tasks.html",
        rows=rows,
        cases=cases_list,
        today=date.today().isoformat()
    )


@app.route("/billing", methods=["GET", "POST"])
def billing():
    with db() as con:
        if request.method == "POST":
            try:
                con.execute("""
                    INSERT INTO invoices(
                        invoice_number,case_id,issued_on,due_date,amount,status
                    ) VALUES(?,?,?,?,?,'Unpaid')
                """, (
                    request.form["invoice_number"].strip().upper(),
                    int(request.form["case_id"]),
                    request.form["issued_on"],
                    request.form["due_date"],
                    float(request.form["amount"])
                ))
                flash("Invoice created.", "success")
            except sqlite3.IntegrityError:
                flash(
                    "Invoice number already exists or amount is invalid.",
                    "error"
                )
            return redirect(url_for("billing"))

        rows = con.execute("""
            SELECT i.*, c.case_number, c.title,
                   COALESCE(p.paid,0) paid,
                   i.amount-COALESCE(p.paid,0) balance
            FROM invoices i
            JOIN cases c ON c.id=i.case_id
            LEFT JOIN (
                SELECT invoice_id,SUM(amount) paid
                FROM payments GROUP BY invoice_id
            ) p ON p.invoice_id=i.id
            ORDER BY i.id DESC
        """).fetchall()

        cases_list = con.execute(
            "SELECT id,case_number,title FROM cases ORDER BY case_number"
        ).fetchall()

    return render_template(
        "billing.html",
        rows=rows,
        cases=cases_list,
        today=date.today().isoformat()
    )


@app.route("/payments", methods=["GET", "POST"])
def payments():
    with db() as con:
        if request.method == "POST":
            invoice_id = int(request.form["invoice_id"])
            amount = float(request.form["amount"])

            row = con.execute("""
                SELECT i.amount-COALESCE(SUM(p.amount),0) balance
                FROM invoices i
                LEFT JOIN payments p ON p.invoice_id=i.id
                WHERE i.id=?
                GROUP BY i.id
            """, (invoice_id,)).fetchone()

            if row is None:
                flash("Invoice not found.", "error")
            elif amount <= 0 or amount > row["balance"]:
                flash(
                    "Payment must be positive and cannot exceed "
                    "the outstanding invoice balance.",
                    "error"
                )
            else:
                con.execute("""
                    INSERT INTO payments(invoice_id,paid_on,amount,method)
                    VALUES(?,?,?,?)
                """, (
                    invoice_id,
                    request.form["paid_on"],
                    amount,
                    request.form["method"]
                ))

                new_balance = row["balance"] - amount
                con.execute(
                    "UPDATE invoices SET status=? WHERE id=?",
                    (
                        "Paid" if new_balance == 0 else "Partially Paid",
                        invoice_id
                    )
                )
                flash("Payment recorded.", "success")

            return redirect(url_for("payments"))

        invoices = con.execute("""
            SELECT i.id, i.invoice_number, c.case_number,
                   i.amount-COALESCE(p.paid,0) balance
            FROM invoices i
            JOIN cases c ON c.id=i.case_id
            LEFT JOIN (
                SELECT invoice_id,SUM(amount) paid
                FROM payments GROUP BY invoice_id
            ) p ON p.invoice_id=i.id
            WHERE i.amount-COALESCE(p.paid,0)>0
            ORDER BY i.due_date
        """).fetchall()

        rows = con.execute("""
            SELECT p.*, i.invoice_number, c.case_number
            FROM payments p
            JOIN invoices i ON i.id=p.invoice_id
            JOIN cases c ON c.id=i.case_id
            ORDER BY p.paid_on DESC
        """).fetchall()

    return render_template(
        "payments.html",
        invoices=invoices,
        rows=rows,
        today=date.today().isoformat()
    )


@app.route("/reports")
def reports():
    with db() as con:
        workload = con.execute("""
            SELECT l.name,
                   COUNT(DISTINCT a.case_id) cases,
                   COALESCE(SUM(te.hours),0) hours,
                   COALESCE(
                       SUM(
                           CASE WHEN te.billable=1
                           THEN te.hours*l.hourly_rate ELSE 0 END
                       ),0
                   ) billable_value
            FROM lawyers l
            LEFT JOIN assignments a ON a.lawyer_id=l.id
            LEFT JOIN time_entries te ON te.lawyer_id=l.id
            GROUP BY l.id
            ORDER BY cases DESC
        """).fetchall()

        statuses = con.execute(
            "SELECT status,COUNT(*) count FROM cases GROUP BY status"
        ).fetchall()

        outstanding = con.execute("""
            SELECT i.invoice_number, c.case_number, c.title, i.due_date,
                   i.amount-COALESCE(p.paid,0) balance
            FROM invoices i
            JOIN cases c ON c.id=i.case_id
            LEFT JOIN (
                SELECT invoice_id,SUM(amount) paid
                FROM payments GROUP BY invoice_id
            ) p ON p.invoice_id=i.id
            WHERE i.amount-COALESCE(p.paid,0)>0
            ORDER BY i.due_date
        """).fetchall()

        upcoming = con.execute("""
            SELECT h.hearing_date, h.start_time, c.case_number,
                   c.title, l.name lawyer
            FROM hearings h
            JOIN cases c ON c.id=h.case_id
            JOIN lawyers l ON l.id=h.lawyer_id
            WHERE h.hearing_date>=?
            ORDER BY h.hearing_date,h.start_time
        """, (date.today().isoformat(),)).fetchall()

    return render_template(
        "reports.html",
        workload=workload,
        statuses=statuses,
        outstanding=outstanding,
        upcoming=upcoming
    )


if __name__ == "__main__":
    app.run(debug=True)