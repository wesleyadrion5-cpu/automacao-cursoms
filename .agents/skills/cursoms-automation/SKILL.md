---
name: cursoms-automation
description: Use when modifying or debugging the CursoMS migration automation in this repo. Start by checking logs/erro_log_*.txt, then inspect Meus testes copy.py and derived variants, prioritize Selenium session and window stability, robust module matching on the new site, and validate changes with python -m py_compile.
---

# CursoMS Automation

Use this skill for maintenance of the migration robots in this repository.

## Workflow

1. Read the newest files in `logs/erro_log_*.txt` before changing code.
2. Prioritize fixes in this order:
   - Selenium session or window failures
   - Module lookup and duplicate detection on the new platform
   - Video upload flow
   - Material and slide upload flow
3. Preserve the original script when the change is risky by creating a derived `.py` variant.
4. Prefer shared helpers for:
   - Module-name normalization and matching
   - Safe window switching
   - Diagnostics capture to `logs/diagnosticos`
   - Reusable searches on the new platform
5. Validate every edited script with `python -m py_compile "<arquivo>.py"`.

## Key Files

- `Meus testes copy.py`: current base automation script
- `Meus testes copy melhorado.py`: derived script for safer experiments and targeted improvements
- `logs/`: recurring production errors to guide fixes
- `config_unificada.json`: runtime settings

## Notes

- Avoid weakening the “skip if already exists” behavior on the new platform.
- When a module is created but not found afterwards, retry the search on `/modules` before treating it as failure.
- When Selenium loses session, stop cascading actions and save diagnostics.
