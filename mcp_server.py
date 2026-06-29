#!/usr/bin/env python3
import os
import sys
from typing import List, Dict, Any

# Ensure standard import path works
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from mcp.server.fastmcp import FastMCP
from fitwiki.config import ScraperConfig
from fitwiki.scraper import FitWikiScraper
from fitwiki.pdf import FitWikiPDFCompiler

# Initialize FastMCP server
mcp = FastMCP("FitWiki Server")

def _get_config(cookies: str = "") -> ScraperConfig:
    """
    Creates ScraperConfig using given cookies or falling back to environment variables.
    """
    if cookies:
        return ScraperConfig.from_cookie_string(cookie_str=cookies)
    return ScraperConfig.from_env()

@mcp.tool()
def scrape_index(index_path_or_url: str, cookies: str = "") -> str:
    """
    Parses a course index page (either a local HTML file or a live URL)
    and lists all discovered pages, their URLs, and dynamically detected categories.

    Args:
        index_path_or_url: Path to local HTML (e.g. 'index-page.html') or full URL.
        cookies: DokuWiki session cookies (e.g. 'DokuWiki=...; DW...=...'). Optional.
    """
    config = _get_config(cookies)
    scraper = FitWikiScraper(config)
    
    try:
        # Load content either from local file or URL
        if os.path.exists(index_path_or_url):
            with open(index_path_or_url, 'r', encoding='utf-8') as f:
                html_content = f.read()
        else:
            # It's an URL
            html_content = scraper._get_page_html(index_path_or_url)
            
        links = scraper.scrape_index(html_content)
        
        if not links:
            return "No subpage links found. Make sure the HTML is a DokuWiki page and contains links."
            
        # Group by category
        categories_dict = {}
        for l in links:
            cat = l['category']
            if cat not in categories_dict:
                categories_dict[cat] = []
            categories_dict[cat].append(l)
            
        output = [f"Found {len(links)} links across {len(categories_dict)} categories:\n"]
        for cat, items in categories_dict.items():
            output.append(f"\n### Category: {cat} ({len(items)} pages)")
            for i, item in enumerate(items, 1):
                output.append(f"{i}. {item['title']} - URL: {item['url']}")
                
        return "\n".join(output)
        
    except Exception as e:
        return f"Error scraping index: {str(e)}"

@mcp.tool()
def scrape_page(url: str, category: str, title: str, cookies: str = "") -> str:
    """
    Scrapes a single DokuWiki page. Extracts content, downloads LaTeX formulas and images,
    sanitizes layout, converts to Markdown, and saves to file.

    Args:
        url: URL of the page to scrape.
        category: Target category directory for storing output (e.g., 'zkouska', 'test1').
        title: Title of the page.
        cookies: DokuWiki session cookies. Optional.
    """
    config = _get_config(cookies)
    scraper = FitWikiScraper(config)
    
    try:
        md_path = scraper.scrape_page(url, category, title)
        return f"Success! Saved Markdown to: {md_path}"
    except Exception as e:
        return f"Error scraping page: {str(e)}"

@mcp.tool()
def scrape_course(index_path_or_url: str, categories: str = "all", cookies: str = "") -> str:
    """
    Runs the full scraping pipeline. Extracts index, filters by category list,
    downloads and converts all matching pages, and caches raw HTML files.

    Args:
        index_path_or_url: Path to local HTML or URL to scrape index from.
        categories: Comma-separated list of categories to scrape (e.g., 'zkouska,test1') or 'all'.
        cookies: DokuWiki session cookies. Optional.
    """
    config = _get_config(cookies)
    scraper = FitWikiScraper(config)
    
    try:
        if os.path.exists(index_path_or_url):
            with open(index_path_or_url, 'r', encoding='utf-8') as f:
                html_content = f.read()
        else:
            html_content = scraper._get_page_html(index_path_or_url)
            
        links = scraper.scrape_index(html_content)
        if not links:
            return "No subpage links found in the index."
            
        # Parse selected categories
        selected = []
        if categories.strip().lower() != "all":
            selected = [c.strip().lower() for c in categories.split(',')]
            
        scraped_count = 0
        skipped_count = 0
        failed = []
        
        results = ["Starting course scrape..."]
        
        for l in links:
            cat = l['category']
            # Filter if categories list is set
            if selected and cat not in selected:
                skipped_count += 1
                continue
                
            results.append(f"Scraping [{cat}] '{l['title']}'...")
            try:
                scraper.scrape_page(l['url'], cat, l['title'])
                scraped_count += 1
            except Exception as e:
                failed.append((l['title'], str(e)))
                results.append(f"  FAILED: {str(e)}")
                
        summary = [
            "\nScrape Finished!",
            f"Successfully scraped: {scraped_count}",
            f"Skipped: {skipped_count}",
            f"Failed: {len(failed)}"
        ]
        
        if failed:
            summary.append("\nFailures:")
            for title, err in failed:
                summary.append(f"- {title}: {err}")
                
        results.extend(summary)
        return "\n".join(results)
        
    except Exception as e:
        return f"Error scraping course: {str(e)}"

@mcp.tool()
def compile_pdf(markdown_path: str, pdf_path: str) -> str:
    """
    Compiles a specific Markdown file to a lightweight PDF.
    Resolves relative image paths to absolute paths so xhtml2pdf handles them.

    Args:
        markdown_path: Absolute or relative path to the Markdown file.
        pdf_path: Absolute or relative path for saving the resulting PDF file.
    """
    config = _get_config()
    compiler = FitWikiPDFCompiler(config)
    
    try:
        success = compiler.compile_file(markdown_path, pdf_path)
        if success:
            return f"Success! PDF compiled to: {pdf_path}"
        else:
            return "Failed to compile PDF. Check log for details."
    except Exception as e:
        return f"Error compiling PDF: {str(e)}"

@mcp.tool()
def compile_category_pdfs(category: str) -> str:
    """
    Compiles all Markdown files within a category folder (e.g. 'zkouska') to PDFs.

    Args:
        category: Name of the category folder inside markdown_output/ to compile.
    """
    config = _get_config()
    compiler = FitWikiPDFCompiler(config)
    
    try:
        pdf_paths = compiler.compile_category(category)
        if pdf_paths:
            return f"Success! Compiled {len(pdf_paths)} PDFs in category '{category}':\n" + "\n".join([f"- {p}" for p in pdf_paths])
        else:
            return f"No PDFs compiled. Check if the directory 'markdown_output/{category}' exists and contains Markdown files."
    except Exception as e:
        return f"Error compiling category PDFs: {str(e)}"

@mcp.tool()
def list_courses(cookies: str = "") -> str:
    """
    Lists all subjects/courses taught at FIT. Fetches and parses the main subjects page on Fit-Wiki.

    Args:
        cookies: DokuWiki session cookies. Optional.
    """
    config = _get_config(cookies)
    scraper = FitWikiScraper(config)
    
    try:
        courses = scraper.get_courses()
        if not courses:
            return "No courses found on the subjects page."
            
        output = [f"Found {len(courses)} courses vyučovaných na FIT:\n"]
        for c in courses:
            output.append(f"- [{c['code'].upper()}] {c['title']} - URL: {c['url']}")
            
        return "\n".join(output)
    except Exception as e:
        return f"Error listing courses: {str(e)}"

if __name__ == "__main__":
    # FastMCP server runs on stdin/stdout by default
    mcp.run()
