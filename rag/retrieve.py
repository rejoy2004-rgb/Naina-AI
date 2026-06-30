from langchain_community.vectorstores import Chroma
from langchain_huggingface import HuggingFaceEmbeddings

# Embedding model
embeddings = HuggingFaceEmbeddings(
    model_name="sentence-transformers/all-MiniLM-L6-v2"
)

# Load existing vector DB
db = Chroma(
    persist_directory="vector_db",
    embedding_function=embeddings
)

def retrieve_context(query, k=5):
    """
    Retrieve relevant chunks from ChromaDB with Nainocular platform boosting.
    """

    try:
        # 1. Standard search across all documents
        docs = db.similarity_search(
            query=query,
            k=k
        )

        # 2. Check if the query refers to Nainocular, games, articles, etc.
        query_lower = query.lower()
        nainocular_keywords = [
            "nainocular", "naintaara", "game", "play", "article", "benefit",
            "driver", "hunter", "match", "square", "fusion", "tracking",
            "blink", "blind", "odd", "safety", "child", "children"
        ]

        is_nainocular_query = any(kw in query_lower for kw in nainocular_keywords)

        # If it is, perform a targeted search on the Nainocular data file
        if is_nainocular_query:
            nainocular_docs = db.similarity_search(
                query=query,
                k=k,
                filter={"source": "documents\\nainocular_data.md"}
            )

            # Combine documents, keeping uniqueness based on page_content
            seen = set()
            combined_docs = []

            # Prioritize Nainocular platform docs first
            for doc in nainocular_docs + docs:
                content_hash = hash(doc.page_content)
                if content_hash not in seen:
                    seen.add(content_hash)
                    combined_docs.append(doc)

            docs = combined_docs[:k+2]  # return slightly more context if combined

        if not docs:
            return ""

        context = "\n\n".join(
            [doc.page_content for doc in docs]
        )

        return context

    except Exception as e:

        print(f"Retrieval Error: {e}")

        return ""