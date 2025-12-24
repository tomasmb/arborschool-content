import json
import re
import os
import requests
import io
from typing import Optional, Dict, Any, List
import xml.etree.ElementTree as ET
try:
    from PIL import Image
except ImportError:
    Image = None

from app.gemini_client import load_default_gemini_service, GeminiService
from app.tagging.kg_utils import get_all_atoms, get_atom_by_id, filter_redundant_atoms

class AtomTagger:
    """Tags QTI questions with atoms using Gemini."""

    def __init__(self, model: str = "gemini-3-pro-preview"):
        # Note: Using a model capable of longer context and vision
        config = load_default_gemini_service().config
        config.model = model
        self.service = GeminiService(config)

    def _safe_json_loads(self, text: str, xml_path: str = "") -> Any:
        """Attempts to parse JSON, handling common LLM/LaTeX escaping issues."""
        try:
            return json.loads(text)
        except json.JSONDecodeError as e:
            # Common issue: Gemini returns LaTeX backslashes without escaping them for JSON.
            # e.g., "reasoning": "Usa \frac{a}{b}" instead of "Usa \\frac{a}{b}"
            # We fix this by escaping backslashes that are not already part of a valid escape.
            cleaned = re.sub(r'\\(?![/"\\bfnrtu])', r'\\\\', text)
            try:
                return json.loads(cleaned)
            except Exception:
                # Fallback: Save raw output for manual recovery
                if xml_path:
                    raw_path = xml_path + ".json.raw"
                    try:
                        with open(raw_path, "w", encoding="utf-8") as f:
                            f.write(text)
                        print(f"  ⚠️ JSON Parse Error. Raw response saved to {raw_path}")
                    except Exception as fatal:
                        print(f"  ❌ Critical error saving raw response: {fatal}")
                raise e

    def _save_result(self, result: Dict[str, Any], output_path: str, is_final: bool = False):
        """Saves current result state to file. Partial results go to a backup folder."""
        if not output_path:
            return
        
        target_path = output_path
        if not is_final:
            # Route partial results to a backup directory, mirroring the structure
            backup_root = "app/data/backups/tagging"
            # Attempt to extract a relative path from app/data/pruebas for a clean backup structure
            try:
                if "app/data/pruebas/finalizadas" in output_path:
                    rel = os.path.relpath(output_path, "app/data/pruebas/finalizadas")
                else:
                    rel = os.path.basename(output_path)
                target_path = os.path.join(backup_root, rel)
            except Exception:
                target_path = os.path.join(backup_root, os.path.basename(output_path))
            
            os.makedirs(os.path.dirname(target_path), exist_ok=True)

        try:
            with open(target_path, "w", encoding="utf-8") as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
            if not is_final:
                print(f"  💾 Partial backup saved to {target_path}")
        except Exception as e:
            print(f"  ⚠️ Failed to save {'final' if is_final else 'incremental'} result to {target_path}: {e}")

    def _process_mathml(self, element: ET.Element) -> str:
        """Recursively converts MathML elements to a readable text representation."""
        tag = element.tag.split('}')[-1]  # Handle namespaced tags
        
        if tag == 'mfrac':
            children = list(element)
            if len(children) == 2:
                num = self._process_mathml(children[0])
                den = self._process_mathml(children[1])
                return f"({num}/{den})"
        elif tag == 'msup':
            children = list(element)
            if len(children) == 2:
                base = self._process_mathml(children[0])
                exp = self._process_mathml(children[1])
                return f"{base}^({exp})"
        elif tag == 'msub':
            children = list(element)
            if len(children) == 2:
                base = self._process_mathml(children[0])
                sub = self._process_mathml(children[1])
                return f"{base}_({sub})"
        elif tag in ('msqrt', 'mroot'):
            children = list(element)
            if tag == 'msqrt':
                inner = "".join([self._process_mathml(c) for c in children])
                return f"sqrt({inner})"
            elif len(children) == 2:
                inner = self._process_mathml(children[0])
                index = self._process_mathml(children[1])
                return f"root[{index}]({inner})"
        elif tag == 'mfenced':
            inner = "".join([self._process_mathml(c) for c in element])
            return f"({inner})"
        elif tag == 'mtable':
            rows = []
            for row in element:
                rows.append(self._process_mathml(row))
            return " [ " + " ; ".join(rows) + " ] "
        elif tag == 'mtr':
            cols = []
            for col in element:
                cols.append(self._process_mathml(col))
            return " ".join(cols)
        elif tag == 'mtd':
            parts = []
            if element.text:
                parts.append(element.text.strip())
            for child in element:
                parts.append(self._process_mathml(child))
            return "".join(parts)
        elif tag == 'mi' or tag == 'mn' or tag == 'mo' or tag == 'mtext':
            return (element.text or "").strip()
        
        # Default: recursive join of all children text/processing
        parts = []
        if element.text:
            parts.append(element.text.strip())
        for child in element:
            parts.append(self._process_mathml(child))
            if child.tail:
                parts.append(child.tail.strip())
        return "".join(parts)

    def _process_html_table(self, element: ET.Element) -> str:
        """Converts an HTML table to a readable text representation."""
        rows = []
        # Support both standard tr and namespaced qti-tr, etc.
        # Find rows directly under the table or inside thead/tbody
        tr_nodes = element.findall(".//{*}tr")
        for tr in tr_nodes:
            cols = []
            # Find all cells (th or td)
            for cell in tr.findall(".//{*}th") + tr.findall(".//{*}td"):
                cell_text = self._extract_full_text(cell).strip()
                cols.append(cell_text)
            if cols:
                rows.append(" | ".join(cols))
        
        if rows:
            return "\n[ " + " | ".join(rows) if len(rows) == 1 else "\n" + "\n".join(rows) + "\n"
        return ""

    def _extract_full_text(self, element: ET.Element) -> str:
        """Extracts text from an element, processing MathML, Tables, and Images specially."""
        parts = []
        if element.text:
            parts.append(element.text)
        
        for child in element:
            tag = child.tag.split('}')[-1].lower()
            if tag == 'math':
                parts.append(self._process_mathml(child))
            elif tag == 'table':
                parts.append(self._process_html_table(child))
            elif tag in ['p', 'div', 'li', 'br']:
                # Add spacing for block elements
                content = self._extract_full_text(child)
                parts.append(f"\n{content}\n" if tag != 'br' else "\n")
            elif tag in ['img', 'qti-img']:
                alt = child.get('alt')
                if alt:
                    parts.append(f" [Imagen: {alt}] ")
            else:
                parts.append(self._extract_full_text(child))
            
            if child.tail:
                parts.append(child.tail)
        
        return "".join(parts)

    def _extract_text_from_xml(self, xml_content: str) -> Dict[str, Any]:
        """Extracts text content and image URLs from QTI XML."""
        try:
            root = ET.fromstring(xml_content)
        except ET.ParseError:
            # Fallback for very broken XML
            return {"text": "", "choices": [], "image_urls": [], "correct_answer_id": None, "choice_id_map": {}}
        
        # Extract Correct Answer ID
        correct_answer_id = None
        # 3.0 Standard: responseDeclaration -> correctResponse -> value
        # We use {*} wildcard to handle namespaces robustly.
        resp_decl = root.find(".//{*}responseDeclaration") or root.find(".//{*}qti-response-declaration")
        if resp_decl is not None:
            corr_resp = resp_decl.find(".//{*}correctResponse") or resp_decl.find(".//{*}qti-correct-response")
            if corr_resp is not None:
                val_node = corr_resp.find(".//{*}value") or corr_resp.find(".//{*}qti-value")
                if val_node is not None:
                    correct_answer_id = (val_node.text or "").strip()
        
        # Fallback: literal search for value inside any correct response tag
        if not correct_answer_id:
            any_corr = root.find(".//{*}qti-correct-response") or root.find(".//{*}correctResponse")
            if any_corr is not None:
                val_node = any_corr.find(".//{*}qti-value") or any_corr.find(".//{*}value")
                if val_node is not None:
                    correct_answer_id = (val_node.text or "").strip()

        # Extract Question Text
        # Support both v2 (itemBody) and v3 (qti-item-body)
        item_body = root.find(".//{*}itemBody") or root.find(".//{*}qti-item-body")
        question_text = ""
        if item_body is not None:
            # We want the full text of the body, which includes context AND the prompt
            raw_text = self._extract_full_text(item_body)
            question_text = self._clean_text(raw_text)

        # Extract Choices
        choices = []
        choice_id_map = {} # To keep track of which choice is which
        # Find all simpleChoice or qti-simple-choice
        choice_nodes = root.findall(".//{*}simpleChoice") + root.findall(".//{*}qti-simple-choice")
        for choice in choice_nodes:
            cid = choice.get("identifier")
            raw_choice = self._extract_full_text(choice)
            cleaned_choice = self._clean_text(raw_choice)
            choices.append(cleaned_choice)
            if cid:
                choice_id_map[cid] = cleaned_choice

        # Extract Image URLs
        image_urls = []
        # Support img in any namespace/prefix
        for img in root.findall(".//{*}img") + root.findall(".//{*}qti-img"):
             src = img.get("src")
             if src:
                 image_urls.append(src)
        
        # Fallback regex
        if not image_urls:
            image_urls = re.findall(r'<img[^>]+src=["\']([^"\']+)["\']', xml_content)

        return {
            "text": question_text, 
            "choices": choices,
            "image_urls": sorted(list(set(image_urls))),
            "correct_answer_id": correct_answer_id,
            "choice_id_map": choice_id_map
        }

    def _clean_text(self, text: str) -> str:
        """Cleans extracted text, preserving structural newlines."""
        if not text:
            return ""
        # Collapse multiple spaces but preserve single ones
        text = re.sub(r'[ \t]+', ' ', text)
        # Collapse excessive newlines (more than 2) to 2
        text = re.sub(r'\n{3,}', '\n\n', text)
        # Remove space at start/end of lines
        text = re.sub(r'^ +| +$', '', text, flags=re.MULTILINE)
        return text.strip()

    def _download_image(self, url: str) -> Any:
        """Downloads an image and returns a PIL Image object."""
        if not Image:
            print("  ⚠️ PIL not installed, skipping image download.")
            return None
            
        try:
            # print(f"  Fetching image: {url}")
            response = requests.get(url, timeout=10)
            response.raise_for_status() # This will raise an exception for 4xx/5xx responses
            
            # Verify image integrity before using
            img_io = io.BytesIO(response.content)
            img = Image.open(img_io)
            img.verify() # Checks for truncation/corruption
            
            # Re-open because verify() consumes the stream
            img_io.seek(0)
            img = Image.open(img_io)
            
            return img
        except Exception as e:
            print(f"  ⚠️ Failed to download image {url}: {e}")
            return None

    def _build_prompt(self, question_text: str, choices: List[str], atoms: List[Dict[str, Any]]) -> str:
        """Constructs the long-context prompt."""
        
        # Format atoms efficiently
        atoms_text = []
        for atom in atoms:
            atoms_text.append(f"ID: {atom['id']}\nTitle: {atom.get('titulo', '')}\nDesc: {atom.get('descripcion', '')}\n")
        
        atoms_block = "\n---\n".join(atoms_text)
        
        choices_text = "\n".join([f"- {c}" for c in choices])
        
        prompt = f"""

Eres un experto en evaluación educativa y diseño curricular (matemáticas).

TAREA: Identificar los "Átomos" (Habilidades/Conocimientos) relevantes que coinciden con la siguiente pregunta.
Generalmente una pregunta evalúa un átomo principal, pero a veces puede involucrar múltiples habilidades distintas.
Selecciona uno o más átomos necesarios para resolver la pregunta.
Clasifícalos por relevancia (PRIMARY vs SECONDARY).
Si absolutamente ningún átomo coincide bien, retorna una lista vacía.
**IMPORTANTE**: El campo 'reasoning' y 'general_analysis' deben estar en **ESPAÑOL**.

PREGUNTA:
{question_text}

OPCIONES:
{choices_text}

ÁTOMOS DISPONIBLES:
{atoms_block}

FORMATO DE RESPUESTA (JSON):
Retorna un objeto JSON con:
{{
  "selected_atoms": [
      {{
          "atom_id": "ID_DEL_ATOMO",
          "relevance": "primary" o "secondary",
          "reasoning": "Por qué este átomo coincide (en Español)..."
      }}
  ],
  "general_analysis": "Breve análisis de las demandas cognitivas de la pregunta (en Español)."
}}

REGLAS DE RELEVANCIA:
- **PRIMARY**: Asígnalo si el Átomo describe el OBJETIVO MATEMÁTICO CENTRAL de la pregunta. No te dejes llevar solo por el verbo del título (ej: si el átomo dice 'Construcción' pero el alumno debe 'Interpretar' ese objeto, sigue siendo PRIMARY).
- **SECONDARY**: Asígnalo a habilidades de soporte o requisitos previos necesarios pero que no son el foco de la evaluación.
- **IMPERATIVO**: DEBE HABER AL MENOS UN ÁTOMO MARCADO COMO 'PRIMARY'. Si dudas, elige el que mejor describa la acción principal que realiza el estudiante.
- Debe haber al menos un átomo PRIMARY si la pregunta tiene sentido matemático.
"""
        return prompt

    def _generate_analysis(self, question_text: str, choices: List[str], selected_atoms: List[Dict[str, Any]], images: Optional[List[Any]] = None, correct_answer: Optional[str] = None) -> Dict[str, Any]:
        """Generates difficulty evaluation AND instructional feedback."""
        
        correct_info = f"\nRESPUESTA CORRECTA: {correct_answer}\n" if correct_answer else ""

        prompt = f"""
Eres un experto en evaluación educativa y diseño curricular (matemáticas).

TAREA: Analizar en profundidad la siguiente pregunta.
1. Evaluar su **Nivel de Dificultad** basado en la demanda cognitiva.
2. Proveer **Feedback Instruccional** para el estudiante.
**IMPORTANTE**: Todo el texto generado (análisis y explicaciones) debe estar en **ESPAÑOL**.
**ADVERTENCIA**: Si generas feedback perezoso (solo repitiendo el texto de la opción), la respuesta será RECHAZADA automáticamente. Debes explicar pedagógicamente.

PREGUNTA:
{question_text}

OPCIONES:
{json.dumps(choices, ensure_ascii=False)}
{correct_info}

ÁTOMOS RELEVANTES (HABILIDADES):
{json.dumps([a.get('titulo') for a in selected_atoms], ensure_ascii=False)}

RÚBRICA DE DIFICULTAD:
- **Low (Baja)**: Procedimiento rutinario, recuerdo directo, ejecución de un solo paso.
- **Medium (Media)**: Pensamiento estratégico, multi-paso, interpretación de datos/gráficos.
- **High (Alta)**: Razonamiento complejo, síntesis, transferencia, justificación abstracta.

GUÍAS PARA EL FEEDBACK:
- **Respuesta Correcta**: Explica POR QUÉ es correcta usando los conceptos de los átomos.
- **Distractores**: Explica el error conceptual o de cálculo probable que lleva a esta opción. Evita decir solo "es incorrecta".
- **Tono**: Constructivo, educativo, alentador (estilo tutor).

FORMATO DE RESPUESTA (JSON):
Retorna un objeto JSON con:
{{
  "difficulty": {{
      "level": "Low" | "Medium" | "High",
      "score": 0.0 a 1.0,
      "analysis": "Explicación de la demanda cognitiva (en Español)..."
  }},
  "thought_process": "Razonamiento paso a paso ANTES de generar el feedback. Analiza aquí la resolución del problema y por qué cada opción es correcta o incorrecta. Esto es tu 'borrador' mental.",
  "feedback": {{
      "general_guidance": "Cómo abordar este tipo de problemas (en Español)...",
      "per_option_feedback": {{
          "ChoiceA": "Explicación detalla del por qué es incorrecta o qué error conceptual cometió el alumno (en Español)...",
          "ChoiceB": "Explicación detalla de por qué es la correcta y qué conceptos aplica (en Español)...",
          ... (para todas las opciones)
      }}
  }}
}}

REGLA DE ORO DEL FEEDBACK:
1. **CRÍTICO**: Sigue el orden del JSON. Primero piensa en "thought_process", luego escribe el "feedback".
2. **PROHIBIDO**: Devolver solo el valor de la opción o frases cortas como "Es incorrecta".
3. Cada opción debe tener al menos 2 oraciones de explicación pedagógica.
4. **EJEMPLO MALO (RECHAZADO)**: "ChoiceA": "21"
5. **EJEMPLO BUENO (APROBADO)**: "ChoiceA": "Esta opción corresponde al cálculo de 20 + 1, pero ignora el aumento porcentual..."
6. Si no puedes proveer una explicación pedagógica completa, MEJOR NO RETORNES NADA (el sistema lo marcará como fallo para revisión humana).
"""
        full_prompt = [prompt]
        if images:
            full_prompt.extend(images)

        try:
            response_text = self.service.generate_text(
                full_prompt, response_mime_type="application/json", temperature=0.0
            )
            return json.loads(response_text)
        except Exception as e:
            print(f"Error generating analysis: {e}")
            import traceback
            traceback.print_exc()
            return {}

    def _validate_output(self, question_text: str, choices: List[str], result: Dict[str, Any], images: Optional[List[Any]] = None, correct_answer: Optional[str] = None) -> Dict[str, Any]:
        """Validates the generated tags and feedback using an LLM Judge."""
        
        correct_info = f"\nRESPUESTA CORRECTA OFICIAL (La Verdad Absoluta): {correct_answer}\n" if correct_answer else ""

        prompt = f"""
Eres un Especialista en Aseguramiento de Calidad (QA) para contenido educativo.

TAREA: Revisar los metadatos generados por IA para una pregunta de matemáticas.
Verificar consistencia, precisión y calidad pedagógica.

PREGUNTA:
{question_text}

OPCIONES:
{json.dumps(choices, ensure_ascii=False)}
{correct_info}

METADATOS GENERADOS:
{json.dumps(result, ensure_ascii=False, indent=2)}

CHECKLIST (VERIFICAR):
1. **Átomos**: ¿El átomo PRIMARY refleja el concepto central? (Ignora si el verbo no encaja perfecto, prioriza el concepto).
2. **Dificultad**: ¿Es plausible la clasificación de dificultad?
3. **Feedback**: ¿Es pedagógico? ¿Explica el error o el acierto? **RECHAZA (FAIL)** si el feedback solo repite el valor de la opción o es muy corto.
4. **Idioma**: ¿Todo en ESPAÑOL fluido?
5. **Exactitud Matemática**: Si se provee una RESPUESTA OFICIAL, asume que es CORRECTA (La Verdad Absoluta). NO cuestiones la aritmética básica (ej: 20*1.05 = 21, eso es un hecho, no un error de redondeo). Si tu cálculo difiere, asume que tú estás equivocado o te falta contexto.
6. **Tipificación**: Verifica que el tipo de problema (ej: Ecuación Lineal vs Cuadrática) coincida con el Átomo seleccionado.
7. **Existencia de Primary**: RECHAZA (FAIL) si no hay ningún átomo marcado como PRIMARY.

FORMATO DE RESPUESTA (JSON):
Retorna un objeto JSON:
{{
  "status": "PASS" o "FAIL",
  "issues": ["Lista de problemas detectados (en Español)"],
  "score": 1 a 5
}}
"""
        full_prompt = [prompt]
        if images:
            full_prompt.extend(images)

        try:
            response_text = self.service.generate_text(
                full_prompt, response_mime_type="application/json", temperature=0.0
            )
            return json.loads(response_text)
        except Exception as e:
            print(f"Error validating output: {e}")
            return {"status": "ERROR", "issues": [str(e)]}

    def _select_primary_heuristic(self, selected_atoms: List[Dict[str, Any]]) -> str:
        """Selects a Primary atom locally based on verb hierarchy constraints."""
        
        # Hierarchy: "Doing" > "Understanding" > "Remembering"
        # We prioritize complex tasks over simple identification.
        
        tier_1_keywords = ["resolución", "resolver", "calcular", "cálculo", "modelar", "modelado", "optimización"]
        tier_2_keywords = ["aplicar", "aplicación", "transformar", "construir", "determinación"]
        tier_3_keywords = ["identificar", "reconocer", "evaluar", "interpretar", "representar"]
        
        best_atom_id = ""
        best_score = -1
        
        for atom in selected_atoms:
            title = atom.get("atom_title", "").lower()
            score = 0
            
            if any(k in title for k in tier_1_keywords):
                score = 3
            elif any(k in title for k in tier_2_keywords):
                score = 2
            elif any(k in title for k in tier_3_keywords):
                score = 1
            
            # Tie-breaker: prefer the one that appears earlier in the list (usually higher relevance in search)
            # strictly greater to keep the first high-score found
            if score > best_score:
                best_score = score
                best_atom_id = atom.get("atom_id")
                
        return best_atom_id if best_atom_id else (selected_atoms[0].get("atom_id") if selected_atoms else "")

    def tag_xml_file(self, xml_path: str, output_path: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Tags a single XML file and optionally saves metadata."""
        
        if not os.path.exists(xml_path):
            print(f"File not found: {xml_path}")
            return None
            
        with open(xml_path, "r", encoding="utf-8") as f:
            xml_content = f.read()
            
        parsed = self._extract_text_from_xml(xml_content)
        question_text = parsed["text"]
        choices = parsed["choices"]
        image_urls = parsed.get("image_urls", [])
        correct_answer_id = parsed.get("correct_answer_id")
        choice_id_map = parsed.get("choice_id_map", {})

        # Resolve correct answer text
        correct_answer_text = choice_id_map.get(correct_answer_id) if correct_answer_id else None

        # Download Images
        images_content = []
        if image_urls:
            print(f"  Found {len(image_urls)} images, downloading...")
            for url in image_urls:
                img = self._download_image(url)
                if img:
                    images_content.append(img)
            print(f"  Successfully loaded {len(images_content)} images.")
        
        # Load ALL atoms for context
        atoms = get_all_atoms()
        
        # 1. Identify Atoms
        print(f"Tagging atoms for {os.path.basename(xml_path)}...")
        prompt_text = self._build_prompt(question_text, choices, atoms)
        
        full_prompt = [prompt_text]
        if images_content:
            full_prompt.extend(images_content)

        try:
            response_text = self.service.generate_text(
                full_prompt, 
                response_mime_type="application/json",
                temperature=0.0
            )
            
            result = self._safe_json_loads(response_text, xml_path)
            
            # Save progress: Selected Atoms (to backup)
            self._save_result(result, output_path, is_final=False)
            
            # 1.5 Apply Transitivity Filter (Prerequisites)
            if "selected_atoms" in result and isinstance(result["selected_atoms"], list):
                original_count = len(result["selected_atoms"])
                atom_ids = [item.get("atom_id") for item in result["selected_atoms"] if item.get("atom_id")]
                
                # Filter out ancestors
                filtered_ids = filter_redundant_atoms(atom_ids)
                
                # Update list retaining only survivors
                result["selected_atoms"] = [
                    item for item in result["selected_atoms"] 
                    if item.get("atom_id") in filtered_ids
                ]
                
                if len(result["selected_atoms"]) < original_count:
                    print(f"  filtered {original_count - len(result['selected_atoms'])} redundant prerequisite atoms.")
                    print(f"  filtered {original_count - len(result['selected_atoms'])} redundant prerequisite atoms.")


            # 1.6 INTELLIGENT REPAIR OF MISSING PRIMARY
            if "selected_atoms" in result and result["selected_atoms"]:
                has_primary = any(a.get("relevance") == "primary" for a in result["selected_atoms"])
                
                # Check 1: If single atom, FORCE primary (Logic: Only one atom = It must be the primary)
                if len(result["selected_atoms"]) == 1 and not has_primary:
                     print("  ⚠️ Only one atom found but marked Secondary. Auto-promoting to Primary.")
                     result["selected_atoms"][0]["relevance"] = "primary"
                     has_primary = True

                # Check 2: If multiple atoms and NO primary, use smart heuristic
                if not has_primary and len(result["selected_atoms"]) > 1:
                    print("  ⚠️ No PRIMARY atom found. Using Heuristic to decide...")
                    # We need titles for the heuristic, ensure they are present
                    for sel in result["selected_atoms"]:
                        # Quick lookup 
                        atom_id = sel.get("atom_id")
                        if atom_id and not sel.get("atom_title"):
                            atom_data = get_atom_by_id(atom_id)
                            if atom_data:
                                sel["atom_title"] = atom_data.get("titulo")
                    
                    target_id = self._select_primary_heuristic(result["selected_atoms"])
                    
                    if target_id:
                        print(f"  ✅ Heuristic identified {target_id} as the Primary atom.")
                        for atom in result["selected_atoms"]:
                            if atom.get("atom_id") == target_id:
                                atom["relevance"] = "primary"
                                atom["reasoning"] += " (Identified as Primary by Heuristic)"
                                break
                    else:
                         print("  ⚠️ Heuristic failed. Fallback: Promoting first atom.")
                         result["selected_atoms"][0]["relevance"] = "primary"

            # Enrich result with atom details
            enriched_selections = []
            if "selected_atoms" in result and isinstance(result["selected_atoms"], list):
                for selection in result["selected_atoms"]:
                    atom_id = selection.get("atom_id")
                    if atom_id:
                        atom_data = get_atom_by_id(atom_id)
                        if atom_data:
                            selection["atom_title"] = atom_data.get("titulo")
                            selection["atom_eje"] = atom_data.get("eje")
                            selection["atom_standard"] = atom_data.get("standard_ids", [])[0] if atom_data.get("standard_ids") else None
                            enriched_selections.append(selection)

            # 2. Evaluate Difficulty AND Generate Feedback (multimodal)
            if enriched_selections:
                print(f"Generating analysis (Difficulty + Feedback) for {os.path.basename(xml_path)}...")
                analysis_data = self._generate_analysis(
                    question_text, 
                    choices, 
                    [s for s in enriched_selections], 
                    images=images_content,
                    correct_answer=correct_answer_text
                )
                
                # STRICT CHECK: If analysis failed (empty dict), abort.
                if not analysis_data or not analysis_data.get("difficulty"):
                    print(f"  ❌ Analysis Generation FAILED (Empty response). Aborting tagging for {os.path.basename(xml_path)}.")
                    return None

                result["difficulty"] = analysis_data.get("difficulty", {})
                result["feedback"] = analysis_data.get("feedback", {})
                
                # Save progress: Difficulty + Feedback (to backup)
                self._save_result(result, output_path, is_final=False)
                
                # 3. Validation Phase (multimodal)
                print(f"Validating results for {os.path.basename(xml_path)}...")
                validation_result = self._validate_output(
                    question_text, 
                    choices, 
                    result, 
                    images=images_content,
                    correct_answer=correct_answer_text
                )
                result["validation"] = validation_result
                if validation_result.get("status") != "PASS":
                     print(f"  ⚠️ Validation WARNING: {validation_result.get('status')} - {validation_result.get('issues')}")

            else:
                result["difficulty"] = {}
                result["feedback"] = {}
                result["validation"] = {"status": "SKIPPED", "reason": "No atoms found"}
            # 4. Final Save (to final destination)
            self._save_result(result, output_path, is_final=True)

            return result

        except Exception as e:
            print(f"Error tagging {xml_path}: {e}")
            import traceback
            traceback.print_exc()
            return None
