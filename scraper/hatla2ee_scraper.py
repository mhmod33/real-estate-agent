"""
سحب إعلانات عقارات من موقع هتلاقي (hatla2ee.com)
يستخدم Playwright في stealth mode
"""

import os
import json
import random
import asyncio

from playwright.async_api import async_playwright, Page, Browser

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
OUTPUT_FILE = os.path.join(DATA_DIR, "hatla2ee_listings.json")
PROGRESS_FILE = os.path.join(DATA_DIR, "_hatla2ee_progress.json")

BASE_URL = "https://www.hatla2ee.com"
SEARCH_URL = f"{BASE_URL}/ar/property/egypt"

MAX_PAGES = 15
DELAY_MIN = 2
DELAY_MAX = 4


def load_progress() -> list[dict]:
    if os.path.exists(PROGRESS_FILE):
        with open(PROGRESS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


def save_progress(data: list[dict]):
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(PROGRESS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def save_final(data: list[dict]):
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


async def random_delay():
    delay = random.uniform(DELAY_MIN, DELAY_MAX)
    await asyncio.sleep(delay)


async def stealth_context(browser: Browser):
    """إنشاء context مع إعدادات stealth لتجنب الحظر."""
    context = await browser.new_context(
        locale="ar-EG",
        timezone_id="Africa/Cairo",
        viewport={"width": 1366, "height": 768},
        user_agent=(
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
        extra_http_headers={
            "Accept-Language": "ar-EG,ar;q=0.9,en;q=0.8",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-User": "?1",
            "Upgrade-Insecure-Requests": "1",
        },
    )

    # إخفاء webdriver
    await context.add_init_script("""
        Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
        Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3]});
        Object.defineProperty(navigator, 'languages', {get: () => ['ar-EG', 'ar', 'en']});
        window.chrome = {runtime: {}};
    """)

    return context


async def extract_listing_details(page: Page, url: str) -> dict | None:
    """استخراج تفاصيل إعلان واحد."""
    try:
        await page.goto(url, wait_until="domcontentloaded", timeout=30000)
        await page.wait_for_timeout(2000)

        listing = {"رابط_الإعلان": url, "المصدر": "hatla2ee"}

        # العنوان
        title_el = page.locator("h1").first
        if await title_el.count():
            listing["العنوان"] = (await title_el.text_content()).strip()

        # السعر
        price_selectors = [
            "[class*='price']", "[class*='Price']",
            "[data-price]", ".listing-price",
        ]
        for sel in price_selectors:
            el = page.locator(sel).first
            if await el.count():
                price_text = (await el.text_content()).strip()
                listing["السعر_نص"] = price_text
                digits = "".join(c for c in price_text if c.isdigit())
                if digits:
                    listing["السعر"] = int(digits)
                break

        # الموقع
        location_selectors = [
            "[class*='location']", "[class*='Location']",
            "[class*='address']", "[class*='area']",
        ]
        for sel in location_selectors:
            el = page.locator(sel).first
            if await el.count():
                location_text = (await el.text_content()).strip()
                if location_text:
                    parts = [p.strip() for p in location_text.replace("،", ",").split(",")]
                    listing["الموقع_كامل"] = location_text
                    listing["المنطقة"] = parts[0] if parts else ""
                    listing["المحافظة"] = parts[-1] if len(parts) > 1 else ""
                    break

        # التفاصيل (مساحة، غرف، إلخ)
        all_text_elements = page.locator(
            "[class*='detail'], [class*='spec'], [class*='feature'], "
            "[class*='info'], [class*='attribute'], li"
        )
        count = await all_text_elements.count()

        for i in range(min(count, 40)):
            try:
                text = (await all_text_elements.nth(i).text_content()).strip()
            except Exception:
                continue

            if not text or len(text) > 200:
                continue

            if ("متر" in text or "م²" in text or "مساحة" in text) and "المساحة" not in listing:
                digits = "".join(c for c in text if c.isdigit())
                if digits and 10 < int(digits) < 100000:
                    listing["المساحة"] = int(digits)
            elif ("غرف" in text or "غرفة" in text) and "غرف_النوم" not in listing:
                digits = "".join(c for c in text if c.isdigit())
                if digits and int(digits) < 20:
                    listing["غرف_النوم"] = int(digits)
            elif ("حمام" in text) and "الحمامات" not in listing:
                digits = "".join(c for c in text if c.isdigit())
                if digits and int(digits) < 10:
                    listing["الحمامات"] = int(digits)
            elif ("طابق" in text or "دور" in text) and "الطابق" not in listing:
                digits = "".join(c for c in text if c.isdigit())
                if digits and int(digits) < 50:
                    listing["الطابق"] = int(digits)
            elif "نوع" in text and "نوع_العقار" not in listing:
                listing["نوع_العقار"] = text.split(":")[-1].strip() if ":" in text else text

        # الوصف
        desc_selectors = ["[class*='description']", "[class*='desc']", "[class*='content']"]
        for sel in desc_selectors:
            el = page.locator(sel).first
            if await el.count():
                desc = (await el.text_content()).strip()
                if len(desc) > 20:
                    listing["الوصف"] = desc[:500]
                    break

        return listing

    except Exception as e:
        print(f"    ⚠️  خطأ في استخراج: {url} — {e}")
        return None


async def extract_listing_links(page: Page) -> list[str]:
    """استخراج روابط الإعلانات من صفحة النتائج."""
    links = []

    # محاولة عدة selectors
    selectors = [
        "a[href*='/property/']",
        "a[href*='/listing/']",
        "a[href*='/ad/']",
        ".listing-card a",
        "[class*='listing'] a",
        "[class*='card'] a[href]",
    ]

    for sel in selectors:
        anchors = page.locator(sel)
        count = await anchors.count()
        if count > 0:
            for i in range(count):
                href = await anchors.nth(i).get_attribute("href")
                if href and href not in links:
                    full_url = href if href.startswith("http") else BASE_URL + href
                    if "/property/" in full_url or "/listing/" in full_url or "/ad/" in full_url:
                        links.append(full_url)
            if links:
                break

    # إزالة التكرار
    return list(dict.fromkeys(links))


async def scrape_hatla2ee():
    """السحب الرئيسي من هتلاقي."""
    print("=" * 60)
    print("  🏘️  سحب إعلانات من hatla2ee.com (عقارات)")
    print("=" * 60)

    all_listings = load_progress()
    seen_urls = {l.get("رابط_الإعلان") for l in all_listings}

    if all_listings:
        print(f"  📂 تم تحميل {len(all_listings)} إعلان من التقدم السابق")

    async with async_playwright() as p:
        browser: Browser = await p.chromium.launch(headless=True)
        context = await stealth_context(browser)
        page = await context.new_page()

        total_new = 0

        for page_num in range(1, MAX_PAGES + 1):
            url = f"{SEARCH_URL}?page={page_num}"
            print(f"\n📄 صفحة {page_num}/{MAX_PAGES}: {url}")

            try:
                await page.goto(url, wait_until="domcontentloaded", timeout=30000)
                await page.wait_for_timeout(3000)

                # تحقق من Block
                content = await page.content()
                if "captcha" in content.lower() or "blocked" in content.lower() or "403" in content:
                    print("  🚫 تم الحظر! جاري الانتظار 30 ثانية...")
                    await asyncio.sleep(30)
                    continue

                links = await extract_listing_links(page)
                new_links = [l for l in links if l not in seen_urls]
                print(f"  🔗 {len(links)} إعلان ({len(new_links)} جديد)")

                if not links:
                    print("  ⏭️  مفيش إعلانات في الصفحة دي")
                    await random_delay()
                    continue

                for idx, link in enumerate(new_links, 1):
                    print(f"  [{idx}/{len(new_links)}] سحب: {link[:60]}...")
                    listing = await extract_listing_details(page, link)

                    if listing:
                        all_listings.append(listing)
                        seen_urls.add(link)
                        total_new += 1
                        title = listing.get("العنوان", "؟")[:35]
                        price = listing.get("السعر_نص", "؟")
                        print(f"    ✅ {title} — {price}")

                    # حفظ التقدم كل 10 إعلانات
                    if total_new % 10 == 0 and total_new > 0:
                        save_progress(all_listings)
                        print(f"    💾 حفظ التقدم ({len(all_listings)} إعلان)")

                    await random_delay()

            except Exception as e:
                print(f"  ❌ خطأ في الصفحة {page_num}: {e}")
                await random_delay()
                continue

        await browser.close()

    # حفظ النتيجة النهائية
    if all_listings:
        save_final(all_listings)
        if os.path.exists(PROGRESS_FILE):
            os.remove(PROGRESS_FILE)

    # إحصائيات
    print(f"\n{'=' * 60}")
    print(f"  📊 إحصائيات السحب من هتلاقي:")
    print(f"  📝 إجمالي الإعلانات: {len(all_listings)}")
    print(f"  🆕 إعلانات جديدة: {total_new}")
    print(f"  💾 محفوظ في: {OUTPUT_FILE}")

    # توزيع حسب المنطقة
    areas = {}
    for l in all_listings:
        area = l.get("المنطقة", "غير محدد")
        areas[area] = areas.get(area, 0) + 1
    if areas:
        print(f"\n  📍 توزيع المناطق (أعلى 10):")
        for a, c in sorted(areas.items(), key=lambda x: x[1], reverse=True)[:10]:
            print(f"    • {a}: {c} إعلان")

    print(f"{'=' * 60}")


if __name__ == "__main__":
    asyncio.run(scrape_hatla2ee())
