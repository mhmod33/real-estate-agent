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

IMPORTANT RULES:
- When the user asks about areas, prices, rent, or comparisons, search the local database first.
- For comparisons between two areas: search for each area separately (two search_local_database calls), then compare the results.
- Use ONLY the data returned from tools. Do NOT add information from your own knowledge.
- If search_local_database returns results, use them directly in your answer. Do not search again for the same query.
- Only use ROI or listing analysis tools when the user provides actual numbers.
- If the user is just greeting, reply normally without using any tools.
- After getting tool results, answer immediately. Do not call the same tool again.
- All search queries must be in Arabic only.
"""

# أداة البحث في قاعدة البيانات المحلية (RAG)
SEARCH_LOCAL_TOOL = {
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
}


def search_local_database(query: str) -> str:
    """تنفيذ البحث في الـ Vector Store المحلي."""
    return search_formatted(query, top_k=5)


# تحويل تعريفات الأدوات لصيغة OpenAI-compatible (Groq format)
TOOLS = [
    SEARCH_LOCAL_TOOL,
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

# ربط الأداة الجديدة بالدوال
TOOL_FUNCTIONS["search_local_database"] = search_local_database


def run_agent(user_message: str, history: list | None = None) -> str:
    """
    تشغيل الـ Agent مع Agent Loop:
    يبعت الرسالة → يشوف لو الموديل طلب tool call → ينفذها → يرجع النتيجة → يكرر لحد ما يخلص.
    """
    if history is None:
        history = []

    messages = [{"role": "system", "content": SYSTEM_PROMPT}] + history
    messages.append({"role": "user", "content": user_message})

    # Agent Loop
    while True:
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=messages,
            tools=TOOLS,
        )

        assistant_message = response.choices[0].message
        messages.append(assistant_message)

        # لو مفيش tool calls → خلص
        if not assistant_message.tool_calls:
            break

        # تنفيذ كل الـ tool calls
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

            # النتيجة لازم تكون string
            if not isinstance(result, str):
                result = json.dumps(result, ensure_ascii=False)

            messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": result,
            })

    # استخرج الرد النصي النهائي
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
