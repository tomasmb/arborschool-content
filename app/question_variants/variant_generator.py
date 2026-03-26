"""Variant question generator.

This module generates pedagogically-sound variant questions from source
exemplars, guided by planning blueprints that enforce same-construct
alignment with non-mechanizable structural variation.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from app.question_variants.generation_prompt import (
    build_generation_prompt,
    build_variant_metadata,
)
from app.question_variants.models import (
    PipelineConfig,
    SourceQuestion,
    VariantBlueprint,
    VariantQuestion,
)
from app.question_variants.postprocess.generation_parsing import (
    parse_generation_response,
)


# ---------------------------------------------------------------------------
# VariantGenerator class -- sync path (used by --no-batch mode)
# ---------------------------------------------------------------------------


class VariantGenerator:
    """Generates variant questions from source exemplars (sync mode)."""

    def __init__(self, config: Optional[PipelineConfig] = None):
        self.config = config or PipelineConfig()
        self.last_error: str | None = None
        from app.question_variants.llm_service import build_text_service

        self.service = build_text_service(
            "openai",
            self.config.model,
            timeout_seconds=self.config.llm_request_timeout_seconds,
            max_attempts=self.config.llm_max_attempts,
        )

    def generate_variants(
        self,
        source: SourceQuestion,
        num_variants: Optional[int] = None,
        blueprints: Optional[List[VariantBlueprint]] = None,
    ) -> List[VariantQuestion]:
        """Generate variant questions from a source question."""
        self.last_error = None
        n = num_variants or self.config.variants_per_question
        print(f"  Generating {n} variants for {source.question_id}...")

        try:
            if blueprints:
                variants = self._generate_from_blueprints(
                    source, blueprints[:n],
                )
            else:
                prompt = build_generation_prompt(source, n, None)
                variants_data = self._call_llm(prompt)
                variants = _to_variant_objects(source, variants_data, None)

            print(f"  ✅ Generated {len(variants)} variants")
            return variants
        except Exception as e:
            print(f"  ❌ Error generating variants: {e}")
            self.last_error = str(e)
            import traceback
            traceback.print_exc()
            return []

    def _generate_from_blueprints(
        self,
        source: SourceQuestion,
        blueprints: List[VariantBlueprint],
    ) -> List[VariantQuestion]:
        variants: List[VariantQuestion] = []
        for blueprint in blueprints:
            try:
                prompt = build_generation_prompt(source, 1, [blueprint])
                variants_data = self._call_llm(prompt)
                generated = _to_variant_objects(
                    source, variants_data[:1], [blueprint],
                )
                if generated:
                    variants.extend(generated)
                else:
                    self.last_error = (
                        f"No se pudo parsear la variante {blueprint.variant_id}"
                    )
                    print(f"  ⚠️ {self.last_error}")
            except Exception as e:
                self.last_error = str(e)
                print(f"  ⚠️ Error generating {blueprint.variant_id}: {e}")
        return variants

    def _call_llm(self, prompt: str) -> List[Dict[str, Any]]:
        """Call the LLM and parse the generation response."""
        response = self.service.generate_text(
            prompt,
            response_mime_type="application/json",
            temperature=self.config.temperature,
            reasoning_effort="medium",
        )
        variants_data = parse_generation_response(response)
        if variants_data:
            return variants_data

        retry_prompt = (
            f"{prompt}\n\n<correccion_formato>\n"
            "Tu respuesta anterior no fue parseable. Reintenta devolviendo "
            "SOLO JSON válido, sin texto adicional.\n"
            "</correccion_formato>\n"
        )
        retry_response = self.service.generate_text(
            retry_prompt,
            response_mime_type="application/json",
            temperature=0.1,
            reasoning_effort="medium",
        )
        return parse_generation_response(retry_response)

    def regenerate_with_feedback(
        self,
        source: SourceQuestion,
        blueprint: VariantBlueprint,
        rejection_reason: str,
    ) -> Optional[VariantQuestion]:
        """Re-generate a single variant using the rejection reason as feedback."""
        print(f"    🔄 Retrying {blueprint.variant_id}...")

        base_prompt = build_generation_prompt(source, 1, [blueprint])
        feedback_section = f"""
<feedback_del_intento_anterior>
Tu variante anterior para el blueprint {blueprint.variant_id} fue RECHAZADA:

"{rejection_reason}"

DEBES corregir este problema específico en tu nuevo intento.
Genera una variante que:
1. Resuelva exactamente el problema descrito arriba
2. Siga respetando todas las reglas del contrato y del blueprint
3. Sea diferente de la variante rechazada
</feedback_del_intento_anterior>
"""
        prompt_with_feedback = base_prompt + feedback_section

        try:
            response = self.service.generate_text(
                prompt_with_feedback,
                response_mime_type="application/json",
                temperature=self.config.temperature + 0.1,
                reasoning_effort="medium",
            )
            variants_data = parse_generation_response(response)
            if not variants_data:
                print(
                    f"    ⚠️ Retry failed to parse for {blueprint.variant_id}",
                )
                return None

            generated = _to_variant_objects(
                source, variants_data[:1], [blueprint],
            )
            if generated:
                variant = generated[0]
                variant.metadata["retry_context"] = {
                    "is_retry": True,
                    "original_rejection_reason": rejection_reason,
                }
                print(f"    ✅ Retry generated {blueprint.variant_id}")
                return variant
            return None
        except Exception as e:
            print(f"    ⚠️ Retry error for {blueprint.variant_id}: {e}")
            self.last_error = str(e)
            return None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _to_variant_objects(
    source: SourceQuestion,
    variants_data: List[Dict[str, Any]],
    blueprints: Optional[List[VariantBlueprint]],
) -> List[VariantQuestion]:
    """Convert raw variant dicts to VariantQuestion objects."""
    variants: List[VariantQuestion] = []
    for i, vdata in enumerate(variants_data):
        if blueprints and i < len(blueprints):
            variant_id = blueprints[i].variant_id
        else:
            variant_id = f"{source.question_id}_v{i + 1}"
        variants.append(
            VariantQuestion(
                variant_id=variant_id,
                source_question_id=source.question_id,
                source_test_id=source.test_id,
                qti_xml=vdata.get("qti_xml", ""),
                metadata=build_variant_metadata(
                    source,
                    vdata,
                    blueprints[i] if blueprints and i < len(blueprints) else None,
                ),
            )
        )
    return variants
