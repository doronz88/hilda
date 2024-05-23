import logging
import subprocess
import sys
from types import ModuleType
from typing import Optional

logger = logging.getLogger(__name__)


def get_lldb_python_path() -> str:
    result = subprocess.run(['lldb', '-P'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True)
    return result.stdout.strip()


def import_lldb() -> Optional[ModuleType]:
    lldb_python_path = get_lldb_python_path()
    if lldb_python_path not in sys.path:
        sys.path.append(lldb_python_path)
    import lldb
    return lldb


lldb = import_lldb()
