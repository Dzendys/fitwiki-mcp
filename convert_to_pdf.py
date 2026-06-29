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
    
    # Discover categories in markdown_output
    categories = [
        d for d in os.listdir(config.markdown_dir)
        if os.path.isdir(os.path.join(config.markdown_dir, d))
    ]
    
    if not categories:
        print(f"No categories found in '{config.markdown_dir}'. Make sure pages have been scraped.")
        sys.exit(0)
        
    print(f"Discovered categories for PDF compilation: {', '.join(categories)}")
    
    total_compiled = 0
    for cat in categories:
        print(f"\n--- Compiling Category: {cat} ---")
        compiled_paths = compiler.compile_category(cat)
        total_compiled += len(compiled_paths)
        
    print(f"\nDone! Compiled a total of {total_compiled} PDFs.")
    print(f"PDFs saved to '{config.pdf_dir}'")

if __name__ == "__main__":
    main()
