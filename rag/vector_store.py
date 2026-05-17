"""
تخزين الـ embeddings في ChromaDB (Vector Database محلي).
"""

import os
import json

import chromadb
from chromadb.config import Settings

from rag.embeddings import create_embeddings, load_all_records, record_to_text, get_model

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
CHROMA_DIR = os.path.join(DATA_DIR, "chroma_db")
COLLECTION_NAME = "real_estate_areas"


def get_client() -> chromadb.ClientAPI:
    """إنشاء ChromaDB client محلي."""
    os.makedirs(CHROMA_DIR, exist_ok=True)
    client = chromadb.PersistentClient(path=CHROMA_DIR)
    return client


def get_or_create_collection(client: chromadb.ClientAPI = None):
    """جلب أو إنشاء الـ collection."""
    if client is None:
        client = get_client()
    collection = client.get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
    )
    return collection


def index_areas(force_rebuild: bool = False):
    """
    فهرسة كل المناطق في ChromaDB.
    لو force_rebuild=True يمسح القديم ويبني من الأول.
    """
    client = get_client()

    if force_rebuild:
        try:
            client.delete_collection(COLLECTION_NAME)
            print("🗑️  تم مسح الـ collection القديم")
        except Exception:
            pass

    collection = get_or_create_collection(client)
    existing_count = collection.count()

    if existing_count > 0 and not force_rebuild:
        print(f"✅ الـ collection موجود بالفعل ({existing_count} منطقة)")
        return collection

    # إنشاء embeddings
    records, texts, embeddings = create_embeddings()

    if not records:
        print("❌ مفيش بيانات للفهرسة!")
        return collection

    # تحضير البيانات لـ ChromaDB
    ids = []
    documents = []
    metadatas = []
    embed_list = []

    for i, (record, text, embedding) in enumerate(zip(records, texts, embeddings)):
        area_id = f"area_{i:03d}_{record.get('اسم_المنطقة', 'unknown').replace(' ', '_')}"
        ids.append(area_id)
        documents.append(text)
        embed_list.append(embedding)
        metadatas.append({
            "اسم_المنطقة": str(record.get("اسم_المنطقة", "")),
            "المحافظة": str(record.get("المحافظة", "")),
            "المدينة": str(record.get("المدينة", "")),
            "متوسط_سعر_المتر_بيع": int(record.get("متوسط_سعر_المتر_بيع", 0)),
            "متوسط_الإيجار_الشهري": int(record.get("متوسط_الإيجار_الشهري", 0)),
            "نوع_العقارات_الغالبة": str(record.get("نوع_العقارات_الغالبة", "")),
            "تصنيف_المنطقة": str(record.get("تصنيف_المنطقة", "")),
        })

    # إضافة على دفعات (ChromaDB limit)
    batch_size = 100
    for start in range(0, len(ids), batch_size):
        end = start + batch_size
        collection.add(
            ids=ids[start:end],
            documents=documents[start:end],
            embeddings=embed_list[start:end],
            metadatas=metadatas[start:end],
        )

    print(f"\n✅ تم فهرسة {len(ids)} منطقة في ChromaDB")
    print(f"📂 مخزن في: {CHROMA_DIR}")
    return collection


if __name__ == "__main__":
    print("=" * 60)
    print("  🗄️  فهرسة المناطق في ChromaDB")
    print("=" * 60)
    collection = index_areas(force_rebuild=True)
    print(f"\n📊 عدد العناصر في الـ collection: {collection.count()}")
