from __future__ import annotations

import json
from typing import Any, Dict, List

from openai import OpenAI
from pydantic import BaseModel, Field


class FilteredTables(BaseModel):
    """A Pydantic model to structure the response for table filtering."""

    indices_to_keep: List[int] = Field(
        ..., description=("A list of integer IDs of the tables that are part of the actual question content and should be kept.")
    )


def get_indices_of_tables_to_keep(tables: List[Dict[str, Any]], openai_api_key: str) -> List[int]:
    """
    Uses an LLM call to identify tables that should be kept.

    It filters out tables that are for physical/interactive
    answering, like bubble sheets or numeric entry grids.

    Args:
        tables: A list of table dictionaries. Each dict must have 'html_content'.
        openai_api_key: The OpenAI API key.

    Returns:
        A list of indices of tables that should be kept.
    """
    if not tables:
        return []

    table_html_contents = [{"id": i, "html_content": table.get("html_content", "<table></table>")} for i, table in enumerate(tables)]

    prompt = f"""
You are an expert in educational content analysis.
Based on the following list of HTML tables, identify which tables are part of the question's content and which are interactive elements for answering.

Here are the HTML tables:
{json.dumps(table_html_contents, indent=2)}

Please return a JSON object with a single key "indices_to_keep", which is a list of the
integer IDs of the tables that are part of the actual question content and should be kept.
Exclude tables that are purely for user interaction on a physical paper or a specific digital interface for bubbling answers.

Example of what to exclude:
- A table representing a grid of bubbles for multiple-choice answers.
- A table forming a numeric grid for gridded responses.

Example of what to keep:
- A table presenting data needed to answer the question.
- A table that is part of a reading passage.

Respond with only a valid JSON object.
Example response:
{{
  "indices_to_keep": [0]
}}
"""

    client = OpenAI(api_key=openai_api_key)

    try:
        response = client.beta.chat.completions.parse(
            model="gpt-5.1",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are an expert in educational content analysis. "
                        "Your task is to distinguish between content tables and "
                        "interactive answering elements based on their HTML structure. "
                        "Respond only with valid JSON that conforms to the provided schema."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            response_format=FilteredTables,
            reasoning_effort="high",
        )

        result = response.choices[0].message.parsed
        if result and isinstance(result, FilteredTables):
            indices_to_keep = result.indices_to_keep
            print(f"Table filtering: LLM decided to keep indices {indices_to_keep}.")
            return indices_to_keep
        else:
            print("Table filtering LLM returned an invalid Pydantic object. Keeping all tables.")
            return list(range(len(tables)))

    except Exception as e:
        print(f"Error during table filtering LLM call: {e}. Keeping all tables.")
        return list(range(len(tables)))
