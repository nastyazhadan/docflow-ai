from pathlib import Path

from llama_index.core import SimpleDirectoryReader, VectorStoreIndex

from llm_factory import configure_llm_from_env

DOCS_DIR = Path("data/docs")


def build_index() -> VectorStoreIndex:
    """Строим in-memory индекс по локальным файлам в data/docs."""
    if not DOCS_DIR.exists():
        raise FileNotFoundError(f"Docs directory not found: {DOCS_DIR}")

    configure_llm_from_env()

    documents = SimpleDirectoryReader(str(DOCS_DIR)).load_data()
    index = VectorStoreIndex.from_documents(documents)
    return index


def ask_question(question: str) -> str:
    """Задаём вопрос индексу и возвращаем текст ответа."""
    index = build_index()
    query_engine = index.as_query_engine()
    response = query_engine.query(question)
    return str(response)


if __name__ == "__main__":
    import sys

    q = " ".join(sys.argv[1:]) or "О чём эти документы?"
    answer = ask_question(q)
    print(f"Q: {q}\n")
    print("A:", answer)
