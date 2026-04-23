import os
import sys
from pathlib import Path


APP_BASE_DIR = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))

if getattr(sys, "frozen", False):
    _default_data_dir = Path(os.environ.get("LOCALAPPDATA", str(Path.home()))) / "PEF_Payroll"
else:
    _default_data_dir = Path(__file__).resolve().parent

DATA_DIR = Path(os.environ.get("PEF_PAYROLL_DATA_DIR", str(_default_data_dir))).resolve()
DATA_DIR.mkdir(parents=True, exist_ok=True)


def path_in_data(*parts: str) -> Path:
    return DATA_DIR.joinpath(*parts)
