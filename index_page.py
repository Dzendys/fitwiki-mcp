#!/usr/bin/env python3
import os
import sys
import requests
from fitwiki.config import ScraperConfig


def main():
    if len(sys.argv) < 2:
        print("Usage: python index_page.py <course_code_or_url>")
        sys.exit(1)

    config = ScraperConfig.from_env()

    arg = sys.argv[1].strip()
    if arg.startswith("http"):
        url = arg
    else:
        url = f"{config.base_url}/škola/předměty/{arg.lower()}"
        print(f"Targeting course code: {arg.upper()}")

    if not config.cookies:
        print("Warning: No cookies found in .env or environment.")
        print("Set FITWIKI_COOKIES in .env (see .env.example).")

    print(f"Downloading index page from {url}...")
    try:
        response = requests.get(url, headers=config.headers, cookies=config.cookies)
        response.raise_for_status()

        output_filename = "index-page.html"
        with open(output_filename, "w", encoding="utf-8") as f:
            f.write(response.text)

        print(f"Saved index page to: {output_filename}")

    except Exception as e:
        print(f"Error downloading page: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
