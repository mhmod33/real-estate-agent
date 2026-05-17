"""
تحويل بيانات المناطق العقارية لـ embeddings باستخدام Google Generative AI.
يقرأ من JSON و Excel ويحول كل منطقة لنص واضح ثم يعمل embedding.
"""

import os
import json

from openpyxl import load_workbook
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

MODEL_NAME = "models/text-embedding-004"
BASE_DIR = os.path.dirname(os.path.dirname(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
JSON_FILE = os.path.join(DATA_DIR, "_progress.json")
EXCEL_FILE = os.path.join(DATA_DIR, "areas_prices.xlsx")

_configured = False


def _configure():
    """تهيئة Google Generative AI مرة واحدة بس."""
    global _configured
    if not _configured:
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY not set in environment variables")
        genai.configure(api_key=api_key)
        _configured = True


def get_embedding(text: str) -> list[float]:
    """الحصول على embedding لنص واحد."""
    _configure()
    result = genai.embed_content(
        model=MODEL_NAME,
        content=text
    )
    return result["embedding"]


def init_model():
    """تهيئة الـ embedding API عند بدء التطبيق."""
    _configure()
    print("✅ Google Generative AI Embeddings configured")


def load_from_json(path: str = JSON_FILE) -> list[dict]:
    """قراءة البيانات من ملف JSON."""
    if not os.path.exists(path):
        print(f"⚠️  ملف JSON مش موجود: {path}")
        return []
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    print(f"📄 تم تحميل {len(data)} منطقة من JSON")
    return data


def load_from_excel(path: str = EXCEL_FILE) -> list[dict]:
    """قراءة البيانات من ملف Excel."""
    if not os.path.exists(path):
        print(f"⚠️  ملف Excel مش موجود: {path}")
        return []

    wb = load_workbook(path, read_only=True)
    ws = wb.active
    rows = list(ws.iter_rows(values_only=True))

    if len(rows) < 2:
        return []

    headers = rows[0]
    data = []
    for row in rows[1:]:
        item = {}
        for h, v in zip(headers, row):
            if h and v is not None:
                key = str(h).strip().replace(" ", "_").replace("(", "").replace(")", "")
                item[key] = v
        if item:
            data.append(item)

    wb.close()
    print(f"📊 تم تحميل {len(data)} منطقة من Excel")
    return data


def normalize_record(record: dict) -> dict:
    """توحيد أسماء الحقول بين JSON و Excel."""
    mapping = {
        "اسم_المنطقة": ["اسم_المنطقة"],
        "المحافظة": ["المحافظة"],
        "المدينة": ["المدينة"],
        "متوسط_سعر_المتر_بيع": ["متوسط_سعر_المتر_بيع"],
        "متوسط_الإيجار_الشهري": ["متوسط_الإيجار_الشهري"],
        "نوع_العقارات_الغالبة": ["نوع_العقارات_الغالبة"],
        "تصنيف_المنطقة": ["تصنيف_المنطقة"],
        "ملاحظات": ["ملاحظات"],
    }

    normalized = {}
    for target_key, source_keys in mapping.items():
        for sk in source_keys:
            if sk in record:
                normalized[target_key] = record[sk]
                break
        if target_key not in normalized:
            normalized[target_key] = record.get(target_key, "")

    return normalized


def record_to_text(record: dict) -> str:
    """تحويل سجل منطقة لنص واضح بالعربي مناسب للـ embedding."""
    r = normalize_record(record)

    name = r.get("اسم_المنطقة", "غير معروف")
    gov = r.get("المحافظة", "")
    city = r.get("المدينة", "")
    price_sqm = r.get("متوسط_سعر_المتر_بيع", 0)
    rent = r.get("متوسط_الإيجار_الشهري", 0)
    prop_type = r.get("نوع_العقارات_الغالبة", "")
    category = r.get("تصنيف_المنطقة", "")
    notes = r.get("ملاحظات", "")

    parts = [f"منطقة {name}"]
    if gov:
        parts.append(f"في محافظة {gov}")
    if city and city != gov:
        parts.append(f"مدينة {city}")
    if price_sqm:
        parts.append(f"متوسط سعر المتر {price_sqm:,} جنيه مصري")
    if rent:
        parts.append(f"متوسط الإيجار الشهري {rent:,} جنيه")
    if prop_type:
        parts.append(f"نوع العقارات الغالبة {prop_type}")
    if category:
        parts.append(f"تصنيف المنطقة {category}")
    if notes:
        parts.append(notes)

    return ". ".join(parts) + "."


def load_all_records() -> list[dict]:
    """تحميل كل البيانات من JSON و Excel بدون تكرار."""
    json_data = load_from_json()
    excel_data = load_from_excel()

    seen = set()
    all_records = []

    for record in json_data + excel_data:
        r = normalize_record(record)
        name = r.get("اسم_المنطقة", "")
        if name and name not in seen:
            seen.add(name)
            all_records.append(r)

    print(f"📋 إجمالي المناطق بعد الدمج: {len(all_records)}")
    return all_records


def create_embeddings(records: list[dict] | None = None) -> tuple[list[dict], list[str], list[list[float]]]:
    """
    إنشاء embeddings لكل المناطق.

    Returns:
        (records, texts, embeddings)
    """
    if records is None:
        records = load_all_records()

    texts = [record_to_text(r) for r in records]

    print(f"🔄 جاري عمل embeddings لـ {len(texts)} منطقة...")
    embeddings = []
    for i, text in enumerate(texts):
        emb = get_embedding(text)
        embeddings.append(emb)
        if (i + 1) % 10 == 0:
            print(f"   {i + 1}/{len(texts)} ...")

    print(f"✅ تم إنشاء {len(embeddings)} embedding")
    return records, texts, embeddings
