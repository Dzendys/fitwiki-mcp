# Fit-Wiki Agent Workflow Rules

These instructions guide how AI agents should interact with the user and the codebase when discussing subjects, exams, or test materials in this workspace.

## 1. Context and Tools
- This workspace contains a Fit-Wiki scraper and PDF compiler, integrated as an MCP server.
- **CRITICAL:** Do NOT read, parse, or analyze the python files (e.g., `mcp_server.py`, `scraper.py`, `index_page.py`, `fitwiki/scraper.py`, `fitwiki/pdf.py`) to understand how to scrape or compile. The workspace has custom pre-registered MCP tools. Use them directly.
- **Exposed MCP Tools:**
  - `list_courses`: Lists all subjects and courses available on the Fit-Wiki.
  - `list_course_sections`: Lists sections and categories (e.g., 'zkouska', 'test1') for a given subject.
  - `list_section_pages`: Lists individual pages and exam terms in specific course sections.
  - `download_page`: Scrapes a single page to Markdown and compiles it to PDF in one action.
  - `compile_pdf`: Compiles a specified Markdown file into a lightweight PDF.
  - `compile_category_pdfs`: Compiles all Markdown files inside a category folder to PDFs.

## 2. Directory Structure
- `cache/`: Local HTML files cache.
- `markdown_output/`: Converted markdown files grouped by category (e.g., `markdown_output/zkouska/`).
- `pdfs/`: Compiled PDF files grouped by category (e.g., `pdfs/zkouska/`).

## 3. Resolving Course & Exam Queries
If the user asks about a course or exam questions (e.g., "Co bylo na zkoušce z BI-PA1?"):
1. **Identify the Course Code:** E.g., `BI-PA1` or `bi-pai`.
2. **List Sections:** Call `list_course_sections` with the course code.
3. **List Pages in Section:** Call `list_section_pages` for the relevant section (typically `zkouska` for exams).
4. **Locate Downloaded Markdown:** Check if the corresponding `.md` file is already in `markdown_output/<category>/`.
   - If yes: read it using `view_file` to answer the question directly.
   - If no: call `download_page` for the term to fetch the content, and then read the generated Markdown file to answer the user.
5. **LaTeX Math:** When explaining math formulas from the wiki, refer to the LaTeX formulas embedded in the Markdown image alt attributes (e.g., `![formula](...)`).
6. **DO NOT write custom python scripts or run raw curl commands to download or scrape pages.** Always use the MCP tools.
7. **Proactively offer completeness:** When a user requests downloading or discussing a specific exam term, check if there are other terms in the same section (using `list_section_pages`). Proactively offer to download or list the other related terms so the user has the complete set of study materials.

## 4. Fallback if MCP Tools are Missing
If the MCP tools (such as `list_course_sections`, `download_page`, etc.) are NOT present in your active tool declaration list:
1. **Notify the User:** Inform the user that the `fitwiki` MCP server is not yet configured in their client settings, and suggest they copy the configuration block from the generated `scratch/mcp_config.json` to their `~/.gemini/antigravity-cli/settings.json` (or Claude's config) as described in `README.md`.
2. **Use CLI Scripts Fallback:** To answer the user's current query immediately, fall back to running the CLI scripts directly:
   - Run `./venv/bin/python scraper.py <course_code>` via shell to download/update files.
   - Read the resulting Markdown files in `markdown_output/` using `view_file` to extract answers.
   - Do NOT spend multiple turns inspecting python source files (like `mcp_server.py`) or running environment audits (like `pip list`). Just use the CLI scraper script directly.
