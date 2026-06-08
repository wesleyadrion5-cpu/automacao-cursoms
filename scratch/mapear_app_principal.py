import re

path = r"d:\Automação CursoMS\Programação (Wesley)\Programação (Wesley)\Subir Aula CursoMS\Subir Aulas (Forma Final)\Subir Aula - Modulos Varios.py"

with open(path, "r", encoding="utf-8") as f:
    lines = f.readlines()

in_app = False
method_lines = []

for idx, line in enumerate(lines):
    line_num = idx + 1
    if line.startswith("class AppPrincipal"):
        in_app = True
        print(f"AppPrincipal inicia na linha {line_num}")
    elif line.startswith("class ") and in_app:
        in_app = False
        print(f"AppPrincipal termina antes da linha {line_num}")
    
    if in_app:
        match = re.match(r"^\s+def\s+(\w+)\(", line)
        if match:
            method_lines.append((line_num, match.group(1)))

print("\nMétodos da classe AppPrincipal:")
for num, name in method_lines:
    print(f"Linha {num}: {name}")
