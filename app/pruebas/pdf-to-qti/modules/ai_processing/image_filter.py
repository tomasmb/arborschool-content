from __future__ import annotations

import json
from typing import Any, Dict, List

from openai import OpenAI
from pydantic import BaseModel, Field


class FilteredImages(BaseModel):
    """A Pydantic model to structure the response for image filtering."""
    indices_to_keep: List[int] = Field(..., description="A list of integer IDs of the images that should be kept.")


def get_indices_of_images_to_keep(
    images: List[Dict[str, Any]],
    openai_api_key: str
) -> List[int]:
    """
    Uses an LLM call to identify images that should be kept.

    It filters out images that are for physical/interactive
    answering, like bubble sheets or numeric keypads.

    Args:
        images: A list of image dictionaries. Each dict must have a 'description'.
        openai_api_key: The OpenAI API key.

    Returns:
        A list of indices of images that should be kept.
    """
    if not images:
        return []

    image_descriptions = [
        {
            "id": i,
            "description": image.get('description', 'No description available.'),
            "is_choice_image": image.get('is_choice_diagram', False)
        } for i, image in enumerate(images)
    ]

    prompt = f"""
You are an expert in educational content analysis.
Based on the following list of image descriptions, identify which images are part of the
question's content and which are interactive elements for answering, such as bubble
sheets, numeric keypads for bubbling, or other answer areas not intrinsic to the
question's content.

An image with `is_choice_image: true` is an image representing an answer choice
(e.g. four different diagrams for choices A, B, C, D) and should almost always be kept.

Here are the image descriptions:
{json.dumps(image_descriptions, indent=2)}

Please return a JSON object with a single key "indices_to_keep", which is a list of the
integer IDs of the images that are part of the actual question content and should be kept.
Exclude images that are purely for user interaction on a physical paper or a specific digital interface for bubbling answers.

Example of what to exclude:
- An image showing a grid of bubbles for multiple-choice answers (A, B, C, D).
- A numeric keypad for filling in a gridded response.
- An area for writing an essay that is just a box.

Example of what to keep:
- Diagrams, graphs, charts, maps, photos that are referenced by the question.
- Images that are part of the answer choices themselves (e.g., four different diagrams for A, B, C, D), these are marked with `is_choice_image: true`.
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
                        "Your task is to distinguish between content images and "
                        "interactive answering elements based on their descriptions. "
                        "Respond only with valid JSON that conforms to the provided schema."
                    )
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            response_format=FilteredImages,
            reasoning_effort="high",
        )

        result = response.choices[0].message.parsed
        if result and isinstance(result, FilteredImages):
            indices_to_keep = result.indices_to_keep
            print(f"Image filtering: LLM decided to keep indices {indices_to_keep}.")
            return indices_to_keep
        else:
            print("Image filtering LLM returned an invalid Pydantic object. Keeping all images.")
            return list(range(len(images)))

    except Exception as e:
        print(f"Error during structured output LLM call: {e}. Keeping all images.")
        return list(range(len(images)))
