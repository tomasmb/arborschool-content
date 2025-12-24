import os
import json

def apply_fix():
    base_dir = "app/data/pruebas/finalizadas/Prueba-invierno-2025"
    count = 0

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
                    
                    # Only apply fix if there are NO primary atoms
                    if not has_primary:
                        print(f"Fixing {path}...")
                        changed = False
                        for atom in atoms:
                            if atom.get("relevance") == "secondary":
                                atom["relevance"] = "primary"
                                changed = True
                        
                        if changed:
                            with open(path, 'w', encoding='utf-8') as f:
                                json.dump(data, f, ensure_ascii=False, indent=2)
                            count += 1
                except Exception as e:
                    print(f"Error processing {path}: {e}")
    
    print(f"Successfully fixed {count} files.")

if __name__ == "__main__":
    apply_fix()
