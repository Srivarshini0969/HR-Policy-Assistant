from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import requests
from flask import Flask, jsonify, render_template, request
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:3b")
MIN_RETRIEVAL_SCORE = float(os.getenv("MIN_RETRIEVAL_SCORE", "0.12"))

app = Flask(__name__)


def load_policy_sections() -> list[dict[str, str]]:
    sections = []
    for path in sorted(DATA_DIR.glob("*.txt")):
        content = path.read_text(encoding="utf-8", errors="replace")
        for paragraph in content.split("\n\n"):
            paragraph = paragraph.strip()
            if paragraph:
                sections.append({"source": path.name, "text": paragraph})
    return sections


class PolicyRetriever:
    def __init__(self):
        self.sections = []
        self.vectorizer = None
        self.matrix = None
        self.rebuild()

    def rebuild(self):
        self.sections = load_policy_sections()
        if not self.sections:
            self.vectorizer, self.matrix = None, None
            return
        self.vectorizer = TfidfVectorizer(stop_words="english", ngram_range=(1, 2))
        self.matrix = self.vectorizer.fit_transform([s["text"] for s in self.sections])

    def retrieve(self, question: str, top_k: int = 3):
        if not self.sections or self.vectorizer is None or self.matrix is None:
            return []
        scores = cosine_similarity(self.vectorizer.transform([question]), self.matrix).flatten()
        indices = scores.argsort()[::-1][:top_k]
        return [
            {**self.sections[int(i)], "score": float(scores[int(i)])}
            for i in indices if scores[int(i)] > 0
        ]


retriever = PolicyRetriever()


def should_escalate(question: str, matches: list[dict[str, Any]]):
    q = question.lower()
    sensitive_terms = [
        "harassment", "discrimination", "termination", "fire me", "fired",
        "disciplinary", "medical diagnosis", "mental health", "lawsuit",
        "legal action", "pregnancy complication", "personal employee record",
        "medical documentation", "documentation required", "sick leave documentation",
    ]
    if any(term in q for term in sensitive_terms):
        return True, "This may be sensitive or requires a policy detail not established by the sample. Please refer it to HR."
    if not matches or float(matches[0]["score"]) < MIN_RETRIEVAL_SCORE:
        return True, "I couldn't find sufficiently relevant support in the available policy documents."
    if any(term in q for term in ["am i eligible", "my eligibility", "my personal", "my case"]):
        return True, "Individual eligibility or case-specific decisions require HR review."
    return False, ""


def generate_answer(question: str, matches: list[dict[str, Any]]) -> str:
    context = "\n\n".join(f"Source: {m['source']}\nPolicy text: {m['text']}" for m in matches)
    prompt = f"""You are a precise HR Policy Assistant for an academic demonstration.

Your task is to answer employee questions using ONLY the provided policy context.

STRICT RULES:
1. Read the policy context carefully before answering.
2. If the answer is explicitly stated in the policy context, provide it directly.
3. Never claim that information is missing if the context explicitly contains it.
4. Never contradict the information in the policy context.
5. Do not invent policies, leave entitlements, benefits, eligibility criteria, or procedures.
6. If the policy context does not contain the requested information, clearly state:
   "The available policy documents do not specify this information. Please contact HR for clarification."
7. If the question involves a personal employee case, sensitive issue, or individual eligibility decision, recommend contacting HR.
8. Keep the answer concise, professional, and easy to understand.
9. Identify the source filename when answering from the provided policy context.
10. Remember that the provided policies are fictional demonstration data, not official company policies.

EXAMPLE:
Policy context: "The fictional company provides 20 days of annual leave per calendar year."
Employee question: "How many annual leave days are available?"
Correct answer: "The fictional company provides 20 days of annual leave per calendar year. Source: hr_policies_demo.txt."

POLICY CONTEXT:
{context}

EMPLOYEE QUESTION:
{question}

Write the answer based strictly on the policy context above.
ANSWER:"""
    try:
        response = requests.post(
            f"{OLLAMA_URL.rstrip('/')}/api/generate",
            json={"model": OLLAMA_MODEL, "prompt": prompt, "stream": False},
            timeout=90,
        )
        response.raise_for_status()
        answer = str(response.json().get("response", "")).strip()
        if not answer:
            raise RuntimeError("Ollama returned an empty response.")
        return answer
    except requests.RequestException as exc:
        raise RuntimeError(
            "Cannot reach Ollama. Start Ollama and confirm the configured Qwen model "
            f"is installed ({OLLAMA_MODEL}). Details: {exc}"
        ) from exc


@app.get("/")
def index():
    return render_template("index.html", model=OLLAMA_MODEL)


@app.get("/api/health")
def health():
    try:
        response = requests.get(f"{OLLAMA_URL.rstrip('/')}/api/tags", timeout=3)
        response.raise_for_status()
        models = [m.get("name", "") for m in response.json().get("models", [])]
        return jsonify({"ok": True, "ollama_url": OLLAMA_URL, "model": OLLAMA_MODEL, "installed_models": models})
    except requests.RequestException as exc:
        return jsonify({"ok": False, "model": OLLAMA_MODEL, "error": str(exc)}), 503


@app.post("/api/chat")
def chat():
    body = request.get_json(silent=True) or {}
    question = str(body.get("question", "")).strip()
    if not question:
        return jsonify({"error": "Please enter a question."}), 400
    if len(question) > 1500:
        return jsonify({"error": "Please keep the question under 1500 characters."}), 400
    matches = retriever.retrieve(question)
    escalated, reason = should_escalate(question, matches)
    sources = [
        {"filename": m["source"], "score": round(float(m["score"]), 3), "excerpt": str(m["text"])[:500]}
        for m in matches
    ]
    if escalated:
        return jsonify({
            "answer": "This question needs HR review rather than an unsupported policy answer.",
            "escalated": True, "escalation_reason": reason, "sources": sources,
            "mode": "retrieval/escalation",
        })
    try:
        answer = generate_answer(question, matches)
        return jsonify({
            "answer": answer, "escalated": False, "escalation_reason": "",
            "sources": sources, "mode": "ollama",
        })
    except RuntimeError as exc:
        return jsonify({"error": str(exc), "sources": sources}), 503


@app.post("/api/reindex")
def reindex():
    retriever.rebuild()
    return jsonify({"ok": True, "document_sections": len(retriever.sections)})


if __name__ == "__main__":
    print(f"HR Policy Agent starting; Ollama={OLLAMA_URL}; model={OLLAMA_MODEL}")
    print(f"Loaded {len(retriever.sections)} policy sections from {DATA_DIR}")
    app.run(host="127.0.0.1", port=int(os.getenv("PORT", "5000")), debug=False)
