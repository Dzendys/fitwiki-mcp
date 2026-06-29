#!/usr/bin/env python3
import os
import re
import sys
import requests
from fitwiki.config import ScraperConfig

def extract_from_index_sh() -> tuple:
    """
    Tries to parse the URL and cookies from index.sh.
    """
    url = "https://fit-wiki.cz/škola/předměty/bi-osy"
    cookies = ""
    
    if os.path.exists("index.sh"):
        try:
            with open("index.sh", "r", encoding="utf-8") as f:
                content = f.read()
                
            # Extract URL (first argument of curl)
            url_match = re.search(r"curl\s+'([^']+)'", content)
            if url_match:
                url = url_match.group(1)
                
            # Extract cookies from -b flag
            cookie_match = re.search(r"-b\s+'([^']+)'", content)
            if cookie_match:
                cookies = cookie_match.group(1)
        except Exception as e:
            print(f"Warning: Could not parse index.sh: {e}")
            
    return url, cookies

def main():
    config = ScraperConfig.from_env()
    
    # Default fallback URL and cookies from index.sh
    url, cookie_str = extract_from_index_sh()
    
    # Overwrite target URL if CLI argument is provided
    if len(sys.argv) > 1:
        arg = sys.argv[1].strip()
        if arg.startswith("http"):
            url = arg
        else:
            url = f"{config.base_url}/škola/předměty/{arg.lower()}"
            print(f"Targeting course code: {arg.upper()}")
    else:
        print("No subject argument provided, reading target from index.sh...")
        
    print(f"Target URL: {url}")
    if cookie_str:
        print("Cookies loaded from index.sh.")
        config.cookies = ScraperConfig.from_cookie_string(cookie_str).cookies
    elif config.cookies:
        print("Cookies loaded from environment/dotenv.")
    else:
        print("Warning: No cookies found in index.sh or environment/dotenv.")

    
    print(f"Downloading main page {url}...")
    try:
        response = requests.get(url, headers=config.headers, cookies=config.cookies)
        response.raise_for_status()
        
        output_filename = "index-page.html"
        with open(output_filename, "w", encoding="utf-8") as f:
            f.write(response.text)
            
        print(f"Successfully saved index page to: {output_filename}")
        
    except Exception as e:
        print(f"Error downloading page: {e}")
        exit(1)

if __name__ == "__main__":
    main()
