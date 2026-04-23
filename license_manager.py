"""
License Manager — SoftFlow Ltd (EULA only)
"""
import json
from datetime import datetime
from company_config import SOFTWARE_VERSION, DEVELOPER, AUTHOR, COPYRIGHT_YEAR, SOFTWARE_NAME, COMPANY_NAME
from runtime_paths import path_in_data

EULA_FILE = path_in_data("eula_accepted.json")

def is_eula_accepted() -> bool:
    if EULA_FILE.exists():
        try:
            d = json.loads(EULA_FILE.read_text())
            return d.get("accepted", False)
        except Exception:
            pass
    return False

def accept_eula():
    EULA_FILE.write_text(json.dumps({
        "accepted": True,
        "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "version": SOFTWARE_VERSION,
    }, indent=2))

EULA_TEXT = f"""END USER LICENSE AGREEMENT (EULA)
{SOFTWARE_NAME} {SOFTWARE_VERSION}
{DEVELOPER} © {COPYRIGHT_YEAR} — All Rights Reserved

PLEASE READ THIS AGREEMENT CAREFULLY BEFORE USING THIS SOFTWARE.

1. GRANT OF LICENSE
{DEVELOPER} grants you a non-exclusive, non-transferable license to install and use
{SOFTWARE_NAME} ("Software") on a single computer. This license is valid only for
{COMPANY_NAME} and this specific installation.

2. OWNERSHIP
The Software is the intellectual property of {DEVELOPER} and is protected by copyright
law. {AUTHOR} is the author and developer of this Software. All rights not expressly
granted are reserved by {DEVELOPER}.

3. RESTRICTIONS
You may NOT:
  a) Copy, modify, or distribute the Software without written permission from {DEVELOPER}.
  b) Reverse engineer, decompile, or disassemble the Software.
  c) Transfer, sublicense, rent, or lease the Software to any third party.
  d) Remove or alter any copyright, trademark, or proprietary notices.
  e) Use the Software for any unlawful purpose.
  f) Use this Software for any company or organisation other than {COMPANY_NAME}.

4. IMPORTANT DISCLAIMER — CALCULATIONS
THE SOFTWARE DOES NOT CALCULATE OR COMPUTE SALARIES, RELATED DEDUCTIONS OR ADDITIONS.
All financial figures — including but not limited to gross pay, net pay, income tax,
EOBI, leave deductions, arrears, and reimbursements — are imported directly from
user-provided Excel payroll sheets. {DEVELOPER} accepts NO responsibility or liability
for the accuracy of any figures, calculations, or financial data entered into or
displayed by this Software. The Software serves solely as a payroll data management,
reporting, and payslip generation tool. Calculations performed by this Software are
limited to report-level totals and grand totals only.

5. USER RESPONSIBILITY
You are solely responsible for:
  a) The accuracy and completeness of all payroll data imported into the Software.
  b) Compliance with applicable tax, labour, and financial regulations.
  c) Verification of all figures before use in official documents or submissions.
  d) Maintaining backups of your data.

6. DATA PRIVACY
The Software operates entirely offline on your local computer. No data is transmitted
to {DEVELOPER} or any third party. You are responsible for the security of your data files.

7. LIMITATION OF LIABILITY
TO THE MAXIMUM EXTENT PERMITTED BY LAW, {DEVELOPER.upper()} SHALL NOT BE LIABLE FOR ANY
INDIRECT, INCIDENTAL, SPECIAL, CONSEQUENTIAL, OR PUNITIVE DAMAGES ARISING FROM YOUR
USE OF OR INABILITY TO USE THE SOFTWARE.

8. TERMINATION
This license is effective until terminated. It will terminate automatically if you
fail to comply with any term of this Agreement.

9. GOVERNING LAW
This Agreement shall be governed by the laws of Pakistan.

By clicking "I Agree", you confirm that you have read, understood, and agree to be
bound by the terms of this Agreement.

{DEVELOPER}
Developer: {AUTHOR}
Contact: softflow.ltd@email.com
© {COPYRIGHT_YEAR} {DEVELOPER}. All Rights Reserved.
"""
