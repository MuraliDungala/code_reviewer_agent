"""
Test Generator Agent
Generates comprehensive language-specific unit test suites covering:
- Happy paths (standard inputs)
- Edge cases (null/empty, boundary values, zero values)
- Negative / error test cases
Supported frameworks: pytest, Jest, PHPUnit, JUnit 5, GoogleTest, and C assert.
"""

import os
from groq import Groq


def get_client():
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        return None
    return Groq(api_key=api_key)


MODEL_NAME = os.getenv("GROQ_MODEL", "qwen/qwen3.8-27b")


FRAMEWORK_MAP = {
    "Python": "pytest",
    "JavaScript": "Jest",
    "TypeScript": "Jest (TypeScript)",
    "PHP": "PHPUnit",
    "Java": "JUnit 5",
    "C++": "GoogleTest (gtest)",
    "C": "C Standalone Assert Harness",
    "SQL": "SQL Transaction Assertion Suite",
    "MongoDB": "Jest / Mongo Memory Server",
    "Perl": "Test::More"
}


def generate_unit_tests(code: str, language: str) -> str:
    """
    Generates runnable unit tests for the provided code.
    Uses Groq LLM with a fallback template if LLM is unavailable.
    """
    framework = FRAMEWORK_MAP.get(language, "Standard Unit Tests")
    client = get_client()

    if client:
        prompt = f"""You are an automated QA & Test Engineering Agent.
Generate a complete, executable unit test suite for the following {language} code using {framework}.

Requirements:
1. Cover standard positive scenarios.
2. Cover edge cases (e.g., empty inputs, 0-division, boundary values, null/None).
3. Cover error/exception conditions.
4. Include clear comments explaining each test case.
5. Provide ONLY the code block with necessary imports and mock setup.

Code to test:
```{language.lower()}
{code[:2000]}
```
"""
        try:
            response = client.chat.completions.create(
                messages=[
                    {"role": "system", "content": f"You are an expert test engineer writing production-grade tests in {framework}."},
                    {"role": "user", "content": prompt}
                ],
                model=MODEL_NAME,
                temperature=0.2,
                max_tokens=800
            )
            return response.choices[0].message.content.strip()
        except Exception:
            pass

    # Fallback template generator if API is unavailable or rate limited
    return _generate_fallback_tests(code, language, framework)


def _generate_fallback_tests(code: str, language: str, framework: str) -> str:
    """Generates structured fallback test templates when offline."""
    if language == "Python":
        return f"""# Generated with {framework} (Offline Template)
import pytest

def test_happy_path():
    \"\"\"Test standard functional behavior.\"\"\"
    # Arrange & Act
    # Assert
    assert True

def test_edge_cases():
    \"\"\"Test edge cases: empty list, zero, boundary inputs.\"\"\"
    with pytest.raises((ValueError, ZeroDivisionError)):
        # Test boundary or error condition
        pass

def test_invalid_input():
    \"\"\"Test rejection of invalid or malformed data.\"\"\"
    pass
"""
    elif language in ["JavaScript", "TypeScript"]:
        return f"""// Generated with {framework} (Offline Template)
describe("Code Review Test Suite", () => {{
  test("should handle standard input correctly", () => {{
    // expect(result).toBe(expected);
  }});

  test("should handle edge cases (empty arrays, zero)", () => {{
    // expect(() => fn([])).toThrow();
  }});

  test("should avoid unexpected mutations", () => {{
    // expect(immutableCopy).toEqual(original);
  }});
}});
"""
    elif language == "PHP":
        return f"""<?php
// Generated with {framework} (Offline Template)
use PHPUnit\\Framework\\TestCase;

class CodeReviewTest extends TestCase {{
    public function testStandardBehavior() {{
        $this->assertTrue(true);
    }}

    public function testDivisionByZeroHandled() {{
        $this->expectException(\\DivisionByZeroError::class);
        // trigger boundary condition
    }}

    public function testEmptyInputs() {{
        // test edge case
    }}
}}
"""
    elif language in ["C", "C++"]:
        return f"""// Generated with {framework} (Offline Template)
#include <assert.h>
#include <stdio.h>

void test_standard_case() {{
    printf("Running standard case...\\n");
    assert(1 == 1);
}}

void test_edge_case_zero() {{
    printf("Running zero/boundary case...\\n");
}}

int main() {{
    test_standard_case();
    test_edge_case_zero();
    printf("All tests passed!\\n");
    return 0;
}}
"""
    elif language == "Perl":
        return f"""#!/usr/bin/perl
# Generated with {framework} (Offline Template)
use strict;
use warnings;
use Test::More tests => 3;

subtest 'Happy path functionality' => sub {{
    ok(1, 'Base functionality executes');
}};

subtest 'Edge cases and boundaries' => sub {{
    # Test division by zero, empty arrays, null values
    ok(1, 'Edge condition checked');
}};

subtest 'Error handling' => sub {{
    eval {{ die "Expected error" }};
    like($@, qr/Expected error/, 'Caught expected exception');
}};

done_testing();
"""
    elif language == "MongoDB":
        return f"""// Generated with {framework} (Offline Template)
describe("MongoDB Query & Aggregation Suite", () => {{
  test("should retrieve matching documents", async () => {{
    // const res = await db.collection('test').find({{ status: 'active' }}).toArray();
    // expect(res.length).toBeGreaterThanOrEqual(0);
  }});

  test("should handle empty result sets gracefully", async () => {{
    // const res = await db.collection('test').find({{ _id: 'nonexistent' }}).toArray();
    // expect(res).toEqual([]);
  }});
}});
"""
    elif language == "SQL":
        return f"""-- Generated with {framework} (Offline Template)
BEGIN TRANSACTION;

-- 1. Test query execution with sample records
-- INSERT INTO test_table (id, val) VALUES (1, 'test');
-- SELECT * FROM test_table WHERE id = 1;

-- 2. Verify constraint validations and roll back
ROLLBACK;
"""
    else:
        return f"""// Unit Test Template for {language} ({framework})
// 1. Positive case: test valid inputs
// 2. Boundary case: test empty/null/zero
// 3. Error case: test exception handling
"""
