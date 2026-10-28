"""Guarda de regresión contra XSS (issue #10).

Los datos que escribe el usuario (nombres, teléfonos, notas, mensajes de error) nunca
deben interpolarse en una plantilla de innerHTML sin pasar por esc().
"""
import re
from pathlib import Path

import pytest

FRONTEND = Path(__file__).resolve().parents[2] / "frontend"
# Expresiones ${...} que tocan campos controlados por el usuario
RISKY = re.compile(r"\$\{([^}]*\.(?:name|customer_name|customer_phone|notes|message)\b[^}]*)\}")


def unescaped_interpolations(html: str) -> list[str]:
    found = []
    for line in html.splitlines():
        if "textContent" in line:  # textContent no interpreta HTML: es seguro
            continue
        found += [m.group(1) for m in RISKY.finditer(line) if not m.group(1).strip().startswith("esc(")]
    return found


@pytest.mark.parametrize("page", ["index.html", "admin.html"])
def test_user_controlled_fields_are_escaped_in_templates(page):
    html = (FRONTEND / page).read_text(encoding="utf-8")
    assert unescaped_interpolations(html) == []


def test_checker_detects_the_original_vulnerability():
    vulnerable = "tr.innerHTML = `<td>${a.customer_name}</td><td>${esc(a.customer_phone)}</td>`"
    assert unescaped_interpolations(vulnerable) == ["a.customer_name"]
