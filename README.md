# Fit-Wiki Scraper & MCP Server

Python tool for extracting course materials, exam variants, and notes from Fit-Wiki. Includes an MCP server for integration with LLM clients (Claude, AGY, OpenCode).

---

## Requirements

- Python 3.12+
- Liberation Sans and Liberation Mono fonts (for correct Czech diacritics in PDFs)

## Setup

```bash
python3 -m venv venv
./venv/bin/pip install -r requirements.txt
```

## Configuration

Copy [`.env.example`](.env.example) to `.env` and fill in your cookies:

```bash
cp .env.example .env
```

Alternatively, pass `FITWIKI_COOKIES` as an environment variable in the MCP client config.

---

## CLI Usage

### Scrape a course to Markdown

```bash
./venv/bin/python scraper.py [course_code]
```

### Convert Markdown to PDF

```bash
./venv/bin/python convert_to_pdf.py
```

Compiles all files in `markdown_output/` to `pdfs/`.

### Pipeline (single page)

```bash
./venv/bin/python index_page.py bi-osy            # download index
./venv/bin/python scraper.py                      # scrape to Markdown
./venv/bin/python convert_to_pdf.py               # compile PDFs
```

---

## MCP Server

The MCP server exposes Fit-Wiki tools to LLM clients. It runs via stdio or streamable-http.

### Client Configuration

Add the following to your client's MCP config file. Cookies are loaded from the `.env` file (see [`.env.example`](.env.example)).

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

Restart the client after saving. For AGY, verify with `/mcp` in chat.

### Transports

- **stdio** (default) – the client spawns the server as a subprocess. Use for Claude Desktop, AGY, OpenCode.
- **streamable-http** – for Docker or remote setups. Set `MCP_TRANSPORT=streamable-http` and point the client to `http://host:8000/mcp`.

---

## Docker

### Build & Run

```bash
docker compose up -d
```

The container exposes the MCP server on port 8000 via streamable-http. Mounted volumes persist `markdown_output/` and `pdfs/` on the host.

### GitHub Container Registry

The Docker image is built automatically on push (see `.github/workflows/docker-build.yml`) and published to `ghcr.io/<your-username>/fitwiki-mcp`. Tags: `latest`, `master`, short SHA.

---

## Exposed MCP Tools

- `list_courses` – List all courses on the FIT platform.
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

- `fitwiki://list`: Returns the list of subjects/courses documented on the student wiki.
- `fitwiki://{course_code}/sections`: Returns the sections/categories for a given course.
- `fitwiki://{course_code}/sections/{section}`: Returns the pages in a specific section.
- `fitwiki://{course_code}/sections/{section}/{slug}`: Returns the content of a saved markdown page.
