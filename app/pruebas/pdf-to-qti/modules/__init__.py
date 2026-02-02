# PDF to QTI Converter Modules

# Re-export main functions for backward compatibility
from .qti_transformer import (
    transform_to_qti,
    detect_encoding_errors,
    verify_and_fix_encoding,
)
from .qti_encoding import ENCODING_FIXES
from .qti_answer_utils import (
    extract_correct_answer_from_qti,
    update_correct_answer_in_qti_xml,
)
from .qti_response_parsers import (
    parse_transformation_response,
    parse_correction_response,
)
from .qti_xml_utils import (
    clean_qti_xml,
    replace_data_uris_with_s3_urls,
    fix_qti_xml_with_llm,
)

__all__ = [
    "transform_to_qti",
    "detect_encoding_errors",
    "verify_and_fix_encoding",
    "ENCODING_FIXES",
    "extract_correct_answer_from_qti",
    "update_correct_answer_in_qti_xml",
    "parse_transformation_response",
    "parse_correction_response",
    "clean_qti_xml",
    "replace_data_uris_with_s3_urls",
    "fix_qti_xml_with_llm",
]
