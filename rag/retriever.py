"""
Retriever: يبحث عن أقرب مناطق لسؤال المستخدم من ChromaDB.
"""

import json

from rag.embeddings import get_embedding
from rag.vector_store import get_client, get_or_create_collection, COLLECTION_NAME

_collection = None


def _get_collection():
    """جلب الـ collection مرة واحدة بس (cached)."""
    global _collection
    if _collection is None:
        client = get_client()
        _collection = get_or_create_collection(client)
    return _collection


def search(query: str, top_k: int = 5) -> list[dict]:
    """
    البحث عن أقرب مناطق لسؤال المستخدم.

    Args:
        query: سؤال أو استعلام المستخدم بالعربي.
        top_k: عدد النتائج المطلوبة.

    Returns:
        list من dict كل واحد فيه المنطقة والبيانات والـ score.
    """
    collection = _get_collection()

    if collection.count() == 0:
        print("⚠️  الـ Vector Store فاضي! شغّل vector_store.py الأول.")
        return []

    query_embedding = get_embedding(query)

    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=min(top_k, collection.count()),
        include=["documents", "metadatas", "distances"],
    )

    output = []
    if results and results["ids"] and results["ids"][0]:
        for i, doc_id in enumerate(results["ids"][0]):
            item = {
                "id": doc_id,
                "النص": results["documents"][0][i] if results["documents"] else "",
                "المسافة": results["distances"][0][i] if results["distances"] else 0,
                "التشابه": 1 - results["distances"][0][i] if results["distances"] else 0,
            }
            if results["metadatas"] and results["metadatas"][0]:
                item.update(results["metadatas"][0][i])
            output.append(item)

    return output


def search_formatted(query: str, top_k: int = 5) -> str:
    """
    البحث وإرجاع نتائج منسقة كنص (مناسب لإرساله للـ Agent).
    """
    results = search(query, top_k)

    if not results:
        return "لم يتم العثور على نتائج مطابقة."

    lines = [f"🔍 نتائج البحث عن: \"{query}\"\n"]
    lines.append(f"تم العثور على {len(results)} نتيجة:\n")

    for i, r in enumerate(results, 1):
        name = r.get("اسم_المنطقة", "؟")
        gov = r.get("المحافظة", "")
        price = r.get("متوسط_سعر_المتر_بيع", 0)
        rent = r.get("متوسط_الإيجار_الشهري", 0)
        category = r.get("تصنيف_المنطقة", "")
        similarity = r.get("التشابه", 0)

        lines.append(f"{i}. {name} ({gov}) — تشابه: {similarity:.0%}")
        lines.append(f"   سعر المتر: {price:,} جنيه | إيجار: {rent:,} جنيه | تصنيف: {category}")
        lines.append("")

    return "\n".join(lines)
