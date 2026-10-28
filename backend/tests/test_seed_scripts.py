"""#8: los scripts de siembra deben correr en consolas Windows (cp1252)."""
import os
import subprocess
import sys
from pathlib import Path

import pytest

BACKEND = Path(__file__).resolve().parents[1]


def _run(script, db_path):
    env = {
        **os.environ,
        "DATABASE_URL": "sqlite:///" + db_path.as_posix(),
        "PYTHONIOENCODING": "cp1252",  # simula la consola de Windows
        "PYTHONUTF8": "0",
    }
    return subprocess.run(
        [sys.executable, script], cwd=BACKEND, env=env, capture_output=True, text=True, timeout=120
    )


@pytest.mark.parametrize("script", ["seed.py", "seed_history.py"])
def test_seed_scripts_run_with_cp1252_console(tmp_path, script):
    db = tmp_path / "seed.db"
    if script == "seed_history.py":
        assert _run("seed.py", db).returncode == 0  # necesita los servicios
    result = _run(script, db)
    assert result.returncode == 0, result.stderr[-500:]


def test_seed_is_idempotent(tmp_path):
    db = tmp_path / "seed.db"
    assert _run("seed.py", db).returncode == 0
    second = _run("seed.py", db)
    assert second.returncode == 0
    assert "Ya existen" in second.stdout
