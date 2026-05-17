"""
سحب إعلانات عقارات من موقع عقار مصر (aqarmap.com.eg)
يستخدم Playwright لأن الموقع dynamic (JavaScript rendered)
"""

import os
import json
import time
import random
import asyncio

from playwright.async_api import async_playwright, Page, Browser

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
OUTPUT_FILE = os.path.join(DATA_DIR, "aqar_listings.json")
PROGRESS_FILE = os.path.join(DATA_DIR, "_aqar_progress.json")

BASE_URL = "https://aqarmap.com.eg"
SEARCH_URL = f"{BASE_URL}/ar/for-sale/property-type/egypt"

MAX_PAGES = 20
DELAY_MIN = 2
DELAY_MAX = 5

HEADERS = {
    "Accept-Language": "ar,en;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}


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


async def extract_listing_details(page: Page, url: str) -> dict | None:
    """استخراج تفاصيل إعلان واحد."""
    try:
        await page.goto(url, wait_until="domcontentloaded", timeout=30000)
        await page.wait_for_timeout(2000)

        listing = {"رابط_الإعلان": url}

        # العنوان
        title_el = page.locator("h1").first
        if await title_el.count():
            listing["العنوان"] = (await title_el.text_content()).strip()

        # السعر
        price_el = page.locator("[class*='price'], [class*='Price']").first
        if await price_el.count():
            price_text = (await price_el.text_content()).strip()
            listing["السعر_نص"] = price_text
            digits = "".join(c for c in price_text if c.isdigit())
            listing["السعر"] = int(digits) if digits else 0

        # المنطقة والموقع
        location_el = page.locator("[class*='location'], [class*='Location'], [class*='address']").first
        if await location_el.count():
            location_text = (await location_el.text_content()).strip()
            parts = [p.strip() for p in location_text.split(",")]
            listing["الموقع_كامل"] = location_text
            listing["المنطقة"] = parts[0] if parts else ""
            listing["المحافظة"] = parts[-1] if len(parts) > 1 else ""

        # التفاصيل (مساحة، غرف، حمامات، طابق)
        detail_items = page.locator("[class*='detail'], [class*='feature'], [class*='spec'], [class*='info-item']")
        count = await detail_items.count()
        for i in range(min(count, 20)):
            text = (await detail_items.nth(i).text_content()).strip()
            text_lower = text.lower()

            if "متر" in text or "م²" in text or "sqm" in text_lower:
                digits = "".join(c for c in text if c.isdigit())
                if digits:
                    listing["المساحة"] = int(digits)
            elif "غرف" in text or "غرفة" in text or "bedroom" in text_lower:
                digits = "".join(c for c in text if c.isdigit())
                if digits:
                    listing["غرف_النوم"] = int(digits)
            elif "حمام" in text or "bathroom" in text_lower:
                digits = "".join(c for c in text if c.isdigit())
                if digits:
                    listing["الحمامات"] = int(digits)
            elif "طابق" in text or "دور" in text or "floor" in text_lower:
                digits = "".join(c for c in text if c.isdigit())
                if digits:
                    listing["الطابق"] = int(digits)

        # نوع العقار
        type_el = page.locator("[class*='type'], [class*='category'], [class*='property-type']").first
        if await type_el.count():
            listing["نوع_العقار"] = (await type_el.text_content()).strip()

        # الوصف
        desc_el = page.locator("[class*='description'], [class*='desc']").first
        if await desc_el.count():
            listing["الوصف"] = (await desc_el.text_content()).strip()[:500]

        return listing

    except Exception as e:
        print(f"    ⚠️  خطأ في استخراج: {url} — {e}")
        return None


async def extract_listing_links(page: Page) -> list[str]:
    """استخراج روابط الإعلانات من صفحة النتائج."""
    links = []
    anchors = page.locator("a[href*='/ar/listing/'], a[href*='/listing/']")
    count = await anchors.count()

    for i in range(count):
        href = await anchors.nth(i).get_attribute("href")
        if href:
            full_url = href if href.startswith("http") else BASE_URL + href
            if full_url not in links:
                links.append(full_url)

    return links


async def scrape_aqar():
    """السحب الرئيسي من عقار."""
    print("=" * 60)
    print("  🏠 سحب إعلانات من aqarmap.com.eg")
    print("=" * 60)

    all_listings = load_progress()
    seen_urls = {l.get("رابط_الإعلان") for l in all_listings}

    if all_listings:
        print(f"  📂 تم تحميل {len(all_listings)} إعلان من التقدم السابق")

    async with async_playwright() as p:
        browser: Browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            locale="ar-EG",
            extra_http_headers=HEADERS,
            viewport={"width": 1366, "height": 768},
        )
        page = await context.new_page()

        total_new = 0

        for page_num in range(1, MAX_PAGES + 1):
            url = f"{SEARCH_URL}?page={page_num}"
            print(f"\n📄 صفحة {page_num}/{MAX_PAGES}: {url}")

            try:
                await page.goto(url, wait_until="domcontentloaded", timeout=30000)
                await page.wait_for_timeout(3000)

                links = await extract_listing_links(page)
                new_links = [l for l in links if l not in seen_urls]
                print(f"  🔗 {len(links)} إعلان ({len(new_links)} جديد)")

                if not new_links:
                    print("  ⏭️  مفيش إعلانات جديدة، الصفحة التالية...")
                    await random_delay()
                    continue

                for idx, link in enumerate(new_links, 1):
                    print(f"  [{idx}/{len(new_links)}] جاري سحب: {link[:60]}...")
                    listing = await extract_listing_details(page, link)

                    if listing:
                        all_listings.append(listing)
                        seen_urls.add(link)
                        total_new += 1
                        print(f"    ✅ {listing.get('العنوان', '؟')[:40]}")

                    # حفظ التقدم كل 10 إعلانات
                    if total_new % 10 == 0 and total_new > 0:
                        save_progress(all_listings)
                        print(f"    💾 تم حفظ التقدم ({len(all_listings)} إعلان)")

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
    print(f"  📊 إحصائيات السحب من عقار:")
    print(f"  📝 إجمالي الإعلانات: {len(all_listings)}")
    print(f"  🆕 إعلانات جديدة: {total_new}")
    print(f"  💾 محفوظ في: {OUTPUT_FILE}")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    asyncio.run(scrape_aqar())
