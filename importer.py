import pandas as pd
from database import MONTH_ORDER, insert_rows, delete_month

# Map Excel column names → DB column names
COL_MAP = {
    "Employe Code":               "employee_code",
    "Employee Code":              "employee_code",
    "Name":                       "name",
    "Department":                 "department",
    "Designation":                "designation",
    "Status":                     "status",
    "District":                   "district",
    "City / Town":                "city",
    "City/Town":                  "city",
    "Date ( DOJ)":                "date_joined",
    "Date (DOJ)":                 "date_joined",
    "Salary":                     "salary",
    "Basic":                      "basic",
    "H-Rent":                     "house_rent",
    "Utility":                    "utility",
    "Medical":                    "medical",
    "Gross Pay":                  "gross_pay",
    "Travelling Allowance":       "travelling",
    "Accomodation Allowance":     "accommodation",
    "Accommodation Allowance":    "accommodation",
    "Working Days":               "working_days",
    "Gross Total Payable":        "gross_total",
    "I. Tax":                     "income_tax",
    "E.O.B.I":                    "eobi",
    "Leaves":                     "leaves",
    "Leave Deduction":            "leave_deduction",
    "Late Deductible":            "late_deduction",
    "Other":                      "other_deduction",
    "Total Deduction":            "total_deduction",
    "Arear":                      "arrear",
    "Reimbursement":              "reimbursement",
    "Total payable (reconcile)":  "total_payable",
}

def read_file(filepath):
    """Read Excel or CSV into DataFrame."""
    fp = str(filepath)
    if fp.endswith(".xlsx") or fp.endswith(".xls"):
        df = pd.read_excel(fp, dtype=str)
    else:
        df = pd.read_csv(fp, dtype=str)
    df.columns = [str(c).strip() for c in df.columns]
    return df

def find_net_payable_col(df):
    """Auto-detect Net Payable column (name varies by month)."""
    for col in df.columns:
        if str(col).strip().lower().startswith("net payable"):
            return col
    return None

def clean_number(val):
    """Convert string like '1,234.56' to float."""
    try:
        return float(str(val).replace(",", "").strip())
    except:
        return 0.0

def import_file(filepath, year, month):
    """
    Read Excel/CSV, map columns, insert into SQLite.
    Returns dict with counts and any warnings.
    """
    year = int(year)
    month_order = MONTH_ORDER.get(month.lower(), 99)

    df = read_file(filepath)

    # Auto-detect Net Payable column
    net_col = find_net_payable_col(df)
    if net_col:
        df.rename(columns={net_col: "Net Payable"}, inplace=True)
        COL_MAP["Net Payable"] = "net_payable"

    # Drop completely empty rows
    df.dropna(how="all", inplace=True)

    # Drop rows with no Name
    if "Name" in df.columns:
        df = df[df["Name"].astype(str).str.strip().notna()]
        df = df[df["Name"].astype(str).str.strip() != ""]
        df = df[df["Name"].astype(str).str.strip() != "nan"]

    # Drop totals row
    if "Name" in df.columns:
        df = df[~df["Name"].astype(str).str.lower().str.contains("total", na=False)]

    rows = []
    warnings = []

    for _, row in df.iterrows():
        name = str(row.get("Name", "")).strip()
        if not name or name == "nan":
            continue

        rec = {
            "year":         year,
            "month":        month,
            "month_order":  month_order,
            "employee_code": "",
            "name":         name,
            "department":   "",
            "designation":  "",
            "status":       "Active",
            "district":     "",
            "city":         "",
            "date_joined":  "",
            "salary":       0, "basic": 0, "house_rent": 0,
            "utility":      0, "medical": 0, "gross_pay": 0,
            "travelling":   0, "accommodation": 0, "working_days": 0,
            "gross_total":  0, "income_tax": 0, "eobi": 0,
            "leaves":       0, "leave_deduction": 0, "late_deduction": 0,
            "other_deduction": 0, "total_deduction": 0,
            "net_payable":  0, "arrear": 0, "reimbursement": 0,
            "total_payable": 0,
        }

        for excel_col, db_col in COL_MAP.items():
            if excel_col in df.columns:
                val = row.get(excel_col, "")
                if db_col in ["employee_code","name","department",
                              "designation","status","district",
                              "city","date_joined"]:
                    rec[db_col] = str(val).strip() if str(val).strip() != "nan" else ""
                else:
                    rec[db_col] = clean_number(val)

        rows.append(rec)

    # Check if month already exists
    from database import month_exists
    existed = month_exists(year, month)

    # Delete existing month data then insert fresh
    delete_month(year, month)
    insert_rows(rows)

    return {
        "rows_imported": len(rows),
        "year":          year,
        "month":         month,
        "overwritten":   existed,
        "warnings":      warnings,
    }
