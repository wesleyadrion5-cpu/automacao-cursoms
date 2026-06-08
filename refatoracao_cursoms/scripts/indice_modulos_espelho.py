from __future__ import annotations

import json
import re
from pathlib import Path
import sys


CURRENT_DIR = Path(__file__).resolve().parent
SRC_DIR = CURRENT_DIR.parent / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from cursoms_refatoracao.dom_contract import get_default_mirror_base
from cursoms_refatoracao.matching import is_plano_estudos_module, normalize_text


MODULE_ROW_PATTERN = re.compile(
    r"<h6>(?P<name>.*?)</h6>.*?Professor:\s*<span>(?P<teacher>.*?)</span>.*?href=\"(?P<lessons>https://novo\.cursoms\.com\.br/modules/lessons/[^\"]+)\"",
    re.IGNORECASE | re.DOTALL,
)


def strip_html(text: str) -> str:
    clean = re.sub(r"<.*?>", "", text or "", flags=re.DOTALL)
    return re.sub(r"\s+", " ", clean).strip()


def main() -> int:
    modules_file = get_default_mirror_base() / r"novo.cursoms.com.br\modules.html"
    if not modules_file.exists():
        print(f"Arquivo nao encontrado: {modules_file}")
        return 1

    content = modules_file.read_text(encoding="utf-8", errors="ignore")
    rows = []
    seen = set()

    for match in MODULE_ROW_PATTERN.finditer(content):
        name = strip_html(match.group("name"))
        teacher = strip_html(match.group("teacher"))
        lessons_url = match.group("lessons").strip()
        key = (normalize_text(name), lessons_url)
        if key in seen:
            continue
        seen.add(key)
        rows.append(
            {
                "nome": name,
                "nome_normalizado": normalize_text(name),
                "professor": teacher,
                "url_aulas": lessons_url,
                "plano_estudos": is_plano_estudos_module(name),
            }
        )

    output_path = CURRENT_DIR.parent / "referencias" / "indice_modulos_espelho.json"
    output_path.write_text(
        json.dumps(rows, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(f"Modulos extraidos: {len(rows)}")
    print(f"Arquivo gerado: {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
