import json
import os

files_to_check = [
    "app/data/pruebas/finalizadas/Prueba-invierno-2025/qti/Q16/metadata_tags.json",
    "app/data/pruebas/finalizadas/Prueba-invierno-2025/qti/Q45/metadata_tags.json",
    "app/data/pruebas/finalizadas/Prueba-invierno-2025/qti/Q47/metadata_tags.json",
    "app/data/pruebas/finalizadas/Prueba-invierno-2025/qti/Q48/metadata_tags.json",
    "app/data/pruebas/finalizadas/Prueba-invierno-2025/qti/Q50/metadata_tags.json",
    "app/data/pruebas/finalizadas/Prueba-invierno-2025/qti/Q51/metadata_tags.json",
    "app/data/pruebas/finalizadas/Prueba-invierno-2025/qti/Q53/metadata_tags.json",
    "app/data/pruebas/finalizadas/Prueba-invierno-2025/qti/Q57/metadata_tags.json",
    "app/data/pruebas/finalizadas/Prueba-invierno-2025/qti/Q65/metadata_tags.json"
]

print("Analysis of Restored Files:")
print("-" * 30)

for path in files_to_check:
    if os.path.exists(path):
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            q_id = path.split('/')[-2]
            atoms = data.get("selected_atoms", [])
            
            print(f"\n{q_id}:")
            if not atoms:
                print("  No atoms found.")
                continue

            for atom in atoms:
                print(f"  - [{atom.get('relevance', '').upper()}] {atom.get('atom_title')} ({atom.get('atom_id')})")
                print(f"    Reasoning: {atom.get('reasoning')[:100]}...")
        except Exception as e:
            print(f"Error reading {path}: {e}")
