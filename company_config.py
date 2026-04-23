# ============================================================
#  COMPANY CONFIGURATION — SoftFlow Ltd
#  Payroll_View v1.0
# ============================================================
#  To update client details, edit ONLY this file.
#  Do not modify any other Python files.
# ============================================================

# ── Client Details ────────────────────────────────────────────
COMPANY_NAME   = "Berlitz"
COMPANY_REGION = "Lahore"
# Note: TAX_YEAR is stored in config.json (changeable without code edit)

# ── Software Details ──────────────────────────────────────────
SOFTWARE_NAME    = "Payroll_View"
SOFTWARE_VERSION = "v1.0"
DEVELOPER        = "SoftFlow Ltd"
AUTHOR           = "Iqbal Ahmed"
COPYRIGHT_YEAR   = "2026"
CONTACT          = "softflow.ltd@email.com"

# ─────────────────────────────────────────────────────────────
# DO NOT MODIFY BELOW THIS LINE
# ─────────────────────────────────────────────────────────────
COMPANY_INFO = {
    "name":   COMPANY_NAME,
    "region": COMPANY_REGION,
}

SOFTWARE_INFO = {
    "name":      SOFTWARE_NAME,
    "version":   SOFTWARE_VERSION,
    "developer": DEVELOPER,
    "author":    AUTHOR,
    "copyright": f"© {COPYRIGHT_YEAR} {DEVELOPER}",
    "contact":   CONTACT,
}
