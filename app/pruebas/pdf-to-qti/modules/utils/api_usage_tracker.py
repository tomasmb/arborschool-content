"""
API Usage Tracker
-----------------
Tracks and logs API usage (tokens, costs) for OpenAI and Gemini API calls.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

# Pricing per million tokens (November 2025)
PRICING = {
    "openai": {
        "gpt-5.1": {
            "input": 1.25,
            "output": 10.00,
            "cached_input": 0.125,
        },
        "gpt-5.1-mini": {
            "input": 0.25,
            "output": 2.00,
            "cached_input": 0.025,
        },
    },
    "gemini": {
        "gemini-3-pro-preview": {
            "input": 0.0,  # Update when pricing is known
            "output": 0.0,
        },
    },
}


def calculate_cost(
    provider: str,
    model: str,
    input_tokens: int,
    output_tokens: int,
    cached_input_tokens: int = 0,
) -> float:
    """Calculate cost for API usage."""
    provider_pricing = PRICING.get(provider, {})
    model_pricing = provider_pricing.get(model, {})

    if not model_pricing:
        return 0.0

    input_cost = (input_tokens / 1_000_000) * model_pricing.get("input", 0)
    output_cost = (output_tokens / 1_000_000) * model_pricing.get("output", 0)
    cached_cost = (
        (cached_input_tokens / 1_000_000)
        * model_pricing.get("cached_input", 0)
    )

    return input_cost + output_cost - cached_cost


def log_api_usage(
    provider: str,
    model: str,
    input_tokens: int,
    output_tokens: int,
    cached_input_tokens: int = 0,
    question_id: Optional[str] = None,
    output_dir: Optional[str] = None,
    operation: str = "api_call",
) -> Dict[str, Any]:
    """
    Log API usage and save to file.

    Args:
        provider: "openai" or "gemini"
        model: Model name
        input_tokens: Number of input tokens
        output_tokens: Number of output tokens
        cached_input_tokens: Number of cached input tokens (OpenAI only)
        question_id: Optional question identifier
        output_dir: Optional output directory to save usage file
        operation: Description of the operation

    Returns:
        Dictionary with usage information
    """
    timestamp = datetime.now().isoformat()
    cost = calculate_cost(provider, model, input_tokens, output_tokens, cached_input_tokens)

    usage_data = {
        "timestamp": timestamp,
        "provider": provider,
        "model": model,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "cached_input_tokens": cached_input_tokens,
        "total_tokens": input_tokens + output_tokens,
        "cost_usd": round(cost, 6),
        "operation": operation,
    }

    # Save per-question usage if question_id and output_dir provided
    if question_id and output_dir:
        usage_file = Path(output_dir) / "api_usage.json"
        usage_history = []

        if usage_file.exists():
            try:
                with open(usage_file, "r", encoding="utf-8") as f:
                    usage_history = json.load(f)
            except Exception:
                usage_history = []

        usage_history.append(usage_data)

        try:
            with open(usage_file, "w", encoding="utf-8") as f:
                json.dump(usage_history, f, indent=2)
        except Exception as e:
            print(f"⚠️  Warning: Could not save usage to {usage_file}: {e}")

    # Print summary
    print(f"📊 API Usage: {provider}/{model} | "
          f"Input: {input_tokens:,} | Output: {output_tokens:,} | "
          f"Cost: ${cost:.4f}")

    return usage_data


def get_usage_summary(
    output_dir: str,
    question_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Get summary of API usage from saved files."""
    if question_id:
        usage_file = Path(output_dir) / question_id / "api_usage.json"
    else:
        usage_file = Path(output_dir) / "api_usage.json"

    if not usage_file.exists():
        return {
            "total_calls": 0,
            "total_input_tokens": 0,
            "total_output_tokens": 0,
            "total_cost_usd": 0.0,
            "by_provider": {},
        }

    try:
        with open(usage_file, "r", encoding="utf-8") as f:
            usage_history = json.load(f)
    except Exception:
        return {
            "total_calls": 0,
            "total_input_tokens": 0,
            "total_output_tokens": 0,
            "total_cost_usd": 0.0,
            "by_provider": {},
        }

    total_calls = len(usage_history)
    total_input = sum(u.get("input_tokens", 0) for u in usage_history)
    total_output = sum(u.get("output_tokens", 0) for u in usage_history)
    total_cost = sum(u.get("cost_usd", 0) for u in usage_history)

    by_provider = {}
    for usage in usage_history:
        provider = usage.get("provider", "unknown")
        if provider not in by_provider:
            by_provider[provider] = {
                "calls": 0,
                "input_tokens": 0,
                "output_tokens": 0,
                "cost_usd": 0.0,
            }
        by_provider[provider]["calls"] += 1
        by_provider[provider]["input_tokens"] += usage.get("input_tokens", 0)
        by_provider[provider]["output_tokens"] += usage.get("output_tokens", 0)
        by_provider[provider]["cost_usd"] += usage.get("cost_usd", 0)

    return {
        "total_calls": total_calls,
        "total_input_tokens": total_input,
        "total_output_tokens": total_output,
        "total_cost_usd": round(total_cost, 4),
        "by_provider": by_provider,
    }


def print_usage_summary(summary: Dict[str, Any], title: str = "API Usage Summary"):
    """Print a formatted usage summary."""
    print(f"\n{'=' * 60}")
    print(f"📊 {title}")
    print(f"{'=' * 60}")
    print(f"Total calls: {summary['total_calls']}")
    print(f"Total input tokens: {summary['total_input_tokens']:,}")
    print(f"Total output tokens: {summary['total_output_tokens']:,}")
    print(f"Total cost: ${summary['total_cost_usd']:.4f}")

    if summary.get("by_provider"):
        print("\nBy provider:")
        for provider, stats in summary["by_provider"].items():
            print(f"  {provider}:")
            print(f"    Calls: {stats['calls']}")
            print(f"    Input: {stats['input_tokens']:,} tokens")
            print(f"    Output: {stats['output_tokens']:,} tokens")
            print(f"    Cost: ${stats['cost_usd']:.4f}")

    print(f"{'=' * 60}\n")
