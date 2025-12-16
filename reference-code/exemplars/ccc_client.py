"""
CommonCoreCrawl GraphQL API client for fetching MA science test questions.
"""

import json
from typing import Any

import requests

from app.io import EXEMPLAR_PATH


API_URL = "https://api.commoncorecrawl.com/graphql"
API_KEY = "fa_ccc_2e7d94c1af358b06"

HEADERS = {"x-api-key": API_KEY, "Content-Type": "application/json"}


def execute_query(query: str, variables: dict[str, Any] | None = None) -> dict[str, Any]:
    """Execute a GraphQL query against CommonCoreCrawl API."""
    payload = {"query": query}
    if variables:
        payload["variables"] = variables

    response = requests.post(API_URL, json=payload, headers=HEADERS)

    if response.status_code != 200:
        print(f"Error response: {response.status_code}")
        print(f"Response body: {response.text}")
        response.raise_for_status()

    result = response.json()
    if "errors" in result:
        raise Exception(f"GraphQL errors: {result['errors']}")

    return result["data"]


def fetch_ma_science_tests(grades: list[str] | None = None) -> list[dict[str, Any]]:
    """
    Fetch all MA science tests for grades 3-5.

    Returns:
        List of test objects with id, name, and metadata.
    """
    if grades is None:
        grades = ["G3", "G4", "G5"]
    all_tests = []

    for grade in grades:
        query = """
        query FetchTests($subject: SubjectType!, $grade: GradeType!, $educationLevel: EducationLevelType!, $state: String!, $hasQtiXml: Boolean!, $language: LanguageType!) {
            tests(
                subject: $subject,
                grade: $grade,
                educationLevel: $educationLevel,
                state: $state,
                hasQuestionsWithQtiXml: $hasQtiXml,
                language: $language
            ) {
                edges {
                    node {
                        id
                        title
                        grade
                        subject
                        state
                        releaseYear
                        pdfUrl
                        language
                    }
                }
            }
        }
        """

        variables = {
            "subject": "science",
            "grade": grade,
            "educationLevel": "elementary",
            "state": "MA",
            "hasQtiXml": True,
            "language": "en",
        }

        data = execute_query(query, variables)

        if data and "tests" in data and "edges" in data["tests"]:
            for edge in data["tests"]["edges"]:
                test = edge["node"]
                all_tests.append(test)

    return all_tests


def fetch_test_questions(test_id: str) -> list[dict[str, Any]]:
    """
    Fetch all questions for a given test.

    Returns:
        List of question objects with id, qtiXml, difficulty, and metadata.
    """
    query = """
    query FetchTestQuestions($testId: ID!) {
        testQuestions(testId: $testId) {
            edges {
                node {
                    id
                    qtiXml
                    orderIndex
                    title
                    questionType
                    difficulty
                }
            }
        }
    }
    """

    variables = {"testId": test_id}

    data = execute_query(query, variables)

    questions = []
    if data and "testQuestions" in data and "edges" in data["testQuestions"]:
        for edge in data["testQuestions"]["edges"]:
            questions.append(edge["node"])

    return questions


def fetch_all_ma_questions() -> dict[str, Any]:
    """
    Fetch all questions from all MA science tests for grades 3-5.

    Returns:
        Dictionary with test metadata and all their questions.
    """
    print("Fetching MA science tests for grades 3-5...")
    tests = fetch_ma_science_tests()

    print(f"Found {len(tests)} MA science tests")

    all_data = {"tests": [], "total_tests": len(tests), "total_questions": 0}

    for test in tests:
        test_id = test["id"]
        test_name = test.get("title", "Unknown")
        grade = test.get("grade", "Unknown")
        year = test.get("releaseYear", "Unknown")

        print(f"Fetching questions for test: {test_name} (Grade {grade}, {year})...")

        questions = fetch_test_questions(test_id)

        test_data = {
            "test_id": test_id,
            "title": test_name,
            "grade": grade,
            "year": year,
            "subject": test.get("subject"),
            "state": test.get("state"),
            "language": test.get("language"),
            "pdfUrl": test.get("pdfUrl"),
            "question_count": len(questions),
            "questions": questions,
        }

        all_data["tests"].append(test_data)
        all_data["total_questions"] += len(questions)

        print(f"  → Retrieved {len(questions)} questions")

    return all_data


def save_questions_to_file(data: dict[str, Any], output_file: str) -> None:
    """Save fetched questions to a JSON file."""
    from pathlib import Path

    if Path(output_file).exists():
        raise FileExistsError(
            f"File {output_file} already exists. Remove or rename it before fetching new exemplars to prevent data loss."
        )

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print(f"\nSaved {data['total_questions']} questions from {data['total_tests']} tests to {output_file}")


def run() -> None:
    """Fetch MA science questions from CommonCore Crawl API."""
    data = fetch_all_ma_questions()
    save_questions_to_file(data, EXEMPLAR_PATH)

    print("\nSummary:")
    print(f"  Total tests: {data['total_tests']}")
    print(f"  Total questions: {data['total_questions']}")
    print("\nBreakdown by grade:")
    for grade in ["G3", "G4", "G5"]:
        grade_tests = [t for t in data["tests"] if t["grade"] == grade]
        grade_questions = sum(t["question_count"] for t in grade_tests)
        print(f"  Grade {grade}: {len(grade_tests)} tests, {grade_questions} questions")


if __name__ == "__main__":
    run()
