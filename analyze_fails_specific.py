import json
import os

base_dir = "/Users/francosolari/Arbor/arborschool-content/app/data/pruebas/finalizadas/seleccion-regular-2025/qti"
questions = ["Q32", "Q33", "Q48", "Q57", "Q42", "Q44", "Q63", "Q64"]

results = {}

for q in questions:
    path = os.path.join(base_dir, q, "metadata_tags.json")
    if os.path.exists(path):
        try:
            with open(path, 'r') as f:
                data = json.load(f)
            
            val = data.get("validation", {})
            feedback = data.get("feedback", {}).get("per_option_feedback", {})
            
            results[q] = {
                "status": val.get("status"),
                "issues": val.get("issues", []),
                "feedback_keys": list(feedback.keys()),
                "empty_feedback": [k for k, v in feedback.items() if not v or not v.strip()]
            }
        except Exception as e:
            results[q] = {"error": str(e)}
    else:
        results[q] = {"status": "MISSING_FILE"}

print(json.dumps(results, indent=2))
