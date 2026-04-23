import builtins
import io
import sqlite3
import tempfile
import unittest
import zipfile
from pathlib import Path

import app as app_module
import database
import payslip_generator
import year_manager


class AppRouteSecurityTests(unittest.TestCase):
    def setUp(self):
        self.client = app_module.app.test_client()

    def test_dashboard_requires_eula(self):
        original = app_module.is_eula_accepted
        try:
            app_module.is_eula_accepted = lambda: False
            resp = self.client.get("/", follow_redirects=False)
            self.assertEqual(resp.status_code, 302)
            self.assertEqual(resp.headers.get("Location"), "/eula")
        finally:
            app_module.is_eula_accepted = original

    def test_backup_download_blocks_path_traversal(self):
        resp = self.client.post(
            "/years",
            data={"action": "download_backup", "backup_name": "..\\app.py"},
            follow_redirects=False,
        )
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(resp.headers.get("Location"), "/years")

    def test_import_rejects_non_payroll_extension(self):
        data = {
            "year": "2025",
            "month": "January",
            "file": (io.BytesIO(b"dummy"), "malicious.exe"),
        }
        resp = self.client.post(
            "/import",
            data=data,
            content_type="multipart/form-data",
            follow_redirects=True,
        )
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b"Please upload a valid Excel or CSV file.", resp.data)


class MergeBehaviorTests(unittest.TestCase):
    def test_merge_pdfs_raises_when_pypdf_missing(self):
        original_import = builtins.__import__

        def fake_import(name, *args, **kwargs):
            if name == "pypdf":
                raise ImportError("mocked missing pypdf")
            return original_import(name, *args, **kwargs)

        builtins.__import__ = fake_import
        try:
            with self.assertRaises(RuntimeError):
                payslip_generator.merge_pdfs([b"not-a-real-pdf"], "out.pdf")
        finally:
            builtins.__import__ = original_import


class YearRestoreValidationTests(unittest.TestCase):
    def test_restore_year_rejects_nested_db_path(self):
        with tempfile.TemporaryDirectory() as td:
            tmp_base = Path(td)
            bad_zip = tmp_base / "bad.zip"
            with zipfile.ZipFile(bad_zip, "w", zipfile.ZIP_DEFLATED) as zf:
                zf.writestr("nested/FY2025-26.db", b"bad")

            original_base = year_manager.BASE_DIR
            original_backups = year_manager.BACKUPS_DIR
            try:
                year_manager.BASE_DIR = tmp_base
                year_manager.BACKUPS_DIR = tmp_base / "backups"
                year_manager.BACKUPS_DIR.mkdir(parents=True, exist_ok=True)
                with self.assertRaises(ValueError):
                    year_manager.restore_year(str(bad_zip))
            finally:
                year_manager.BASE_DIR = original_base
                year_manager.BACKUPS_DIR = original_backups

    def test_restore_year_accepts_valid_file_name(self):
        with tempfile.TemporaryDirectory() as td:
            tmp_base = Path(td)
            good_zip = tmp_base / "good.zip"
            with zipfile.ZipFile(good_zip, "w", zipfile.ZIP_DEFLATED) as zf:
                zf.writestr("FY2025-26.db", b"sqlite-bytes")

            original_base = year_manager.BASE_DIR
            original_backups = year_manager.BACKUPS_DIR
            try:
                year_manager.BASE_DIR = tmp_base
                year_manager.BACKUPS_DIR = tmp_base / "backups"
                year_manager.BACKUPS_DIR.mkdir(parents=True, exist_ok=True)
                label = year_manager.restore_year(str(good_zip))
                self.assertEqual(label, "FY2025-26")
                self.assertTrue((tmp_base / "FY2025-26.db").exists())
            finally:
                year_manager.BASE_DIR = original_base
                year_manager.BACKUPS_DIR = original_backups


class SchemaMigrationTests(unittest.TestCase):
    def test_init_db_migrates_legacy_unique_constraint(self):
        with tempfile.TemporaryDirectory() as td:
            db_path = Path(td) / "legacy.db"
            conn = sqlite3.connect(str(db_path))
            conn.execute(
                """
                CREATE TABLE payroll (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    year INTEGER NOT NULL,
                    month TEXT NOT NULL,
                    month_order INTEGER NOT NULL,
                    employee_code TEXT,
                    name TEXT NOT NULL,
                    department TEXT,
                    designation TEXT,
                    status TEXT,
                    district TEXT,
                    city TEXT,
                    date_joined TEXT,
                    salary REAL DEFAULT 0,
                    basic REAL DEFAULT 0,
                    house_rent REAL DEFAULT 0,
                    utility REAL DEFAULT 0,
                    medical REAL DEFAULT 0,
                    gross_pay REAL DEFAULT 0,
                    travelling REAL DEFAULT 0,
                    accommodation REAL DEFAULT 0,
                    working_days REAL DEFAULT 0,
                    gross_total REAL DEFAULT 0,
                    income_tax REAL DEFAULT 0,
                    eobi REAL DEFAULT 0,
                    leaves REAL DEFAULT 0,
                    leave_deduction REAL DEFAULT 0,
                    late_deduction REAL DEFAULT 0,
                    other_deduction REAL DEFAULT 0,
                    total_deduction REAL DEFAULT 0,
                    net_payable REAL DEFAULT 0,
                    arrear REAL DEFAULT 0,
                    reimbursement REAL DEFAULT 0,
                    total_payable REAL DEFAULT 0,
                    UNIQUE(year, month, name)
                )
                """
            )
            conn.execute(
                """
                INSERT INTO payroll (year, month, month_order, employee_code, name)
                VALUES (2025, 'January', 1, NULL, 'Alice')
                """
            )
            conn.commit()
            conn.close()

            database.init_db(db_path=str(db_path))

            conn = sqlite3.connect(str(db_path))
            schema_sql = conn.execute(
                "SELECT sql FROM sqlite_master WHERE type='table' AND name='payroll'"
            ).fetchone()[0]
            self.assertIn("UNIQUE(year, month, employee_code, name)", schema_sql)
            self.assertNotIn("UNIQUE(year, month, name)", schema_sql)
            row = conn.execute(
                "SELECT employee_code, name FROM payroll WHERE year=2025 AND month='January'"
            ).fetchone()
            conn.close()
            self.assertEqual(row[0], "")
            self.assertEqual(row[1], "Alice")


if __name__ == "__main__":
    unittest.main()
