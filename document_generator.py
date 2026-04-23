"""
Document Generator — SoftFlow Ltd
Generates Agreement and Help Manual PDFs using ReportLab.
"""
from pathlib import Path
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer,
                                 Table, TableStyle, HRFlowable, PageBreak)
from reportlab.platypus import KeepTogether

BASE_DIR       = Path(__file__).resolve().parent
AGREEMENTS_DIR = BASE_DIR / "agreements"
AGREEMENTS_DIR.mkdir(exist_ok=True)

# ── Colours ────────────────────────────────────────────────────────────────────
NAVY   = colors.HexColor("#0a1628")
BLUE   = colors.HexColor("#1565c0")
GOLD   = colors.HexColor("#f9a825")
LGREY  = colors.HexColor("#f4f7fb")
MGREY  = colors.HexColor("#d0dce8")
RED    = colors.HexColor("#c62828")
WHITE  = colors.white
BLACK  = colors.HexColor("#1a2535")
SOFT   = colors.HexColor("#5a6b82")

W, H = A4

def _styles():
    s = getSampleStyleSheet()
    base = dict(fontName="Helvetica", textColor=BLACK, leading=16)
    return {
        "title":    ParagraphStyle("title",    fontSize=22, fontName="Helvetica-Bold",
                                   textColor=NAVY,  alignment=TA_CENTER, spaceAfter=4),
        "subtitle": ParagraphStyle("subtitle", fontSize=13, fontName="Helvetica",
                                   textColor=SOFT,  alignment=TA_CENTER, spaceAfter=20),
        "h1":       ParagraphStyle("h1",       fontSize=13, fontName="Helvetica-Bold",
                                   textColor=NAVY,  spaceBefore=14, spaceAfter=6),
        "h2":       ParagraphStyle("h2",       fontSize=11, fontName="Helvetica-Bold",
                                   textColor=BLUE,  spaceBefore=10, spaceAfter=4),
        "body":     ParagraphStyle("body",     fontSize=10, fontName="Helvetica",
                                   textColor=BLACK, leading=16, spaceAfter=6,
                                   alignment=TA_JUSTIFY),
        "bullet":   ParagraphStyle("bullet",   fontSize=10, fontName="Helvetica",
                                   textColor=BLACK, leading=15, spaceAfter=3,
                                   leftIndent=16, bulletIndent=6),
        "small":    ParagraphStyle("small",    fontSize=8,  fontName="Helvetica",
                                   textColor=SOFT,  alignment=TA_CENTER),
        "warning":  ParagraphStyle("warning",  fontSize=10, fontName="Helvetica-Bold",
                                   textColor=RED,   alignment=TA_CENTER, spaceAfter=6),
        "centre":   ParagraphStyle("centre",   fontSize=10, fontName="Helvetica",
                                   textColor=BLACK, alignment=TA_CENTER),
    }

def _header_footer(canvas, doc):
    """Page header and footer."""
    canvas.saveState()
    # Header bar
    canvas.setFillColor(NAVY)
    canvas.rect(0, H - 22*mm, W, 22*mm, fill=1, stroke=0)
    canvas.setFillColor(WHITE)
    canvas.setFont("Helvetica-Bold", 11)
    canvas.drawString(20*mm, H - 13*mm, "Payroll_View v1.0")
    canvas.setFont("Helvetica", 9)
    canvas.drawRightString(W - 20*mm, H - 13*mm, "SoftFlow Ltd  ·  Iqbal Ahmed")
    canvas.setFillColor(GOLD)
    canvas.rect(0, H - 23*mm, W, 1*mm, fill=1, stroke=0)
    # Footer
    canvas.setFillColor(LGREY)
    canvas.rect(0, 0, W, 14*mm, fill=1, stroke=0)
    canvas.setFillColor(SOFT)
    canvas.setFont("Helvetica", 8)
    canvas.drawString(20*mm, 5*mm, f"© 2026 SoftFlow Ltd. All Rights Reserved.")
    canvas.drawRightString(W - 20*mm, 5*mm, f"Page {doc.page}")
    canvas.restoreState()

# ══════════════════════════════════════════════════════════════════════════════
# AGREEMENT PDF
# ══════════════════════════════════════════════════════════════════════════════
def generate_agreement(company_name="Berlitz", region="Lahore") -> str:
    """Generate Service Agreement PDF. Returns file path."""
    out = AGREEMENTS_DIR / "Service_Agreement_Berlitz.pdf"
    doc = SimpleDocTemplate(str(out), pagesize=A4,
                            topMargin=28*mm, bottomMargin=20*mm,
                            leftMargin=20*mm, rightMargin=20*mm)
    S = _styles()
    story = []
    today = datetime.now().strftime("%d %B %Y")

    # Cover
    story += [
        Spacer(1, 10*mm),
        Paragraph("SOFTWARE SERVICE AGREEMENT", S["title"]),
        Paragraph("Payroll_View v1.0", S["subtitle"]),
        HRFlowable(width="100%", thickness=1, color=GOLD, spaceAfter=10),
        Spacer(1, 4*mm),
    ]

    # Parties table
    parties = [
        ["PROVIDER",  "SoftFlow Ltd"],
        ["Developer", "Iqbal Ahmed"],
        ["CLIENT",    f"{company_name}, {region}"],
        ["Date",      today],
        ["Software",  "Payroll_View v1.0"],
    ]
    pt = Table(parties, colWidths=[45*mm, 120*mm])
    pt.setStyle(TableStyle([
        ("BACKGROUND",   (0,0),(0,-1), LGREY),
        ("FONTNAME",     (0,0),(0,-1), "Helvetica-Bold"),
        ("FONTNAME",     (1,0),(1,-1), "Helvetica"),
        ("FONTSIZE",     (0,0),(-1,-1), 10),
        ("TEXTCOLOR",    (0,0),(0,-1), NAVY),
        ("GRID",         (0,0),(-1,-1), 0.4, MGREY),
        ("TOPPADDING",   (0,0),(-1,-1), 6),
        ("BOTTOMPADDING",(0,0),(-1,-1), 6),
        ("LEFTPADDING",  (0,0),(-1,-1), 10),
    ]))
    story += [pt, Spacer(1, 8*mm)]

    clauses = [
        ("1. SCOPE OF SERVICES",
         f"SoftFlow Ltd agrees to provide {company_name} with the Payroll_View software system "
         f"(\"Software\") for the purpose of payroll data management, reporting, and payslip generation. "
         f"The Software is installed on {company_name}'s local computer systems in {region}, Pakistan."),

        ("2. IMPORTANT DISCLAIMER — CALCULATIONS",
         "THE SOFTWARE DOES NOT CALCULATE OR COMPUTE SALARIES, RELATED DEDUCTIONS OR ADDITIONS. "
         "All financial figures including but not limited to gross pay, net pay, income tax, EOBI, "
         "leave deductions, arrears, and reimbursements are imported directly from monthly payroll "
         "Excel sheets prepared and provided by the Client. SoftFlow Ltd accepts NO responsibility "
         "or liability for the accuracy of any figures displayed by the Software."),

        ("3. CLIENT RESPONSIBILITIES",
         f"{company_name} is solely responsible for: (a) the accuracy and completeness of all "
         "payroll data imported into the Software; (b) compliance with applicable tax, labour, "
         "and financial regulations of Pakistan; (c) verification of all figures before use in "
         "official documents or submissions; (d) maintaining regular backups of data files; "
         "(e) ensuring the Software is used only by authorised personnel."),

        ("4. LICENSE & RESTRICTIONS",
         f"This Software is licensed exclusively to {company_name}, {region}. The Client may NOT "
         "copy, distribute, sublicense, or transfer the Software to any third party. The Client may "
         "NOT reverse engineer or modify the Software. This license covers a single installation only."),

        ("5. DATA PRIVACY & SECURITY",
         "The Software operates entirely offline on the Client's local computer. No payroll data "
         "is transmitted to SoftFlow Ltd or any third party. The Client is responsible for the "
         "physical and digital security of the computer on which the Software is installed."),

        ("6. SUPPORT & MAINTENANCE",
         "SoftFlow Ltd will provide reasonable technical support for issues directly related to "
         "Software functionality. Support does not cover issues arising from incorrect data entry, "
         "hardware failures, operating system issues, or third-party software conflicts."),

        ("7. LIMITATION OF LIABILITY",
         "To the maximum extent permitted by law, SoftFlow Ltd shall not be liable for any "
         "indirect, incidental, or consequential damages arising from use of the Software. "
         "SoftFlow Ltd's total liability shall not exceed the amount paid for the Software license."),

        ("8. GOVERNING LAW",
         "This Agreement shall be governed by the laws of Pakistan. Any disputes shall be "
         "subject to the exclusive jurisdiction of the courts of Pakistan."),

        ("9. ENTIRE AGREEMENT",
         "This Agreement constitutes the entire agreement between SoftFlow Ltd and the Client "
         "regarding the Software and supersedes all prior agreements and understandings."),
    ]

    for heading, text in clauses:
        story.append(Paragraph(heading, S["h1"]))
        story.append(Paragraph(text, S["body"]))
        story.append(Spacer(1, 2*mm))

    # Signature block
    story += [
        Spacer(1, 10*mm),
        HRFlowable(width="100%", thickness=0.5, color=MGREY),
        Spacer(1, 6*mm),
    ]
    sig_data = [
        ["FOR SOFTFLOW LTD", "", f"FOR {company_name.upper()}"],
        ["", "", ""],
        ["_______________________", "", "_______________________"],
        ["Iqbal Ahmed", "", "Authorised Signatory"],
        ["Developer & Founder", "", f"{company_name}, {region}"],
        [today, "", "Date: _______________"],
    ]
    st = Table(sig_data, colWidths=[70*mm, 30*mm, 70*mm])
    st.setStyle(TableStyle([
        ("FONTNAME",  (0,0),(-1,-1), "Helvetica"),
        ("FONTNAME",  (0,0),(0,0),   "Helvetica-Bold"),
        ("FONTNAME",  (2,0),(2,0),   "Helvetica-Bold"),
        ("FONTSIZE",  (0,0),(-1,-1), 9),
        ("TEXTCOLOR", (0,0),(-1,-1), BLACK),
        ("TOPPADDING",(0,0),(-1,-1), 3),
    ]))
    story.append(st)

    doc.build(story, onFirstPage=_header_footer, onLaterPages=_header_footer)
    return str(out)


# ══════════════════════════════════════════════════════════════════════════════
# HELP MANUAL PDF
# ══════════════════════════════════════════════════════════════════════════════
def generate_help_manual() -> str:
    """Generate Help Manual PDF. Returns file path."""
    out = BASE_DIR / "Payroll_View_Help_Manual.pdf"
    doc = SimpleDocTemplate(str(out), pagesize=A4,
                            topMargin=28*mm, bottomMargin=20*mm,
                            leftMargin=20*mm, rightMargin=20*mm)
    S = _styles()
    story = []

    def section(title):
        story.append(PageBreak())
        story.append(Paragraph(title, S["h1"]))
        story.append(HRFlowable(width="100%", thickness=1, color=BLUE, spaceAfter=8))

    def sub(title):
        story.append(Paragraph(title, S["h2"]))

    def body(text):
        story.append(Paragraph(text, S["body"]))

    def bullet(text):
        story.append(Paragraph(f"• {text}", S["bullet"]))

    def space():
        story.append(Spacer(1, 4*mm))

    # ── Cover Page ──────────────────────────────────────────────────────────
    story += [
        Spacer(1, 20*mm),
        Paragraph("PAYROLL_VIEW", S["title"]),
        Paragraph("User Help Manual", S["subtitle"]),
        Paragraph("v1.0", S["centre"]),
        Spacer(1, 6*mm),
        HRFlowable(width="100%", thickness=2, color=GOLD, spaceAfter=8),
        Spacer(1, 4*mm),
        Paragraph("Berlitz · Lahore", S["centre"]),
        Spacer(1, 30*mm),
    ]
    info = [
        ["Developer", "SoftFlow Ltd"],
        ["Author",    "Iqbal Ahmed"],
        ["Version",   "v1.0"],
        ["Date",      datetime.now().strftime("%B %Y")],
    ]
    it = Table(info, colWidths=[45*mm, 100*mm])
    it.setStyle(TableStyle([
        ("BACKGROUND",  (0,0),(0,-1), LGREY),
        ("FONTNAME",    (0,0),(0,-1), "Helvetica-Bold"),
        ("FONTSIZE",    (0,0),(-1,-1), 10),
        ("GRID",        (0,0),(-1,-1), 0.4, MGREY),
        ("TOPPADDING",  (0,0),(-1,-1), 6),
        ("BOTTOMPADDING",(0,0),(-1,-1), 6),
        ("LEFTPADDING", (0,0),(-1,-1), 10),
    ]))
    story.append(it)
    story.append(Spacer(1, 20*mm))
    story.append(Paragraph(
        "⚠  IMPORTANT: This software does NOT calculate or compute salaries, "
        "related deductions or additions. All figures are imported from monthly "
        "payroll Excel sheets.", S["warning"]))

    # ── 1. Getting Started ──────────────────────────────────────────────────
    section("1. Getting Started")
    sub("1.1 Launching the Software")
    body("To start Payroll_View, run the application from your desktop shortcut or "
         "by running app.py from the installation folder. The software will open "
         "automatically in your web browser.")
    space()
    sub("1.2 Login")
    body("Enter your username and password on the login screen. Default credentials are:")
    bullet("Username: admin")
    bullet("Password: admin123")
    body("You will be prompted to accept the End User License Agreement (EULA) on first run.")
    space()
    sub("1.3 Dashboard Overview")
    body("The Dashboard is your home screen showing:")
    bullet("Months Loaded — number of payroll months imported for the active year")
    bullet("Total Employees — distinct employees in the active database")
    bullet("Net Payroll — total net payable for the latest month")
    bullet("Latest Month — the most recently imported month")
    body("The Payroll Data table shows all imported months with employee counts and totals. "
         "Quick Action buttons provide fast access to common tasks.")

    # ── 2. Importing Payroll ────────────────────────────────────────────────
    section("2. Importing Payroll Data")
    sub("2.1 Preparing Your Excel File")
    body("The Excel file must follow the standard Berlitz payroll format with these columns:")
    for col in ["Status", "Employee Code", "Name", "District", "City / Town",
                "Department", "Designation", "Salary", "Basic", "H-Rent",
                "Utility", "Medical", "Gross Pay", "Travelling Allowance",
                "Accommodation Allowance", "Working Days", "Gross Total Payable",
                "I. Tax", "E.O.B.I", "Leaves", "Leave Deduction", "Late Deductible",
                "Other", "Total Deduction", "Net Payable", "Arrear",
                "Reimbursement", "Total payable (reconcile)", "Date (DOJ)"]:
        bullet(col)
    space()
    sub("2.2 Uploading the File")
    body("Navigate to Import Payroll from the sidebar. Select the Year and Month for the data. "
         "Click Choose File and select your Excel (.xlsx) or CSV file. "
         "Click Import to load the data into the database.")
    space()
    sub("2.3 Re-importing / Overwriting")
    body("If you need to correct data for a month already imported, simply import the corrected "
         "file again for the same year and month. The system will automatically delete the "
         "existing data and replace it with the new import.")
    space()
    sub("2.4 Deleting a Month")
    body("On the Import page, existing months are listed with a Delete button. "
         "Click Delete to remove all data for that month before re-importing.")

    # ── 3. Payroll Register ─────────────────────────────────────────────────
    section("3. Payroll Register")
    body("The Payroll Register shows all employees for a selected month with full salary details.")
    space()
    sub("3.1 Viewing the Register")
    body("Select Year and Month from the dropdowns and click Show. The table displays all "
         "employees with their salary breakdown, deductions, and net pay.")
    space()
    sub("3.2 Printing")
    body("Click the Print button at the top right. The register prints in landscape A4 format. "
         "The sidebar and navigation are automatically hidden during printing.")
    space()
    sub("3.3 Totals Row")
    body("The bottom of the register shows column totals for all numeric fields including "
         "gross total, total deductions, net payable, and total payable.")

    # ── 4. Employee Account ─────────────────────────────────────────────────
    section("4. Employee Account")
    body("The Employee Account page shows complete year history and YTD totals for any employee.")
    space()
    sub("4.1 Searching for an Employee")
    body("Click the Employee dropdown and start typing the employee name. The list filters "
         "instantly as you type. Select the employee to load their full account.")
    space()
    sub("4.2 YTD Summary Banner")
    body("The dark banner at the top shows Year-to-Date totals including months paid, "
         "gross YTD, tax YTD, EOBI YTD, total deductions, net payable YTD, and total paid YTD.")
    space()
    sub("4.3 Month-by-Month Table")
    body("The table below shows one row per month with all salary figures. "
         "The Year Totals row at the bottom sums all columns including leave days taken.")
    space()
    sub("4.4 Printing")
    body("Click Print at the top right. Prints in landscape A4. Sidebar is hidden automatically.")

    # ── 5. Generate Payslips ────────────────────────────────────────────────
    section("5. Generate Payslips")
    body("Payslips are generated as browser-based previews and can be printed or saved as PDF.")
    space()
    sub("5.1 Selecting Employee and Period")
    body("On the left card, type to search and select an employee. Choose the Year and Month.")
    space()
    sub("5.2 Selecting Mode")
    body("On the right card, choose one of four modes:")
    bullet("Single Employee — One Month: One payslip for one employee for the selected month")
    bullet("Single Employee — Date Range: Multiple months for one employee in one PDF")
    bullet("Single Employee — Full Year: All months for one employee for the full year")
    bullet("All Employees — One Month: Payslips for all employees for the selected month")
    space()
    sub("5.3 Previewing")
    body("Click Preview Payslip. A new window opens showing the payslip(s). "
         "From the preview window, use the Print button to print or save as PDF.")
    space()
    sub("5.4 Saving as PDF")
    body("In the preview window, click Save as PDF. In the print dialog that opens, "
         "change the Destination to 'Save as PDF' and choose your save location.")
    space()
    sub("5.5 Payslip Contents")
    body("Each payslip contains:")
    bullet("Employee Info: Name, Code, Department, Designation, District, City, Status, DOJ, Working Days")
    bullet("Salary Breakdown: Basic, House Rent, Utility, Medical, Travelling, Accommodation, Gross Total")
    bullet("Deductions: Income Tax, EOBI, Leave Deduction, Late Deduction, Other, Total Deductions")
    bullet("Net Pay Summary: Net Payable, Arrear, Reimbursement, Total Payable")
    bullet("YTD figures alongside every This Month figure")

    # ── 6. EOBI Report ──────────────────────────────────────────────────────
    section("6. EOBI Report")
    body("The EOBI Report shows employee EOBI contributions for a selected month.")
    space()
    sub("6.1 Generating the Report")
    body("Select Year and Month from the dropdowns and click Show. The report displays "
         "all employees with EOBI contributions greater than zero for that month.")
    space()
    sub("6.2 Reading the Report")
    body("Each row shows Employee Name, Code, Department, and EOBI amount. "
         "The Total row at the bottom shows the grand total EOBI for the month.")
    space()
    sub("6.3 Note on EOBI Figures")
    body("All EOBI figures are sourced directly from the imported Excel payroll sheet. "
         "The software does not calculate EOBI — it only displays and totals the imported values.")
    space()
    sub("6.4 Printing")
    body("Click the Print button. The report prints in portrait A4 format.")

    # ── 7. Year Manager ─────────────────────────────────────────────────────
    section("7. Year Manager")
    body("The Year Manager handles multiple financial years. Pakistan FY runs July to June.")
    space()
    sub("7.1 Opening a Year")
    body("All available year databases are listed. Click Open next to any year to switch to it. "
         "All pages (Register, Employee Account, Payslips, EOBI) will use that year's data.")
    space()
    sub("7.2 Creating a New Year")
    body("At the start of each new financial year (July), click Create New Financial Year. "
         "Select the start year (e.g. 2026 for FY2026-27) and click Create. "
         "A fresh empty database is created and set as active.")
    space()
    sub("7.3 Backing Up")
    body("Click Backup next to any year to create a ZIP backup of that year's database. "
         "Backups are saved to the backups\\ folder in the installation directory.")
    space()
    sub("7.4 Restoring")
    body("To restore from a backup, click the upload area under Restore from Backup. "
         "Select a backup ZIP file. The system will restore the database, automatically "
         "creating a backup of the current data before overwriting.")
    space()
    sub("7.5 Downloading Backups")
    body("Click the download icon next to any backup in the Available Backups list "
         "to save the backup ZIP to your computer.")

    # ── 8. Settings ─────────────────────────────────────────────────────────
    section("8. Settings")
    sub("8.1 Tax Year")
    body("The Tax Year is displayed on reports and payslips. To change it, enter the new "
         "tax year (e.g. 2026-2027) in the Tax Year field and click Save Tax Year.")
    space()
    sub("8.2 Company Information")
    body("Company Name and Region are fixed by SoftFlow Ltd and cannot be changed from "
         "the Settings page. Contact Iqbal Ahmed at SoftFlow Ltd for any changes.")

    # ── 9. Disclaimer ───────────────────────────────────────────────────────
    section("9. Important Disclaimer")
    story.append(Paragraph(
        "THIS SOFTWARE DOES NOT CALCULATE OR COMPUTE SALARIES, "
        "RELATED DEDUCTIONS OR ADDITIONS.", S["warning"]))
    space()
    body("All financial figures displayed in Payroll_View — including but not limited to:")
    for item in ["Gross Pay", "Net Pay", "Income Tax", "EOBI Contributions",
                 "Leave Deductions", "Late Deductions", "Arrears", "Reimbursements",
                 "Total Payable"]:
        bullet(item)
    space()
    body("— are imported directly from monthly payroll Excel sheets prepared and "
         "provided by the client (Berlitz). SoftFlow Ltd accepts NO responsibility "
         "or liability for the accuracy of any figures displayed by this software.")
    space()
    body("The only calculations performed by this software are report-level totals "
         "and grand totals (i.e. summing imported figures for display purposes only).")
    space()
    body("It is the sole responsibility of Berlitz to verify all payroll figures "
         "before use in official documents, salary payments, or regulatory submissions.")

    doc.build(story, onFirstPage=_header_footer, onLaterPages=_header_footer)
    return str(out)
