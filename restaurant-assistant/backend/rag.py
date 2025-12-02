import json
from pathlib import Path
from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import SentenceTransformerEmbeddings
from langchain_core.documents import Document


DATA_DIR = Path(__file__).parent.parent / "data"
MENU_PATH = DATA_DIR / "menu.json"
FAQ_PATH = DATA_DIR / "faq.txt"


def load_menu():
    """Load menu items list from JSON file."""
    with open(MENU_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    # Expect structure: { "menu_items": [ ... ] }
    return data["menu_items"]


def build_documents():
    """Build LangChain documents from menu and FAQ."""
    menu = load_menu()
    docs = []

    # Add menu items as documents
    for item in menu:
        allergens = item.get("allergens", [])
        allergen_text = ", ".join(allergens) if allergens else "none"

        ingredients = item.get("ingredients", [])
        ingredients_text = ", ".join(ingredients) if ingredients else "not specified"

        category = item.get("category", "main")
        emoji = item.get("emoji", "🍽️")

        text = (
            f"{item['name']} ({category} {emoji}): {item['description']}. "
            f"Price: €{item['price']:.2f}. "
            f"Ingredients: {ingredients_text}. "
            f"Allergens: {allergen_text}."
        )

        docs.append(
            Document(
                page_content=text,
                metadata={
                    "type": "menu",
                    "id": item["id"],
                    "name": item["name"],
                    "category": category,
                    "allergens": allergen_text
                },
            )
        )

    # Add FAQ as documents
    with open(FAQ_PATH, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                docs.append(
                    Document(
                        page_content=line,
                        metadata={"type": "faq"},
                    )
                )

    return docs


def get_vectorstore():
    """Create and return a Chroma vector store."""
    embeddings = SentenceTransformerEmbeddings(model_name="all-MiniLM-L6-v2")
    docs = build_documents()
    vs = Chroma.from_documents(
        docs,
        embedding=embeddings,
        collection_name="restaurant_assistant",
    )
    return vs


def get_retriever(k: int = 4):
    """Get a retriever for RAG."""
    vs = get_vectorstore()
    return vs.as_retriever(search_kwargs={"k": k})
