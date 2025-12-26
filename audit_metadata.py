import json
import os
import glob

base_dir = "/Users/francosolari/Arbor/arborschool-content/app/data/pruebas/finalizadas/"
files = glob.glob(os.path.join(base_dir, "**/metadata_tags.json"), recursive=True)

results = []

for file_path in files:
    try:
        with open(file_path, 'r') as f:
            data = json.load(f)
            
        validation = data.get("validation", {})
        status = validation.get("status")
        issues = validation.get("issues", [])
        feedback = data.get("feedback", {}).get("per_option_feedback", {})
        
        if status == "PASS":
            has_issues = len(issues) > 0
            
            # Check for missing standard options (A, B, C, D)
            # Most questions have A, B, C, D. Some have E.
            # If it has ChoiceD, it should probably have A, B, C.
            standard_options = ["ChoiceA", "ChoiceB", "ChoiceC", "ChoiceD"]
            missing_options = []
            max_opt = ""
            for opt in ["ChoiceE", "ChoiceD", "ChoiceC", "ChoiceB", "ChoiceA"]:
                if opt in feedback:
                    max_opt = opt
                    break
            
            if max_opt:
                # If ChoiceD exists, check A, B, C
                limit = ord(max_opt[-1]) # A=65, B=66...
                for i in range(65, limit + 1):
                    opt_name = f"Choice{chr(i)}"
                    if opt_name not in feedback or not feedback[opt_name].strip():
                        missing_options.append(opt_name)

            lazy_feedback_details = []
            for opt, text in feedback.items():
                if "_label" in opt: continue
                text_stripped = text.strip()
                word_count = len(text_stripped.split())
                if not text_stripped or word_count < 10:
                    lazy_feedback_details.append(f"{opt}: too short ({word_count} words)")
                
                text_low = text_stripped.lower()
                if any(x in text_low for x in ["opción correcta", "opción incorrecta", "es correcta", "es incorrecta"]) and word_count < 15:
                     lazy_feedback_details.append(f"{opt}: generic text")

            if has_issues or missing_options or lazy_feedback_details:
                results.append({
                    "path": os.path.relpath(file_path, base_dir),
                    "has_issues": has_issues,
                    "issues": issues,
                    "missing_options": missing_options,
                    "lazy_feedback_details": lazy_feedback_details
                })
    except Exception as e:
        pass

print(json.dumps(results, indent=2))
