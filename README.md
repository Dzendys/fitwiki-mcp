# Fit-Wiki Scraper & PDF Compiler + MCP Server

A robust, object-oriented Python scraper and PDF compiler for extracting course materials, exam variants, and notes from the Fit-Wiki platform. It includes a Model Context Protocol (MCP) server for seamless integration with LLM clients (such as Claude Desktop), enabling them to search, download, and compile wiki pages directly.

---

## 1. System Requirements and Installation

The tool requires Python 3.x and the system fonts **Liberation Sans** and **Liberation Mono** to render Czech diacritics (e.g., characters like `Ř`, `ě`, `š`) correctly without formatting fallback issues in compiled PDFs.

### Install dependencies:
```bash
python3 -m venv venv
# Activate and install base packages + MCP
./venv/bin/pip install beautifulsoup4 markdownify requests markdown mcp python-dotenv
# Install xhtml2pdf and its supporting libraries
./venv/bin/pip install xhtml2pdf --no-deps
./venv/bin/pip install html5lib Pillow pypdf "reportlab<5" svglib arabic-reshaper python-bidi pyhanko asn1crypto
```

---

## 2. Project Architecture

The codebase is organized into a modular Python package `fitwiki` along with helper CLI scripts:

- **`fitwiki/` (Python Package):**
  - [config.py](file:///home/dzendys_/Downloads/fitwiki/fitwiki/config.py): `ScraperConfig` manages configuration loading from environment variables, `.env` files, or raw cookie strings.
  - [scraper.py](file:///home/dzendys_/Downloads/fitwiki/fitwiki/scraper.py): `FitWikiScraper` handles subject index parsing, HTML caching, DOM sanitization (stripping navigation, modals, and comment sections), high-resolution image downloading, and Markdown generation. It automatically replaces DokuWiki LaTeX image tags with original text formulas in the image alt attributes to make math readable for LLMs.
  - [pdf.py](file:///home/dzendys_/Downloads/fitwiki/fitwiki/pdf.py): `FitWikiPDFCompiler` processes tables and code blocks, registers Liberation Sans fonts, and compiles Markdown into clean, lightweight PDFs.

- **CLI Scripts:**
  - [index_page.py](file:///home/dzendys_/Downloads/fitwiki/index_page.py): Downloads the course index page to `index-page.html`. It automatically parses cookies and base URLs from an existing `index.sh` or local configuration.
  - [scraper.py](file:///home/dzendys_/Downloads/fitwiki/scraper.py): Interactive console downloader. It prompts the user to select specific course categories and processes them into Markdown files.
  - [convert_to_pdf.py](file:///home/dzendys_/Downloads/fitwiki/convert_to_pdf.py): Compiles all downloaded Markdown files in `markdown_output/` into PDF files in `pdfs/`.

- **MCP Server:**
  - [mcp_server.py](file:///home/dzendys_/Downloads/fitwiki/mcp_server.py): Implements a FastMCP server, exposing the scraping and compilation features as tools for LLM integration.

---

## 3. Configuration and Authentication

Authorized access is required to scrape content from Fit-Wiki. The scraper configuration supports two credentials lookup methods:
1. **Using `.env` file (recommended):** Create a `.env` file in the root directory specifying your cookies:
   ```env
   FITWIKI_COOKIES="DokuWiki=your_session_id; DW7fa...=your_auth_token"
   ```
2. **Using environment variables:** Expose the cookies directly using `FITWIKI_COOKIES` environment variable.
3. **Using `index.sh` fallback:** If no credentials are found in the environment, CLI scripts attempt to parse curl cookies from your local `index.sh` script.

---

## 4. CLI Pipeline Usage

Follow this workflow to scrape and compile a course manually via CLI:

1. **Download the course index page:**
   ```bash
   ./index_page.py
   ```
   This saves the page structure to `index-page.html`.

2. **Run the interactive scraper:**
   ```bash
   ./scraper.py
   ```
   Specify the categories you wish to download (e.g. `1,2` or `all`). The generated Markdown files and downloaded media are saved to the `markdown_output/` directory.

3. **Export Markdown to PDF:**
   ```bash
   ./convert_to_pdf.py
   ```
   The compiled PDF files are saved to the `pdfs/` directory under corresponding categories.

---

## 5. MCP Server Configuration

To connect this workspace as a tool provider for LLM clients like Claude Desktop, add the server to your configuration file (usually located at `~/.config/Claude/claude_desktop_config.json` on Linux):

```json
{
  "mcpServers": {
    "fitwiki": {
      "command": "/home/dzendys_/Downloads/fitwiki/venv/bin/python",
      "args": ["/home/dzendys_/Downloads/fitwiki/mcp_server.py"],
      "env": {
        "FITWIKI_COOKIES": "DokuWiki=your_session_id; DW7fa...=your_auth_token"
      }
    }
  }
}
```

### Exposed MCP Tools

The server registers the following tools for the LLM client:
- `list_courses`: Lists all subjects and courses available on the FIT platform.
- `list_course_sections`: Lists sections and categories (e.g. 'zkouska', 'test1') for a given subject.
- `list_section_pages`: Lists individual pages and exam terms in specific course sections.
- `download_page`: Scrapes a single page to Markdown and compiles it to PDF in one action.
- `compile_pdf`: Compiles a specified Markdown file into a lightweight PDF.
- `compile_category_pdfs`: Compiles all Markdown files inside a category folder to PDFs.
- `scrape_index`: Parses a course index page (local HTML file or URL) and lists discovered subpage links.
- `scrape_page`: Scrapes a single page to Markdown only.
- `scrape_course`: Downloads and converts all pages belonging to selected categories in a course.
