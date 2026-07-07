import os
import re
import urllib.parse
import unicodedata
from typing import List, Dict, Any, Optional

from .config import FitWikiConfig
from .scraper import FitWikiScraper
from .pdf import FitWikiPDFCompiler


class FitWikiClient:
    """
    Client orchestrating all operations for Fit-Wiki, including scraping,
    categorization, listing, and compiling Markdown/PDF files.
    """
    def __init__(self, config: Optional[FitWikiConfig] = None):
        self.config = config or FitWikiConfig.from_env()
        self.scraper = FitWikiScraper(self.config)
        self.pdf_compiler = FitWikiPDFCompiler(self.config)

    def set_cookies(self, cookies_str: str):
        """
        Parses cookie string and updates config/scraper/compiler.
        """
        self.config.cookies_str = cookies_str
        self.config.cookies = {}
        if cookies_str:
            for item in cookies_str.split(';'):
                item = item.strip()
                if '=' in item:
                    k, v = item.split('=', 1)
                    self.config.cookies[k.strip()] = v.strip()

    def _resolve_url(self, code_or_url: str) -> str:
        """Resolves a course code or absolute URL into a full DokuWiki URL."""
        if code_or_url.startswith("http"):
            return code_or_url
        return f"{self.config.base_url}/škola/předměty/{code_or_url.lower()}"

    def _page_slug(self, url: str) -> str:
        """Converts a page URL to its filename slug."""
        parsed = urllib.parse.urlparse(url.lower())
        _, ext = os.path.splitext(parsed.path)
        is_attachment = ('fetch.php' in url.lower() or 
                         'media=' in url.lower() or 
                         '_media/' in url.lower() or 
                         '_detail/' in url.lower() or 
                         ext in ['.pdf', '.zip', '.tar', '.gz', '.rar', '.7z', '.png', '.jpg', '.jpeg', '.docx', '.xlsx', '.pptx'])
                         
        if is_attachment:
            parsed_orig = urllib.parse.urlparse(url)
            query = urllib.parse.parse_qs(parsed_orig.query)
            media_id = query.get('media', [''])[0]
            if not media_id:
                media_id = query.get('id', [''])[0]
            if not media_id:
                media_id = parsed_orig.path.split('/')[-1]
            filename = urllib.parse.unquote(media_id.split(':')[-1])
            slug, _ = os.path.splitext(filename)
            slug = re.sub(r'[\/\\:*?"<>|]', '_', slug)
            return slug if slug else 'attachment'
            
        parsed = urllib.parse.urlparse(url)
        decoded = urllib.parse.unquote(parsed.path)
        nfd = unicodedata.normalize('NFD', decoded)
        unaccented = "".join(c for c in nfd if unicodedata.category(c) != 'Mn')
        name = unaccented.strip('/')
        if parsed.query:
            name += '_' + parsed.query
        slug = re.sub(r'[^a-zA-Z0-9_\-]', '_', name)
        return slug if slug else 'index'

    def _extract_course_code(self, url: str) -> str:
        """Extracts the course code from a Fit-Wiki URL."""
        parsed = urllib.parse.urlparse(url)
        path = parsed.path
        parts = [p for p in path.split('/') if p]
        for i, part in enumerate(parts):
            decoded = urllib.parse.unquote(part).lower()
            nfd = unicodedata.normalize('NFD', decoded)
            unaccented = "".join(c for c in nfd if unicodedata.category(c) != 'Mn')
            if unaccented in ['predmety', 'subjects'] and i + 1 < len(parts):
                return urllib.parse.unquote(parts[i+1]).lower().split('_')[0].split(':')[0]
        return ""

    def list_courses(self) -> List[Dict[str, str]]:
        """Lists all subjects/courses taught at FIT."""
        return self.scraper.get_courses()

    def list_course_sections(self, course_code_or_url: str) -> List[Dict[str, Any]]:
        """Lists all material sections/categories (e.g. 'zkouska', 'test1') for a given subject."""
        url = self._resolve_url(course_code_or_url)
        html = self.scraper._get_page_html(url)
        links = self.scraper.scrape_index(html)
        if not links:
            return []
            
        sections_map = {}
        for l in links:
            cat = l['category']
            sections_map[cat] = sections_map.get(cat, 0) + 1
            
        return [{'name': name, 'count': count} for name, count in sorted(sections_map.items())]

    def list_section_pages(self, course_code_or_url: str, sections: str) -> List[Dict[str, str]]:
        """Lists all pages within specific sections of a course."""
        url = self._resolve_url(course_code_or_url)
        html = self.scraper._get_page_html(url)
        links = self.scraper.scrape_index(html)
        if not links:
            return []
            
        if course_code_or_url.startswith("http"):
            course_code = self._extract_course_code(course_code_or_url) or course_code_or_url
        else:
            course_code = course_code_or_url.lower()
            
        filter_sections = [s.strip().lower() for s in sections.split(',')]
        filtered_links = [l for l in links if l['category'] in filter_sections]
        
        pages = []
        for l in filtered_links:
            slug = self._page_slug(l['url'])
            md_path = f"markdown_output/{course_code}/{l['category']}/{slug}.md"
            pages.append({
                'category': l['category'],
                'title': l['title'],
                'url': l['url'],
                'path': md_path
            })
        return pages

    def scrape_index(self, index_path_or_url: str) -> List[Dict[str, str]]:
        """Parses a course index page and lists discovered pages with category, URL, title."""
        if os.path.exists(index_path_or_url):
            with open(index_path_or_url, 'r', encoding='utf-8') as f:
                html_content = f.read()
        else:
            html_content = self.scraper._get_page_html(index_path_or_url)
            
        return self.scraper.scrape_index(html_content)

    def _clean_title(self, title: str, category: str, url: str) -> str:
        """Enhances title if it is just a number or very short, appending semester details from URL if present."""
        title = title.strip()
        slug = self._page_slug(url)
        
        # Extract semester/year from slug if present (e.g., _zs1819 or _ls2021)
        sem_str = ""
        sem_match = re.search(r'_(zs|ls)(\d{2})(\d{2})$', slug.lower())
        if sem_match:
            sem_type = sem_match.group(1).upper()
            yr1 = sem_match.group(2)
            yr2 = sem_match.group(3)
            sem_str = f"{sem_type} {yr1}/{yr2}"

        # If title is just a semester code like "zs1112"
        if re.match(r'^(zs|ls)\d{4}$', title.lower()) and sem_str:
            return sem_str
            
        if title.isdigit() or len(title) <= 3:
            nice_categories = {
                'zkouska': 'Zkouška',
                'test1': 'Test 1',
                'test2': 'Test 2',
                'test-a': 'Test A',
                'testy': 'Test',
                'ostatni': 'Ostatní',
                'ukoly-1': 'Úkol 1',
                'ukoly-2': 'Úkol 2',
                'ukoly-3': 'Úkol 3',
                'ukoly': 'Úkol',
                'semestralky': 'Semestrální práce',
                'cviceni': 'Cvičení',
                'prednasky': 'Přednáška'
            }
            cat_name = nice_categories.get(category.lower(), category.capitalize())
            base_title = f"{cat_name} - {title}" if not title.startswith(cat_name) else title
            if sem_str:
                return f"{base_title} ({sem_str})"
            return base_title
            
        # If title is already a descriptive title but we have semester info, append it if not already present
        if sem_str and sem_str.lower() not in title.lower():
            return f"{title} ({sem_str})"
            
        return title

    def scrape_page(self, url: str, category: str, title: str, course_code: Optional[str] = None) -> str:
        """Scrapes a single DokuWiki page, converts it to Markdown, and returns the MD path."""
        title = self._clean_title(title, category, url)
        return self.scraper.scrape_page(url, category, title, course_code=course_code)

    def download_page(self, url: str, category: str, title: str, compile_pdf: bool = True, course_code: Optional[str] = None) -> Dict[str, Any]:
        """Scrapes a page to Markdown, compiles it to PDF, and returns both paths + content."""
        title = self._clean_title(title, category, url)
        
        # Check if URL is a DokuWiki media attachment or has a binary extension
        parsed = urllib.parse.urlparse(url.lower())
        _, ext = os.path.splitext(parsed.path)
        is_attachment = ('fetch.php' in url or 
                         'media=' in url or 
                         '_media/' in url or 
                         '_detail/' in url or 
                         ext in ['.pdf', '.zip', '.tar', '.gz', '.rar', '.7z', '.png', '.jpg', '.jpeg', '.docx', '.xlsx', '.pptx'])
                         
        if is_attachment:
            return self._download_attachment(url, category, title, course_code=course_code)
            
        # 1. Scrape to Markdown
        md_path = self.scraper.scrape_page(url, category, title, course_code=course_code)
        
        pdf_success = False
        pdf_path = ""
        if compile_pdf:
            # 2. Compile to PDF (preserving the same nested folder structure under pdf_dir)
            rel_md_path = os.path.relpath(md_path, self.config.markdown_dir)
            pdf_rel_path = rel_md_path.replace('.md', '.pdf')
            pdf_path = os.path.join(self.config.pdf_dir, pdf_rel_path)
            os.makedirs(os.path.dirname(pdf_path), exist_ok=True)
            pdf_success = self.pdf_compiler.compile_file(md_path, pdf_path)
        
        # Read content
        with open(md_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        return {
            'markdown_path': md_path,
            'pdf_path': pdf_path if pdf_success else "",
            'content': content,
            'pdf_success': pdf_success
        }

    def _download_attachment(self, url: str, category: str, title: str, course_code: Optional[str] = None) -> Dict[str, Any]:
        parsed = urllib.parse.urlparse(url)
        query = urllib.parse.parse_qs(parsed.query)
        media_id = query.get('media', [''])[0]
        
        if not media_id:
            media_id = parsed.path.split('/')[-1]
            
        filename = urllib.parse.unquote(media_id.split(':')[-1])
        
        # Safe slug for md placeholder
        slug = self._page_slug(url)
        
        course_code = course_code or self.scraper._extract_course_code(url)
        
        md_dir = os.path.join(self.config.markdown_dir, course_code, category)
        pdf_dir = os.path.join(self.config.pdf_dir, course_code, category)
        os.makedirs(md_dir, exist_ok=True)
        os.makedirs(pdf_dir, exist_ok=True)
        
        import requests
        # Download attachment using configured headers/cookies
        response = requests.get(url, cookies=self.config.cookies, headers=self.config.headers, timeout=15)
        response.raise_for_status()
        
        is_pdf = filename.lower().endswith('.pdf')
        pdf_path = ""
        
        if is_pdf:
            md_path = os.path.join(md_dir, f"{slug}.md")
            pdf_path = os.path.join(pdf_dir, f"{slug}.pdf")
            with open(pdf_path, 'wb') as f:
                f.write(response.content)
                
            placeholder_content = f"# {title}\n\nSource: [{url}]({url})\n\n---\n\nTento dokument je PDF příloha stažená z wiki.\n"
            with open(md_path, 'w', encoding='utf-8') as f:
                f.write(placeholder_content)
                
            return {
                'markdown_path': md_path,
                'pdf_path': pdf_path,
                'content': placeholder_content,
                'pdf_success': True,
                'is_attachment': True
            }
        else:
            # Non-PDF attachments go directly into md_dir with their raw filename (no md placeholder)
            attachment_path = os.path.join(md_dir, filename)
            with open(attachment_path, 'wb') as f:
                f.write(response.content)
                
            return {
                'markdown_path': "",
                'pdf_path': "",
                'content': "",
                'pdf_success': False,
                'attachment_path': attachment_path,
                'is_attachment': True
            }
                

    def scrape_course(self, index_path_or_url: str, categories: str = "all") -> Dict[str, Any]:
        """Downloads all pages in selected categories in one batch."""
        if os.path.exists(index_path_or_url):
            with open(index_path_or_url, 'r', encoding='utf-8') as f:
                html_content = f.read()
        else:
            html_content = self.scraper._get_page_html(index_path_or_url)

        links = self.scraper.scrape_index(html_content)
        if not links:
            return {'scraped': [], 'skipped': [], 'failed': []}

        # Parse selected categories
        selected = []
        if categories.strip().lower() != "all":
            selected = [c.strip().lower() for c in categories.split(',')]

        scraped = []
        skipped = []
        failed = []

        for l in links:
            cat = l['category']
            if selected and cat not in selected:
                skipped.append(l)
                continue

            cleaned_title = self._clean_title(l['title'], cat, l['url'])
            try:
                md_path = self.scraper.scrape_page(l['url'], cat, cleaned_title)
                scraped.append({'title': cleaned_title, 'path': md_path, 'category': cat})
            except Exception as e:
                failed.append({'title': cleaned_title, 'error': str(e), 'category': cat})

        return {
            'scraped': scraped,
            'skipped': skipped,
            'failed': failed
        }

    def compile_pdf(self, markdown_path: str, pdf_path: str) -> bool:
        """Compiles a specific Markdown file to PDF."""
        return self.pdf_compiler.compile_file(markdown_path, pdf_path)

    def compile_category_pdfs(self, category: str) -> List[str]:
        """Compiles all Markdown files in a category folder to PDFs."""
        return self.pdf_compiler.compile_category(category)

    def read_saved_file(self, path: str) -> Dict[str, Any]:
        """Re-reads a previously saved Markdown file or lists available files if missing."""
        if not os.path.isabs(path):
            base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            path = os.path.join(base, path)

        if os.path.isfile(path):
            with open(path, 'r', encoding='utf-8') as f:
                content = f.read()
            return {'found': True, 'content': content, 'path': path}

        # List directory contents if file not found
        dir_path = os.path.dirname(path) if os.path.dirname(path) else os.path.dirname(os.path.abspath(__file__))
        md_files = []
        if os.path.isdir(dir_path):
            files = sorted(os.listdir(dir_path))
            md_files = [f for f in files if f.endswith('.md')]
            
        return {
            'found': False,
            'path': path,
            'directory': dir_path,
            'available_files': md_files[:50]
        }
