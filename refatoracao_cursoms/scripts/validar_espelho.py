from pathlib import Path
import sys


CURRENT_DIR = Path(__file__).resolve().parent
SRC_DIR = CURRENT_DIR.parent / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from cursoms_refatoracao.dom_contract import build_contract, get_default_mirror_base


def main() -> int:
    base_dir = get_default_mirror_base()
    contract = build_contract()
    failures: list[str] = []

    print(f"Base do espelho: {base_dir}")
    print("")

    for area, expectations in contract.items():
        print(f"[{area}]")
        for expectation in expectations:
            target = base_dir / expectation.relative_path
            if not target.exists():
                failures.append(f"Arquivo ausente: {target}")
                print(f"  FALHA - arquivo ausente: {target}")
                continue

            content = target.read_text(encoding="utf-8", errors="ignore")
            missing = [marker for marker in expectation.required_markers if marker not in content]
            if missing:
                failures.append(f"Marcadores ausentes em {target}: {missing}")
                print(f"  FALHA - marcadores ausentes em {target.name}: {', '.join(missing)}")
                continue

            print(f"  OK - {target.name}")
        print("")

    if failures:
        print("Resumo: contrato do DOM com falhas.")
        for item in failures:
            print(f"- {item}")
        return 1

    print("Resumo: contrato do DOM validado com sucesso.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
