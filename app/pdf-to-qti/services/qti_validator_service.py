"""
QTI Extraction Validator Service.

Validates that QTI 3.0 XML was correctly extracted/parsed from a source PDF.
Focus: Extraction completeness, NOT assessment completeness.

VALIDATES:
- Question content was fully extracted (stem, choices, interactive elements)
- No parsing artifacts or encoding issues
- Images match the question context
- Structure is correct for the question type

DOES NOT VALIDATE:
- responseDeclaration / correctResponse (answer keys)
- Feedback elements
- Distractor quality
- Pedagogical completeness
"""

import logging
import requests
from typing import Optional, List, Dict, Any
from xml.etree import ElementTree as ET

# Import from parent package
try:
    from models import (
        QTIValidationOutput,
        ValidationResult,
        MediaValidationDetail,
        AIValidationResponse,
        create_error_validation_output,
    )
    from prompts.qti_validation import (
        build_validation_prompt,
        build_image_validation_prompt,
    )
    from services.ai_client_factory import AIClient
except ImportError:
    from ..models import (
        QTIValidationOutput,
        ValidationResult,
        MediaValidationDetail,
        AIValidationResponse,
        create_error_validation_output,
    )
    from ..prompts.qti_validation import (
        build_validation_prompt,
        build_image_validation_prompt,
    )
    from ..services.ai_client_factory import AIClient

logger = logging.getLogger(__name__)

# QTI 3.0 namespace
QTI_NS = {"qti": "http://www.imsglobal.org/xsd/imsqtiasi_v3p0"}


class QTIValidatorService:
    """
    Service for validating QTI 3.0 extraction quality.
    
    Combines:
    1. XML structural parsing (deterministic)
    2. AI content analysis (semantic understanding)
    3. Image validation (visual verification)
    
    Focus is on extraction completeness - was the question correctly
    parsed from the source PDF? NOT on assessment completeness.
    """
    
    def __init__(
        self,
        ai_client: AIClient,
        model_provider: str = "gemini",
    ):
        """
        Initialize the validator service.
        
        Args:
            ai_client: AI client for content analysis
            model_provider: Backing AI provider identifier
        """
        self.ai_client = ai_client
        self.model_provider = model_provider
    
    def validate(
        self,
        qti_xml: str,
        images: List[Dict[str, Any]] = None,
        question_id: str = "unknown",
    ) -> QTIValidationOutput:
        """
        Validate QTI extraction quality.
        
        Args:
            qti_xml: QTI 3.0 XML string
            images: List of image dicts with url and optional alt_text
            question_id: Question identifier for logging
            
        Returns:
            QTIValidationOutput with all validation results
        """
        images = images or []
        errors = []
        
        # Step 1: Parse XML and extract basic structure
        try:
            xml_info = self._parse_qti_structure(qti_xml)
        except Exception as e:
            logger.error(f"XML parsing failed for {question_id}: {e}")
            return create_error_validation_output(question_id, f"XML parsing failed: {e}")
        
        # Step 2: Validate media URLs exist (quick check)
        media_details = self._validate_media_urls(xml_info.get("images", []), images)
        
        # Step 3: AI-powered validation (content + structure + parse quality)
        has_images = len(images) > 0
        ai_validation_failed = False
        try:
            ai_result = self._run_ai_validation(
                qti_xml=qti_xml,
                images=images,
                has_images=has_images,
                xml_images=xml_info.get("images", []),
            )
        except Exception as e:
            logger.error(f"AI validation failed for {question_id}: {e}")
            errors.append(f"AI validation error: {e}")
            ai_validation_failed = True
            # Return error output with score 0
            ai_result = AIValidationResponse(
                is_complete=False,
                content_score=0,
                content_issues=[f"AI validation failed: {e}"],
                structure_valid=False,
                structure_score=0,
                structure_issues=["Cannot validate - AI call failed"],
                parse_clean=False,
                parse_score=0,
                parse_issues=["Cannot validate - AI call failed"],
                detected_type=xml_info.get("interaction_type", "unknown"),
                reasoning=f"AI validation failed: {e}. Results are incomplete.",
            )
        
        # Build validation results
        # Derive 'passed' from scores (>= 90) for consistency
        content_passed = ai_result.content_score >= 90
        structure_passed = ai_result.structure_score >= 90
        parse_passed = ai_result.parse_score >= 90
        
        content_result = ValidationResult(
            passed=content_passed,
            score=ai_result.content_score,
            issues=ai_result.content_issues,
            details="Content extraction completeness"
        )
        
        structure_result = ValidationResult(
            passed=structure_passed,
            score=ai_result.structure_score,
            issues=ai_result.structure_issues,
            details=f"Detected type: {ai_result.detected_type}"
        )
        
        parse_result = ValidationResult(
            passed=parse_passed,
            score=ai_result.parse_score,
            issues=ai_result.parse_issues,
            details="Parse quality (no artifacts/contamination)"
        )
        
        # Media integrity combines URL accessibility and AI image analysis
        media_score = ai_result.images_score if has_images else 100
        media_issues = ai_result.images_issues.copy()
        
        # Add URL accessibility issues to the list
        for detail in media_details:
            if not detail.exists:
                media_issues.append(f"Media not accessible: {detail.url}")
        
        # Media passes if AI score >= 90 AND all URLs are accessible
        media_urls_accessible = all(m.exists for m in media_details)
        images_score_passed = media_score >= 90
        media_passed = images_score_passed and media_urls_accessible
        
        media_result = ValidationResult(
            passed=media_passed,
            score=media_score,
            issues=media_issues,
            details=f"Validated {len(media_details)} media items"
        )
        
        # Calculate overall score (weighted average)
        overall_score = self._calculate_overall_score(
            content_result.score,
            structure_result.score,
            parse_result.score,
            media_result.score,
            has_media=len(media_details) > 0
        )
        
        # Overall valid if all critical extraction checks pass
        is_valid = (
            not ai_validation_failed
            and content_result.passed
            and structure_result.passed
            and parse_result.passed
            and (media_result.passed or len(media_details) == 0)
            and overall_score >= 90
        )
        
        return QTIValidationOutput(
            question_id=question_id,
            is_valid=is_valid,
            overall_score=overall_score,
            content_completeness=content_result,
            media_integrity=media_result,
            structure_validity=structure_result,
            parse_quality=parse_result,
            media_details=media_details,
            detected_question_type=ai_result.detected_type,
            errors=errors,
            ai_reasoning=ai_result.reasoning,
            ai_validation_failed=ai_validation_failed,
        )
    
    def _parse_qti_structure(self, qti_xml: str) -> dict:
        """
        Parse QTI XML and extract structural information.
        
        Focus on extraction-relevant structure, NOT assessment elements.
        We check for itemBody and interaction elements, NOT responseDeclaration.
        
        Args:
            qti_xml: QTI 3.0 XML string
            
        Returns:
            Dict with structural info (interaction_type, images, etc.)
        """
        result = {
            "interaction_type": "unknown",
            "images": [],
            "has_item_body": False,
            "has_interaction": False,
            "structure_issues": [],
        }
        
        try:
            root = ET.fromstring(qti_xml)
            
            # Detect interaction type
            interaction_types = [
                "choiceInteraction", "textEntryInteraction", "extendedTextInteraction",
                "matchInteraction", "orderInteraction", "hottextInteraction",
                "inlineChoiceInteraction", "gapMatchInteraction", "customInteraction"
            ]
            
            for itype in interaction_types:
                # Check both QTI 3.0 hyphenated and camelCase forms
                qti_elem = f"qti-{itype.replace('Interaction', '-interaction')}"
                
                # Try with namespace first
                if root.find(f".//{qti_elem}", QTI_NS) is not None:
                    result["interaction_type"] = itype
                    result["has_interaction"] = True
                    break
                
                # String-based fallback for various QTI formats
                if (f"<{qti_elem}" in qti_xml or 
                    f"<{itype}" in qti_xml or 
                    f"<qti:{itype}" in qti_xml):
                    result["interaction_type"] = itype
                    result["has_interaction"] = True
                    break
            
            # Extract image URLs with positional context
            def local_name(tag: str) -> str:
                if "}" in tag:
                    return tag.split("}", 1)[1]
                return tag

            def describe_path(path_tags: list) -> str:
                if not path_tags:
                    return "unknown position"
                path_str = " > ".join(path_tags)
                if any("simple-choice" in t for t in path_tags):
                    return f"in answer choice ({path_str})"
                if any("item-body" in t for t in path_tags):
                    return f"in question stem or prompt ({path_str})"
                if any("stimulus" in t or "passage" in t for t in path_tags):
                    return f"in stimulus/passage ({path_str})"
                return path_str

            def walk(element, ancestors: list):
                tag_name = local_name(element.tag).lower()
                current_path = ancestors + [tag_name]

                if "img" in tag_name or tag_name.endswith("img"):
                    src = element.get("src") or element.get("data")
                    if src:
                        result["images"].append({
                            "url": src,
                            "alt": element.get("alt", ""),
                            "context": describe_path(current_path),
                        })

                # Also check for object elements (QTI uses these for media)
                if "object" in tag_name:
                    data = element.get("data")
                    if data and data.lower().endswith(
                        (".png", ".jpg", ".jpeg", ".gif", ".svg")
                    ):
                        result["images"].append({
                            "url": data,
                            "alt": element.get("alt", ""),
                            "context": describe_path(current_path),
                        })

                for child in element:
                    walk(child, current_path)

            walk(root, [])
            
            # Check for itemBody (the actual question content)
            has_item_body = (
                '<itemBody' in qti_xml or
                '<qti-item-body' in qti_xml
            )
            result["has_item_body"] = has_item_body
            
            if not has_item_body:
                result["structure_issues"].append("Missing itemBody - no question content")
            
            if not result["has_interaction"]:
                result["structure_issues"].append("No interaction element detected")
                
        except ET.ParseError as e:
            result["structure_issues"].append(f"XML parse error: {e}")
            
        return result
    
    def _validate_media_urls(
        self,
        xml_images: list,
        provided_images: list
    ) -> List[MediaValidationDetail]:
        """
        Validate that media URLs are accessible.
        
        Uses GET with stream=True and browser-like headers for reliability.
        
        Args:
            xml_images: Images found in XML
            provided_images: Images provided in the request
            
        Returns:
            List of MediaValidationDetail for each image
        """
        details = []
        
        # Browser-like headers for reliable URL checking
        headers = {
            'User-Agent': 'Mozilla/5.0 (compatible; QTIValidator/1.0)',
            'Accept': 'image/webp,image/apng,image/*,*/*;q=0.8',
        }
        
        # Combine images from XML and provided images
        all_urls = set()
        for img in xml_images:
            all_urls.add(img.get("url"))
        for img in provided_images:
            url = img.get("url") if isinstance(img, dict) else getattr(img, "url", None)
            if url:
                all_urls.add(url)
        
        for url in all_urls:
            if not url:
                continue
            
            # Skip data URLs - they're embedded base64 images, no need to validate
            if url.startswith("data:"):
                details.append(MediaValidationDetail(
                    url=url[:50] + "...(base64)",  # Truncate for readability
                    exists=True,  # Data URLs are always "accessible"
                    issues=[],
                ))
                continue
                
            detail = MediaValidationDetail(
                url=url,
                exists=False,
                issues=[],
            )
            
            # Check if URL is accessible using GET with stream=True
            try:
                response = requests.get(
                    url,
                    timeout=15,
                    allow_redirects=True,
                    stream=True,  # Don't download full image
                    headers=headers
                )
                response.close()
                
                if response.status_code == 200:
                    detail.exists = True
                else:
                    detail.issues.append(f"HTTP {response.status_code}")
            except requests.RequestException as e:
                detail.issues.append(f"Request failed: {str(e)[:100]}")
            
            details.append(detail)
        
        return details
    
    def _run_ai_validation(
        self,
        qti_xml: str,
        images: list,
        has_images: bool,
        xml_images: Optional[list] = None,
    ) -> AIValidationResponse:
        """
        Run AI-powered extraction validation.
        
        Args:
            qti_xml: QTI XML string
            images: List of image objects
            has_images: Whether images are being provided
            xml_images: Images discovered in the QTI XML with context
            
        Returns:
            AIValidationResponse with validation results
        """
        if has_images:
            xml_images = xml_images or []
            context_by_url: dict = {}
            for xml_img in xml_images:
                url = xml_img.get("url")
                context = xml_img.get("context") or xml_img.get("path")
                if url and context:
                    context_by_url[url] = context

            image_descriptions: list = []
            for index, img in enumerate(images, 1):
                url = img.get("url") if isinstance(img, dict) else getattr(img, "url", None)
                alt = img.get("alt_text") if isinstance(img, dict) else getattr(img, "alt_text", None)
                parts: list = []
                if alt:
                    parts.append(f"Alt text: {alt}")
                if url and url in context_by_url:
                    parts.append(f"QTI position: {context_by_url[url]}")
                description_core = " | ".join(parts) if parts else "No alt text or position metadata"
                
                prefix = f"Image {index}"
                if url:
                    if url.startswith("data:"):
                        mime_type = url.split(";")[0].replace("data:", "") if ";" in url else "image"
                        prefix += f" (embedded {mime_type})"
                    elif len(url) <= 100:
                        prefix += f" ({url})"
                    else:
                        prefix += f" ({url[:50]}...)"
                image_descriptions.append(f"{prefix}: {description_core}")

            prompt = build_image_validation_prompt(
                qti_xml=qti_xml,
                image_count=len(images),
                image_descriptions=image_descriptions,
            )
            result = self._call_ai_with_images(prompt, images)
        else:
            prompt = build_validation_prompt(qti_xml=qti_xml, has_images=False)
            result = self.ai_client.generate_json(
                prompt, temperature=0.0, max_tokens=4096, thinking_level="high"
            )
        
        return AIValidationResponse(
            is_complete=result.get("is_complete", False),
            content_score=result.get("content_score", 0),
            content_issues=result.get("content_issues", []),
            structure_valid=result.get("structure_valid", False),
            structure_score=result.get("structure_score", 0),
            structure_issues=result.get("structure_issues", []),
            parse_clean=result.get("parse_clean", False),
            parse_score=result.get("parse_score", 0),
            parse_issues=result.get("parse_issues", []),
            images_contextual=result.get("images_contextual"),
            images_score=result.get("images_score", 100),
            images_issues=result.get("images_issues", []),
            detected_type=result.get("detected_type", "unknown"),
            reasoning=result.get("reasoning", ""),
        )
    
    def _call_ai_with_images(self, prompt: str, images: list) -> dict:
        """Call AI with images for multimodal validation."""
        generate_with_images = getattr(self.ai_client, "generate_json_with_images", None)
        if not callable(generate_with_images):
            raise RuntimeError(
                "AI client does not support image inputs. "
                "Expected generate_json_with_images(prompt, images, ...)."
            )

        return generate_with_images(
            prompt=prompt,
            images=images,
            max_tokens=4096,
            thinking_level="high",
        )
    
    def _calculate_overall_score(
        self,
        content_score: int,
        structure_score: int,
        parse_score: int,
        media_score: int,
        has_media: bool,
    ) -> int:
        """
        Calculate weighted overall score for extraction quality.
        
        Weights (focused on extraction completeness):
        - Content: 40% (is all content present?)
        - Structure: 25% (is structure correct for question type?)
        - Parse: 25% (is it clean, no artifacts?)
        - Media: 10% (if applicable, are images correct?)
        
        Args:
            content_score: Content completeness score
            structure_score: Structure validity score
            parse_score: Parse quality score
            media_score: Media integrity score
            has_media: Whether question has media
            
        Returns:
            Weighted overall score 0-100
        """
        if has_media:
            return int(
                content_score * 0.35 +
                structure_score * 0.25 +
                parse_score * 0.25 +
                media_score * 0.15
            )
        else:
            return int(
                content_score * 0.40 +
                structure_score * 0.30 +
                parse_score * 0.30
            )

