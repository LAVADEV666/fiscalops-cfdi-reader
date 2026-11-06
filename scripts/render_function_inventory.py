"""Append the complete lexical function index to the functional inventory."""
from collections import defaultdict
from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[1]
inventory = json.loads((ROOT / 'tests/audit/evidence/inventory.json').read_text(encoding='utf-8'))
doc = ROOT / 'docs/01_INVENTARIO_FUNCIONAL.md'
marker = '<!-- FUNCTION_INDEX -->'
prefix = doc.read_text(encoding='utf-8').split(marker)[0] + marker
groups = defaultdict(list)
for item in inventory['functions']:
    groups[item['name']].append(item['line'])
lines = ['\n\n## Índice completo de declaraciones nombradas\n',
         'Índice léxico reproducible: incluye helpers anidados; no cubre funciones flecha/anónimas como símbolos propios ni sustituye un AST. '
         'Las resoluciones efectivas de funciones de producto están verificadas en00; las propiedades de eventos requieren considerar su elemento y API de registro.\n',
         '| Nombre | Líneas del HTML original | Observación |', '|---|---|---|']
overrides = {'renderChecks': 1128, 'applyColumnEditor': 1129, 'allFieldRows': 1135, 'openPreview': 1136}
for name, locations in sorted(groups.items(), key=lambda item: item[1][0]):
    note = ('Declaración repetida; última L' + str(locations[-1])) if len(locations) > 1 else 'Declaración única en índice'
    if name in overrides:
        note += '; asignación final L' + str(overrides[name])
    lines.append(f'| `{name}` | ' + ', '.join(map(str, locations)) + f' | {note} |')
lines += ['\n## Asignaciones a funciones (incluye propiedades de eventos)\n',
          '| Símbolo/propiedad | Línea |', '|---|---|']
for item in inventory['function_assignments']:
    lines.append(f"| `{item['name']}` | {item['line']} |")
lines += ['\n## Elementos con ID para conservar y probar\n', '| ID | Tag | Línea |', '|---|---|---|']
for item in inventory['elements']:
    lines.append(f"| `{item['id']}` | {item['tag']} | {item['line']} |")
doc.write_text(prefix + '\n'.join(lines) + '\n', encoding='utf-8')
print(f"Indexed {len(inventory['functions'])} named declarations, {len(groups)} unique names, "
      f"{len(inventory['function_assignments'])} assignments and {len(inventory['elements'])} IDs")
