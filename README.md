# FitWiki MCP Server

An MCP (Model Context Protocol) server designed for the student-run Faculty of Information Technology, Czech Technical University (FIT CTU) community wiki: fit-wiki.cz.

It enables LLMs (such as Claude, AGY, or Open WebUI) to list subjects documented on the student wiki, navigate their sections (exams, tests, homework), download pages and attachments, and read study materials converted to clean Markdown.

---

## Features

- **Automated Scraping & Sanitization:** Downloads community wiki pages, handles media/image assets, and converts the content into readable, clean Markdown.
- **Direct Attachment Handling:** Intercepts binary attachments (like ZIPs, RARs, PDFs) and downloads them natively, bypassing markdown wrappers.
- **Document Compiling:** Compiles scraped Markdown pages into high-quality offline PDF documents.
- **Intelligent Cache & Category Detection:** Automatically groups wiki pages into categories (exams, tests, labs) using advanced namespace mapping and maintains a local cache to avoid redundant requests.

---

## Installation

1. Clone or copy this repository into your chosen directory.
2. Initialize the Python virtual environment and install the required dependencies:
   ```bash
   python3 -m venv venv
   ./venv/bin/pip install -r requirements.txt
   ```

---

## Configuration

Duplicate the `.env.example` file to `.env` and set up your preferred authentication method:

```env
# Set session cookie for authenticating private/enrolled subjects
FITWIKI_COOKIES="DokuWiki=your-cookie-value"

# Optional configuration overrides
# FITWIKI_BASE_URL="https://fit-wiki.cz"
# FITWIKI_DELAY=1.0
```

---

## CLI Usage

You can run the scraper directly from the command line using the provided scripts:

### 1. Scrape a Course to Markdown
```bash
./venv/bin/python scraper.py [course_code]
```
If you provide a course code (e.g. `bi-osy`), the scraper downloads the index page, parses it, and lets you choose categories to scrape. If run without arguments, it attempts to read an existing `index-page.html` from the workspace.

### 2. Convert Markdown to PDF
```bash
./venv/bin/python convert_to_pdf.py
```
Compiles all downloaded markdown pages under `markdown_output/` into PDF files in the `pdfs/` directory.

---

## MCP Server Setup

The MCP server exposes Fit-Wiki tools to LLM clients. It runs via stdio or streamable-http.

### Client Configuration

Add the following to your client's MCP configuration file. Cookies are loaded from the `.env` file (see [`.env.example`](.env.example)).

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

### Config File Locations

| Client | Path |
|---|---|
| Claude Desktop | `~/.config/Claude/claude_desktop_config.json` |
| AGY (CLI) | `~/.gemini/antigravity-cli/mcp_config.json` |
| AGY (IDE / 2.0) | `~/.gemini/config/mcp_config.json` |
| OpenCode | `.opencode.json` in the workspace root |

Restart the client after saving.

### Transports

- **stdio** (default) – the client spawns the server as a subprocess. Use for Claude Desktop, AGY, OpenCode.
- **streamable-http** – for Docker or remote setups. Set `MCP_TRANSPORT=streamable-http` and point the client to `http://host:8000/mcp`.

---

## Exposed MCP Tools

- `list_courses` – List all courses documented on the student wiki.
- `list_course_sections` – List sections (e.g. `zkouska`, `test1`) for a course.
- `list_section_pages` – List pages within specific sections.
- `download_page` – Scrape a page to Markdown and compile to PDF in one step.
- `compile_pdf` – Compile a Markdown file to PDF.
- `compile_category_pdfs` – Compile all Markdown files in a category to PDFs.
- `read_saved_file` – Read a previously saved Markdown file by path.
- `scrape_index` – Parse a course index and list discovered links.
- `scrape_page` – Scrape a single page to Markdown and return its content.
- `scrape_course` – Download all pages in selected categories for a course.

---

## Exposed MCP Resources

The server exposes the following read-only resources:

- `fitwiki://list` – Returns the list of subjects/courses documented on the student wiki.
- `fitwiki://{course_code}/sections` – Returns the sections/categories for a given course.
- `fitwiki://{course_code}/sections/{section}` – Returns the pages in a specific section.
- `fitwiki://{course_code}/sections/{section}/{slug}` – Returns the content of a saved markdown page.
