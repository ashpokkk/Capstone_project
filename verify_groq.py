"""
FBR Tax FAQ RAG Chatbot — Phase 4, Step 0: Verify Groq API key

Confirms the GROQ_API_KEY environment variable is set and valid, and that
the model generate.py depends on is actually available on this account,
before wiring anything else into the pipeline.

Usage:
    export GROQ_API_KEY=your_key_here   # never commit this
    python verify_groq.py
"""

import os
import sys

from groq import Groq

MODEL = "openai/gpt-oss-120b"


def main():
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        print("FAIL: GROQ_API_KEY is not set in the environment.")
        sys.exit(1)

    client = Groq(api_key=api_key)

    try:
        resp = client.chat.completions.create(
            model=MODEL,
            temperature=0,
            max_completion_tokens=200,
            reasoning_effort="low",
            messages=[{"role": "user", "content": "Reply with exactly: OK"}],
        )
    except Exception as e:
        print(f"FAIL: API call failed — {e}")
        sys.exit(1)

    reply = resp.choices[0].message.content.strip()
    print(f"Model: {MODEL}")
    print(f"Reply: {reply!r}")
    print("PASS: Groq API key works and the model responded." if reply else
          "WARN: call succeeded but response was empty — check model name.")


if __name__ == "__main__":
    main()