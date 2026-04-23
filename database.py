import sqlite3
from pathlib import Path

# DB file sits next to this script — always found automatically
# DB_PATH is now dynamic — set by year_manager
# Use get_db_path() from year_manager to get current path
from year_manager import get_active_year

def get_db_path_dynamic():
    return Path(get_active_year()["db_path"])

# Keep for backward compat
DB_PATH = Path(__file__).resolve().parent / "payroll.db"

MONTH_ORDER = {
    "january":1,"february":2,"march":3,"april":4,
    "may":5,"june":6,"july":7,"august":8,
    "september":9,"october":10,"november":11,"december":12
}

PAYROLL_COLUMNS = [
    "year", "month", "month_order",
    "employee_code", "name", "department", "designation", "status",
    "district", "city", "date_joined",
    "salary", "basic", "house_rent", "utility", "medical",
    "gross_pay", "travelling", "accommodation", "working_days",
    "gross_total", "income_tax", "eobi", "leaves",
    "leave_deduction", "late_deduction", "other_deduction",
    "total_deduction", "net_payable", "arrear",
    "reimbursement", "total_payable",
]

def get_conn():
    from pathlib import Path as _Path
    db = get_db_path_dynamic()
    # Ensure parent directory exists
    _Path(db).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db))
    conn.row_factory = sqlite3.Row
    return conn

def _create_payroll_table(conn, table_name="payroll"):
    conn.execute(f"""
        CREATE TABLE IF NOT EXISTS {table_name} (
            id                INTEGER PRIMARY KEY AUTOINCREMENT,

            -- Period
            year              INTEGER NOT NULL,
            month             TEXT    NOT NULL,
            month_order       INTEGER NOT NULL,

            -- Employee identity
            employee_code     TEXT    NOT NULL DEFAULT '',
            name              TEXT    NOT NULL,
            department        TEXT,
            designation       TEXT,
            status            TEXT,
            district          TEXT,
            city              TEXT,
            date_joined       TEXT,

            -- Pay components (stored for future reports)
            salary            REAL DEFAULT 0,
            basic             REAL DEFAULT 0,
            house_rent        REAL DEFAULT 0,
            utility           REAL DEFAULT 0,
            medical           REAL DEFAULT 0,
            gross_pay         REAL DEFAULT 0,
            travelling        REAL DEFAULT 0,
            accommodation     REAL DEFAULT 0,
            working_days      REAL DEFAULT 0,

            -- Core payroll figures (payslips + reports)
            gross_total       REAL DEFAULT 0,
            income_tax        REAL DEFAULT 0,
            eobi              REAL DEFAULT 0,
            leaves            REAL DEFAULT 0,
            leave_deduction   REAL DEFAULT 0,
            late_deduction    REAL DEFAULT 0,
            other_deduction   REAL DEFAULT 0,
            total_deduction   REAL DEFAULT 0,
            net_payable       REAL DEFAULT 0,
            arrear            REAL DEFAULT 0,
            reimbursement     REAL DEFAULT 0,
            total_payable     REAL DEFAULT 0,

            UNIQUE(year, month, employee_code, name)
        )
    """)

def _has_legacy_unique_name_constraint(conn):
    row = conn.execute(
        "SELECT sql FROM sqlite_master WHERE type='table' AND name='payroll'"
    ).fetchone()
    if not row or not row[0]:
        return False
    compact = "".join(str(row[0]).lower().split())
    return (
        "unique(year,month,name)" in compact
        and "unique(year,month,employee_code,name)" not in compact
    )

def _migrate_legacy_payroll_schema(conn):
    column_csv = ", ".join(PAYROLL_COLUMNS)
    conn.execute("BEGIN")
    conn.execute("DROP TABLE IF EXISTS payroll_new")
    _create_payroll_table(conn, "payroll_new")
    conn.execute(f"""
        INSERT INTO payroll_new ({column_csv})
        SELECT
            year, month, month_order,
            COALESCE(employee_code, ''), name, department, designation, status,
            district, city, date_joined,
            salary, basic, house_rent, utility, medical,
            gross_pay, travelling, accommodation, working_days,
            gross_total, income_tax, eobi, leaves,
            leave_deduction, late_deduction, other_deduction,
            total_deduction, net_payable, arrear,
            reimbursement, total_payable
        FROM payroll
    """)
    conn.execute("DROP TABLE payroll")
    conn.execute("ALTER TABLE payroll_new RENAME TO payroll")
    conn.commit()

def init_db(db_path=None):
    """Create table if it doesn't exist."""
    from pathlib import Path as _Path
    if db_path:
        _Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(db_path))
        conn.row_factory = sqlite3.Row
    else:
        conn = get_conn()
    _create_payroll_table(conn)
    conn.commit()
    if _has_legacy_unique_name_constraint(conn):
        _migrate_legacy_payroll_schema(conn)
    conn.commit()
    conn.close()

# ── Import ─────────────────────────────────────────────────────────────────────
def delete_month(year, month):
    """Remove all rows for a given year/month before re-import."""
    conn = get_conn()
    conn.execute("DELETE FROM payroll WHERE year=? AND month=?", (year, month))
    conn.commit()
    conn.close()

def insert_rows(rows):
    """Insert list of dicts into payroll table."""
    conn = get_conn()
    conn.executemany("""
        INSERT OR REPLACE INTO payroll (
            year, month, month_order,
            employee_code, name, department, designation, status,
            district, city, date_joined,
            salary, basic, house_rent, utility, medical,
            gross_pay, travelling, accommodation, working_days,
            gross_total, income_tax, eobi, leaves,
            leave_deduction, late_deduction, other_deduction,
            total_deduction, net_payable, arrear,
            reimbursement, total_payable
        ) VALUES (
            :year, :month, :month_order,
            :employee_code, :name, :department, :designation, :status,
            :district, :city, :date_joined,
            :salary, :basic, :house_rent, :utility, :medical,
            :gross_pay, :travelling, :accommodation, :working_days,
            :gross_total, :income_tax, :eobi, :leaves,
            :leave_deduction, :late_deduction, :other_deduction,
            :total_deduction, :net_payable, :arrear,
            :reimbursement, :total_payable
        )
    """, rows)
    conn.commit()
    conn.close()

# ── Queries ────────────────────────────────────────────────────────────────────
def get_months():
    """Return list of distinct year/month combinations loaded."""
    conn = get_conn()
    rows = conn.execute("""
        SELECT year, month, month_order,
               COUNT(*) as employee_count,
               SUM(net_payable) as total_net,
               SUM(total_payable) as total_pay
        FROM payroll
        GROUP BY year, month, month_order
        ORDER BY year, month_order
    """).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_payroll(year, month):
    """All employees for a given month."""
    conn = get_conn()
    rows = conn.execute("""
        SELECT * FROM payroll
        WHERE year=? AND month=?
        ORDER BY name
    """, (year, month)).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_payroll_totals(year, month):
    """Column totals for a given month."""
    conn = get_conn()
    row = conn.execute("""
        SELECT
            COUNT(*) as employee_count,
            SUM(gross_total) as gross_total,
            SUM(income_tax) as income_tax,
            SUM(eobi) as eobi,
            SUM(leave_deduction) as leave_deduction,
            SUM(late_deduction) as late_deduction,
            SUM(other_deduction) as other_deduction,
            SUM(total_deduction) as total_deduction,
            SUM(net_payable) as net_payable,
            SUM(arrear) as arrear,
            SUM(reimbursement) as reimbursement,
            SUM(total_payable) as total_payable
        FROM payroll WHERE year=? AND month=?
    """, (year, month)).fetchone()
    conn.close()
    return dict(row) if row else {}

def get_all_employees():
    """Distinct employee names across all months."""
    conn = get_conn()
    rows = conn.execute("""
        SELECT DISTINCT name, employee_code, department, designation
        FROM payroll ORDER BY name
    """).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_employee_history(name):
    """All months for one employee — for account view."""
    conn = get_conn()
    rows = conn.execute("""
        SELECT * FROM payroll
        WHERE name=?
        ORDER BY year, month_order
    """, (name,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_employee_ytd(name, year, up_to_month_order):
    """YTD totals for one employee up to a given month — ALL columns."""
    conn = get_conn()
    row = conn.execute("""
        SELECT
            SUM(salary)           as salary,
            SUM(basic)            as basic,
            SUM(house_rent)       as house_rent,
            SUM(utility)          as utility,
            SUM(medical)          as medical,
            SUM(gross_pay)        as gross_pay,
            SUM(travelling)       as travelling,
            SUM(accommodation)    as accommodation,
            SUM(working_days)     as working_days,
            SUM(gross_total)      as gross_total,
            SUM(income_tax)       as income_tax,
            SUM(eobi)             as eobi,
            SUM(leaves)           as leaves,
            SUM(leave_deduction)  as leave_deduction,
            SUM(late_deduction)   as late_deduction,
            SUM(other_deduction)  as other_deduction,
            SUM(total_deduction)  as total_deduction,
            SUM(net_payable)      as net_payable,
            SUM(arrear)           as arrear,
            SUM(reimbursement)    as reimbursement,
            SUM(total_payable)    as total_payable
        FROM payroll
        WHERE name=? AND year=? AND month_order<=?
    """, (name, year, up_to_month_order)).fetchone()
    conn.close()
    return dict(row) if row else {}

def get_dashboard_stats():
    """Summary stats for dashboard."""
    conn = get_conn()
    stats = {}
    r = conn.execute("SELECT COUNT(DISTINCT year||month) FROM payroll").fetchone()
    stats["months_loaded"] = r[0] if r else 0
    r = conn.execute("SELECT COUNT(DISTINCT name) FROM payroll").fetchone()
    stats["total_employees"] = r[0] if r else 0
    # Latest month
    r = conn.execute("""
        SELECT year, month, month_order FROM payroll
        ORDER BY year DESC, month_order DESC LIMIT 1
    """).fetchone()
    if r:
        stats["latest_month"] = f"{r['month']} {r['year']}"
        stats["latest_year"]  = r["year"]
        stats["latest_month_name"] = r["month"]
        r2 = conn.execute("""
            SELECT SUM(net_payable) as net, SUM(total_payable) as total,
                   COUNT(*) as emp
            FROM payroll WHERE year=? AND month=?
        """, (r["year"], r["month"])).fetchone()
        stats["latest_net"]   = r2["net"] or 0
        stats["latest_total"] = r2["total"] or 0
        stats["latest_emp"]   = r2["emp"] or 0
    else:
        stats["latest_month"] = "—"
        stats["latest_net"]   = 0
        stats["latest_total"] = 0
        stats["latest_emp"]   = 0
    conn.close()
    return stats

def month_exists(year, month):
    conn = get_conn()
    r = conn.execute(
        "SELECT COUNT(*) FROM payroll WHERE year=? AND month=?",
        (year, month)
    ).fetchone()
    conn.close()
    return r[0] > 0
