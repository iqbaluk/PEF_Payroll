"""
PEF Payroll — PDF Payslip Generator
Produces professional A4 payslips with current month + YTD figures.
"""
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle, Paragraph,
    Spacer, HRFlowable
)
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.pdfgen import canvas
from pathlib import Path
from io import BytesIO
import os

# ── Colours ───────────────────────────────────────────────────────────────────
NAVY   = colors.HexColor("#0a1628")
BLUE   = colors.HexColor("#1565c0")
GOLD   = colors.HexColor("#f9a825")
WHITE  = colors.white
LGREY  = colors.HexColor("#f4f7fb")
MGREY  = colors.HexColor("#d0dce8")
RED    = colors.HexColor("#c62828")
GREEN  = colors.HexColor("#1b7f4f")
BLACK  = colors.black

# ── Helpers ───────────────────────────────────────────────────────────────────
def fmt(v):
    try:
        f = float(v or 0)
        return f"{f:,.0f}"
    except:
        return "0"

def build_payslip_bytes(emp, ytd, company_name, month, year):
    """
    Build a single payslip as PDF bytes.
    emp  = dict of current month row from DB
    ytd  = dict of YTD totals
    """
    buf = BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=15*mm, rightMargin=15*mm,
        topMargin=12*mm,  bottomMargin=12*mm
    )

    W = A4[0] - 30*mm   # usable width

    # ── Styles ─────────────────────────────────────────────────────────────
    def PS(name, size=9, bold=False, color=BLACK, align=TA_LEFT, leading=None):
        return ParagraphStyle(
            name, fontSize=size, fontName="Helvetica-Bold" if bold else "Helvetica",
            textColor=color, alignment=align,
            leading=leading or size*1.3
        )

    story = []

    # ── Header ─────────────────────────────────────────────────────────────
    header_data = [[
        Paragraph(f'<font size="14"><b>{company_name.upper()}</b></font>', PS("h1",14,True,WHITE)),
        Paragraph(
            f'<font size="9">PAYSLIP</font><br/>'
            f'<font size="11"><b>{month.upper()} {year}</b></font>',
            PS("h2",9,False,WHITE,TA_RIGHT)
        )
    ]]
    header_tbl = Table(header_data, colWidths=[W*0.6, W*0.4])
    header_tbl.setStyle(TableStyle([
        ("BACKGROUND",    (0,0),(-1,-1), NAVY),
        ("TEXTCOLOR",     (0,0),(-1,-1), WHITE),
        ("VALIGN",        (0,0),(-1,-1), "MIDDLE"),
        ("LEFTPADDING",   (0,0),(0,-1),  8),
        ("RIGHTPADDING",  (-1,0),(-1,-1),8),
        ("TOPPADDING",    (0,0),(-1,-1), 8),
        ("BOTTOMPADDING", (0,0),(-1,-1), 8),
    ]))
    story.append(header_tbl)
    story.append(Spacer(1, 4*mm))

    # ── Employee Info ───────────────────────────────────────────────────────
    code = emp.get("employee_code","") or "—"
    name = emp.get("name","")
    dept = emp.get("department","") or "—"
    desig= emp.get("designation","") or "—"
    stat = emp.get("status","Active") or "Active"
    doj  = emp.get("date_joined","") or "—"

    district = str(emp.get("district","") or "—")
    city     = str(emp.get("city","") or "—")
    wdays    = str(int(float(emp.get("working_days",0) or 0)))

    info_data = [
        [
            Paragraph("<b>Employee Name</b>", PS("il",7,True,BLUE)),
            Paragraph(name, PS("iv",9,True)),
            Paragraph("<b>Employee Code</b>", PS("il",7,True,BLUE)),
            Paragraph(code, PS("iv",9)),
            Paragraph("<b>Department</b>", PS("il",7,True,BLUE)),
            Paragraph(dept, PS("iv",9)),
        ],
        [
            Paragraph("<b>Designation</b>", PS("il",7,True,BLUE)),
            Paragraph(desig, PS("iv",9)),
            Paragraph("<b>District</b>", PS("il",7,True,BLUE)),
            Paragraph(district, PS("iv",9)),
            Paragraph("<b>City / Town</b>", PS("il",7,True,BLUE)),
            Paragraph(city, PS("iv",9)),
        ],
        [
            Paragraph("<b>Status</b>", PS("il",7,True,BLUE)),
            Paragraph(stat, PS("iv",9)),
            Paragraph("<b>Date of Joining</b>", PS("il",7,True,BLUE)),
            Paragraph(str(doj).split(" ")[0], PS("iv",9)),
            Paragraph("<b>Working Days</b>", PS("il",7,True,BLUE)),
            Paragraph(wdays, PS("iv",9)),
        ],
    ]
    cw = [W*0.15, W*0.185, W*0.12, W*0.185, W*0.12, W*0.24]
    info_tbl = Table(info_data, colWidths=cw)
    info_tbl.setStyle(TableStyle([
        ("BACKGROUND",   (0,0),(-1,-1), LGREY),
        ("GRID",         (0,0),(-1,-1), 0.3, MGREY),
        ("TOPPADDING",   (0,0),(-1,-1), 4),
        ("BOTTOMPADDING",(0,0),(-1,-1), 4),
        ("LEFTPADDING",  (0,0),(-1,-1), 5),
        ("RIGHTPADDING", (0,0),(-1,-1), 5),
        ("VALIGN",       (0,0),(-1,-1), "MIDDLE"),
        # Label columns (0,2,4) slightly different background
        ("BACKGROUND",   (0,0),(0,-1), colors.HexColor("#dce8f5")),
        ("BACKGROUND",   (2,0),(2,-1), colors.HexColor("#dce8f5")),
        ("BACKGROUND",   (4,0),(4,-1), colors.HexColor("#dce8f5")),
    ]))
    story.append(info_tbl)
    story.append(Spacer(1, 4*mm))

    # ── Salary Breakdown ────────────────────────────────────────────────────
    story.append(Paragraph("SALARY BREAKDOWN", PS("sh",8,True,NAVY)))
    story.append(Spacer(1,2*mm))

    sal_data = [
        # Header row
        [
            Paragraph("COMPONENT", PS("sh",7,True,WHITE)),
            Paragraph("THIS MONTH (PKR)", PS("sh",7,True,WHITE,TA_RIGHT)),
            Paragraph("YTD (PKR)", PS("sh",7,True,WHITE,TA_RIGHT)),
        ],
        [
            Paragraph("Basic Pay", PS("sr",8)),
            Paragraph(fmt(emp.get("basic",0)), PS("sv",8,False,BLACK,TA_RIGHT)),
            Paragraph(fmt(ytd.get("basic",0)), PS("sv",8,False,BLACK,TA_RIGHT)),
        ],
        [
            Paragraph("House Rent", PS("sr",8)),
            Paragraph(fmt(emp.get("house_rent",0)), PS("sv",8,False,BLACK,TA_RIGHT)),
            Paragraph(fmt(ytd.get("house_rent",0)), PS("sv",8,False,BLACK,TA_RIGHT)),
        ],
        [
            Paragraph("Utility Allowance", PS("sr",8)),
            Paragraph(fmt(emp.get("utility",0)), PS("sv",8,False,BLACK,TA_RIGHT)),
            Paragraph(fmt(ytd.get("utility",0)), PS("sv",8,False,BLACK,TA_RIGHT)),
        ],
        [
            Paragraph("Medical Allowance", PS("sr",8)),
            Paragraph(fmt(emp.get("medical",0)), PS("sv",8,False,BLACK,TA_RIGHT)),
            Paragraph(fmt(ytd.get("medical",0)), PS("sv",8,False,BLACK,TA_RIGHT)),
        ],
        [
            Paragraph("Travelling Allowance (tax free)", PS("sr",8)),
            Paragraph(fmt(emp.get("travelling",0)), PS("sv",8,False,BLACK,TA_RIGHT)),
            Paragraph(fmt(ytd.get("travelling",0)), PS("sv",8,False,BLACK,TA_RIGHT)),
        ],
        [
            Paragraph("Accommodation Allowance (tax free)", PS("sr",8)),
            Paragraph(fmt(emp.get("accommodation",0)), PS("sv",8,False,BLACK,TA_RIGHT)),
            Paragraph(fmt(ytd.get("accommodation",0)), PS("sv",8,False,BLACK,TA_RIGHT)),
        ],
        [
            Paragraph("<b>Gross Total Payable</b>", PS("sr",8,True,BLUE)),
            Paragraph(f"<b>{fmt(emp.get('gross_total',0))}</b>", PS("sv",8,True,BLUE,TA_RIGHT)),
            Paragraph(f"<b>{fmt(ytd.get('gross_total',0))}</b>", PS("sv",8,True,BLUE,TA_RIGHT)),
        ],
    ]
    cw2 = [W*0.55, W*0.225, W*0.225]
    sal_tbl = Table(sal_data, colWidths=cw2)
    sal_tbl.setStyle(TableStyle([
        ("BACKGROUND",    (0,0),(-1,0),  NAVY),
        ("BACKGROUND",    (0,1),(-1,-2), WHITE),
        ("BACKGROUND",    (0,-1),(-1,-1),LGREY),
        ("ROWBACKGROUNDS",(0,1),(-1,-2), [WHITE, LGREY]),
        ("GRID",          (0,0),(-1,-1), 0.3, MGREY),
        ("TOPPADDING",    (0,0),(-1,-1), 4),
        ("BOTTOMPADDING", (0,0),(-1,-1), 4),
        ("LEFTPADDING",   (0,0),(-1,-1), 6),
        ("RIGHTPADDING",  (0,0),(-1,-1), 6),
        ("LINEABOVE",     (0,-1),(-1,-1),0.8, BLUE),
    ]))
    story.append(sal_tbl)
    story.append(Spacer(1, 4*mm))

    # ── Deductions ──────────────────────────────────────────────────────────
    story.append(Paragraph("DEDUCTIONS", PS("sh",8,True,NAVY)))
    story.append(Spacer(1,2*mm))

    ded_data = [
        [
            Paragraph("DEDUCTION", PS("dh",7,True,WHITE)),
            Paragraph("LEAVES", PS("dh",7,True,WHITE,TA_RIGHT)),
            Paragraph("THIS MONTH (PKR)", PS("dh",7,True,WHITE,TA_RIGHT)),
            Paragraph("YTD (PKR)", PS("dh",7,True,WHITE,TA_RIGHT)),
        ],
        [
            Paragraph("Income Tax", PS("dr",8)),
            Paragraph("—", PS("dv",8,False,BLACK,TA_RIGHT)),
            Paragraph(fmt(emp.get("income_tax",0)), PS("dv",8,False,RED,TA_RIGHT)),
            Paragraph(fmt(ytd.get("income_tax",0)), PS("dv",8,False,RED,TA_RIGHT)),
        ],
        [
            Paragraph("EOBI", PS("dr",8)),
            Paragraph("—", PS("dv",8,False,BLACK,TA_RIGHT)),
            Paragraph(fmt(emp.get("eobi",0)), PS("dv",8,False,RED,TA_RIGHT)),
            Paragraph(fmt(ytd.get("eobi",0)), PS("dv",8,False,RED,TA_RIGHT)),
        ],
        [
            Paragraph("Leave Deduction", PS("dr",8)),
            Paragraph(fmt(emp.get("leaves",0)), PS("dv",8,False,BLACK,TA_RIGHT)),
            Paragraph(fmt(emp.get("leave_deduction",0)), PS("dv",8,False,RED,TA_RIGHT)),
            Paragraph(fmt(ytd.get("leave_deduction",0)), PS("dv",8,False,RED,TA_RIGHT)),
        ],
        [
            Paragraph("Late Deduction", PS("dr",8)),
            Paragraph("—", PS("dv",8,False,BLACK,TA_RIGHT)),
            Paragraph(fmt(emp.get("late_deduction",0)), PS("dv",8,False,RED,TA_RIGHT)),
            Paragraph(fmt(ytd.get("late_deduction",0)), PS("dv",8,False,RED,TA_RIGHT)),
        ],
        [
            Paragraph("Other Deductions", PS("dr",8)),
            Paragraph("—", PS("dv",8,False,BLACK,TA_RIGHT)),
            Paragraph(fmt(emp.get("other_deduction",0)), PS("dv",8,False,RED,TA_RIGHT)),
            Paragraph(fmt(ytd.get("other_deduction",0)), PS("dv",8,False,RED,TA_RIGHT)),
        ],
        [
            Paragraph("<b>Total Deductions</b>", PS("dr",8,True,RED)),
            Paragraph("—", PS("dv",8,False,BLACK,TA_RIGHT)),
            Paragraph(f"<b>{fmt(emp.get('total_deduction',0))}</b>", PS("dv",8,True,RED,TA_RIGHT)),
            Paragraph(f"<b>{fmt(ytd.get('total_deduction',0))}</b>", PS("dv",8,True,RED,TA_RIGHT)),
        ],
    ]
    cw3 = [W*0.45, W*0.1, W*0.225, W*0.225]
    ded_tbl = Table(ded_data, colWidths=cw3)
    ded_tbl.setStyle(TableStyle([
        ("BACKGROUND",    (0,0),(-1,0),  NAVY),
        ("ROWBACKGROUNDS",(0,1),(-1,-2), [WHITE, LGREY]),
        ("BACKGROUND",    (0,-1),(-1,-1),colors.HexColor("#ffebee")),
        ("GRID",          (0,0),(-1,-1), 0.3, MGREY),
        ("TOPPADDING",    (0,0),(-1,-1), 4),
        ("BOTTOMPADDING", (0,0),(-1,-1), 4),
        ("LEFTPADDING",   (0,0),(-1,-1), 6),
        ("RIGHTPADDING",  (0,0),(-1,-1), 6),
        ("LINEABOVE",     (0,-1),(-1,-1),0.8, RED),
    ]))
    story.append(ded_tbl)
    story.append(Spacer(1, 4*mm))

    # ── Net Pay Summary ─────────────────────────────────────────────────────
    story.append(Paragraph("NET PAY SUMMARY", PS("sh",8,True,NAVY)))
    story.append(Spacer(1,2*mm))

    ACCENT = colors.HexColor("#0288d1")
    net_data = [
        # Header
        [
            Paragraph("DESCRIPTION", PS("nh",7,True,WHITE)),
            Paragraph("THIS MONTH (PKR)", PS("nh",7,True,WHITE,TA_RIGHT)),
            Paragraph("YTD (PKR)", PS("nh",7,True,WHITE,TA_RIGHT)),
        ],
        # Net Payable
        [
            Paragraph("<b>Net Payable</b>", PS("nl",9,True,GREEN)),
            Paragraph(f"<b>{fmt(emp.get('net_payable',0))}</b>", PS("nv",10,True,GREEN,TA_RIGHT)),
            Paragraph(fmt(ytd.get('net_payable',0)), PS("ny",9,False,BLACK,TA_RIGHT)),
        ],
        # Arrear
        [
            Paragraph("Arrear", PS("al",8,False,BLACK)),
            Paragraph(fmt(emp.get("arrear",0)), PS("av",9,False,ACCENT,TA_RIGHT)),
            Paragraph(fmt(ytd.get('arrear',0)), PS("ay",9,False,BLACK,TA_RIGHT)),
        ],
        # Reimbursement
        [
            Paragraph("Reimbursement", PS("rl",8,False,BLACK)),
            Paragraph(fmt(emp.get("reimbursement",0)), PS("rv",9,False,ACCENT,TA_RIGHT)),
            Paragraph(fmt(ytd.get('reimbursement',0)), PS("ry",9,False,BLACK,TA_RIGHT)),
        ],
        # Total Payable
        [
            Paragraph("<b>TOTAL PAYABLE</b>", PS("tl",10,True,GOLD)),
            Paragraph(f"<b>{fmt(emp.get('total_payable',0))}</b>", PS("tv",12,True,GOLD,TA_RIGHT)),
            Paragraph(fmt(ytd.get('total_payable',0)), PS("ty",9,False,colors.HexColor("#ffd54f"),TA_RIGHT)),
        ],
    ]
    cw4 = [W*0.5, W*0.25, W*0.25]
    net_tbl = Table(net_data, colWidths=cw4)
    net_tbl.setStyle(TableStyle([
        ("BACKGROUND",    (0,0),(-1,0),  NAVY),
        ("BACKGROUND",    (0,1),(-1,3),  WHITE),
        ("ROWBACKGROUNDS",(0,1),(-1,3),  [colors.HexColor("#e8f5e9"), WHITE, LGREY]),
        ("BACKGROUND",    (0,4),(-1,4),  NAVY),
        ("GRID",          (0,0),(-1,-1), 0.3, MGREY),
        ("TOPPADDING",    (0,0),(-1,-1), 5),
        ("BOTTOMPADDING", (0,0),(-1,-1), 5),
        ("LEFTPADDING",   (0,0),(-1,-1), 6),
        ("RIGHTPADDING",  (0,0),(-1,-1), 6),
        ("LINEABOVE",     (0,4),(-1,4),  1.0, GOLD),
    ]))
    story.append(net_tbl)
    story.append(Spacer(1,4*mm))

    # ── Footer ──────────────────────────────────────────────────────────────
    footer_data = [[
        Paragraph(
            f"Generated by {company_name} Payroll System  ·  {month} {year}  ·  Confidential",
            PS("ft",7,False,colors.HexColor("#8fa3bb"),TA_CENTER)
        )
    ]]
    footer_tbl = Table(footer_data, colWidths=[W])
    footer_tbl.setStyle(TableStyle([
        ("BACKGROUND",    (0,0),(-1,-1), LGREY),
        ("TOPPADDING",    (0,0),(-1,-1), 4),
        ("BOTTOMPADDING", (0,0),(-1,-1), 4),
        ("LINEABOVE",     (0,0),(-1,-1), 0.5, MGREY),
    ]))
    story.append(footer_tbl)

    doc.build(story)
    buf.seek(0)
    return buf.read()


def safe_filename(name):
    """Convert employee name to safe filename."""
    return "".join(c if c.isalnum() or c in " _-" else "_" for c in name).strip().replace(" ","_")


def generate_single(emp, ytd, company_name, month, year, out_dir):
    """Generate one PDF for one employee. Returns filepath."""
    Path(out_dir).mkdir(parents=True, exist_ok=True)
    fname = f"{safe_filename(emp['name'])}_{month}_{year}.pdf"
    fpath = Path(out_dir) / fname
    pdf_bytes = build_payslip_bytes(emp, ytd, company_name, month, year)
    fpath.write_bytes(pdf_bytes)
    return str(fpath)


def generate_merged(emp_list, ytd_map, company_name, month, year, out_dir):
    """
    Generate one merged PDF containing all employees.
    emp_list = list of employee dicts
    ytd_map  = {name: ytd_dict}
    Returns filepath.
    """
    from reportlab.platypus import PageBreak
    Path(out_dir).mkdir(parents=True, exist_ok=True)
    fname = f"ALL_{month}_{year}.pdf"
    fpath = Path(out_dir) / fname

    buf = BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        leftMargin=15*mm, rightMargin=15*mm,
        topMargin=12*mm,  bottomMargin=12*mm
    )
    story = []
    for i, emp in enumerate(emp_list):
        ytd = ytd_map.get(emp["name"], {})
        # Build individual payslip content
        single_bytes = build_payslip_bytes(emp, ytd, company_name, month, year)
        # For merged we rebuild elements — simpler: just concatenate PDFs
        if i > 0:
            story.append(PageBreak())
        # Re-use build function but collect flowables
        story.extend(_build_flowables(emp, ytd, company_name, month, year))

    doc.build(story)
    buf.seek(0)
    fpath.write_bytes(buf.read())
    return str(fpath)


def _build_flowables(emp, ytd, company_name, month, year):
    """Return list of reportlab flowables for one payslip (used in merged PDF)."""
    # Build as single then re-parse — easiest approach is to
    # rebuild the story list directly
    from io import BytesIO as BIO
    # We'll inline a simplified version that returns flowables
    buf = BIO()
    doc = SimpleDocTemplate(buf, pagesize=A4,
        leftMargin=15*mm, rightMargin=15*mm,
        topMargin=12*mm, bottomMargin=12*mm)
    # Capture flowables by overriding build
    captured = []
    original_build = doc.build

    pdf_bytes = build_payslip_bytes(emp, ytd, company_name, month, year)
    return pdf_bytes  # returns bytes for this employee


def generate_batch_separate(emp_list, ytd_map, company_name, month, year, out_dir):
    """Generate one PDF per employee. Returns list of filepaths."""
    Path(out_dir).mkdir(parents=True, exist_ok=True)
    paths = []
    for emp in emp_list:
        ytd = ytd_map.get(emp["name"], {})
        p = generate_single(emp, ytd, company_name, month, year, out_dir)
        paths.append(p)
    return paths


def merge_pdfs(pdf_bytes_list, out_path):
    """Merge list of PDF bytes into one file using PyPDF2 or manual concatenation."""
    try:
        from pypdf import PdfWriter
        writer = PdfWriter()
        for pb in pdf_bytes_list:
            from io import BytesIO as BIO
            from pypdf import PdfReader
            reader = PdfReader(BIO(pb))
            for page in reader.pages:
                writer.add_page(page)
        with open(out_path, "wb") as f:
            writer.write(f)
        return str(out_path)
    except ImportError as exc:
        raise RuntimeError(
            "Cannot merge payslips because dependency 'pypdf' is not installed."
        ) from exc
