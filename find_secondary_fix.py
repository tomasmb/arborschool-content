import os
import json

def find_secondary_only():
    base_dir = "app/data/pruebas/finalizadas/Prueba-invierno-2025"
    secondary_only_files = []

    for root, dirs, files in os.walk(base_dir):
        for file in files:
            if file == "metadata_tags.json":
                path = os.path.join(root, file)
                try:
                    with open(path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    
                    atoms = data.get("selected_atoms", [])
                    if not atoms:
                        continue
                        
                    has_primary = any(a.get("relevance") == "primary" for a in atoms)
                    if not has_primary:
                        secondary_only_files.append(path)
                except:
                    pass
    
    print(f"Found {len(secondary_only_files)} files with ONLY secondary atoms:")
    for p in sorted(secondary_only_files):
        print(p)

if __name__ == "__main__":
    find_secondary_only()
