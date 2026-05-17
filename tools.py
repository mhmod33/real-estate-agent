def calculate_roi(property_price: float, monthly_rent: float) -> dict:
    """
    حساب العائد على الاستثمار العقاري.

    Args:
        property_price: سعر العقار بالجنيه المصري.
        monthly_rent: الإيجار الشهري المتوقع بالجنيه المصري.

    Returns:
        dict يحتوي على الإيجار السنوي ونسبة ROI وسنوات الاسترداد.
    """
    annual_rent = monthly_rent * 12
    roi_percentage = (annual_rent / property_price) * 100 if property_price > 0 else 0
    payback_years = property_price / annual_rent if annual_rent > 0 else float("inf")

    return {
        "سعر_العقار": f"{property_price:,.0f} جنيه",
        "الإيجار_الشهري": f"{monthly_rent:,.0f} جنيه",
        "الإيجار_السنوي": f"{annual_rent:,.0f} جنيه",
        "نسبة_العائد_ROI": f"{roi_percentage:.2f}%",
        "سنوات_الاسترداد": f"{payback_years:.1f} سنة",
    }


def analyze_listing(area: str, price: float, size_sqm: float) -> dict:
    """
    تحليل إعلان عقاري وحساب سعر المتر وإعداد تقرير.

    Args:
        area: اسم المنطقة أو الحي (مثلاً: التجمع الخامس، المعادي).
        price: سعر العقار بالجنيه المصري.
        size_sqm: مساحة العقار بالمتر المربع.

    Returns:
        dict يحتوي على تقرير تحليل العقار.
    """
    price_per_sqm = price / size_sqm if size_sqm > 0 else 0

    if price_per_sqm < 15000:
        price_category = "منخفض"
    elif price_per_sqm < 30000:
        price_category = "متوسط"
    elif price_per_sqm < 60000:
        price_category = "فوق المتوسط"
    else:
        price_category = "مرتفع (فاخر)"

    return {
        "المنطقة": area,
        "السعر_الإجمالي": f"{price:,.0f} جنيه",
        "المساحة": f"{size_sqm:,.0f} متر مربع",
        "سعر_المتر": f"{price_per_sqm:,.0f} جنيه/م²",
        "تصنيف_السعر": price_category,
        "ملاحظات": f"سعر المتر في {area} هو {price_per_sqm:,.0f} جنيه، "
        f"وده يعتبر مستوى {price_category} بالنسبة للسوق المصري.",
    }


# تعريف الأدوات بصيغة Gemini Function Declarations
TOOL_FUNCTIONS = {
    "calculate_roi": calculate_roi,
    "analyze_listing": analyze_listing,
}

TOOL_DECLARATIONS = [
    {
        "name": "calculate_roi",
        "description": "حساب العائد على الاستثمار العقاري (ROI) من سعر العقار والإيجار الشهري. "
        "يحسب الإيجار السنوي ونسبة العائد وعدد سنوات الاسترداد.",
        "parameters": {
            "type": "object",
            "properties": {
                "property_price": {
                    "type": "number",
                    "description": "سعر العقار بالجنيه المصري",
                },
                "monthly_rent": {
                    "type": "number",
                    "description": "الإيجار الشهري المتوقع بالجنيه المصري",
                },
            },
            "required": ["property_price", "monthly_rent"],
        },
    },
    {
        "name": "analyze_listing",
        "description": "تحليل إعلان عقاري: حساب سعر المتر المربع وتصنيف السعر وتقديم تقرير عن العقار.",
        "parameters": {
            "type": "object",
            "properties": {
                "area": {
                    "type": "string",
                    "description": "اسم المنطقة أو الحي (مثل: التجمع الخامس، المعادي، الشيخ زايد)",
                },
                "price": {
                    "type": "number",
                    "description": "سعر العقار بالجنيه المصري",
                },
                "size_sqm": {
                    "type": "number",
                    "description": "مساحة العقار بالمتر المربع",
                },
            },
            "required": ["area", "price", "size_sqm"],
        },
    },
]
