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
  - [config.py](fitwiki/config.py): `ScraperConfig` manages configuration loading from environment variables, `.env` files, or raw cookie strings.
  - [scraper.py](fitwiki/scraper.py): `FitWikiScraper` handles subject index parsing, HTML caching, DOM sanitization (stripping navigation, modals, and comment sections), high-resolution image downloading, and Markdown generation. It automatically replaces DokuWiki LaTeX image tags with original text formulas in the image alt attributes to make math readable for LLMs.
  - [pdf.py](fitwiki/pdf.py): `FitWikiPDFCompiler` processes tables and code blocks, registers Liberation Sans fonts, and compiles Markdown into clean, lightweight PDFs.

- **CLI Scripts:**
  - [index_page.py](index_page.py): Downloads the course index page to `index-page.html` using the configured authentication.
  - [scraper.py](scraper.py): Interactive console downloader. It prompts the user to select specific course categories and processes them into Markdown files.
  - [convert_to_pdf.py](convert_to_pdf.py): Compiles all downloaded Markdown files in `markdown_output/` into PDF files in `pdfs/`.

- **MCP Server:**
  - [mcp_server.py](mcp_server.py): Implements a FastMCP server, exposing the scraping and compilation features as tools for LLM integration.

---

## 3. Configuration and Authentication

Authorized access is required to scrape content from Fit-Wiki. The scraper configuration supports two credentials lookup methods:
1. **Using `.env` file (recommended):** Create a `.env` file in the root directory specifying your cookies:
   ```env
   FITWIKI_COOKIES="DokuWiki=your_session_id; DW7fa...=your_auth_token"
   ```
2. **Using environment variables:** Expose the cookies directly using `FITWIKI_COOKIES` environment variable.

---

## 4. CLI Pipeline Usage

Follow this workflow to scrape and compile a course manually via CLI:

1. **Run the interactive scraper:**
   ```bash
   ./scraper.py [course_code]
   ```
   - If `index-page.html` is not found, the script will prompt you for the course code (default: `bi-osy`) and download the index page automatically.
   - You can force download/refresh a specific course index by passing its code as an argument (e.g., `./scraper.py bi-pst`).
   - Choose the categories you wish to download (e.g., `1,2` or `all`). The generated Markdown files and downloaded media are saved to the `markdown_output/` directory.

2. **Export Markdown to PDF:**
   ```bash
   ./convert_to_pdf.py
   ```
   This compiles all downloaded Markdown documents to PDF files inside the `pdfs/` directory under their corresponding categories.

---

## 5. MCP Server Configuration

To connect this workspace as a tool provider for LLM clients, add the server configuration using one of the configurations below.

> **Authentication note:** The MCP server reads cookies from the `.env` file in the project directory (recommended). If you prefer to pass them directly via the client config, use the `env` block shown below. Either approach works — you do not need both.

### For Claude Desktop
Add the server configuration to your `claude_desktop_config.json` (usually located at `~/.config/Claude/claude_desktop_config.json` on Linux):

```json
{
  "mcpServers": {
    "fitwiki": {
      "command": "/path/to/fitwiki/venv/bin/python",
      "args": ["/path/to/fitwiki/mcp_server.py"],
      "env": {
        "FITWIKI_COOKIES": "DokuWiki=your_session_id; DW7fa...=your_auth_token"
      }
    }
  }
}
```

### For Google Antigravity (AGY)
Add the server configuration to your Antigravity MCP configuration file (`~/.gemini/antigravity-cli/mcp_config.json`):

```json
{
  "mcpServers": {
    "fitwiki": {
      "command": "/path/to/fitwiki/venv/bin/python",
      "args": ["/path/to/fitwiki/mcp_server.py"]
    }
  }
}
```

> If you have not set up a `.env` file, pass cookies directly:
> ```json
> {
>   "mcpServers": {
>     "fitwiki": {
>       "command": "/path/to/fitwiki/venv/bin/python",
>       "args": ["/path/to/fitwiki/mcp_server.py"],
>       "env": {
>         "FITWIKI_COOKIES": "DokuWiki=your_session_id; DW7fa...=your_auth_token"
>       }
>     }
>   }
> }
> ```

After saving the file, **restart the Antigravity CLI** (`agy`) for the MCP server to be picked up. You can verify it loaded correctly by running `/mcp` in the chat.

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
