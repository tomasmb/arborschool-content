import os

# Definición del MST (Extraída de seleccion_mst.md)
mst_questions = [
    # R1
    ("Prueba-invierno-2025", "Q28"),
    ("prueba-invierno-2026", "Q31"),
    ("prueba-invierno-2026", "Q23"),
    ("seleccion-regular-2025", "Q15"),
    ("Prueba-invierno-2025", "Q46"),
    ("prueba-invierno-2026", "Q45"),
    ("prueba-invierno-2026", "Q58"),
    ("seleccion-regular-2026", "Q60"),
    # A2
    ("Prueba-invierno-2025", "Q40"),
    ("seleccion-regular-2026", "Q35"),
    ("prueba-invierno-2026", "Q40"),
    ("seleccion-regular-2025", "Q10"),
    ("Prueba-invierno-2025", "Q6"),
    ("seleccion-regular-2025", "Q63"),
    ("prueba-invierno-2026", "Q64"),
    ("seleccion-regular-2025", "Q54"),
    # B2
    ("prueba-invierno-2026", "Q42"),
    ("seleccion-regular-2025", "Q38"),
    ("seleccion-regular-2025", "Q36"),
    ("seleccion-regular-2025", "Q3"),
    ("Prueba-invierno-2025", "Q22"),
    ("seleccion-regular-2025", "Q60"),
    ("seleccion-regular-2025", "Q55"),
    ("Prueba-invierno-2025", "Q65"),
    # C2
    ("seleccion-regular-2026", "Q59"),
    ("seleccion-regular-2026", "Q11"),
    ("Prueba-invierno-2025", "Q33"),
    ("Prueba-invierno-2025", "Q56"),
    ("seleccion-regular-2026", "Q23"),
    ("Prueba-invierno-2025", "Q50"),
    ("Prueba-invierno-2025", "Q61"),
    ("prueba-invierno-2026", "Q60"),
]

missing = []
found = 0

print(f"{'Proof':<25} | {'ID':<5} | {'Status':<10}")
print("-" * 45)

for prueba, q_id in mst_questions:
    # Ruta esperada: app/data/pruebas/alternativas/[prueba]/[ID]/approved
    path = os.path.join("app/data/pruebas/alternativas", prueba, q_id, "approved")
    
    if os.path.isdir(path) and len(os.listdir(path)) > 0:
        print(f"{prueba:<25} | {q_id:<5} | ✅ Found")
        found += 1
    else:
        print(f"{prueba:<25} | {q_id:<5} | ❌ MISSING")
        missing.append((prueba, q_id))

print("-" * 45)
print(f"Total MST Questions: {len(mst_questions)}")
print(f"Variants Found: {found}")
print(f"Variants Missing: {len(missing)}")
print("-" * 45)
if missing:
    print("MISSING QUESTIONS:")
    for prueba, q_id in missing:
        print(f" - {prueba}/{q_id}")
