from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, send_file as flask_send_file, session
from pathlib import Path
from urllib.parse import quote
from uuid import uuid4
from werkzeug.utils import secure_filename
import os, json
# Auth removed — single user installation
from year_manager import (get_active_year, set_active_year, get_all_years,
                          create_new_year, backup_year, restore_year,
                          get_backups, is_current_year, get_fy_label)
from license_manager import is_eula_accepted, accept_eula, EULA_TEXT
from document_generator import generate_agreement, generate_help_manual
from company_config import COMPANY_INFO, SOFTWARE_INFO

from database import (
    init_db, get_dashboard_stats, get_months,
    get_payroll, get_payroll_totals,
    get_all_employees, get_employee_history, get_employee_ytd,
    MONTH_ORDER, month_exists
)
from importer import import_file

app = Flask(__name__)
app.secret_key = "pef_payroll_2026_secure"
app.config["SESSION_TYPE"] = "filesystem"

BASE_DIR   = Path(__file__).resolve().parent
UPLOAD_TMP = BASE_DIR / "tmp"
UPLOAD_TMP.mkdir(exist_ok=True)

PAYSLIPS_DIR = BASE_DIR / "payslips"
PAYSLIPS_DIR.mkdir(exist_ok=True)

MONTHS_LIST = [
    "January","February","March","April","May","June",
    "July","August","September","October","November","December"
]

ALLOWED_IMPORT_EXTENSIONS = {".xlsx", ".xls", ".csv"}


CONFIG_FILE = BASE_DIR / "config.json"

# ── Ensure required folders exist ─────────────────────────────────────────────
for _folder in ["backups", "archive", "agreements", "tmp"]:
    (BASE_DIR / _folder).mkdir(exist_ok=True)

def get_tax_year():
    """Load tax year from config.json — changeable without code edit."""
    if CONFIG_FILE.exists():
        try:
            return json.loads(CONFIG_FILE.read_text()).get("tax_year","2025-2026")
        except Exception:
            pass
    return "2025-2026"

def save_tax_year(tax_year: str):
    CONFIG_FILE.write_text(json.dumps({"tax_year": tax_year}, indent=2))

def get_company():
    """Returns company info — name/region from company_config.py, tax_year from config.json."""
    info = dict(COMPANY_INFO)
    info["tax_year"] = get_tax_year()
    return info

# ── Runtime state (resets on every app start) ─────────────────────────────────
_reminder_shown = False  # Shows once per app start

# ── Context processor — injects into all templates ────────────────────────────
@app.context_processor
def inject_globals():
    return {
        "active_year":    get_active_year(),
        "current_user":   None,
        "all_years_list": get_all_years(),
        "get_fy_label":   get_fy_label,
        "company":        get_company(),
        "software":       SOFTWARE_INFO,
    }

@app.template_filter("urlencode")
def urlencode_filter(s):
    return quote(str(s))

@app.template_filter("fmt")
def fmt_filter(v):
    try:
        return f"{float(v):,.0f}"
    except:
        return "0"

# ── Dashboard ──────────────────────────────────────────────────────────────────
@app.route("/")
def dashboard():
    if not is_eula_accepted():
        return redirect(url_for("eula"))
    global _reminder_shown
    stats      = get_dashboard_stats()
    months     = get_months()
    company    = get_company()
    show_reminder = not _reminder_shown
    return render_template("dashboard.html",
                           stats=stats, months=months, company=company,
                           show_reminder=show_reminder)

# ── Import ─────────────────────────────────────────────────────────────────────
def detect_year_month(filename):
    """
    Auto-detect year and month from filename.
    Supports: 2025-04_Apr.xlsx, 2026-02_Feb.xlsx, 2025-04_April.xlsx
    Returns (year_str, month_str) or ("", "")
    """
    from database import MONTH_ORDER
    MONTH_FULL = {
        "jan":"January","feb":"February","mar":"March","apr":"April",
        "may":"May","jun":"June","jul":"July","aug":"August",
        "sep":"September","oct":"October","nov":"November","dec":"December",
        "january":"January","february":"February","march":"March","april":"April",
        "june":"June","july":"July","august":"August","september":"September",
        "october":"October","november":"November","december":"December"
    }
    stem = Path(filename).stem  # e.g. 2025-04_Apr
    parts = stem.split("_")
    if len(parts) >= 2:
        date_part  = parts[0]          # 2025-04
        month_part = parts[1].lower()  # apr
        dp = date_part.split("-")
        if len(dp) >= 1 and dp[0].isdigit():
            year = dp[0]
            month = MONTH_FULL.get(month_part, "")
            if month:
                return year, month
    return "", ""

@app.route("/import", methods=["GET","POST"])
def import_page():
    company = get_company()
    result  = None
    detected = {"year": "", "month": ""}

    if request.method == "POST":
        year  = request.form.get("year", "").strip()
        month = request.form.get("month", "").strip()
        f     = request.files.get("file")

        if not f or not f.filename:
            flash("Please choose a file.", "error")
        else:
            safe_filename = secure_filename(Path(f.filename).name)
            if not safe_filename:
                flash("Invalid file name.", "error")
                years  = list(range(2020, 2031))
                months = get_months()
                return render_template("import.html", company=company,
                                       months_list=MONTHS_LIST, years=years,
                                       months=months, result=result, detected=detected)
            ext = Path(safe_filename).suffix.lower()
            if ext not in ALLOWED_IMPORT_EXTENSIONS:
                flash("Please upload a valid Excel or CSV file.", "error")
                years  = list(range(2020, 2031))
                months = get_months()
                return render_template("import.html", company=company,
                                       months_list=MONTHS_LIST, years=years,
                                       months=months, result=result, detected=detected)
            # Auto-detect from filename if not manually set
            det_year, det_month = detect_year_month(safe_filename)
            if not year:  year  = det_year
            if not month: month = det_month

            if not year or not month:
                flash(
                    "Could not detect year/month from filename. "
                    "Please select manually or rename file to format: 2025-04_Apr.xlsx",
                    "error"
                )
            else:
                tmp_path = UPLOAD_TMP / f"{uuid4().hex}_{safe_filename}"
                f.save(tmp_path)
                try:
                    result = import_file(tmp_path, year, month)
                    flash(
                        f"✅ {result['rows_imported']} employees imported for "
                        f"{month} {year}" +
                        (" (previous data replaced)" if result["overwritten"] else " (new month added)"),
                        "success"
                    )
                except Exception as e:
                    flash(f"❌ Import failed: {str(e)}", "error")
                finally:
                    if tmp_path.exists():
                        os.remove(tmp_path)

    years  = list(range(2020, 2031))
    months = get_months()
    return render_template("import.html", company=company,
                           months_list=MONTHS_LIST, years=years,
                           months=months, result=result, detected=detected)

@app.route("/delete_month", methods=["POST"])
def delete_month_route():
    """Delete all rows for a given year/month."""
    from database import delete_month
    year  = request.form.get("year", "")
    month = request.form.get("month", "")
    if year and month:
        delete_month(int(year), month)
        flash(f"🗑 {month} {year} data deleted successfully.", "success")
    else:
        flash("Could not delete — year/month missing.", "error")
    return redirect(url_for("import_page"))

# ── Payroll Register ───────────────────────────────────────────────────────────
@app.route("/payroll")
def payroll():
    company   = get_company()
    months    = get_months()
    sel_year  = request.args.get("year", "")
    sel_month = request.args.get("month", "")

    # Default to latest month
    if not sel_year and months:
        sel_year  = str(months[-1]["year"])
        sel_month = months[-1]["month"]

    employees = []
    totals    = {}
    if sel_year and sel_month:
        employees = get_payroll(int(sel_year), sel_month)
        totals    = get_payroll_totals(int(sel_year), sel_month)

    return render_template("payroll.html", company=company,
                           months=months, employees=employees,
                           totals=totals, sel_year=sel_year,
                           sel_month=sel_month)

# ── Employee Account ───────────────────────────────────────────────────────────
@app.route("/employee")
def employee():
    company      = get_company()
    all_employees = get_all_employees()
    sel_name     = request.args.get("name", "")
    emp_data     = []
    ytd_map      = {}

    if sel_name:
        emp_data = get_employee_history(sel_name)
        # Build YTD for each row
        for row in emp_data:
            key = f"{row['year']}_{row['month_order']}"
            ytd = get_employee_ytd(sel_name, row["year"], row["month_order"])
            ytd_map[key] = ytd

    return render_template("employee.html", company=company,
                           all_employees=all_employees,
                           sel_name=sel_name,
                           emp_data=emp_data,
                           ytd_map=ytd_map)

# ── Payslips ───────────────────────────────────────────────────────────────────
@app.route("/payslips")
def payslips():
    company   = get_company()
    months    = get_months()
    all_emp   = get_all_employees()
    sel_year  = request.args.get("year", "")
    sel_month = request.args.get("month", "")
    # Distinct years and months for dropdowns
    years_avail  = sorted(set(m["year"]  for m in months), reverse=True)
    months_avail = months  # full list for month dropdown (already distinct per year/month combo)
    return render_template("payslips.html", company=company,
                           months=months, all_employees=all_emp,
                           months_list=MONTHS_LIST,
                           years_avail=years_avail,
                           sel_year=sel_year, sel_month=sel_month)

@app.route("/payslips/preview")
def payslip_preview():
    """HTML preview — single employee, one month / range / full year."""
    from database import get_payroll, get_employee_ytd, get_employee_history, MONTH_ORDER
    company    = get_company()
    year       = request.args.get("year","")
    month      = request.args.get("month","")
    emp_name   = request.args.get("emp_name","")
    mode       = request.args.get("mode","single")   # single / range / year
    from_month = request.args.get("from_month","")
    to_month   = request.args.get("to_month","")

    slips = []

    # ── All employees — one month ──────────────────────────────────────────
    if mode == "all":
        if not month:
            flash("Please select a month.", "error")
            return redirect(url_for("payslips"))
        employees = get_payroll(int(year), month)
        if not employees:
            flash(f"No employees found for {month} {year}.", "error")
            return redirect(url_for("payslips"))
        mo = MONTH_ORDER.get(month.lower(), 12)
        for emp in employees:
            ytd = get_employee_ytd(emp["name"], int(year), mo)
            slips.append({"emp": emp, "ytd": ytd,
                          "month": month, "year": year})
        emp_name = f"All Employees — {month} {year}"

    # ── Single — date range ────────────────────────────────────────────────
    elif mode == "range" and from_month and to_month:
        if not emp_name:
            flash("Please select an employee.", "error")
            return redirect(url_for("payslips"))
        from_order = MONTH_ORDER.get(from_month.lower(), 1)
        to_order   = MONTH_ORDER.get(to_month.lower(), 12)
        history    = get_employee_history(emp_name)
        history    = [r for r in history
                      if str(r["year"]) == str(year)
                      and from_order <= r["month_order"] <= to_order]
        for row in history:
            ytd = get_employee_ytd(emp_name, int(year), row["month_order"])
            slips.append({"emp": row, "ytd": ytd,
                          "month": row["month"], "year": year})

    # ── Single — full year ─────────────────────────────────────────────────
    elif mode == "year":
        if not emp_name:
            flash("Please select an employee.", "error")
            return redirect(url_for("payslips"))
        history = get_employee_history(emp_name)
        history = [r for r in history if str(r["year"]) == str(year)]
        for row in history:
            ytd = get_employee_ytd(emp_name, int(year), row["month_order"])
            slips.append({"emp": row, "ytd": ytd,
                          "month": row["month"], "year": year})

    # ── Single — one month (default) ───────────────────────────────────────
    else:
        if not emp_name or not month:
            flash("Please select employee and month.", "error")
            return redirect(url_for("payslips"))
        employees = get_payroll(int(year), month)
        emp = next((e for e in employees if e["name"] == emp_name), None)
        if not emp:
            flash(f"Employee not found in {month} {year}.", "error")
            return redirect(url_for("payslips"))
        mo  = MONTH_ORDER.get(month.lower(), 12)
        ytd = get_employee_ytd(emp_name, int(year), mo)
        slips.append({"emp": emp, "ytd": ytd, "month": month, "year": year})

    if not slips:
        flash("No payroll data found for the selected period.", "error")
        return redirect(url_for("payslips"))

    return render_template("payslip_preview.html",
                           company=company, slips=slips,
                           emp_name=emp_name)

@app.route("/payslips/generate", methods=["POST"])
def generate_payslips():
    from io import BytesIO
    from payslip_generator import merge_pdfs, build_payslip_bytes, safe_filename
    from database import (get_payroll, get_employee_ytd, get_employee_history,
                          get_all_employees, get_months, MONTH_ORDER)
    import zipfile
    from flask import send_file

    company    = get_company()
    mode       = request.form.get("mode", "")
    year       = request.form.get("year", "")
    month      = request.form.get("month", "")
    emp_name   = request.form.get("emp_name", "")
    from_month = request.form.get("from_month", "")
    to_month   = request.form.get("to_month", "")
    output     = request.form.get("output", "separate")
    action     = request.form.get("action", "download")  # download / save

    out_dir = PAYSLIPS_DIR / f"{year}_{month or 'multi'}"
    out_dir.mkdir(parents=True, exist_ok=True)

    def send(pdf_bytes_or_path, fname, is_zip=False):
        """Send file to browser or save to folder."""
        mime = "application/zip" if is_zip else "application/pdf"
        if isinstance(pdf_bytes_or_path, (bytes, bytearray)):
            buf = BytesIO(pdf_bytes_or_path)
            save_path = out_dir / fname
            save_path.write_bytes(pdf_bytes_or_path)
            buf.seek(0)
            return send_file(buf, mimetype=mime, as_attachment=True, download_name=fname)
        else:
            return send_file(str(pdf_bytes_or_path), mimetype=mime,
                           as_attachment=True, download_name=fname)

    def get_range_history(name, yr, f_month, t_month):
        f_ord = MONTH_ORDER.get(f_month.lower(), 1)
        t_ord = MONTH_ORDER.get(t_month.lower(), 12)
        hist  = get_employee_history(name)
        return [r for r in hist
                if str(r["year"]) == str(yr)
                and f_ord <= r["month_order"] <= t_ord]

    try:
        # ── single_month ──────────────────────────────────────────────────
        if mode == "single_month":
            employees = get_payroll(int(year), month)
            emp = next((e for e in employees if e["name"] == emp_name), None)
            if not emp:
                flash(f"Employee not found in {month} {year}.", "error")
                return redirect(url_for("payslips"))
            mo  = MONTH_ORDER.get(month.lower(), 12)
            ytd = get_employee_ytd(emp_name, int(year), mo)
            pdf = build_payslip_bytes(emp, ytd, company["name"], month, year)
            return send(pdf, f"{safe_filename(emp_name)}_{month}_{year}.pdf")

        # ── single_range ──────────────────────────────────────────────────
        elif mode == "single_range":
            history = get_range_history(emp_name, year, from_month, to_month)
            if not history:
                flash("No data found for selected range.", "error")
                return redirect(url_for("payslips"))
            pdf_list = []
            for row in history:
                ytd = get_employee_ytd(emp_name, int(year), row["month_order"])
                pdf_list.append(build_payslip_bytes(row, ytd, company["name"], row["month"], year))
            out = out_dir / f"{safe_filename(emp_name)}_{year}_{from_month}_to_{to_month}.pdf"
            merge_pdfs(pdf_list, out)
            return send(out, out.name)

        # ── single_year ───────────────────────────────────────────────────
        elif mode == "single_year":
            history = get_employee_history(emp_name)
            history = [r for r in history if str(r["year"]) == str(year)]
            if not history:
                flash(f"No data for {emp_name} in {year}.", "error")
                return redirect(url_for("payslips"))
            pdf_list = []
            for row in history:
                ytd = get_employee_ytd(emp_name, int(year), row["month_order"])
                pdf_list.append(build_payslip_bytes(row, ytd, company["name"], row["month"], year))
            out = out_dir / f"{safe_filename(emp_name)}_{year}_FullYear.pdf"
            merge_pdfs(pdf_list, out)
            return send(out, out.name)

        # ── all_month ─────────────────────────────────────────────────────
        elif mode == "all_month":
            employees = get_payroll(int(year), month)
            if not employees:
                flash(f"No employees found for {month} {year}.", "error")
                return redirect(url_for("payslips"))
            mo = MONTH_ORDER.get(month.lower(), 12)
            pdf_list = [(emp, build_payslip_bytes(
                emp, get_employee_ytd(emp["name"], int(year), mo),
                company["name"], month, year)) for emp in employees]
            if output == "merged":
                out = out_dir / f"ALL_{month}_{year}.pdf"
                merge_pdfs([p for _,p in pdf_list], out)
                return send(out, out.name)
            else:
                zip_buf = BytesIO()
                with zipfile.ZipFile(zip_buf, "w", zipfile.ZIP_DEFLATED) as zf:
                    for emp, pdf in pdf_list:
                        zf.writestr(f"{safe_filename(emp['name'])}_{month}_{year}.pdf", pdf)
                zip_buf.seek(0)
                zname = f"Payslips_{month}_{year}.zip"
                zpath = out_dir / zname
                zpath.write_bytes(zip_buf.getvalue())
                zip_buf.seek(0)
                return send_file(zip_buf, mimetype="application/zip",
                               as_attachment=True, download_name=zname)

        # ── all_range ─────────────────────────────────────────────────────
        elif mode == "all_range":
            f_ord = MONTH_ORDER.get(from_month.lower(), 1)
            t_ord = MONTH_ORDER.get(to_month.lower(), 12)
            all_emp = get_all_employees()
            zip_buf = BytesIO()
            with zipfile.ZipFile(zip_buf, "w", zipfile.ZIP_DEFLATED) as zf:
                for emp_rec in all_emp:
                    name = emp_rec["name"]
                    rows = get_range_history(name, year, from_month, to_month)
                    if not rows: continue
                    pdfs = []
                    for row in rows:
                        ytd = get_employee_ytd(name, int(year), row["month_order"])
                        pdfs.append(build_payslip_bytes(row, ytd, company["name"], row["month"], year))
                    ep = out_dir / f"{safe_filename(name)}_{from_month}_to_{to_month}.pdf"
                    merge_pdfs(pdfs, ep)
                    zf.write(str(ep), ep.name)
            zip_buf.seek(0)
            zname = f"Payslips_{year}_{from_month}_to_{to_month}.zip"
            return send_file(zip_buf, mimetype="application/zip",
                           as_attachment=True, download_name=zname)

        # ── all_year ──────────────────────────────────────────────────────
        elif mode == "all_year":
            all_emp = get_all_employees()
            zip_buf = BytesIO()
            with zipfile.ZipFile(zip_buf, "w", zipfile.ZIP_DEFLATED) as zf:
                for emp_rec in all_emp:
                    name = emp_rec["name"]
                    history = get_employee_history(name)
                    history = [r for r in history if str(r["year"]) == str(year)]
                    if not history: continue
                    pdfs = []
                    for row in history:
                        ytd = get_employee_ytd(name, int(year), row["month_order"])
                        pdfs.append(build_payslip_bytes(row, ytd, company["name"], row["month"], year))
                    ep = out_dir / f"{safe_filename(name)}_{year}.pdf"
                    merge_pdfs(pdfs, ep)
                    zf.write(str(ep), ep.name)
            zip_buf.seek(0)
            zname = f"All_Payslips_{year}.zip"
            return send_file(zip_buf, mimetype="application/zip",
                           as_attachment=True, download_name=zname)

        else:
            flash("Please fill in all required fields.", "error")
            return redirect(url_for("payslips"))

    except Exception as e:
        flash(f"Error generating payslips: {str(e)}", "error")
        return redirect(url_for("payslips"))

# ── Settings ───────────────────────────────────────────────────────────────────
@app.route("/settings", methods=["GET","POST"])
def settings():
    """Settings — tax year only."""
    if request.method == "POST":
        ty = request.form.get("tax_year","").strip()
        if ty:
            save_tax_year(ty)
            flash(f"Tax year updated to {ty}.", "success")
        return redirect(url_for("settings"))
    return render_template("settings.html")

# ── EOBI Report ───────────────────────────────────────────────────────────────
@app.route("/eobi")
def eobi_report():
    company     = get_company()
    months      = get_months()
    years_avail = sorted(set(m["year"] for m in months), reverse=True)

    sel_year    = request.args.get("year",  str(years_avail[0]) if years_avail else "")
    sel_month   = request.args.get("month", "")

    rows        = []
    grand_total = 0

    if sel_year and sel_month:
        from database import get_conn
        conn = get_conn()
        result = conn.execute("""
            SELECT name, employee_code, department, eobi
            FROM payroll
            WHERE year=? AND month=?
            AND eobi IS NOT NULL AND eobi > 0
            ORDER BY name
        """, (int(sel_year), sel_month)).fetchall()
        conn.close()
        rows        = [dict(r) for r in result]
        grand_total = sum(r["eobi"] or 0 for r in rows)

    return render_template("eobi.html", company=company,
                           months=months, years_avail=years_avail,
                           months_list=MONTHS_LIST,
                           sel_year=sel_year, sel_month=sel_month,
                           rows=rows, grand_total=grand_total)

# ── Login / Logout ────────────────────────────────────────────────────────────
@app.route("/login")
def login():
    # No login required — redirect straight to dashboard
    if not is_eula_accepted():
        return redirect(url_for("eula"))
    return redirect(url_for("dashboard"))

# ── Year Manager ───────────────────────────────────────────────────────────────
@app.route("/years", methods=["GET","POST"])
def year_manager():
    company = get_company()
    active  = get_active_year()
    all_years = get_all_years()
    backups   = get_backups()
    message   = ""

    if request.method == "POST":
        action = request.form.get("action","")

        if action == "switch":
            label = request.form.get("fy_label","")
            if label:
                set_active_year(label)
                from database import init_db
                init_db()
                flash(f"Switched to {label}.", "success")
                return redirect(url_for("dashboard"))

        elif action == "create":
            start = request.form.get("start_year","")
            if start and start.isdigit():
                try:
                    result = create_new_year(int(start))
                    from database import init_db
                    init_db()
                    flash(f"Created and switched to {result['label']}.", "success")
                    return redirect(url_for("dashboard"))
                except ValueError as e:
                    flash(str(e), "error")

        elif action == "backup":
            label = request.form.get("fy_label","")
            if label:
                try:
                    path = backup_year(label)
                    flash(f"Backup created: {Path(path).name}", "success")
                except Exception as e:
                    flash(f"Backup failed: {e}", "error")
                return redirect(url_for("year_manager"))

        elif action == "restore":
            f = request.files.get("backup_file")
            safe_filename = secure_filename(Path(f.filename).name) if f and f.filename else ""
            if f and safe_filename and safe_filename.lower().endswith(".zip"):
                tmp = BASE_DIR / "tmp" / f"{uuid4().hex}_{safe_filename}"
                tmp.parent.mkdir(exist_ok=True)
                f.save(str(tmp))
                try:
                    label = restore_year(str(tmp))
                    from database import init_db
                    init_db()
                    flash(f"Restored {label} successfully.", "success")
                except Exception as e:
                    flash(f"Restore failed: {e}", "error")
                finally:
                    if tmp.exists(): os.remove(tmp)
            else:
                flash("Please select a valid .zip backup file.", "error")
            return redirect(url_for("year_manager"))

        elif action == "download_backup":
            bname = request.form.get("backup_name","").strip()
            backup_dir = (BASE_DIR / "backups").resolve()
            if (not bname) or (Path(bname).name != bname) or (not bname.lower().endswith(".zip")):
                flash("Invalid backup file name.", "error")
                return redirect(url_for("year_manager"))
            bpath = (backup_dir / bname).resolve()
            if backup_dir not in bpath.parents:
                flash("Invalid backup path.", "error")
                return redirect(url_for("year_manager"))
            if bpath.exists():
                return flask_send_file(str(bpath), as_attachment=True,
                                       download_name=bname)
            flash("Backup file not found.", "error")
            return redirect(url_for("year_manager"))

    active  = get_active_year()
    all_years = get_all_years()
    backups   = get_backups()
    years_for_create = list(range(2020, 2035))
    return render_template("year_manager.html", company=company,
                           active=active, all_years=all_years,
                           backups=backups, years_for_create=years_for_create)

# ── Global Search ──────────────────────────────────────────────────────────────
@app.route("/search")
def global_search():
    from database import get_conn
    company = get_company()
    q = request.args.get("q","").strip()
    results = []
    if q and len(q) >= 2:
        conn = get_conn()
        rows = conn.execute("""
            SELECT DISTINCT name, employee_code, department, designation
            FROM payroll
            WHERE name LIKE ? OR employee_code LIKE ?
            ORDER BY name
        """, (f"%{q}%", f"%{q}%")).fetchall()
        for row in rows:
            r = dict(row)
            # Get latest month data
            latest = conn.execute("""
                SELECT month, year, net_payable, total_payable
                FROM payroll WHERE name=?
                ORDER BY year DESC, month_order DESC LIMIT 1
            """, (r["name"],)).fetchone()
            if latest:
                r["latest"] = dict(latest)
            results.append(r)
        conn.close()
    return render_template("search.html", company=company,
                           q=q, results=results,
                           active_year=get_active_year())

@app.route("/eula", methods=["GET","POST"])
def eula():
    if is_eula_accepted():
        return redirect(url_for("login"))
    company = get_company()
    if request.method == "POST":
        if request.form.get("action") == "accept":
            accept_eula()
            return redirect(url_for("login"))
        else:
            return render_template("eula.html", company=company,
                                   declined=True, eula_text=EULA_TEXT)
    return render_template("eula.html", company=company,
                           declined=False, eula_text=EULA_TEXT)

@app.route("/about")
def about():
    return render_template("about.html", eula_text=EULA_TEXT)

# ── Close App ─────────────────────────────────────────────────────────────────
@app.route("/close_app", methods=["POST"])
def close_app():
    """Shutdown the Flask server gracefully with delay."""
    import threading
    def shutdown():
        import time, os, signal
        time.sleep(2.5)  # Wait for closing page to render fully
        os.kill(os.getpid(), signal.SIGTERM)
    threading.Thread(target=shutdown, daemon=True).start()
    return render_template("closing.html")

# ── Dismiss Reminder ──────────────────────────────────────────────────────────
@app.route("/dismiss_reminder", methods=["POST"])
def dismiss_reminder():
    global _reminder_shown
    _reminder_shown = True
    return "", 204

# ── Document Routes ───────────────────────────────────────────────────────────
@app.route("/help")
def help_manual():
    try:
        path = generate_help_manual()
        return flask_send_file(path, as_attachment=True,
                               download_name="Payroll_View_Help_Manual.pdf",
                               mimetype="application/pdf")
    except Exception as e:
        flash(f"Error generating help manual: {e}", "error")
        return redirect(url_for("about"))

@app.route("/agreement")
def service_agreement():
    try:
        company = get_company()
        path = generate_agreement(company["name"], company.get("region","Lahore"))
        return flask_send_file(path, as_attachment=False,
                               download_name="Service_Agreement_Berlitz.pdf",
                               mimetype="application/pdf")
    except Exception as e:
        flash(f"Error generating agreement: {e}", "error")
        return redirect(url_for("about"))

# ── Error handlers ─────────────────────────────────────────────────────────────
@app.errorhandler(500)
def err500(e):
    import traceback
    app.logger.error("Unhandled error: %s\n%s", e, traceback.format_exc())
    return "<h2>Error 500</h2><p>Something went wrong.</p><a href='/'>Back</a>", 500

@app.errorhandler(404)
def err404(e):
    return "<h2>Page not found</h2><a href='/'>Back to Dashboard</a>", 404

# ── Main ───────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    # ── Startup: ensure year system is ready before DB init ──────────────────
    from year_manager import get_active_year, get_db_path, get_fy_label, current_fy_start
    from pathlib import Path as _Path
    import shutil as _shutil

    # Migrate legacy payroll.db → FY format if needed
    legacy = BASE_DIR / "payroll.db"
    active = get_active_year()
    fy_db  = _Path(active["db_path"])
    if legacy.exists() and not fy_db.exists():
        fy_db.parent.mkdir(parents=True, exist_ok=True)
        _shutil.copy(str(legacy), str(fy_db))
        print(f"  Migrated payroll.db → {fy_db.name}")

    # Ensure active DB exists (create empty if new year)
    fy_db.parent.mkdir(parents=True, exist_ok=True)

    init_db()
    company = get_company()
    active  = get_active_year()
    print("\n" + "="*55)
    print(f"  PEF Payroll System — {company['name']}")
    print(f"  Open  : http://127.0.0.1:5001")
    print(f"  Active: {active['label']}")
    print(f"  DB    : {active['db_path']}")
    print("="*55 + "\n")
    app.run(debug=False, port=5001)
