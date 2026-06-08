import re

path = r"d:\Automação CursoMS\Programação (Wesley)\Programação (Wesley)\Subir Aula CursoMS\Subir Aulas (Forma Final)\Subir Aula - Modulos Varios.py"

with open(path, "r", encoding="utf-8") as f:
    lines = f.readlines()

print(f"Total lines: {len(lines)}")

classes = []
for idx, line in enumerate(lines):
    line_num = idx + 1
    if line.startswith("class "):
        classes.append((line_num, line.strip()))

for i, (num, name) in enumerate(classes):
    end = len(lines)
    if i + 1 < len(classes):
        end = classes[i+1][0] - 1
    print(f"Linha {num} até {end}: {name}")
