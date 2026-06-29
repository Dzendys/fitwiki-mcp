# Fit-Wiki Agent Workflow Rules

These instructions guide how AI agents should interact with the user and the codebase when discussing subjects, exams, or test materials in this workspace.

## 1. Context and Tools
- This workspace contains a Fit-Wiki scraper and PDF compiler, integrated as an MCP server in [mcp_server.py](mcp_server.py).
- Use the MCP tools (`list_courses`, `list_course_sections`, `list_section_pages`, `download_page`, `compile_pdf`, `compile_category_pdfs`) whenever the user asks about courses, topics, exam terms, or test materials.

## 2. Interactive Workflow
- **Subject Mention:** When the user mentions a subject code (e.g., "bi-osy", "osy", "bi-pst"), check if the course sections are already discovered. If not, use `list_course_sections` to fetch them and list categories like `zkouska` (exams) or `test1`/`test2` (term tests) to guide the user.
- **Exam / Test Mentions:** When the user asks about a specific exam variant or term (e.g., "termín z 26.5.2023"):
  1. Check if the page's Markdown file is already downloaded under `markdown_output/<category>/<page_slug>.md`.
  2. If found, read its content to answer the user's questions.
  3. If not found, **proactively offer to download and compile it** using the `download_page` tool.
- **Completeness Offer:** When a user requests downloading or discussing a specific exam term, check if there are other terms in the same section (using `list_section_pages`). **Proactively offer to download or list the other related terms** so the user has the complete set of study materials.
- **LaTeX Math:** When explaining math formulas from the wiki, refer to the LaTeX formulas embedded in the Markdown image alt attributes (e.g., `![formula](...)`).
