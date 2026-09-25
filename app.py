import streamlit as st
from dotenv import load_dotenv

from src.task10_generation import generate_with_citation

load_dotenv()

st.set_page_config(
    page_title="RAG Chatbot - Tuyển sinh Đại học",
    page_icon="🎓",
    layout="wide",
)

if "messages" not in st.session_state:
    st.session_state.messages = []

with st.sidebar:
    st.title("🎓 RAG Chatbot")
    st.caption(
        "Hỏi đáp về Tuyển sinh đại học: phương thức xét tuyển, "
        "chỉ tiêu, học phí, điểm chuẩn."
    )
    top_k = st.slider("Số chunks (top_k)", 3, 10, 5)
    st.divider()
    if st.button("🗑️ Xóa lịch sử chat"):
        st.session_state.messages = []
        st.rerun()

st.title("RAG Chatbot - Tuyển sinh Đại học")
st.caption("Trả lời có trích dẫn nguồn (citation) từ dữ liệu tuyển sinh đã thu thập.")


def render_sources(sources: list[dict], retrieval_source: str) -> None:
    """Hiển thị nguồn, retrieval method và score cho một câu trả lời."""
    if not sources:
        st.caption(f"Retrieval source: `{retrieval_source}` — không có nguồn nào được sử dụng.")
        return

    st.caption(f"Retrieval source: `{retrieval_source}` · {len(sources)} nguồn")
    with st.expander(f"📚 Xem {len(sources)} nguồn trích dẫn"):
        for i, src in enumerate(sources, start=1):
            metadata = src.get("metadata", {})
            title = metadata.get("title", "Không rõ tiêu đề")
            source_name = metadata.get("source", "Không rõ nguồn")
            doc_type = metadata.get("doc_type", "")
            url = metadata.get("url")
            score = src.get("score", 0.0)
            method = src.get("retrieval_method", "unknown")

            st.markdown(f"**[{i}] {title}**")
            cols = st.columns([2, 1, 1, 1])
            cols[0].markdown(f"Nguồn: `{source_name}`" + (f" ({doc_type})" if doc_type else ""))
            cols[1].markdown(f"Score: `{score:.3f}`")
            cols[2].markdown(f"Method: `{method}`")
            if url:
                cols[3].markdown(f"[🔗 Link]({url})")
            st.text(src.get("content", "")[:300] + "...")
            st.divider()


for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        if message["role"] == "assistant" and "sources" in message:
            render_sources(message["sources"], message.get("retrieval_source", "none"))

query = st.chat_input("Nhập câu hỏi về tuyển sinh đại học...")

if query:
    st.session_state.messages.append({"role": "user", "content": query})

    with st.chat_message("user"):
        st.markdown(query)

    with st.chat_message("assistant"):
        with st.spinner("Đang tìm kiếm và tạo câu trả lời..."):
            try:
                result = generate_with_citation(query, top_k=top_k)
                answer = result["answer"]
                sources = result.get("sources", [])
                retrieval_source = result.get("retrieval_source", "none")
            except NotImplementedError:
                answer = (
                    "⚠️ Backend (retrieval/generation pipeline) chưa được implement xong. "
                    "Vui lòng chờ Task 9 và Task 10 hoàn thiện."
                )
                sources = []
                retrieval_source = "none"
            except Exception as e:
                answer = f"⚠️ Đã xảy ra lỗi khi xử lý câu hỏi: {e}"
                sources = []
                retrieval_source = "none"

        st.markdown(answer)
        render_sources(sources, retrieval_source)

    st.session_state.messages.append(
        {
            "role": "assistant",
            "content": answer,
            "sources": sources,
            "retrieval_source": retrieval_source,
        }
    )