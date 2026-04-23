"""
Year Manager — handles multiple financial year databases.
Pakistan FY: July → June  e.g. FY2025-26
Each year has its own DB file: FY2025-26.db
"""
import json, zipfile, shutil
from pathlib import Path
from datetime import datetime
import re
from runtime_paths import DATA_DIR

BASE_DIR     = DATA_DIR
BACKUPS_DIR  = BASE_DIR / "backups"
ACTIVE_FILE  = BASE_DIR / "active_year.json"

# Ensure folders exist on import
BACKUPS_DIR.mkdir(parents=True, exist_ok=True)
(BASE_DIR / "tmp").mkdir(parents=True, exist_ok=True)

# ── Helpers ────────────────────────────────────────────────────────────────────
def get_fy_label(start_year: int) -> str:
    """e.g. 2025 → 'FY2025-26'"""
    return f"FY{start_year}-{str(start_year+1)[-2:]}"

def get_db_path(fy_label: str) -> Path:
    return BASE_DIR / f"{fy_label}.db"

def current_fy_start() -> int:
    """Return the start year of the current Pakistan FY."""
    now = datetime.now()
    return now.year if now.month >= 7 else now.year - 1

# ── Active Year ────────────────────────────────────────────────────────────────
def get_active_year() -> dict:
    """Return active year info. Defaults to current FY if not set."""
    if ACTIVE_FILE.exists():
        try:
            data = json.loads(ACTIVE_FILE.read_text())
            # Always resolve db_path to absolute path on this machine
            label = data.get("label", "")
            if label:
                data["db_path"] = str(get_db_path(label))
                save_active_year(data)
            return data
        except Exception:
            pass
    # Default: current FY
    start = current_fy_start()
    label = get_fy_label(start)
    data  = {"label": label, "start_year": start,
             "db_path": str(get_db_path(label))}
    save_active_year(data)
    return data

def save_active_year(data: dict):
    ACTIVE_FILE.write_text(json.dumps(data, indent=2))

def set_active_year(fy_label: str) -> dict:
    """Switch active year. Returns new active year dict."""
    start = int(fy_label.replace("FY","").split("-")[0])
    data  = {"label": fy_label, "start_year": start,
             "db_path": str(get_db_path(fy_label))}
    save_active_year(data)
    return data

def is_current_year(fy_label: str) -> bool:
    """Is this the current (most recent) FY?"""
    return fy_label == get_fy_label(current_fy_start())

# ── Year Discovery ─────────────────────────────────────────────────────────────
def get_all_years() -> list:
    """Return all FY DB files found, sorted newest first."""
    years = []
    for db in BASE_DIR.glob("FY*.db"):
        label = db.stem  # e.g. FY2025-26
        try:
            start = int(label.replace("FY","").split("-")[0])
            years.append({
                "label":      label,
                "start_year": start,
                "db_path":    str(db),
                "size_kb":    round(db.stat().st_size / 1024, 1),
                "modified":   datetime.fromtimestamp(
                                db.stat().st_mtime).strftime("%d/%m/%Y %H:%M"),
                "is_current": is_current_year(label),
            })
        except Exception:
            pass
    # Also include legacy payroll.db if exists (rename it)
    legacy = BASE_DIR / "payroll.db"
    if legacy.exists():
        label = get_fy_label(current_fy_start())
        target = get_db_path(label)
        if not target.exists():
            shutil.copy(str(legacy), str(target))
    return sorted(years, key=lambda x: x["start_year"], reverse=True)

# ── Create New Year ────────────────────────────────────────────────────────────
def create_new_year(start_year: int) -> dict:
    """Create a new empty FY database. Returns year info."""
    label   = get_fy_label(start_year)
    db_path = get_db_path(label)
    if db_path.exists():
        raise ValueError(f"{label} already exists.")
    # Init empty DB
    import sqlite3
    conn = sqlite3.connect(db_path)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS payroll (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            year INTEGER NOT NULL, month TEXT NOT NULL,
            month_order INTEGER NOT NULL,
            employee_code TEXT NOT NULL DEFAULT '', name TEXT NOT NULL,
            department TEXT, designation TEXT, status TEXT,
            district TEXT, city TEXT, date_joined TEXT,
            salary REAL DEFAULT 0, basic REAL DEFAULT 0,
            house_rent REAL DEFAULT 0, utility REAL DEFAULT 0,
            medical REAL DEFAULT 0, gross_pay REAL DEFAULT 0,
            travelling REAL DEFAULT 0, accommodation REAL DEFAULT 0,
            working_days REAL DEFAULT 0, gross_total REAL DEFAULT 0,
            income_tax REAL DEFAULT 0, eobi REAL DEFAULT 0,
            leaves REAL DEFAULT 0, leave_deduction REAL DEFAULT 0,
            late_deduction REAL DEFAULT 0, other_deduction REAL DEFAULT 0,
            total_deduction REAL DEFAULT 0, net_payable REAL DEFAULT 0,
            arrear REAL DEFAULT 0, reimbursement REAL DEFAULT 0,
            total_payable REAL DEFAULT 0,
            UNIQUE(year, month, employee_code, name)
        )
    """)
    conn.commit()
    conn.close()
    return set_active_year(label)

# ── Backup & Restore ───────────────────────────────────────────────────────────
def backup_year(fy_label: str) -> str:
    """Zip the year's DB into backups folder. Returns zip path."""
    db_path = get_db_path(fy_label)
    if not db_path.exists():
        raise FileNotFoundError(f"Database not found: {db_path}")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    zip_name  = f"{fy_label}_backup_{timestamp}.zip"
    zip_path  = BACKUPS_DIR / zip_name
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.write(db_path, db_path.name)
    return str(zip_path)

def restore_year(zip_path: str) -> str:
    """Restore a DB from a backup zip. Returns FY label restored."""
    with zipfile.ZipFile(zip_path, "r") as zf:
        names = zf.namelist()
        db_names = []
        for n in names:
            p = Path(n)
            if p.name != n:
                continue
            if p.suffix.lower() != ".db":
                continue
            if not re.fullmatch(r"FY\d{4}-\d{2}\.db", p.name):
                continue
            db_names.append(p.name)
        if not db_names:
            raise ValueError("No valid FY database found in zip.")
        db_name = db_names[0]
        # Backup existing before overwriting
        target = BASE_DIR / db_name
        if target.exists():
            backup_year(target.stem)
        with zf.open(db_name) as src, open(target, "wb") as dst:
            shutil.copyfileobj(src, dst)
    return Path(db_name).stem

def get_backups() -> list:
    """List all backup zips."""
    backups = []
    for zf in sorted(BACKUPS_DIR.glob("*.zip"), reverse=True):
        backups.append({
            "name":     zf.name,
            "path":     str(zf),
            "size_kb":  round(zf.stat().st_size / 1024, 1),
            "created":  datetime.fromtimestamp(
                          zf.stat().st_mtime).strftime("%d/%m/%Y %H:%M"),
        })
    return backups
