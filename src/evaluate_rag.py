"""
Task 11 — RAG Evaluation

A/B:
    A = Dense-only
    B = Hybrid + RRF

LLM:
    Gemini

Embedding:
    BAAI/bge-m3

Metrics:
    - Faithfulness
    - Answer Relevance
    - Context Recall
    - Context Precision
"""

import json
import os
from pathlib import Path

from dotenv import load_dotenv

from ragas import evaluate
from ragas import EvaluationDataset, SingleTurnSample
from ragas.metrics.collections import (
    Faithfulness,
    AnswerRelevancy,
    ContextRecall,
    ContextPrecision,
)
from ragas.llms import LangchainLLMWrapper
from ragas.embeddings import LangchainEmbeddingsWrapper

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_huggingface import HuggingFaceEmbeddings

from src.task9_retrieval_pipeline import retrieve
from src.task10_generation import (
    reorder_for_llm,
    format_context,
)


load_dotenv()

ROOT = Path(__file__).resolve().parents[1]

GOLDEN_PATH = (
    ROOT
    / "group_project"
    / "evaluation"
    / "golden_dataset.json"
)

GEMINI_MODEL = os.getenv(
    "EVAL_LLM_MODEL",
    "gemini-3.8-flash",
)

EMBEDDING_MODEL = "BAAI/bge-m3"

TOP_K = 5

SAFE_REFUSAL = (
    "Tôi không thể xác minh thông tin này từ nguồn hiện có."
)


def load_golden_dataset() -> list[dict]:
    with open(GOLDEN_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    items = data.get("items", [])

    if len(items) != 18:
        raise ValueError(
            f"Expected 18 Golden questions, got {len(items)}."
        )

    print(f"Golden dataset: {len(items)} questions")

    return items


def create_gemini():
    api_key = os.getenv("GEMINI_API_KEY")

    if not api_key:
        raise RuntimeError(
            "GEMINI_API_KEY is not configured."
        )

    return ChatGoogleGenerativeAI(
        model=GEMINI_MODEL,
        google_api_key=api_key,
        temperature=0,
        max_output_tokens=2048,
    )


def generate_answer(
    query: str,
    chunks: list[dict],
    gemini,
) -> str:

    if not chunks:
        return SAFE_REFUSAL

    reordered = reorder_for_llm(chunks)
    context = format_context(reordered)

    user_message = (
        "Context:\n"
        f"{context}\n\n"
        f"Question: {query}"
    )

    try:
        response = gemini.invoke(
            [
                (
                    "system",
                    "Trả lời chỉ từ context được cung cấp. "
                    "Mỗi khẳng định phải có citation. "
                    "Nếu thiếu evidence, hãy từ chối xác minh.",
                ),
                (
                    "human",
                    user_message,
                ),
            ]
        )

    
        answer = response.content

        if isinstance(answer, list):
            texts = []

            for part in answer:
             if isinstance(part, dict):
              text = part.get("text", "")
            if text:
                texts.append(text)
        elif isinstance(part, str):
            texts.append(part)

            answer = "".join(texts)

            answer = str(answer).strip()

        return answer if answer else SAFE_REFUSAL

    except Exception as exc:
        print(
            f"      Gemini generation error: "
            f"{type(exc).__name__}: {exc}"
        )
        return SAFE_REFUSAL


def build_samples(
    items: list[dict],
    use_reranking: bool,
    gemini,
) -> list[SingleTurnSample]:

    mode = (
        "HYBRID + RRF"
        if use_reranking
        else "DENSE-ONLY"
    )

    print()
    print("=" * 70)
    print(f"BUILDING {mode}")
    print("=" * 70)

    samples = []

    for index, item in enumerate(items, start=1):

        question = item["question"]
        reference = item.get(
            "expected_answer",
            "",
        )

        print(
            f"[{index:02d}/{len(items)}] "
            f"{item['id']} | "
            f"{question[:80]}"
        )

        chunks = retrieve(
            question,
            top_k=TOP_K,
            use_reranking=use_reranking,
        )

        answer = generate_answer(
            question,
            chunks,
            gemini,
        )

        contexts = [
            chunk.get("content", "")
            for chunk in chunks
            if chunk.get("content")
        ]

        samples.append(
            SingleTurnSample(
                user_input=question,
                response=answer,
                retrieved_contexts=contexts,
                reference=reference,
            )
        )

        method = (
            chunks[0].get("retrieval_method")
            if chunks
            else "none"
        )

        print(
            f"      contexts={len(contexts)} "
            f"retrieval={method}"
        )

    return samples


def create_ragas_components():

    gemini = create_gemini()

    judge = LangchainLLMWrapper(gemini)

    local_embeddings = HuggingFaceEmbeddings(
        model_name=EMBEDDING_MODEL,
        encode_kwargs={
            "normalize_embeddings": True,
        },
    )

    embeddings = LangchainEmbeddingsWrapper(
        local_embeddings
    )

    metrics = [
        Faithfulness(
            llm=judge,
        ),
        AnswerRelevancy(
            llm=judge,
            embeddings=embeddings,
        ),
        ContextRecall(
            llm=judge,
        ),
        ContextPrecision(
            llm=judge,
        ),
    ]

    return gemini, metrics


def run_ragas(
    samples: list[SingleTurnSample],
    metrics,
    config_name: str,
):

    print()
    print("=" * 70)
    print(f"RAGAS EVALUATION: {config_name}")
    print("=" * 70)

    dataset = EvaluationDataset(
        samples=samples
    )

    result = evaluate(
        dataset=dataset,
        metrics=metrics,
        raise_exceptions=False,
        show_progress=True,
    )

    return result


def extract_scores(result) -> dict:

    names = [
        "faithfulness",
        "answer_relevancy",
        "context_recall",
        "context_precision",
    ]

    scores = {}

    for name in names:

        try:
            value = result[name]

            if hasattr(value, "mean"):
                value = value.mean()

            scores[name] = float(value)

        except Exception:
            scores[name] = None

    return scores


def print_scores(
    config_name: str,
    scores: dict,
):

    print()
    print("=" * 70)
    print(config_name)
    print("=" * 70)

    for name, value in scores.items():

        if value is None:
            print(
                f"{name:24s}: N/A"
            )
        else:
            print(
                f"{name:24s}: "
                f"{value:.4f}"
            )


def print_comparison(
    scores_a: dict,
    scores_b: dict,
):

    print()
    print("=" * 70)
    print("A/B COMPARISON")
    print("=" * 70)

    print(
        f"{'Metric':24s}"
        f"{'Dense-only':>15s}"
        f"{'Hybrid+RRF':>15s}"
        f"{'Delta B-A':>15s}"
    )

    print("-" * 70)

    names = [
        "faithfulness",
        "answer_relevancy",
        "context_recall",
        "context_precision",
    ]

    for name in names:

        a = scores_a.get(name)
        b = scores_b.get(name)

        if a is None or b is None:

            print(
                f"{name:24s}"
                f"{'N/A':>15s}"
                f"{'N/A':>15s}"
                f"{'N/A':>15s}"
            )

            continue

        delta = b - a

        print(
            f"{name:24s}"
            f"{a:>15.4f}"
            f"{b:>15.4f}"
            f"{delta:>15.4f}"
        )


def save_results(
    scores_a: dict,
    scores_b: dict,
):

    output = {
        "dataset": str(GOLDEN_PATH),
        "num_questions": 18,
        "judge_model": GEMINI_MODEL,
        "embedding_model": EMBEDDING_MODEL,
        "top_k": TOP_K,
        "config_a": {
            "name": "Dense-only",
            "scores": scores_a,
        },
        "config_b": {
            "name": "Hybrid + RRF",
            "scores": scores_b,
        },
    }

    output_path = (
        ROOT
        / "group_project"
        / "evaluation"
        / "evaluation_results.json"
    )

    with open(
        output_path,
        "w",
        encoding="utf-8",
    ) as f:

        json.dump(
            output,
            f,
            ensure_ascii=False,
            indent=2,
        )

    print()
    print(
        f"Saved results: {output_path}"
    )


def main():

    print("=" * 70)
    print("RAG EVALUATION — GEMINI")
    print("=" * 70)

    print(
        f"Gemini model:     {GEMINI_MODEL}"
    )

    print(
        f"Embedding model:  {EMBEDDING_MODEL}"
    )

    print(
        f"Top-K:            {TOP_K}"
    )

    items = load_golden_dataset()

    gemini, metrics = (
        create_ragas_components()
    )

    # ---------------------------------------------------------
    # Config A — Dense-only
    # ---------------------------------------------------------

    samples_a = build_samples(
        items,
        use_reranking=False,
        gemini=gemini,
    )

    result_a = run_ragas(
        samples_a,
        metrics,
        "CONFIG A — DENSE-ONLY",
    )

    scores_a = extract_scores(
        result_a
    )

    print_scores(
        "CONFIG A — DENSE-ONLY",
        scores_a,
    )

    # ---------------------------------------------------------
    # Config B — Hybrid + RRF
    # ---------------------------------------------------------

    samples_b = build_samples(
        items,
        use_reranking=True,
        gemini=gemini,
    )

    result_b = run_ragas(
        samples_b,
        metrics,
        "CONFIG B — HYBRID + RRF",
    )

    scores_b = extract_scores(
        result_b
    )

    print_scores(
        "CONFIG B — HYBRID + RRF",
        scores_b,
    )

    # ---------------------------------------------------------
    # A/B comparison
    # ---------------------------------------------------------

    print_comparison(
        scores_a,
        scores_b,
    )

    save_results(
        scores_a,
        scores_b,
    )


if __name__ == "__main__":
    main()