# Antigravity Rules - Course Portals & Wiki Integration

You have access to two specialized Model Context Protocol (MCP) servers: `courses` and `fitwiki`. When researching course materials, follow this comprehensive prioritization, workflow, and execution guide.

---

## 1. Portal Prioritization Matrix

Always determine the query target before calling any tools or resources:

| Content Type | Primary Server | Secondary Server / Backup |
| :--- | :--- | :--- |
| **Official requirements, grading, exam criteria** | `courses` (Official) | None |
| **Lecture slides, official labs, announcements** | `courses` (Official) | None |
| **Past exam variants, exam answers, test history** | `fitwiki` (Student-run) | None |
| **Student-written solutions, homework assignments** | `fitwiki` (Student-run) | None |
| **Study guides, cheat sheets, community tips** | `fitwiki` (Student-run) | `courses` (for reference) |

---

## 2. Official Portal (`courses`) - Official Source

### Role & Purpose:
`courses` (querying `courses.fit.cvut.cz`) is the **official source** for all course-related information. It contains authoritative details regarding course requirements, lecture slides, official laboratory sheets, grading/classification criteria, announcements, and structural syllabus.

### Available Tools:
1. `list_courses(cookies)`: Lists subjects/courses available at FIT CTU. Highlights current enrollment when authenticated.
2. `get_course_index(course_code)`: Retrieves the course homepage sidebar navigation menu, returning paths and titles.
3. `get_page_content(course_code, page_path)`: Fetches a specific course subpage and returns its main body as clean Markdown.
4. `search_course_content(course_code, query)`: Searches all subpages of a course for keyword query using local caches.
5. `login(username, password)`: Performs OAuth handshake, logs in, and persists retrieved cookies in the local `.env` file.

### Available Resources:
- `courses://list`: Lists all subjects.
- `courses://{course_code}/index`: Exposes the navigation menu/sidebar for a subject.
- `courses://{course_code}/pages/{page_path*}`: Exposes the content of a specific course subpage.

### Common Workflow Chaining:
- **Retrieve Specific Page Content:**
  `list_courses()` $\rightarrow$ verify course code $\rightarrow$ `get_course_index(course_code)` $\rightarrow$ identify target page path $\rightarrow$ `get_page_content(course_code, page_path)`.
- **Search Subject Matter:**
  `search_course_content(course_code, query)` $\rightarrow$ examine matching snippets $\rightarrow$ `get_page_content(course_code, page_path)` for complete context.
- **Handling Authentication Failures:**
  If a call returns unauthenticated or missing content, locate `.env` settings or invoke `login(username, password)` to establish cookies.

---

## 3. Student Wiki (`fitwiki`) - Student-Run Portal

### Role & Purpose:
`fitwiki` (querying `fit-wiki.cz`) is a **student-run community wiki** used for sharing unofficial study materials, past exam variants (exam papers/tasks from previous years), student-written solutions, homework assignments, study guides, and community tips.

### Available Tools:
1. `list_courses(cookies)`: Lists all FIT ČVUT subjects documented on the student wiki.
2. `list_course_sections(course_code_or_url)`: Lists categories/material types (e.g., `zkouska`, `test1`, `ukoly`) for a course.
3. `list_section_pages(course_code_or_url, sections)`: Lists individual pages (exam dates, test variants) within a section, providing local file paths and source URLs.
4. `scrape_page(url, category, title)`: Scrapes a single wiki page, converts it to Markdown, saves it to disk, and returns the contents.
5. `download_page(url, category, title)`: Scrapes the page, converts to Markdown, compiles a PDF document, and returns paths and markdown content.
6. `scrape_course(index_path_or_url, categories)`: Downloads/scrapes all pages in chosen categories in one fast batch.
7. `scrape_index(index_path_or_url)`: Parses a course index page to list all categories, URLs, and filenames before scraping.
8. `read_saved_file(path)`: Re-reads a previously cached/scraped Markdown file. Lists directory files if target is missing.
9. `compile_pdf(markdown_path, pdf_path)`: Compiles an offline Markdown file into a PDF.
10. `compile_category_pdfs(category)`: Compiles all scraped pages in a category folder to PDFs in batch.

### Available Resources:
- `fitwiki://list`: Lists all subjects on the wiki.
- `fitwiki://{course_code}/sections`: Exposes sections for a course.
- `fitwiki://{course_code}/sections/{section}`: Lists pages in a specific section.
- `fitwiki://{course_code}/sections/{section}/{slug}`: Exposes the contents of a saved/cached page.

### Common Workflow Chaining:
- **Discovering & Scraping Exam Materials:**
  `list_courses()` $\rightarrow$ `list_course_sections(course_code)` $\rightarrow$ `list_section_pages(course_code, "zkouska")` $\rightarrow$ Check if local path exists $\rightarrow$ If cached, `read_saved_file(path)` $\rightarrow$ If not cached, `scrape_page(url, "zkouska", title)`.
- **Batch Scrape & PDF Generation:**
  `list_course_sections(course_code)` $\rightarrow$ `scrape_course(course_code, "zkouska,test1")` $\rightarrow$ `compile_category_pdfs("zkouska")`.

---

## 4. Execution Rules

- **Silent Operations:** Run all tool and resource actions silently. Do NOT explain what tools/resources you are using, why you are calling them, or describe their parameters to the user prior to execution.
- **Smart Caching Policy:** Check for existing offline Markdown files using `read_saved_file` (or path validation) before performing live scrapes. Do not repeat network requests for already saved materials.
- **Automatic Continuation:** If a tool/resource output links to other directories or pages of interest, proceed with the relevant calls immediately without asking for user permission at each step.

