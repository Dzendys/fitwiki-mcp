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
host = os.getenv("MCP_HOST", "127.0.0.1")
port = int(os.getenv("MCP_PORT", "8000"))
mcp = FastMCP("FitWiki Server", host=host, port=port)

def _get_config(cookies: str = "") -> ScraperConfig:
    """
    Creates ScraperConfig using given cookies or falling back to environment variables.
    """
    if cookies:
        return ScraperConfig.from_cookie_string(cookie_str=cookies)
    return ScraperConfig.from_env()

def _resolve_url(code_or_url: str) -> str:
    """
    Resolves a course code or absolute URL into a full DokuWiki URL.
    """
    if code_or_url.startswith("http"):
        return code_or_url
    config = ScraperConfig.from_env()
    return f"{config.base_url}/škola/předměty/{code_or_url.lower()}"


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
        with open(md_path, 'r', encoding='utf-8') as f:
            content = f.read()
        return f"Success! Saved Markdown to: {md_path}\n\n--- Content ---\n\n{content}"
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
def list_course_sections(course_code_or_url: str, cookies: str = "") -> str:
    """
    Lists all material sections/categories (e.g. 'zkouska', 'test1') for a given subject.

    Args:
        course_code_or_url: Subject code (e.g. 'bi-osy') or full course index URL.
        cookies: DokuWiki session cookies. Optional.
    """
    url = _resolve_url(course_code_or_url)
    config = _get_config(cookies)
    scraper = FitWikiScraper(config)
    
    try:
        html = scraper._get_page_html(url)
        links = scraper.scrape_index(html)
        if not links:
            return f"No subpages or sections found for course at {url}."
            
        sections = set(l['category'] for l in links)
        output = [f"Found {len(sections)} sections for course {course_code_or_url.upper()}:\n"]
        for s in sorted(sections):
            count = sum(1 for l in links if l['category'] == s)
            output.append(f"- {s} ({count} pages/terms)")
            
        return "\n".join(output)
    except Exception as e:
        return f"Error listing sections: {str(e)}"

@mcp.tool()
def list_section_pages(course_code_or_url: str, sections: str, cookies: str = "") -> str:
    """
    Lists all pages (exam terms, test variants) within specific sections of a course.

    Args:
        course_code_or_url: Subject code (e.g. 'bi-osy') or course index URL.
        sections: Comma-separated list of sections (e.g. 'zkouska,test1') to filter.
        cookies: DokuWiki session cookies. Optional.
    """
    url = _resolve_url(course_code_or_url)
    config = _get_config(cookies)
    scraper = FitWikiScraper(config)
    
    try:
        html = scraper._get_page_html(url)
        links = scraper.scrape_index(html)
        if not links:
            return f"No pages found for course at {url}."
            
        filter_sections = [s.strip().lower() for s in sections.split(',')]
        filtered_links = [l for l in links if l['category'] in filter_sections]
        
        if not filtered_links:
            return f"No pages found in sections: {sections}."
            
        output = [f"Found {len(filtered_links)} pages/terms in sections [{sections}] of {course_code_or_url.upper()}:\n"]
        for i, l in enumerate(filtered_links, 1):
            output.append(f"{i}. [{l['category']}] {l['title']} - URL: {l['url']}")
            
        return "\n".join(output)
    except Exception as e:
        return f"Error listing section pages: {str(e)}"

@mcp.tool()
def download_page(url: str, category: str, title: str, cookies: str = "") -> str:
    """
    Downloads a single page, converts it to Markdown, and compiles it to PDF.
    Returns paths to both files.

    Args:
        url: URL of the page to download.
        category: Category section (e.g. 'zkouska', 'test1') for storing files.
        title: Title of the page.
        cookies: DokuWiki session cookies. Optional.
    """
    config = _get_config(cookies)
    scraper = FitWikiScraper(config)
    compiler = FitWikiPDFCompiler(config)
    
    try:
        # 1. Scrape to Markdown
        md_path = scraper.scrape_page(url, category, title)
        
        # 2. Compile to PDF (preserving the same nested folder structure under pdf_dir)
        rel_md_path = os.path.relpath(md_path, config.markdown_dir)
        pdf_rel_path = rel_md_path.replace('.md', '.pdf')
        pdf_path = os.path.join(config.pdf_dir, pdf_rel_path)
        os.makedirs(os.path.dirname(pdf_path), exist_ok=True)
        
        success = compiler.compile_file(md_path, pdf_path)
        
        if success:
            with open(md_path, 'r', encoding='utf-8') as f:
                content = f.read()
            return (
                f"Success! Page downloaded and compiled:\n"
                f"- Markdown path: {md_path}\n"
                f"- PDF path: {pdf_path}\n\n"
                f"--- Content ---\n\n{content}"
            )
        else:
            with open(md_path, 'r', encoding='utf-8') as f:
                content = f.read()
            return (
                f"Page scraped to Markdown (PDF compilation failed): {md_path}\n\n"
                f"--- Content ---\n\n{content}"
            )
    except Exception as e:
        return f"Error processing page: {str(e)}"

@mcp.tool()
def read_saved_file(path: str) -> str:
    """
    Reads a previously saved Markdown file and returns its contents.
    Useful when you've scraped a page but the content wasn't fully returned,
    or to re-read a file from a previous session.

    Args:
        path: Absolute or relative path to the Markdown file (e.g. 'markdown_output/bi-osy/zkouska/example.md').
    """
    try:
        # Resolve relative paths against the project root
        if not os.path.isabs(path):
            base = os.path.dirname(os.path.abspath(__file__))
            path = os.path.join(base, path)
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()
        return f"--- {path} ---\n\n{content}"
    except Exception as e:
        return f"Error reading file: {str(e)}"

@mcp.resource("markdown://{path}")
def markdown_resource(path: str) -> str:
    """
    Reads a saved Markdown file by path. The path should be relative to the project root
    (e.g. 'markdown_output/bi-osy/zkouska/example.md').

    Args:
        path: Relative path to the Markdown file.
    """
    try:
        base = os.path.dirname(os.path.abspath(__file__))
        full_path = os.path.join(base, path)
        # Safety: prevent directory traversal
        full_path = os.path.normpath(full_path)
        if not full_path.startswith(os.path.normpath(base)):
            return "Access denied: path outside project directory."
        with open(full_path, 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        return f"File not found: {path}"
    except Exception as e:
        return f"Error reading file: {str(e)}"

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
    transport = os.getenv("MCP_TRANSPORT", "stdio")
    mcp.run(transport=transport)
