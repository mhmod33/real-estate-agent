import os
import json

from dotenv import load_dotenv
from groq import Groq

from tools import TOOL_DECLARATIONS, TOOL_FUNCTIONS
from rag.retriever import search_formatted

load_dotenv()

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

MODEL_NAME = "llama-3.3-70b-versatile"

SYSTEM_PROMPT = """
You are an Egyptian real estate expert. You respond ONLY in Arabic (Egyptian dialect).
CRITICAL: Use ONLY Arabic script in your responses. NEVER use English, Vietnamese, Japanese, Russian, or any other language or script. Every single word must be in Arabic.

IMPORTANT RULES:
- When the user asks about areas, prices, rent, or comparisons, ALWAYS call search_local_database first.
- For comparisons between two areas: search for each area separately (two calls), then compare.
- If search_local_database returns real data, use it directly in your answer.
- If search_local_database returns no useful data, answer using your own deep knowledge of the Egyptian real estate market. You know Egypt's areas, prices, and trends very well.
- NEVER mention "قاعدة البيانات" or "database" or "لم يتم العثور" to the user. The user must not know about any internal system.
- NEVER say you don't have information. Always give a confident, helpful answer like a professional real estate expert.
- NEVER say "مش عارف" or "مش متأكد" - always give your best expert estimate.
- Only use ROI or listing analysis tools when the user provides actual numbers.
- If the user is just greeting, reply normally without using any tools.
- All search queries must be in Arabic only.
"""

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "search_local_database",
            "description": "Search the local Egyptian real estate database for areas, prices, and rent data. Returns top matching results from 60+ areas in Egypt.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query in Arabic about an area, price, or comparison",
                    },
                },
                "required": ["query"],
            },
        },
    },
    *(
        {
            "type": "function",
            "function": {
                "name": t["name"],
                "description": t["description"],
                "parameters": t["parameters"],
            },
        }
        for t in TOOL_DECLARATIONS
    ),
]


def _simplify_query(query: str) -> list[str]:
    """استخراج كلمات مفتاحية أبسط من السؤال للبحث."""
    stop_words = {
        "في", "من", "على", "عن", "إلى", "الى", "لو", "هل", "ما", "ماهو",
        "شقة", "شقه", "عقار", "بيت", "فيلا", "دور", "دوبلكس",
        "مش", "متشطب", "متشطبة", "فاضي", "بيع", "إيجار", "ايجار",
        "أسعار", "اسعار", "سعر", "متر", "المتر", "حاجة", "كويسة",
        "رخيصة", "غالية", "هستأجر", "هشتري", "عايز", "محتاج",
        "أفضل", "احسن", "منطقة", "منطقه", "حي", "مكان",
    }
    words = query.split()
    keywords = [w for w in words if w not in stop_words and len(w) > 2]

    attempts = []
    if keywords and keywords != words:
        attempts.append(" ".join(keywords))
    for word in keywords:
        if len(word) > 3:
            attempts.append(word)
    return attempts


def search_local_database(query: str) -> str:
    """تنفيذ البحث في الـ Vector Store المحلي مع fallback لكلمات أبسط."""
    result = search_formatted(query, top_k=5)

    if result and "لم يتم العثور" not in result:
        return result

    for simplified in _simplify_query(query):
        if simplified == query:
            continue
        print(f"  🔄 جرب بحث مبسط: {simplified}")
        result2 = search_formatted(simplified, top_k=5)
        if result2 and "لم يتم العثور" not in result2:
            return f"(بحثت بـ '{simplified}')\n" + result2

    return "بحثت في القاعدة ومفيش بيانات كافية عن هذه المنطقة. استخدم معرفتك بالسوق المصري للإجابة."


TOOL_FUNCTIONS["search_local_database"] = search_local_database


def run_agent(user_message: str, history: list | None = None) -> str:
    """
    تشغيل الـ Agent مع Agent Loop.
    """
    if history is None:
        history = []

    messages = [{"role": "system", "content": SYSTEM_PROMPT}] + history
    messages.append({"role": "user", "content": user_message})

    while True:
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=messages,
            tools=TOOLS,
        )

        assistant_message = response.choices[0].message
        messages.append(assistant_message)

        if not assistant_message.tool_calls:
            break

        for tool_call in assistant_message.tool_calls:
            func_name = tool_call.function.name

            try:
                func_args = json.loads(tool_call.function.arguments)
            except json.JSONDecodeError:
                func_args = {}

            print(f"  ⚙️  تنفيذ: {func_name}({json.dumps(func_args, ensure_ascii=False)})")

            if func_name in TOOL_FUNCTIONS:
                result = TOOL_FUNCTIONS[func_name](**func_args)
            else:
                result = {"error": f"Unknown tool: {func_name}"}

            if not isinstance(result, str):
                result = json.dumps(result, ensure_ascii=False)

            messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": result,
            })

    final_text = assistant_message.content or "معرفتش أجاوب على السؤال ده."
    return final_text


def main():
    """حلقة المحادثة في الـ Terminal."""
    print("=" * 60)
    print("  🏠 مرحبًا! أنا المستشار العقاري الذكي")
    print("  اسألني أي سؤال عن العقارات في مصر")
    print("  اكتب 'خروج' أو 'exit' للخروج")
    print("=" * 60)

    history = []

    while True:
        user_input = input("\n🧑 أنت: ").strip()
        if not user_input:
            continue
        if user_input.lower() in ("خروج", "exit", "quit"):
            print("👋 مع السلامة!")
            break

        print("\n🤖 المستشار العقاري:")
        try:
            answer = run_agent(user_input, history)
            print(answer)
        except Exception as e:
            print(f"❌ حصل خطأ: {e}")


if __name__ == "__main__":
    main()
