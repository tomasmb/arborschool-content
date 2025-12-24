import json
import os

updates = {
    "Q11": {"primary": "A-M1-NUM-02-02"},
    "Q14": {"primary": "A-M1-NUM-02-11"},
    "Q15": {"primary": "A-M1-NUM-02-11"},
    "Q16": {"primary": "A-M1-NUM-02-07"}, # "Determinación del porcentaje..."
    "Q38": {"primary": "A-M1-ALG-05-11"},
    "Q43": {"primary": "A-M1-ALG-06-12"}, # "Resolución de problemas de optimización..."
    "Q45": {"primary": "A-M1-GEO-01-14"},
    "Q46": {"primary": "A-M1-GEO-01-04"},
    "Q47": {"primary": "A-M1-GEO-02-15"}, # "Resolución de problemas contextualizados..."
    "Q48": {"primary": "A-M1-GEO-03-12"},
    "Q50": {"primary": "A-M1-GEO-03-13"},
    "Q52": {"primary": "A-M1-GEO-03-13"},
    "Q54": {"primary": "A-M1-PROB-01-18"},
    "Q57": {"primary": "A-M1-PROB-01-18"}
}

base_dir = "app/data/pruebas/finalizadas/prueba-invierno-2026/qti"

print("Applying manual atom updates to 2026...")
for q_id, update in updates.items():
    path = os.path.join(base_dir, q_id, "metadata_tags.json")
    if os.path.exists(path):
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            atoms = data.get("selected_atoms", [])
            changed = False
            
            target_id = update["primary"] # All are single strings in this batch manifest
                
            for atom in atoms:
                curr_id = atom.get("atom_id")
                # If this is our target, make it primary
                if curr_id == target_id:
                    if atom.get("relevance") != "primary":
                        atom["relevance"] = "primary"
                        changed = True
                # If we have multiple atoms (like Q16, Q43, Q47) and this is NOT the target,
                # we leave it as secondary (which is what it is currently).
                # No action needed for non-targets as they are already secondary.

            # Special check: If we have single-atom files, we might have missed the target_id check 
            # if the ID was slightly off or just to be safe, let's enforce "if 1 atom -> primary" rule too.
            if len(atoms) == 1:
                if atoms[0].get("relevance") != "primary":
                    atoms[0]["relevance"] = "primary"
                    changed = True

            if changed:
                with open(path, 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
                print(f"Updated {q_id}: Atoms updated.")
            else:
                print(f"Skipped {q_id}: Already correct or target not found.")
                
        except Exception as e:
            print(f"Error updating {path}: {e}")
    else:
        print(f"Warning: {path} not found.")
