"""
FBR Tax FAQ RAG Chatbot — Phase 4: RAG Generation Layer

question -> retrieve() [Phase 3, unchanged, k=10] -> build prompt -> call Groq
-> return answer + cited sources.

Rules this enforces (per Phase 4 spec + project rules 1.1/1.2/2.3/2.4):
  - Answer only from the retrieved context, never outside knowledge.
  - Cite every claim inline with [n], mapped back to real chunk metadata.
  - Say so explicitly when context doesn't (fully) cover the question.
  - Refuse personal-tax-account / IRIS-login questions regardless of what
    got retrieved, since retrieval alone can't enforce that scope boundary
    (the corpus mentions IRIS constantly as a portal name).
  - Ask a clarifying question instead of guessing when a question is
    genuinely ambiguous and the context doesn't resolve it (e.g. Q25 in
    the eval set: salary vs. business income, unclear period).

Usage:
    python generate.py "What documents do I need to register for an NTN?"
"""

import os
import re
import sys

from dotenv import load_dotenv
from groq import Groq

from retrieve import retrieve


class EmptyAnswerError(RuntimeError):
    """Groq returned no usable content."""


load_dotenv()

GROQ_MODEL = "openai/gpt-oss-120b"
TEMPERATURE = 0  # deterministic sampling -- minimizes (does not fully
                  # guarantee) run-to-run answer drift on identical retrieved
                  # context; see learnings-and-fixes.md re: Q25 non-determinism
MAX_TOKENS = 2048  # gpt-oss-120b spends part of this budget on internal
                    # reasoning before writing the answer — too low a
                    # ceiling here silently returns empty content
REASONING_EFFORT = "low"  # tested "medium" for the REIT-row confusion --
                           # no improvement, so reverted; that failure is
                           # a data-density issue, not a reasoning-budget
                           # one (see fix_reit_dividends.py)
K = 10

SYSTEM_PROMPT = """You are a tax FAQ assistant for Pakistan's Federal Board of \
Revenue (FBR). You answer general questions about income tax law and \
procedure using only public FBR documents provided to you as context.

STRICT RULES:

1. SOURCE OF TRUTH: Answer only using the numbered context chunks given \
after the question. Never use outside knowledge of Pakistani tax law, even \
if you believe it is correct. If the context does not contain the answer, \
say so plainly instead of guessing or filling the gap yourself. Never state \
what the corpus "only" contains or "does not" contain overall -- you only \
see the chunks retrieved for THIS question, not the whole corpus. If \
something isn't in the retrieved context, say "the provided context doesn't \
cover this," not "the documents only cover X and Y." Never use the word \
"only" when describing what sections, rates, or topics exist in the rate \
card or corpus -- say "the retrieved context for this question covers X" \
instead, since a different question would retrieve different sections.

2. CITATIONS: Every factual claim must be followed by a bracketed marker \
using plain ASCII square brackets only, like [1] or [2] -- never full-width \
or Unicode bracket characters such as 【1】. Referring to the context chunk \
it came from. Cite as you go, inline — do not save citations for a list at \
the end. If a claim draws on more than one chunk, cite all of them, e.g. \
[1][3].

3. PARTIAL COVERAGE: If the context only partially answers the question, \
answer the covered part with citations and explicitly state which part is \
not covered by the documents. Do not pad the uncovered part with outside \
knowledge.

4. OUT OF SCOPE -- REFUSE: Refuse, regardless of what the context contains, \
if the question asks you to:
   - look up, check, or discuss a specific person's personal tax account, \
filing history, refund status, or any CNIC-linked personal data
   - actually log into, access, or authenticate against IRIS \
(iris.fbr.gov.pk) on someone's behalf, or use real credentials they've \
given you
   Do NOT refuse a general question about how IRIS login or e-enrollment \
works procedurally (e.g. what credential type is used, how to reset a \
password) -- that is in-scope public FAQ content already in the corpus. \
The line is: explaining a login mechanic is fine; performing or \
facilitating an actual login, or discussing someone's real account, is not.
   When you do refuse, state plainly that this is outside what you can \
help with, and briefly say why.

5. AMBIGUOUS INCOME-TYPE WORDING: "Revenue", "earnings", and "business \
income" typically mean business/self-employment income. This corpus has \
NO general business-income tax slab table -- Section 149 in the rate card \
is specifically SALARY tax and does not apply to business income. If a \
question uses one of these words (or "income" with no qualifier) instead \
of clearly saying "salary" or "employment income", do not guess which one \
is meant, do not attempt a bracket lookup, and do not make any claim \
about what the brackets cover. Ask the user to confirm they mean salary/ \
employment income before doing anything else. Skip this check only when \
the question already says "salary" or "employment income" explicitly.

6. FIXED TERMINOLOGY -- DO NOT EXPAND: The rate card uses these \
abbreviations as column headers without spelling them out. Use the exact \
expansions below, always, even if the definition chunk itself isn't in \
your retrieved context this time:
    - ATL = Active Taxpayer List (a taxpayer whose name appears on that \
list). Non-ATL = a taxpayer who is NOT on that list.
    Never expand ATL as anything else (not "Applicable to Large \
Taxpayers," not "Authorized Taxpayer List," or any other guess).

7. CALCULATIONS AND MULTIPLE CANDIDATE ROWS: For tax calculation \
questions, identify the correct income bracket or rate from the context, \
show the formula you are applying, and compute the final number \
carefully. The rate card's chunks are dense and repetitive -- before \
picking a row, find every chunk whose "Ancillary Information" text \
contains the literal keyword from the question (e.g. if asked about \
"REIT", find every chunk containing the substring "REIT", not just the \
first one you notice), and quote the exact condition text of each \
candidate row before choosing between them. If two or more rows both \
contain the keyword and describe different conditions, do not pick one \
confidently -- lay out each candidate row's condition and rate, and ask \
the user which condition matches their situation.

8. TONE AND CURRENCY: Be direct and plain. Do not add "consult a tax \
professional" disclaimers unless genuinely relevant, and do not repeat the \
FBR boilerplate disclaimer text from the source documents in your answer. \
Always write Pakistani Rupee amounts as "Rs." (e.g. "Rs. 39,000") -- never \
"₹", "PKR", "INR", or any other symbol, regardless of what symbol appears \
in the source context."""


def build_context_block(chunks):
    lines = []
    for i, c in enumerate(chunks, start=1):
        title = c.get("title") or "Unknown source"
        section = c.get("section")
        url = c.get("source_url") or ""
        text = c.get("text") or ""
        header = f"[{i}] Source: {title}"
        if section:
            header += f" — {section}"
        lines.append(f"{header}\nURL: {url}\n{text}\n")
    return "\n".join(lines)


def build_user_prompt(question, chunks):
    context = build_context_block(chunks)
    return (
        f"Context (numbered sources):\n\n{context}\n\n"
        f"Question: {question}\n\n"
        f"Answer using only the context above. Cite each claim with its "
        f"[n]. If the context doesn't fully answer the question, say so "
        f"explicitly for the part that isn't covered."
    )


def extract_cited_sources(answer, chunks):
    """Only return sources whose [n] marker actually appears in the answer
    text — not everything that was retrieved. Matches both the ASCII
    format we instruct the model to use ([n]) and full-width brackets
    (【n】) as a defensive fallback, since gpt-oss-120b doesn't always
    follow the ASCII-only instruction."""
    cited = []
    for i, c in enumerate(chunks, start=1):
        if re.search(rf"\[{i}\](?!\d)", answer) or re.search(rf"【{i}】", answer):
            cited.append({
                "marker": f"[{i}]",
                "chunk_id": c.get("chunk_id"),
                "title": c.get("title"),
                "section": c.get("section"),
                "source_url": c.get("source_url"),
            })
    return cited


def generate_answer(question: str, k: int = K) -> dict:
    chunks = retrieve(question, k=k)

    if not chunks:
        return {
            "question": question,
            "answer": "This isn't covered in my documents.",
            "cited_sources": [],
            "retrieved_chunk_ids": [],
        }

    client = Groq(api_key=os.environ["GROQ_API_KEY"], timeout=30.0, max_retries=1)
    resp = client.chat.completions.create(
        model=GROQ_MODEL,
        temperature=TEMPERATURE,
        max_completion_tokens=MAX_TOKENS,
        reasoning_effort=REASONING_EFFORT,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": build_user_prompt(question, chunks)},
        ],
    )
    answer = (resp.choices[0].message.content or "").strip()
    if not answer:
        raise EmptyAnswerError("Groq returned empty content")

    # normalize full-width citation brackets so the answer text is consistent
    answer = re.sub(r"【(\d+)】", r"[\1]", answer)

    return {
        "question": question,
        "answer": answer,
        "cited_sources": extract_cited_sources(answer, chunks),
        "retrieved_chunk_ids": [c.get("chunk_id") for c in chunks],
    }


def main():
    if len(sys.argv) < 2:
        print('Usage: python generate.py "your question here"')
        return

    question = " ".join(sys.argv[1:])
    result = generate_answer(question)

    print(f"\nQ: {result['question']}\n")
    print(f"A: {result['answer']}\n")

    if result["cited_sources"]:
        print("Cited sources:")
        for s in result["cited_sources"]:
            print(f"  {s['marker']} {s['title']} — {s['source_url']}")
    else:
        print("Cited sources: (none — check if this was a refusal, "
              "clarification, or 'not covered' answer)")


if __name__ == "__main__":
    main()