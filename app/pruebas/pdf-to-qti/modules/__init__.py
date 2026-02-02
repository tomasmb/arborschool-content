# PDF to QTI Converter Modules

# Re-export main functions for backward compatibility
from .external_validation import (
    build_validation_result_dict,
    is_validation_error_recoverable,
    print_validation_debug,
    validate_with_external_service,
)
from .pipeline_cache import (
    check_existing_xml,
    extract_test_name_from_path,
    try_auto_regenerate_on_error,
    try_regenerate_from_processed,
)
from .pipeline_helpers import (
    build_output_files_dict,
    generate_question_id,
    load_answer_key,
    save_conversion_result,
    save_debug_files,
    save_detection_result,
)
from .pipeline_s3 import (
    count_remaining_base64,
    initialize_s3_mapping_from_xml,
    load_s3_mapping,
    post_validation_s3_processing,
    print_base64_warning_with_instructions,
    process_restored_base64_images,
    save_s3_mapping,
    validate_all_images_in_s3,
)
from .qti_answer_utils import (
    extract_correct_answer_from_qti,
    update_correct_answer_in_qti_xml,
)
from .qti_encoding import ENCODING_FIXES
from .qti_response_parsers import (
    parse_correction_response,
    parse_transformation_response,
)
from .qti_transformer import (
    detect_encoding_errors,
    transform_to_qti,
    verify_and_fix_encoding,
)
from .qti_xml_utils import (
    clean_qti_xml,
    fix_qti_xml_with_llm,
    replace_data_uris_with_s3_urls,
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
