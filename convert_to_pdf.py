#!/usr/bin/env python3
import os
import sys
from fitwiki.config import ScraperConfig
from fitwiki.pdf import FitWikiPDFCompiler

def main():
    config = ScraperConfig.from_env()
    
    if not os.path.exists(config.markdown_dir):
        print(f"Error: Markdown directory '{config.markdown_dir}' does not exist. Please run scraper.py first.")
        sys.exit(1)
        
    compiler = FitWikiPDFCompiler(config)
    
    # Discover unique categories across all course directories
    unique_categories = set()
    for course_code in os.listdir(config.markdown_dir):
        course_path = os.path.join(config.markdown_dir, course_code)
        if os.path.isdir(course_path):
            for d in os.listdir(course_path):
                if os.path.isdir(os.path.join(course_path, d)) and d != 'images':
                    unique_categories.add(d)
                    
    if not unique_categories:
        print(f"No categories found in '{config.markdown_dir}'. Make sure pages have been scraped.")
        sys.exit(0)
        
    print(f"Discovered categories for PDF compilation: {', '.join(sorted(unique_categories))}")
    
    total_compiled = 0
    for cat in sorted(unique_categories):
        print(f"\n--- Compiling Category: {cat} ---")
        compiled_paths = compiler.compile_category(cat)
        total_compiled += len(compiled_paths)
        
    print(f"\nDone! Compiled a total of {total_compiled} PDFs.")
    print(f"PDFs saved to '{config.pdf_dir}'")

if __name__ == "__main__":
    main()
