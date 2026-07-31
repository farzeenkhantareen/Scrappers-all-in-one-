import asyncio
from playwright.async_api import async_playwright
import sys

async def main():
    url = "https://www.google.com/maps/search/Ensys%20Technologies%20India%20Private%20Limited%2C%2041%2C%207th%20Ave%2C%20Sarvamangala%20Colony%2C%20Manthope%20Colony%2C%20Ashok%20Nagar%2C%20Chennai%2C%20Greater%20Chennai%2C%20Tamil%20Nadu%20600083%2C%20India"
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = await context.new_page()
        print("Navigating to URL...")
        try:
            await page.goto(url, wait_until="commit", timeout=30000)
        except Exception as e:
            print(f"Navigation timed out or failed: {e}")
        await page.wait_for_timeout(5000)
        
        # Take a screenshot to see what's loaded
        screenshot_path = "C:/Users/farze/.gemini/antigravity-ide/brain/18b2e60a-7b9a-46e7-a272-88fdb8a65814/scratch_gmaps.png"
        await page.screenshot(path=screenshot_path)
        print(f"Screenshot saved to {screenshot_path}")
        
        # Try extracting text content of h1 and rating elements
        h1 = await page.query_selector("h1")
        if h1:
            print(f"Found h1: '{await h1.inner_text()}'")
        else:
            print("No h1 found")
            
        f7 = await page.query_selector(".F7nice")
        if f7:
            print(f"Found F7nice: '{await f7.inner_text()}'")
        else:
            print("No F7nice found")
            
        html = await page.content()
        with open("C:/Users/farze/.gemini/antigravity-ide/brain/18b2e60a-7b9a-46e7-a272-88fdb8a65814/scratch_gmaps.html", "w", encoding="utf-8") as f:
            f.write(html)
        print("HTML content saved.")
        
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
