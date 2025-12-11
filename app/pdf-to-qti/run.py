#!/usr/bin/env python3
"""
PDF to QTI Converter - Main Entry Point

Converts PDF test documents into QTI 3.0 XML files.

Pipeline Steps:
1. PARSE:    PDF → Parsed JSON (using Extend.ai)
2. SEGMENT:  Parsed JSON → Individual Questions
3. GENERATE: Questions → QTI XML
4. VALIDATE: QTI XML → Validated QTI (extraction quality check)

Usage:
    # Full pipeline
    python run.py input.pdf --output ./output --provider gemini
    
    # Step by step
    python run.py input.pdf --step parse --output ./output
    python run.py ./output/parsed.json --step segment --output ./output
    python run.py ./output/segmented.json --step generate --output ./output
    python run.py ./output/qti --step validate --output ./output

IMPORTANT: PDF parsing with Extend.ai should only be run ONCE per test file.
The Extend.ai parser is deterministic - running it again will produce the same result.
Always save and reuse the parsed.json output to avoid wasting API calls.
"""

from __future__ import annotations

import sys
import json
import logging
from pathlib import Path

try:
    import click
except ImportError:
    print("Error: click not installed. Run: pip install click")
    sys.exit(1)

from config import Config
from models import PipelineReport, GeneratorOutput
from pipeline import PDFParser, Segmenter, Generator, Validator


def setup_logging(verbose: bool) -> None:
    """Configure logging based on verbosity level."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%H:%M:%S'
    )


@click.command()
@click.argument('input_file', type=click.Path(exists=True))
@click.option(
    '--output', '-o',
    type=click.Path(),
    default='./output',
    help='Output directory (default: ./output)'
)
@click.option(
    '--provider', '-p',
    type=click.Choice(['gemini', 'gpt', 'opus']),
    default=None,
    help='AI provider (default: gemini)'
)
@click.option(
    '--step', '-s',
    type=click.Choice(['parse', 'segment', 'generate', 'validate', 'all']),
    default='all',
    help='Pipeline step to run (default: all)'
)
@click.option(
    '--skip-validation',
    is_flag=True,
    default=False,
    help='Skip XSD and semantic validation during generation'
)
@click.option(
    '--verbose', '-v',
    is_flag=True,
    default=False,
    help='Enable verbose logging'
)
def main(
    input_file: str,
    output: str,
    provider: str | None,
    step: str,
    skip_validation: bool,
    verbose: bool
) -> None:
    """
    Convert PDF test documents to QTI 3.0 XML.
    
    INPUT_FILE: Path to PDF file or intermediate JSON/directory
    
    \b
    PIPELINE STEPS:
      parse     - Convert PDF to structured JSON (Extend.ai)
      segment   - Split JSON into individual questions
      generate  - Convert questions to QTI XML
      validate  - Validate QTI extraction quality
      all       - Run all applicable steps
    
    \b
    IMPORTANT: PDF parsing is deterministic!
    Run 'parse' only ONCE per PDF and reuse the parsed.json output.
    This avoids wasting Extend.ai API calls.
    """
    setup_logging(verbose)
    logger = logging.getLogger(__name__)
    
    input_path = Path(input_file)
    output_dir = Path(output)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Determine provider
    if provider is None:
        available = Config.get_available_providers()
        if not available:
            click.echo(
                "Error: No AI provider credentials found.\n"
                "Set one of: GEMINI_API_KEY, OPENAI_API_KEY, or AWS credentials",
                err=True
            )
            sys.exit(1)
        provider = available[0]
        logger.info(f"Using auto-detected provider: {provider}")
    else:
        if not Config.validate_provider(provider):
            click.echo(f"Error: No credentials found for provider '{provider}'", err=True)
            sys.exit(1)
    
    # Initialize report
    report = PipelineReport(
        input_file=str(input_path),
        total_questions=0,
        successful_questions=0,
        failed_questions=0
    )
    
    try:
        # Determine what step(s) to run based on input file type
        if step == 'all':
            steps_to_run = _determine_steps_from_input(input_path, output_dir)
        else:
            steps_to_run = [step]
        
        parsed_data = None
        segmenter_output = None
        generator_output = None
        
        # =====================================================================
        # STEP 1: PARSE (PDF → JSON)
        # =====================================================================
        if 'parse' in steps_to_run:
            if not Config.can_parse_pdf():
                click.echo(
                    "Error: PDF parsing requires EXTEND_API_KEY.\n"
                    "Set the environment variable or use a pre-parsed JSON file.",
                    err=True
                )
                sys.exit(1)
            
            # Check if already parsed
            parsed_json_path = output_dir / 'parsed.json'
            if parsed_json_path.exists():
                click.echo(
                    f"⚠️  WARNING: parsed.json already exists at {parsed_json_path}\n"
                    "   Extend.ai parsing is deterministic - re-parsing will give the same result.\n"
                    "   Skipping parse step. Delete parsed.json to force re-parsing."
                )
                with open(parsed_json_path, 'r') as f:
                    parsed_data = json.load(f)
                report.parse_status = "skipped (cached)"
            else:
                click.echo(f"📄 Parsing PDF: {input_path.name}")
                click.echo("   (Remember: only parse ONCE per PDF, then reuse parsed.json)")
                parser = PDFParser()
                parsed_data = parser.parse(str(input_path), str(output_dir))
                report.parse_status = "completed"
                click.echo(f"   ✓ Extracted {len(parsed_data.get('chunks', []))} pages")
        
        # =====================================================================
        # STEP 2: SEGMENT (JSON → Questions)
        # =====================================================================
        if 'segment' in steps_to_run:
            # Load parsed data if not from previous step
            if parsed_data is None:
                parsed_data = _load_parsed_data(input_path, output_dir)
            
            click.echo(f"✂️  Segmenting into questions...")
            segmenter = Segmenter(model_provider=provider)
            segmenter_output = segmenter.segment(
                parsed_data,
                output_dir=str(output_dir),
                save_individual_questions=True
            )
            report.segment_status = "completed" if segmenter_output.success else "failed"
            
            if segmenter_output.success:
                report.total_questions = len(segmenter_output.validated_questions)
                click.echo(
                    f"   ✓ Found {len(segmenter_output.validated_questions)} valid questions"
                )
                if segmenter_output.unvalidated_questions:
                    click.echo(
                        f"   ⚠ {len(segmenter_output.unvalidated_questions)} "
                        "questions failed split validation"
                    )
            else:
                click.echo(f"   ✗ Segmentation failed", err=True)
                for error in segmenter_output.errors[:3]:
                    click.echo(f"      {error}", err=True)
        
        # =====================================================================
        # STEP 3: GENERATE (Questions → QTI XML)
        # =====================================================================
        if 'generate' in steps_to_run:
            # Load segmenter output if not from previous step
            if segmenter_output is None:
                segmenter_output = _load_segmenter_output(input_path, output_dir)
            
            click.echo(f"🔧 Generating QTI XML...")
            generator = Generator(
                model_provider=provider,
                skip_validation=skip_validation
            )
            generator_output = generator.generate(
                segmenter_output,
                output_dir=str(output_dir)
            )
            report.generate_status = "completed" if generator_output.success else "failed"
            
            report.successful_questions = len(generator_output.qti_items)
            report.failed_questions = len(generator_output.errors)
            
            if generator_output.success:
                click.echo(
                    f"   ✓ Generated {len(generator_output.qti_items)} QTI files"
                )
            if generator_output.errors:
                click.echo(f"   ⚠ {len(generator_output.errors)} questions failed")
                for error in generator_output.errors[:3]:
                    click.echo(f"      {error}", err=True)
        
        # =====================================================================
        # STEP 4: VALIDATE (QTI XML → Validated QTI)
        # =====================================================================
        if 'validate' in steps_to_run:
            # Load generator output if not from previous step
            if generator_output is None:
                generator_output = _load_generator_output(input_path, output_dir)
            
            click.echo(f"🔍 Validating QTI extraction quality...")
            validator = Validator(model_provider=provider)
            validator_output = validator.validate(
                generator_output,
                output_dir=str(output_dir)
            )
            report.validate_status = "completed" if validator_output.success else "failed"
            
            if validator_output.success:
                total = len(validator_output.validation_results)
                valid = validator_output.valid_count
                click.echo(
                    f"   ✓ {valid}/{total} questions passed extraction validation"
                )
            if validator_output.invalid_count > 0:
                click.echo(
                    f"   ⚠ {validator_output.invalid_count} questions have extraction issues"
                )
        
        # Save report
        report_path = output_dir / 'report.json'
        with open(report_path, 'w') as f:
            json.dump(report.model_dump(), f, indent=2)
        
        # Final summary
        click.echo("")
        click.echo("=" * 60)
        click.echo("Pipeline Complete!")
        click.echo(f"  Output directory: {output_dir}")
        if report.total_questions > 0:
            success_rate = (report.successful_questions / report.total_questions) * 100
            click.echo(
                f"  Questions: {report.successful_questions}/{report.total_questions} "
                f"({success_rate:.0f}% success)"
            )
        click.echo("=" * 60)
        
    except Exception as e:
        logger.exception(f"Pipeline failed: {e}")
        report.errors.append(str(e))
        
        report_path = output_dir / 'report.json'
        with open(report_path, 'w') as f:
            json.dump(report.model_dump(), f, indent=2)
        
        click.echo(f"\n❌ Error: {e}", err=True)
        sys.exit(1)


def _determine_steps_from_input(input_path: Path, output_dir: Path) -> list:
    """Determine which steps to run based on input file type."""
    # If input is a directory, assume it's the qti/ folder for validation
    if input_path.is_dir():
        return ['validate']
    
    if input_path.suffix.lower() == '.pdf':
        return ['parse', 'segment', 'generate', 'validate']
    
    if input_path.name == 'parsed.json':
        return ['segment', 'generate', 'validate']
    
    if input_path.name == 'segmented.json':
        return ['generate', 'validate']
    
    if input_path.name == 'generator_output.json':
        return ['validate']
    
    # Try to detect from content
    try:
        with open(input_path, 'r') as f:
            data = json.load(f)
        
        if 'chunks' in data:
            return ['segment', 'generate', 'validate']
        elif 'validated_questions' in data:
            return ['generate', 'validate']
        elif 'qti_items' in data:
            return ['validate']
    except (json.JSONDecodeError, KeyError):
        pass
    
    click.echo("Error: Cannot determine file type. Use --step to specify.", err=True)
    sys.exit(1)


def _load_parsed_data(input_path: Path, output_dir: Path) -> dict:
    """Load parsed data from file."""
    if input_path.suffix.lower() == '.json':
        with open(input_path, 'r') as f:
            return json.load(f)
    else:
        parsed_path = output_dir / 'parsed.json'
        if not parsed_path.exists():
            click.echo(f"Error: parsed.json not found at {parsed_path}", err=True)
            sys.exit(1)
        with open(parsed_path, 'r') as f:
            return json.load(f)


def _load_segmenter_output(input_path: Path, output_dir: Path):
    """Load segmenter output from file."""
    from models import SegmenterOutput
    
    if input_path.suffix.lower() == '.json' and 'segmented' in str(input_path):
        segmented_path = input_path
    else:
        segmented_path = output_dir / 'segmented.json'
    
    if not segmented_path.exists():
        click.echo(f"Error: segmented.json not found at {segmented_path}", err=True)
        sys.exit(1)
    
    with open(segmented_path, 'r') as f:
        return SegmenterOutput(**json.load(f))


def _load_generator_output(input_path: Path, output_dir: Path) -> GeneratorOutput:
    """Load generator output from file or directory."""
    from models import QTIItem
    
    # If input is a directory, treat it as the qti/ folder
    if input_path.is_dir():
        qti_items = []
        for xml_file in input_path.glob("*.xml"):
            with open(xml_file, 'r') as f:
                qti_xml = f.read()
            qti_items.append(QTIItem(
                question_id=xml_file.stem,
                qti_xml=qti_xml,
            ))
        
        if not qti_items:
            click.echo(f"Error: No QTI files found in {input_path}", err=True)
            sys.exit(1)
        
        return GeneratorOutput(success=True, qti_items=qti_items)
    
    # Check for generator_output.json
    if input_path.suffix.lower() == '.json' and 'generator' in str(input_path):
        generator_path = input_path
    else:
        generator_path = output_dir / 'generator_output.json'
    
    if generator_path.exists():
        with open(generator_path, 'r') as f:
            return GeneratorOutput(**json.load(f))
    
    # Fall back to qti/ directory
    qti_dir = output_dir / 'qti'
    if qti_dir.exists():
        qti_items = []
        for xml_file in qti_dir.glob("*.xml"):
            with open(xml_file, 'r') as f:
                qti_xml = f.read()
            qti_items.append(QTIItem(
                question_id=xml_file.stem,
                qti_xml=qti_xml,
            ))
        
        if not qti_items:
            click.echo(f"Error: No QTI files found in {qti_dir}", err=True)
            sys.exit(1)
        
        return GeneratorOutput(success=True, qti_items=qti_items)
    
    click.echo(
        f"Error: No generator output found. Expected:\n"
        f"  - {output_dir / 'generator_output.json'} or\n"
        f"  - {output_dir / 'qti'}/*.xml",
        err=True
    )
    sys.exit(1)


if __name__ == '__main__':
    main()
