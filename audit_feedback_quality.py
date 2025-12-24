import os
import json

def audit_feedback():
    base_dir = "app/data/pruebas/finalizadas"
    to_report = []
    
    for root, dirs, files in os.walk(base_dir):
        for file in files:
            if file == "metadata_tags.json":
                path = os.path.join(root, file)
                try:
                    with open(path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        
                    if data.get("validation", {}).get("status") == "PASS":
                        feedback = data.get("feedback", {}).get("per_option_feedback", {})
                        is_suspicious = False
                        
                        # Check each choice
                        for choice_key, text in feedback.items():
                            # If text is very short (less than 10 chars) or just a number
                            if len(text.strip()) < 10 or text.strip().replace('.', '').replace(',', '').isdigit():
                                is_suspicious = True
                                break
                        
                        if is_suspicious:
                            to_report.append(path)
                except Exception:
                    pass
    
    if to_report:
        print("Suspicious PASS questions with minimal feedback:")
        for p in sorted(to_report):
            print(p)
    else:
        print("No suspicious PASS questions found.")

if __name__ == "__main__":
    audit_feedback()
