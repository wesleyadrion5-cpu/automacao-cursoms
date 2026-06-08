import re

path = r"d:\Automação CursoMS\Programação (Wesley)\Programação (Wesley)\Subir Aula CursoMS\Subir Aulas (Forma Final)\Subir Aula - Modulos Varios.py"

with open(path, "r", encoding="utf-8") as f:
    lines = f.readlines()

in_motor = False
methods = []

for idx, line in enumerate(lines):
    line_num = idx + 1
    if line.startswith("class MotorRobo"):
        in_motor = True
    elif line.startswith("class ") and in_motor:
        in_motor = False
        
    if in_motor:
        match = re.match(r"^\s+def\s+(\w+)\(", line)
        if match:
            methods.append((line_num, match.group(1)))

print("Métodos de MotorRobo:")
for num, name in methods:
    print(f"Linha {num}: {name}")
