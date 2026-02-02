"""
Atom Tagger

Tags QTI questions with learning atoms using Gemini.
Delegates prompt construction to tagger_prompts module.
"""

from __future__ import annotations

import io
import json
import os
import re
import xml.etree.ElementTree as ET
from typing import Any

import requests

try:
    from PIL import Image
except ImportError:
    Image = None  # type: ignore

from app.gemini_client import GeminiService, load_default_gemini_service
from app.tagging.kg_utils import filter_redundant_atoms, get_all_atoms, get_atom_by_id
from app.tagging.tagger_prompts import (
    build_analysis_prompt,
    build_atom_tagging_prompt,
    build_validation_prompt,
)
from app.utils.mathml_parser import process_mathml
from app.utils.qti_extractor import parse_qti_xml


class AtomTagger:
    """Tags QTI questions with atoms using Gemini."""

    def __init__(self, model: str = "gemini-3-pro-preview"):
        config = load_default_gemini_service().config
        config.model = model
        self.service = GeminiService(config)

    def _safe_json_loads(self, text: str, xml_path: str = "") -> Any:
        """Attempts to parse JSON, handling common LLM/LaTeX escaping issues."""
        try:
            return json.loads(text)
        except json.JSONDecodeError as e:
            # Fix unescaped LaTeX backslashes
            cleaned = re.sub(r'\\(?![/"\\bfnrtu])', r"\\\\", text)
            try:
                return json.loads(cleaned)
            except Exception:
                if xml_path:
                    raw_path = xml_path + ".json.raw"
                    try:
                        with open(raw_path, "w", encoding="utf-8") as f:
                            f.write(text)
                        print(f"  ⚠️ JSON Parse Error. Raw response saved to {raw_path}")
                    except Exception as fatal:
                        print(f"  ❌ Critical error saving raw response: {fatal}")
                raise e

    def _save_result(self, result: dict[str, Any], output_path: str, is_final: bool = False) -> None:
        """Saves current result state. Partial results go to a backup folder."""
        if not output_path:
            return

        target_path = output_path
        if not is_final:
            backup_root = "app/data/backups/tagging"
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
            status = "final" if is_final else "incremental"
            print(f"  ⚠️ Failed to save {status} result to {target_path}: {e}")

    def _process_mathml(self, element: ET.Element) -> str:
        """Converts MathML elements to readable text. Delegates to shared utility."""
        return process_mathml(element)

    def _extract_text_from_xml(self, xml_content: str) -> dict[str, Any]:
        """Extracts text content and image URLs from QTI XML."""
        parsed = parse_qti_xml(xml_content)
        return {
            "text": parsed.text,
            "choices": parsed.choices,
            "image_urls": parsed.image_urls,
            "correct_answer_id": parsed.correct_answer_id,
            "choice_id_map": parsed.choice_id_map,
        }

    def _download_image(self, url: str) -> Any:
        """Downloads an image and returns a PIL Image object."""
        if not Image:
            print("  ⚠️ PIL not installed, skipping image download.")
            return None

        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()

            img_io = io.BytesIO(response.content)
            img = Image.open(img_io)
            img.verify()

            img_io.seek(0)
            img = Image.open(img_io)
            return img
        except Exception as e:
            print(f"  ⚠️ Failed to download image {url}: {e}")
            return None

    def _generate_analysis(
        self,
        question_text: str,
        choices: list[str],
        selected_atoms: list[dict[str, Any]],
        images: list[Any] | None = None,
        correct_answer: str | None = None,
    ) -> dict[str, Any]:
        """Generates difficulty evaluation AND instructional feedback."""
        prompt = build_analysis_prompt(question_text, choices, selected_atoms, correct_answer)

        full_prompt: list[Any] = [prompt]
        if images:
            full_prompt.extend(images)

        try:
            response_text = self.service.generate_text(full_prompt, response_mime_type="application/json", temperature=0.0)
            return json.loads(response_text)
        except Exception as e:
            print(f"Error generating analysis: {e}")
            import traceback

            traceback.print_exc()
            return {}

    def _validate_output(
        self, question_text: str, choices: list[str], result: dict[str, Any], images: list[Any] | None = None, correct_answer: str | None = None
    ) -> dict[str, Any]:
        """Validates the generated tags and feedback using an LLM Judge."""
        prompt = build_validation_prompt(question_text, choices, result, correct_answer)

        full_prompt: list[Any] = [prompt]
        if images:
            full_prompt.extend(images)

        try:
            response_text = self.service.generate_text(full_prompt, response_mime_type="application/json", temperature=0.0)
            return json.loads(response_text)
        except Exception as e:
            print(f"Error validating output: {e}")
            return {"status": "ERROR", "issues": [str(e)]}

    def _select_primary_heuristic(self, selected_atoms: list[dict[str, Any]]) -> str:
        """Selects a Primary atom locally based on verb hierarchy constraints."""
        tier_1 = ["resolución", "resolver", "calcular", "cálculo", "modelar", "modelado", "optimización"]
        tier_2 = ["aplicar", "aplicación", "transformar", "construir", "determinación"]
        tier_3 = ["identificar", "reconocer", "evaluar", "interpretar", "representar"]

        best_atom_id = ""
        best_score = -1

        for atom in selected_atoms:
            title = atom.get("atom_title", "").lower()
            score = 0

            if any(k in title for k in tier_1):
                score = 3
            elif any(k in title for k in tier_2):
                score = 2
            elif any(k in title for k in tier_3):
                score = 1

            if score > best_score:
                best_score = score
                best_atom_id = atom.get("atom_id")

        return best_atom_id if best_atom_id else (selected_atoms[0].get("atom_id") if selected_atoms else "")

    def tag_xml_file(self, xml_path: str, output_path: str | None = None) -> dict[str, Any] | None:
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

        correct_answer_text = choice_id_map.get(correct_answer_id) if correct_answer_id else None

        # Download Images
        images_content = self._download_images(image_urls)

        # Load ALL atoms for context
        atoms = get_all_atoms()

        # 1. Identify Atoms
        print(f"Tagging atoms for {os.path.basename(xml_path)}...")
        prompt_text = build_atom_tagging_prompt(question_text, choices, atoms)

        full_prompt: list[Any] = [prompt_text]
        if images_content:
            full_prompt.extend(images_content)

        try:
            response_text = self.service.generate_text(full_prompt, response_mime_type="application/json", temperature=0.0)

            result = self._safe_json_loads(response_text, xml_path)
            self._save_result(result, output_path, is_final=False)

            # Apply filters and repairs
            self._apply_transitivity_filter(result)
            self._repair_missing_primary(result)

            # Enrich with atom details
            enriched_selections = self._enrich_selections(result)

            # 2. Evaluate Difficulty AND Generate Feedback
            if enriched_selections:
                result = self._generate_and_validate(
                    result, question_text, choices, enriched_selections, images_content, correct_answer_text, output_path, xml_path
                )
                if result is None:
                    return None
            else:
                result["difficulty"] = {}
                result["feedback"] = {}
                result["validation"] = {"status": "SKIPPED", "reason": "No atoms found"}

            self._save_result(result, output_path, is_final=True)
            return result

        except Exception as e:
            print(f"Error tagging {xml_path}: {e}")
            import traceback

            traceback.print_exc()
            return None

    def _download_images(self, image_urls: list[str]) -> list[Any]:
        """Download all images from URLs."""
        images_content = []
        if image_urls:
            print(f"  Found {len(image_urls)} images, downloading...")
            for url in image_urls:
                img = self._download_image(url)
                if img:
                    images_content.append(img)
            print(f"  Successfully loaded {len(images_content)} images.")
        return images_content

    def _apply_transitivity_filter(self, result: dict[str, Any]) -> None:
        """Filter out redundant prerequisite atoms."""
        if "selected_atoms" not in result or not isinstance(result["selected_atoms"], list):
            return

        original_count = len(result["selected_atoms"])
        atom_ids = [item.get("atom_id") for item in result["selected_atoms"] if item.get("atom_id")]

        filtered_ids = filter_redundant_atoms(atom_ids)

        result["selected_atoms"] = [item for item in result["selected_atoms"] if item.get("atom_id") in filtered_ids]

        if len(result["selected_atoms"]) < original_count:
            removed = original_count - len(result["selected_atoms"])
            print(f"  filtered {removed} redundant prerequisite atoms.")

    def _repair_missing_primary(self, result: dict[str, Any]) -> None:
        """Ensure at least one atom is marked as PRIMARY."""
        if "selected_atoms" not in result or not result["selected_atoms"]:
            return

        has_primary = any(a.get("relevance") == "primary" for a in result["selected_atoms"])

        # Single atom: force primary
        if len(result["selected_atoms"]) == 1 and not has_primary:
            print("  ⚠️ Only one atom found but marked Secondary. Auto-promoting to Primary.")
            result["selected_atoms"][0]["relevance"] = "primary"
            return

        # Multiple atoms, no primary: use heuristic
        if not has_primary and len(result["selected_atoms"]) > 1:
            print("  ⚠️ No PRIMARY atom found. Using Heuristic to decide...")
            for sel in result["selected_atoms"]:
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

    def _enrich_selections(self, result: dict[str, Any]) -> list[dict[str, Any]]:
        """Enrich selected atoms with full atom details."""
        enriched = []
        if "selected_atoms" not in result or not isinstance(result["selected_atoms"], list):
            return enriched

        for selection in result["selected_atoms"]:
            atom_id = selection.get("atom_id")
            if atom_id:
                atom_data = get_atom_by_id(atom_id)
                if atom_data:
                    selection["atom_title"] = atom_data.get("titulo")
                    selection["atom_eje"] = atom_data.get("eje")
                    std_ids = atom_data.get("standard_ids", [])
                    selection["atom_standard"] = std_ids[0] if std_ids else None
                    enriched.append(selection)
        return enriched

    def _generate_and_validate(
        self,
        result: dict[str, Any],
        question_text: str,
        choices: list[str],
        enriched_selections: list[dict[str, Any]],
        images_content: list[Any],
        correct_answer_text: str | None,
        output_path: str | None,
        xml_path: str,
    ) -> dict[str, Any] | None:
        """Generate analysis and validate results."""
        print(f"Generating analysis (Difficulty + Feedback) for {os.path.basename(xml_path)}...")
        analysis_data = self._generate_analysis(
            question_text, choices, enriched_selections, images=images_content, correct_answer=correct_answer_text
        )

        if not analysis_data or not analysis_data.get("difficulty"):
            print(f"  ❌ Analysis Generation FAILED. Aborting for {os.path.basename(xml_path)}.")
            return None

        result["difficulty"] = analysis_data.get("difficulty", {})
        result["feedback"] = analysis_data.get("feedback", {})

        self._save_result(result, output_path, is_final=False)

        # Validation Phase
        print(f"Validating results for {os.path.basename(xml_path)}...")
        validation_result = self._validate_output(question_text, choices, result, images=images_content, correct_answer=correct_answer_text)
        result["validation"] = validation_result

        if validation_result.get("status") != "PASS":
            print(f"  ⚠️ Validation WARNING: {validation_result.get('status')} - {validation_result.get('issues')}")

        return result
