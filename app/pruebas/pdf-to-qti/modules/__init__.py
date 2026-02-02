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
from .external_validation import (
    validate_with_external_service,
    is_validation_error_recoverable,
    build_validation_result_dict,
    print_validation_debug,
)
from .pipeline_helpers import (
    generate_question_id,
    load_answer_key,
    save_debug_files,
    save_detection_result,
    save_conversion_result,
    build_output_files_dict,
)
from .pipeline_cache import (
    check_existing_xml,
    try_regenerate_from_processed,
    try_auto_regenerate_on_error,
    extract_test_name_from_path,
)
from .pipeline_s3 import (
    load_s3_mapping,
    save_s3_mapping,
    initialize_s3_mapping_from_xml,
    process_restored_base64_images,
    count_remaining_base64,
    validate_all_images_in_s3,
    print_base64_warning_with_instructions,
    post_validation_s3_processing,
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
    "validate_with_external_service",
    "is_validation_error_recoverable",
    "build_validation_result_dict",
    "print_validation_debug",
    "generate_question_id",
    "load_answer_key",
    "save_debug_files",
    "save_detection_result",
    "save_conversion_result",
    "build_output_files_dict",
    "check_existing_xml",
    "try_regenerate_from_processed",
    "try_auto_regenerate_on_error",
    "extract_test_name_from_path",
    "load_s3_mapping",
    "save_s3_mapping",
    "initialize_s3_mapping_from_xml",
    "process_restored_base64_images",
    "count_remaining_base64",
    "validate_all_images_in_s3",
    "print_base64_warning_with_instructions",
    "post_validation_s3_processing",
]
