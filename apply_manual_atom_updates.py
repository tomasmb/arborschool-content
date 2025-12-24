import json
import os

updates = {
    "Q16": {"primary": "A-M1-NUM-02-11"},
    "Q45": {"primary": "A-M1-GEO-02-15"},
    "Q47": {"primary": "A-M1-GEO-01-14"},
    "Q48": {"primary": "A-M1-GEO-01-13"},
    "Q50": {"primary": "A-M1-GEO-01-14"},
    "Q51": {"primary": ["A-M1-NUM-01-05", "A-M1-NUM-01-08"]},
    "Q53": {"primary": "A-M1-GEO-03-13"},
    "Q57": {"primary": "A-M1-PROB-01-17"},
    "Q65": {"primary": "A-M1-PROB-03-08"}
}

base_dir = "app/data/pruebas/finalizadas/Prueba-invierno-2025/qti"

print("Applying manual atom updates...")
for q_id, update in updates.items():
    path = os.path.join(base_dir, q_id, "metadata_tags.json")
    if os.path.exists(path):
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            atoms = data.get("selected_atoms", [])
            changed = False
            
            target_ids = update["primary"]
            if isinstance(target_ids, str):
                target_ids = [target_ids]
                
            for atom in atoms:
                curr_id = atom.get("atom_id")
                # If this is one of our targets, make it primary
                if curr_id in target_ids:
                    if atom.get("relevance") != "primary":
                        atom["relevance"] = "primary"
                        changed = True
                else:
                    # If this question only has 1 atom (e.g. Q16, Q47...), it must be primary
                    # But if we are in Q45 (multi), others should remain secondary unless specified
                    if len(atoms) == 1:
                         if atom.get("relevance") != "primary":
                            atom["relevance"] = "primary"
                            changed = True

            if changed:
                with open(path, 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
                print(f"Updated {q_id}: Atoms updated to PRIMARY.")
            else:
                print(f"Skipped {q_id}: Already correct.")
                
        except Exception as e:
            print(f"Error updating {path}: {e}")
    else:
        print(f"Warning: {path} not found.")
