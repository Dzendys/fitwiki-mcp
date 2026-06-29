#!/usr/bin/env python3
import os
import sys
from fitwiki.config import ScraperConfig
from fitwiki.scraper import FitWikiScraper
from index_page import extract_from_index_sh

def main():
    index_file = "index-page.html"
    if not os.path.exists(index_file):
        print(f"Error: {index_file} not found. Please run index_page.py first.")
        sys.exit(1)
        
    # Read index content
    with open(index_file, "r", encoding="utf-8") as f:
        html_content = f.read()
        
    # Load config and cookies from env/dotenv
    config = ScraperConfig.from_env()
    
    # Extract cookies from index.sh to override if found
    _, cookie_str = extract_from_index_sh()
    if cookie_str:
        config.cookies = ScraperConfig.from_cookie_string(cookie_str).cookies
        
    scraper = FitWikiScraper(config)
    
    print("Parsing index page and extracting links...")
    links = scraper.scrape_index(html_content)
    
    if not links:
        print("No subpage links found. Check if the index page format has changed or if it was empty.")
        sys.exit(1)
        
    # Group links by category
    categories = {}
    for item in links:
        cat = item['category']
        if cat not in categories:
            categories[cat] = []
        categories[cat].append(item)
        
    # Print categories menu
    print("\nDiscovered Categories:")
    cat_keys = sorted(categories.keys())
    for idx, cat in enumerate(cat_keys, 1):
        print(f"  {idx}) {cat} ({len(categories[cat])} pages)")
        
    print("  all) Download everything")
    
    # Get user selection
    try:
        user_input = input("\nSelect categories to download (e.g. 1,2 or 'all'): ").strip().lower()
    except KeyboardInterrupt:
        print("\nOperation cancelled.")
        sys.exit(0)
        
    selected_cats = []
    if user_input == 'all' or not user_input:
        selected_cats = cat_keys
    else:
        parts = [p.strip() for p in user_input.split(',')]
        for part in parts:
            if part.isdigit():
                idx = int(part) - 1
                if 0 <= idx < len(cat_keys):
                    selected_cats.append(cat_keys[idx])
                else:
                    print(f"Warning: Index {part} is out of range.")
            elif part in cat_keys:
                selected_cats.append(part)
            else:
                print(f"Warning: Category '{part}' not recognized.")
                
    if not selected_cats:
        print("No categories selected. Exiting.")
        sys.exit(0)
        
    # Filter and scrape pages
    selected_links = []
    for cat in selected_cats:
        selected_links.extend(categories[cat])
        
    print(f"\nStarting to scrape {len(selected_links)} pages from categories: {', '.join(selected_cats)}...")
    
    scraped_count = 0
    failed_count = 0
    
    for i, item in enumerate(selected_links, 1):
        print(f"[{i}/{len(selected_links)}] Scraping ({item['category']}) '{item['title']}'...")
        try:
            scraper.scrape_page(item['url'], item['category'], item['title'])
            scraped_count += 1
        except Exception as e:
            print(f"  Failed: {e}")
            failed_count += 1
            
    print(f"\nDone! Successfully scraped: {scraped_count}, Failed: {failed_count}")
    print(f"Markdown output saved to '{config.markdown_dir}'")

if __name__ == "__main__":
    main()
