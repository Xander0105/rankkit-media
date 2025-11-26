# main.py
import asyncio
import json
import logging
import os
import random

from playwright.async_api import async_playwright

from utils import USER_AGENTS, delay
from scrape_collegedunia import scrape_collegedunia_questions

LOG_FILE = os.getenv("LOG_FILE", "collegedunia_questions.log")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, mode="a", encoding="utf-8"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)


async def setup_driver(p, headless: bool = True):
    """Setup Playwright browser, context and page with desired settings"""
    browser = await p.chromium.launch(
        headless=headless,
        args=[
            "--disable-gpu",
            "--disable-dev-shm-usage",
            "--no-sandbox",
            "--disable-extensions",
            "--disable-blink-features=AutomationControlled",
        ],
    )

    ua = random.choice(USER_AGENTS)
    context = await browser.new_context(
        user_agent=ua,
        viewport={"width": 1280, "height": 800},
        java_script_enabled=True,
    )

    # Block fonts / websockets etc. but allow images (we need them)
    async def route_intercept(route, request):
        if request.resource_type in ["font", "websocket"]:
            await route.abort()
        else:
            await route.continue_()

    await context.route("**/*", route_intercept)
    page = await context.new_page()

    # Reduce animations for stability
    await page.add_style_tag(
        content="""
        *, *::before, *::after {
            transition: none !important;
            animation: none !important;
        }
        """
    )

    return browser, context, page


async def scrape_article(
    article_url: str,
    headless: bool = True,
    output_file: str = "jee_main_shift1_full.json",
):
    """
    Open a Collegedunia article (question paper), scrape:
      - all solution URLs (array 1)
      - all solution-page details from cdquestions (array 2)
    and save everything as JSON.
    """
    async with async_playwright() as p:
        browser, context, page = await setup_driver(p, headless=headless)
        try:
            logger.info(f"Loading article: {article_url}")
            resp = await page.goto(
                article_url,
                timeout=45_000,
                wait_until="domcontentloaded",
            )
            if resp is None:
                logger.warning("Navigation returned None for article page")

            # Give JS a moment to render main content
            await page.wait_for_timeout(2_000)

            # Small scrolls to trigger lazy loading if any
            for _ in range(3):
                await page.mouse.wheel(0, 500)
                await page.wait_for_timeout(500)

            # Scrape data (two arrays)
            data = await scrape_collegedunia_questions(context, page)

            # Optional: short pause before closing
            await delay(0.5, 1.5)

            # Save JSON
            os.makedirs(os.path.dirname(output_file) or ".", exist_ok=True)
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

            # num_urls = len(data.get("solution_urls", []))
            # num_details = len(data.get("solutions_detail", []))
            # logger.info(
            #     f"Saved data to {output_file} "
            #     f"(solution_urls={num_urls}, solutions_detail={num_details})"
            # )
            num_details = len(data)
            logger.info(f"Saved {num_details} questions to {output_file}")

        except Exception as e:
            logger.exception(f"Error scraping article: {e}")
        finally:
            await browser.close()


if __name__ == "__main__":
    # Example JEE paper URL (change this to any Collegedunia paper URL)
    ARTICLE_URL = (
        "https://collegedunia.com/news/e-457-neet-2025-question-paper-with-answer-key-and-solutions-pdf"
    )

    # If you want to see the browser, set headless=False
    asyncio.run(
        scrape_article(
            ARTICLE_URL,
            headless=False,
            output_file="neet_2025_full.json",
        )
    )
