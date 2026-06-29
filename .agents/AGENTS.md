# Fit-Wiki Agent Workflow Rules

These instructions guide how AI agents should interact with the user and the codebase when discussing subjects, exams, or test materials in this workspace.

## 1. Context and Tools
- This workspace contains a Fit-Wiki scraper and PDF compiler, integrated as an MCP server.
- **CRITICAL:** Do NOT read, parse, or analyze the python files (e.g., `mcp_server.py`, `scraper.py`, `index_page.py`, `fitwiki/scraper.py`, `fitwiki/pdf.py`) to understand how to scrape or compile. The workspace has custom pre-registered MCP tools. Use them directly.
- **CRITICAL:** MCP tools are **native agent tools** — they appear in your tool list just like `view_file` or `list_dir`. Call them directly. Do NOT try to invoke them via Bash, `run_command`, or any shell command. Do NOT try `./venv/bin/python -m fitwiki ...` or similar.
- **How to detect if MCP is available:** Check your active tool list. If you see `list_course_sections`, `download_page`, etc. as callable tools — use them. If they are absent from your tool list — follow Section 4 (Fallback).
- **Exposed MCP Tools** (callable as native agent tools, not shell commands):
  - `list_courses`: Lists all subjects and courses available on the Fit-Wiki.
  - `list_course_sections`: Lists sections and categories (e.g., 'zkouska', 'test1') for a given subject.
  - `list_section_pages`: Lists individual pages and exam terms in specific course sections.
  - `download_page`: Scrapes a single page to Markdown and compiles it to PDF in one action.
  - `compile_pdf`: Compiles a specified Markdown file into a lightweight PDF.
  - `compile_category_pdfs`: Compiles all Markdown files inside a category folder to PDFs.

## 2. Directory Structure
- `cache/`: Local HTML files cache.
- `markdown_output/<course_code>/<category>/`: Converted markdown files, grouped first by course code (e.g., `bi-osy`), then by category (e.g., `zkouska`). Example: `markdown_output/bi-osy/zkouska/`.
- `pdfs/<course_code>/<category>/`: Compiled PDF files using the same nested structure. Example: `pdfs/bi-osy/zkouska/`.

## 3. Resolving Course & Exam Queries
If the user asks about a course or exam questions (e.g., "Co bylo na zkoušce z BI-PA1?"):
1. **Identify the Course Code:** E.g., `BI-PA1` → `bi-pa1`, `bi-pai` → `bi-pai`.
2. **List Sections:** Call `list_course_sections` with the course code.
3. **List Pages in Section:** Call `list_section_pages` for the relevant section (typically `zkouska` for exams).
4. **Locate Downloaded Markdown:** Check if the corresponding `.md` file is already in `markdown_output/<course_code>/<category>/`.
   - If yes: read it using `view_file` to answer the question directly.
   - If no: call `download_page` for the term to fetch the content, and then read the generated Markdown file to answer the user.
5. **LaTeX Math:** When explaining math formulas from the wiki, refer to the LaTeX formulas embedded in the Markdown image alt attributes (e.g., `![formula](...)`).
6. **DO NOT write custom python scripts or run raw curl commands to download or scrape pages.** Always use the MCP tools.
7. **Proactively offer completeness:** When a user requests downloading or discussing a specific exam term, check if there are other terms in the same section (using `list_section_pages`). Proactively offer to download or list the other related terms so the user has the complete set of study materials.

## 4. Fallback if MCP Tools are Missing
**How to detect:** If `list_course_sections`, `download_page`, and similar tools are NOT listed in your available tools — the MCP server is not running. Do NOT try to figure out why by reading source files.

If the MCP tools are NOT present in your active tool declaration list, follow this exact sequence:

**Step 1 — Immediately notify the user** (one sentence max):
> "The `fitwiki` MCP server is not running. To enable it, add the config from `~/.gemini/antigravity-cli/mcp_config.json` to your client settings and restart."

**Step 2 — Answer immediately using the CLI fallback** (do NOT explore the codebase first):
- Check if `markdown_output/<course_code>/` already has the relevant `.md` files using `list_dir`.
- If files exist: read them with `view_file` and answer the user directly.
- If files are missing: run `echo "all" | ./venv/bin/python scraper.py <course_code>` via Bash to download them, then read the resulting markdown.

**STRICT PROHIBITIONS in fallback mode:**
- Do NOT read `README.md`, `scraper.py`, `index_page.py`, `mcp_server.py`, or any other `.py` file.
- Do NOT run `pip list`, `find`, or any other environment audit command.
- Do NOT list the root workspace directory before acting.
- Go directly to Step 2 without any exploration.
