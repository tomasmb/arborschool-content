import os
import json

def find_secondary_only_2026():
    base_dir = "app/data/pruebas/finalizadas/prueba-invierno-2026"
    secondary_only_files = []

    if not os.path.exists(base_dir):
        print(f"Directory not found: {base_dir}")
        return

    for root, dirs, files in os.walk(base_dir):
        for file in files:
            if file == "metadata_tags.json":
                path = os.path.join(root, file)
                try:
                    with open(path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    
                    # Only check if status is PASS (as per user request context, though checking all is safer)
                    # The user specifically mentioned "questions with status passed".
                    # Let's check all for completeness but note the status.
                    status = data.get("validation", {}).get("status", "UNKNOWN")
                    
                    atoms = data.get("selected_atoms", [])
                    if not atoms:
                        continue
                        
                    has_primary = any(a.get("relevance") == "primary" for a in atoms)
                    if not has_primary:
                        q_id = path.split('/')[-2]
                        secondary_only_files.append({"id": q_id, "status": status, "path": path})
                except:
                    pass
    
    print(f"Found {len(secondary_only_files)} files with ONLY secondary atoms in 2026:")
    for item in sorted(secondary_only_files, key=lambda x: int(x['id'][1:]) if x['id'][1:].isdigit() else 999):
        print(f"{item['id']} ({item['status']})")

if __name__ == "__main__":
    find_secondary_only_2026()
