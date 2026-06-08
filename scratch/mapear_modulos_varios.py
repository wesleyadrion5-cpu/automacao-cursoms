import re

path = r"d:\Automação CursoMS\Programação (Wesley)\Programação (Wesley)\Subir Aula CursoMS\Subir Aulas (Forma Final)\Subir Aula - Modulos Varios.py"

with open(path, "r", encoding="utf-8") as f:
    lines = f.readlines()

print(f"Total lines: {len(lines)}")

# Buscar imports de flask, inicialização do flask, rotas, etc.
flask_refs = []
ctk_refs = []
class_defs = []

for idx, line in enumerate(lines):
    line_num = idx + 1
    if "flask" in line.lower():
        flask_refs.append((line_num, line.strip()))
    if "customtkinter" in line.lower() or "ctk" in line.lower():
        # Apenas algumas ocorrências relevantes
        if "class" in line or "def " in line or "init" in line or "theme" in line:
            ctk_refs.append((line_num, line.strip()))
    if line.startswith("class "):
        class_defs.append((line_num, line.strip()))

print("\n--- Classes encontradas ---")
for num, text in class_defs:
    print(f"Linha {num}: {text}")

print("\n--- Referências a Flask (Primeiras 30) ---")
for num, text in flask_refs[:30]:
    print(f"Linha {num}: {text}")

print("\n--- Referências a CustomTkinter / CTK (Amostra) ---")
for num, text in ctk_refs[:20]:
    print(f"Linha {num}: {text}")
