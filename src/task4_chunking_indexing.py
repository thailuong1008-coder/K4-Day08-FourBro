"""
Task 4 — Chunking, embedding và indexing.

Hướng dẫn:
    1. Đọc toàn bộ Markdown trong data/standardized/.
    2. Chia văn bản bằng strategy đã chọn.
    3. Embed chunks bằng một provider duy nhất.
    4. Upsert vào ChromaDB với cosine distance.

Mỗi document/chunk phải theo docs/MODULE_CONTRACTS.md. ID cần ổn định để
chạy lại pipeline không tạo dữ liệu trùng. Task 5 phải dùng chung embed_texts().
"""

import json
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

STANDARDIZED_DIR = Path(__file__).parent.parent / "data" / "standardized"
CHROMA_DIR = Path(__file__).parent.parent / "chroma_db"

# Giải thích lựa chọn tham số trong báo cáo nhóm.
CHUNK_SIZE = 500
CHUNK_OVERLAP = 50
CHUNKING_METHOD = "recursive"

# Đọc embedding config từ .env, fallback về OpenAI
EMBEDDING_PROVIDER = os.getenv("EMBEDDING_PROVIDER", "openai")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")
EMBEDDING_DIM = 1024

COLLECTION_NAME = "rag_documents"

# ---------------------------------------------------------------------------
# Embedding — hỗ trợ nhiều provider, dùng chung cho Task 5
# ---------------------------------------------------------------------------

# Cache model để không load lại mỗi lần gọi
_st_model = None


def _embed_openai(texts: list[str]) -> list[list[float]]:
    """Embed bằng OpenAI API."""
    from openai import OpenAI

    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    model = EMBEDDING_MODEL if EMBEDDING_PROVIDER == "openai" else "text-embedding-3-small"

    # OpenAI batch limit = 2048 inputs
    all_embeddings: list[list[float]] = []
    batch_size = 512
    for i in range(0, len(texts), batch_size):
        batch = texts[i : i + batch_size]
        response = client.embeddings.create(input=batch, model=model)
        all_embeddings.extend([d.embedding for d in response.data])
    return all_embeddings


def _embed_sentence_transformers(texts: list[str]) -> list[list[float]]:
    """Embed bằng SentenceTransformer (local)."""
    global _st_model
    if _st_model is None:
        from sentence_transformers import SentenceTransformer
        _st_model = SentenceTransformer(EMBEDDING_MODEL)
    return _st_model.encode(texts, show_progress_bar=True).tolist()


def _embed_gemini(texts: list[str]) -> list[list[float]]:
    """Embed bằng Google Gemini API."""
    from google import genai

    client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
    model = EMBEDDING_MODEL if EMBEDDING_PROVIDER == "gemini" else "text-embedding-004"

    all_embeddings: list[list[float]] = []
    batch_size = 100
    for i in range(0, len(texts), batch_size):
        batch = texts[i : i + batch_size]
        result = client.models.embed_content(model=model, contents=batch)
        all_embeddings.extend([e.values for e in result.embeddings])
    return all_embeddings


def embed_texts(texts: list[str]) -> list[list[float]]:
    """Dispatch embedding theo EMBEDDING_PROVIDER trong .env.

    Provider được hỗ trợ: openai, sentence_transformers, gemini.
    Hàm này được dùng chung bởi Task 4 và Task 5.
    """
    provider = EMBEDDING_PROVIDER.lower().strip()

    if provider == "openai":
        return _embed_openai(texts)
    elif provider == "sentence_transformers":
        return _embed_sentence_transformers(texts)
    elif provider == "gemini":
        return _embed_gemini(texts)
    else:
        raise ValueError(
            f"EMBEDDING_PROVIDER='{provider}' không hỗ trợ. "
            f"Dùng: openai | sentence_transformers | gemini"
        )


# ---------------------------------------------------------------------------
# ChromaDB
# ---------------------------------------------------------------------------


def get_collection():
    """Mở Chroma collection dùng cosine distance."""
    import chromadb

    CHROMA_DIR.mkdir(parents=True, exist_ok=True)
    client = chromadb.PersistentClient(path=str(CHROMA_DIR))
    return client.get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
    )


# ---------------------------------------------------------------------------
# Load documents
# ---------------------------------------------------------------------------


def load_documents() -> list[dict]:
    """Đọc Markdown và trả về danh sách Document theo contract.

    Mỗi document có:
    - id: đường dẫn tương đối (e.g. "legal/hust-quy-che-tuyen-sinh-2024.md")
    - content: nội dung Markdown
    - metadata: {source, title, doc_type, url}
    """
    documents = []

    for path in sorted(STANDARDIZED_DIR.rglob("*.md")):
        content = path.read_text(encoding="utf-8").strip()
        if not content:
            continue

        # Xác định doc_type từ cấu trúc thư mục
        rel_path = path.relative_to(STANDARDIZED_DIR)
        doc_type = "legal" if "legal" in rel_path.parts else "news"

        # Trích xuất URL từ metadata header nếu có
        url = None
        for line in content.split("\n")[:10]:
            if line.startswith("**Source:**"):
                url = line.replace("**Source:**", "").strip()
                break

        # Trích xuất title từ dòng đầu
        title = path.stem
        for line in content.split("\n"):
            line = line.strip()
            if line.startswith("# "):
                title = line[2:].strip()
                break

        documents.append({
            "id": rel_path.as_posix(),
            "content": content,
            "metadata": {
                "source": path.name,
                "title": title,
                "doc_type": doc_type,
                "url": url,
            },
        })

    return documents


# ---------------------------------------------------------------------------
# Chunking
# ---------------------------------------------------------------------------


def chunk_documents(documents: list[dict]) -> list[dict]:
    """Chia Document thành chunks có id và chunk_index.

    Dùng RecursiveCharacterTextSplitter với separator phù hợp
    cho văn bản tiếng Việt. ID ổn định: "{doc_id}::chunk-{index}".
    """
    from langchain_text_splitters import RecursiveCharacterTextSplitter

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        separators=["\n\n", "\n", ". ", ", ", " ", ""],
    )

    chunks = []
    for document in documents:
        texts = splitter.split_text(document["content"])
        for index, text in enumerate(texts):
            chunks.append({
                "id": f"{document['id']}::chunk-{index}",
                "content": text,
                "metadata": {
                    **document["metadata"],
                    "chunk_index": index,
                },
            })

    return chunks


# ---------------------------------------------------------------------------
# Embedding
# ---------------------------------------------------------------------------


def embed_chunks(chunks: list[dict]) -> list[dict]:
    """Thêm embedding vào từng chunk.

    Embed theo batch, giữ nguyên các field gốc của chunk.
    """
    print(f"  Embedding {len(chunks)} chunks with {EMBEDDING_PROVIDER}...")
    texts = [chunk["content"] for chunk in chunks]
    vectors = embed_texts(texts)
    for chunk, vector in zip(chunks, vectors):
        chunk["embedding"] = vector
    return chunks


# ---------------------------------------------------------------------------
# Indexing
# ---------------------------------------------------------------------------


def index_to_vectorstore(chunks: list[dict]) -> None:
    """Upsert chunks vào ChromaDB.

    Dùng upsert để chạy lại không tạo dữ liệu trùng.
    Chia thành batch 500 để tránh giới hạn ChromaDB.
    """
    collection = get_collection()
    batch_size = 500

    for i in range(0, len(chunks), batch_size):
        batch = chunks[i : i + batch_size]
        collection.upsert(
            ids=[chunk["id"] for chunk in batch],
            documents=[chunk["content"] for chunk in batch],
            embeddings=[chunk["embedding"] for chunk in batch],
            metadatas=[chunk["metadata"] for chunk in batch],
        )
        print(f"  Upserted batch {i // batch_size + 1} ({len(batch)} chunks)")


# ---------------------------------------------------------------------------
# Pipeline
# ---------------------------------------------------------------------------


def run_pipeline() -> None:
    """Chạy load, chunk, embed và index."""
    print("Step 1: Loading documents...")
    documents = load_documents()
    print(f"  Loaded {len(documents)} documents")

    if not documents:
        print("  No documents found. Run task3 first!")
        return

    print("Step 2: Chunking documents...")
    chunks = chunk_documents(documents)
    print(f"  Created {len(chunks)} chunks (size={CHUNK_SIZE}, overlap={CHUNK_OVERLAP})")

    # Kiểm tra duplicate IDs
    ids = [chunk["id"] for chunk in chunks]
    unique_ids = set(ids)
    if len(ids) != len(unique_ids):
        dupes = [x for x in ids if ids.count(x) > 1]
        print(f"  WARNING: {len(ids) - len(unique_ids)} duplicate IDs detected: {set(dupes)}")
    else:
        print(f"  All {len(ids)} chunk IDs are unique [OK]")

    # Kiểm tra chunks không rỗng
    empty_chunks = [c for c in chunks if not c["content"].strip()]
    if empty_chunks:
        print(f"  WARNING: {len(empty_chunks)} empty chunks detected")
    else:
        print(f"  All chunks have content [OK]")

    # Kiểm tra metadata
    for chunk in chunks[:3]:
        meta = chunk["metadata"]
        assert "source" in meta and meta["source"], "Missing source"
        assert "title" in meta and meta["title"], "Missing title"
        assert "doc_type" in meta and meta["doc_type"] in {"legal", "news"}, "Invalid doc_type"
        assert "chunk_index" in meta and isinstance(meta["chunk_index"], int), "Missing chunk_index"
    print(f"  Metadata validation passed [OK]")

    print("Step 3: Embedding chunks...")
    embedded_chunks = embed_chunks(chunks)
    print(f"  Embedded {len(embedded_chunks)} chunks (dim={len(embedded_chunks[0]['embedding'])})")

    print("Step 4: Indexing to ChromaDB...")
    index_to_vectorstore(embedded_chunks)

    # Verify index
    collection = get_collection()
    count = collection.count()
    print(f"\n{'='*50}")
    print(f"Pipeline complete!")
    print(f"  Documents: {len(documents)}")
    print(f"  Chunks:    {len(chunks)}")
    print(f"  Indexed:   {count} (in ChromaDB)")
    print(f"  Provider:  {EMBEDDING_PROVIDER}")
    print(f"  DB path:   {CHROMA_DIR}")
    print(f"{'='*50}")


if __name__ == "__main__":
    run_pipeline()
