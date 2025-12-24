import os
import json

def analyze_failures():
    base_dir = "app/data/pruebas/finalizadas/prueba-invierno-2026/qti"
    fails = []
    skipped = []
    
    for root, dirs, files in os.walk(base_dir):
        for file in files:
            if file == "metadata_tags.json":
                path = os.path.join(root, file)
                try:
                    with open(path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    
                    q_id = os.path.basename(os.path.dirname(path))
                    val = data.get("validation", {})
                    status = val.get("status")
                    
                    if status == "FAIL":
                        issues = val.get("issues", [])
                        feedback = data.get("feedback", {}).get("per_option_feedback", {})
                        # Check if feedback is just numbers/short
                        is_short = any(len(txt) < 5 for txt in feedback.values()) if feedback else False
                        fails.append({"id": q_id, "issues": issues, "short_feedback": is_short})
                        
                    elif status == "SKIPPED":
                        reason = val.get("reason", "Unknown")
                        # Sometimes skipped reasoning is in the root if validation dict didn't exist fully
                        if not reason and "reason" in data: 
                             reason = data["reason"]
                        skipped.append({"id": q_id, "reason": reason})
                        
                except Exception as e:
                    print(f"Error reading {path}: {e}")

    print("\n=== SKIPPED QUESTIONS ===")
    for item in sorted(skipped, key=lambda x: int(x['id'][1:]) if x['id'][1:].isdigit() else 999):
        print(f"{item['id']}: {item['reason']}")

    print("\n=== FAIL QUESTIONS ===")
    for item in sorted(fails, key=lambda x: int(x['id'][1:]) if x['id'][1:].isdigit() else 999):
        short_note = " (Detected Short Feedback)" if item['short_feedback'] else ""
        print(f"{item['id']}: {item['issues']}{short_note}")

if __name__ == "__main__":
    analyze_failures()
