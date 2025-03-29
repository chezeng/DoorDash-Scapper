import os
import asyncio
import json
from scrapybara import Scrapybara
from undetected_playwright.async_api import async_playwright

# Constants
DOORDASH_GRAPHQL_URL = "https://www.doordash.com/graphql/itemPage?operation=itemPage"

async def get_scrapybara_browser():
    """Creates a Scrapybara browser instance."""
    client = Scrapybara(api_key=os.getenv("SCRAPYBARA_API_KEY"))
    instance = client.start_browser()
    return instance

async def retrieve_menu_items(instance, start_url: str) -> list[dict]:
    """
    Navigates to a DoorDash store page and extracts menu item details.
    """
    cdp_url = instance.get_cdp_url().cdp_url
    async with async_playwright() as p:
        browser = await p.chromium.connect_over_cdp(cdp_url)
        context = await browser.new_context()
        page = await context.new_page()

        await page.goto(start_url)
        await page.wait_for_load_state("networkidle")

        menu_items = []

        async def intercept_response(response):
            """Intercepts network responses to extract menu data."""
            if "graphql/itemPage" in response.url:
                print(f"📡 Intercepted request: {response.url}")  # Debug log
                try:
                    json_data = await response.json()
                    print(f"📡 Received Data: {json_data}")  # Debug log
                    item_data = json_data.get("data", {}).get("itemPage", {}).get("store", {}).get("items", [])
                    for item in item_data:
                        menu_items.append({
                            "id": item.get("id"),
                            "name": item.get("name"),
                            "price": item.get("price"),
                            "description": item.get("description"),
                            "image": item.get("image", {}).get("url"),
                        })
                except Exception as e:
                    print(f"❌ Error parsing response: {e}")

        page.on("response", intercept_response)

        print("📜 Scrolling to load menu items...")
        previous_height = None
        while True:
            height = await page.evaluate("document.body.scrollHeight")
            if previous_height == height:
                break
            previous_height = height
            await page.evaluate("window.scrollBy(0, window.innerHeight)")
            await asyncio.sleep(1.5)

        await asyncio.sleep(5)

        print(f"✅ Scraped {len(menu_items)} items.")
        return menu_items


async def main():
    """Main function to execute the scraper."""
    instance = await get_scrapybara_browser()

    try:
        menu_data = await retrieve_menu_items(
            instance,
            "https://www.doordash.com/store/panda-express-san-francisco-980938/12722988/?event_type=autocomplete&pickup=false",
        )
        print(json.dumps(menu_data, indent=2))  # Output scraped data as JSON
    finally:
        instance.stop()

if __name__ == "__main__":
    asyncio.run(main())
