import os
import re
import time
import urllib.parse
import unicodedata
from typing import List, Dict, Any, Optional
import requests
from bs4 import BeautifulSoup
from markdownify import markdownify as md, MarkdownConverter

class FitWikiMarkdownConverter(MarkdownConverter):
    """
    Custom MarkdownConverter that preserves <table> elements as raw HTML in the Markdown file,
    ensuring that complex cells (containing blocks, lists, or multiple lines) do not break the table structure.
    """
    def convert_table(self, el, text, **kwargs):
        # Return the raw HTML representation of the table element
        return "\n\n" + str(el) + "\n\n"


from .config import ScraperConfig

class FitWikiScraper:
    """
    Robust Object-Oriented Scraper for Fit-Wiki.
    """
    def __init__(self, config: ScraperConfig):
        self.config = config
        
        # Ensure directories exist
        os.makedirs(self.config.cache_dir, exist_ok=True)
        os.makedirs(self.config.markdown_dir, exist_ok=True)

    def scrape_index(self, index_html: str) -> List[Dict[str, str]]:
        """
        Parses the index page HTML and extracts course subpage links inside .hiddenBody containers.
        Returns a list of dicts: [{'title': '...', 'url': '...', 'category': '...'}]
        """
        soup = BeautifulSoup(index_html, 'html.parser')
        links = []
        
        # Find all elements with class 'hiddenBody'
        containers = soup.find_all(class_='hiddenBody')
        if not containers:
            # Fallback: search for any page content link if hiddenBody is not found
            containers = [soup]
            
        for container in containers:
            for a_tag in container.find_all('a', href=True):
                href = a_tag['href']
                title = a_tag.get_text(strip=True)
                
                # Resolve relative URLs
                if href.startswith('/'):
                    full_url = self.config.base_url + href
                elif href.startswith('http'):
                    full_url = href
                else:
                    # Handle paths relative to the current page if needed
                    full_url = f"{self.config.base_url}/{href}"
                
                # Exclude edit/history/admin actions
                if 'do=' in full_url:
                    continue
                    
                # Check media/attachment utility links
                is_media = ('fetch.php' in full_url or 
                            'detail.php' in full_url or 
                            'media=' in full_url or 
                            '_media/' in full_url or
                            '_detail/' in full_url)
                            
                if is_media:
                    # Keep only if it belongs to a valid course code namespace (not 'ostatni')
                    course_code = self._extract_course_code(full_url)
                    if course_code == 'ostatni':
                        continue
                elif 'id=' not in full_url and 'fit-wiki.cz' not in full_url:
                    continue
                
                # Categorize page based on URL patterns
                category = self.categorize_url(full_url)
                
                links.append({
                    'title': title,
                    'url': full_url,
                    'category': category
                })
                
        # Remove duplicates preserving order
        seen = set()
        unique_links = []
        for l in links:
            if l['url'] not in seen:
                seen.add(l['url'])
                unique_links.append(l)
                
        return unique_links

    def categorize_url(self, url: str) -> str:
        """
        Dynamically detects material category based on URL namespace patterns,
        grouping granular namespaces into standard categories.
        """
        # If it's a media utility URL, rewrite it using the media parameter for category detection
        if 'media=' in url.lower():
            parsed_media = urllib.parse.urlparse(url)
            query_media = urllib.parse.parse_qs(parsed_media.query)
            media_id = query_media.get('media', [''])[0]
            if media_id:
                normalized_path = media_id.replace(':', '/')
                url = f"{parsed_media.scheme}://{parsed_media.netloc}/{normalized_path}"

        decoded_url = urllib.parse.unquote(url.lower())
        parsed = urllib.parse.urlparse(decoded_url)
        
        # 1. Gather all potential namespace parts
        parts = []
        
        # Add path parts
        for p in parsed.path.split('/'):
            if p:
                parts.append(p)
                
        # Add query 'id' parts
        query = urllib.parse.parse_qs(parsed.query)
        if 'id' in query:
            id_val = query['id'][0]
            for p in id_val.split(':'):
                if p:
                    parts.append(p)
                    
        # Remove diacritics from all parts for clean comparison
        clean_parts = []
        for p in parts:
            nfd = unicodedata.normalize('NFD', p)
            clean_p = "".join(c for c in nfd if unicodedata.category(c) != 'Mn')
            clean_parts.append(clean_p)
            
        # 2. Extract course code first
        course_code = self._extract_course_code(url)
        
        # 3. Determine the raw namespace category (the part immediately after the course code)
        raw_category = ""
        if course_code and course_code != 'ostatni':
            for i, part in enumerate(clean_parts):
                is_match = (part == course_code or 
                            part.startswith(course_code + '_') or 
                            part.startswith(course_code + '-'))
                if is_match and i + 1 < len(clean_parts):
                    raw_category = clean_parts[i+1]
                    break
                    
        # If no raw category was extracted from namespaces, fall back to looking at the path parts
        if not raw_category or raw_category in ['start', 'index', 'doku.php']:
            # Try to grab a non-empty part that isn't administrative
            for p in reversed(clean_parts):
                if p not in ['start', 'index', 'doku.php', course_code]:
                    raw_category = p
                    break

        # Clean raw category
        raw_category = re.sub(r'[^a-z0-9_\-]', '', raw_category.lower())
        
        # Guard against administrative utility names
        if raw_category in ['fetchphp', 'detailphp', 'lib', 'exe', 'media']:
            return 'ostatni'

        # 4. Group granular raw categories into logical buckets using keyword matching
        if 'zkousk' in raw_category or 'zkoušk' in raw_category:
            return 'zkouska'
        elif 'test1' in raw_category or 'test-1' in raw_category:
            return 'test1'
        elif 'test2' in raw_category or 'test-2' in raw_category:
            return 'test2'
        elif 'test-a' in raw_category:
            return 'test-a'
        elif 'test' in raw_category:
            return 'testy'
        elif 'prednask' in raw_category or 'lecture' in raw_category:
            return 'prednasky'
        elif 'cvicen' in raw_category or 'lab' in raw_category:
            return 'cviceni'
        elif 'ukol' in raw_category or 'homework' in raw_category:
            if 'ukol01' in raw_category or 'ukol_01' in raw_category or 'ukol1' in raw_category or 'ukol_1' in raw_category or 'homework1' in raw_category or 'homework_1' in raw_category:
                return 'ukoly-1'
            elif 'ukol02' in raw_category or 'ukol_02' in raw_category or 'ukol2' in raw_category or 'ukol_2' in raw_category or 'homework2' in raw_category or 'homework_2' in raw_category:
                return 'ukoly-2'
            elif 'ukol03' in raw_category or 'ukol_03' in raw_category or 'ukol3' in raw_category or 'ukol_3' in raw_category or 'homework3' in raw_category or 'homework_3' in raw_category:
                return 'ukoly-3'
            return 'ukoly'
        elif 'semestr' in raw_category:
            return 'semestralky'
            
        # If it doesn't fit standard buckets but is a valid custom namespace, return it
        if raw_category and raw_category not in ['start', 'index', 'doku.php']:
            return raw_category

        return 'ostatni'



    def _url_to_cache_filename(self, url: str) -> str:
        """
        Converts an URL into a safe, readable cache filename after stripping diacritics.
        """
        parsed = urllib.parse.urlparse(url)
        path = urllib.parse.unquote(parsed.path)
        
        # Remove accents/diacritics using Unicode normalization
        nfd_form = unicodedata.normalize('NFD', path)
        unaccented_path = "".join([c for c in nfd_form if unicodedata.category(c) != 'Mn'])
        
        # Combine path and query to create unique identifier
        name = unaccented_path.strip('/')
        if parsed.query:
            name += '_' + parsed.query
        # Replace unsafe characters
        name = re.sub(r'[^a-zA-Z0-9_\-]', '_', name)
        if not name:
            name = 'index'
        return f"{name}.html"

    def _get_page_html(self, url: str) -> str:
        """
        Gets page HTML from cache if it exists, otherwise downloads and caches it.
        """
        cache_filename = self._url_to_cache_filename(url)
        cache_path = os.path.join(self.config.cache_dir, cache_filename)
        
        if os.path.exists(cache_path):
            with open(cache_path, 'r', encoding='utf-8') as f:
                return f.read()
                
        # Fetch from network
        response = requests.get(
            url,
            headers=self.config.headers,
            cookies=self.config.cookies,
            timeout=10
        )
        response.raise_for_status()
        html = response.text
        
        # Save cache
        with open(cache_path, 'w', encoding='utf-8') as f:
            f.write(html)
            
        # Network delay to prevent rate limits
        if self.config.delay > 0:
            time.sleep(self.config.delay)
            
        return html

    def sanitize_html(self, html_content: str) -> BeautifulSoup:
        """
        Sanitizes page HTML by removing non-content elements.
        """
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Decompose all script and style elements completely from the source
        for script_style in soup.find_all(['script', 'style']):
            script_style.decompose()
            
        # Find main content container in DokuWiki (usually div.page or inside div#dokuwiki__content)
        content_div = soup.select_one('div.page')
        if not content_div:
            content_div = soup.select_one('#dokuwiki__content')
        if not content_div:
            content_div = soup.body if soup.body else soup
            
        # Create a new clean BeautifulSoup object from the content
        clean_soup = BeautifulSoup(str(content_div), 'html.parser')
        
        # Remove any nested script/style elements inside content
        for script_style in clean_soup.find_all(['script', 'style']):
            script_style.decompose()
            
        # Remove non-content elements
        selectors_to_remove = [
            # Table of Contents
            '.toc', '#dw__toc', '.dw-toc', '.bootstrap3-toc', '.bootstrap-toc', '.toc-wrapper',
            # Section Edit buttons
            '.btn_secedit', '.secedit',
            # Discussions
            '#discussion__section', '.discussion', '#comment_wrapper', '.comment_wrapper',
            # Navigation breadcrumbs & page ID
            '.breadcrumbs', '.pageId',
            # Fastwiki markers & edit buttons
            '.style-buttons', '.editbutton', '.fn_back',
            # DokuWiki action/share panels & tools
            '.bar', '.meta', '.docInfo', '.pagetools', '.usertools',
            '#dokuwiki__pagetools', '#dokuwiki__usertools',
            '.dw-page-icons', '.shareon', '.share', '.share-buttons', '.social-share', '.share-icon',
            # Helper dialog modals & close buttons
            '.modal', '.close'
        ]
        
        for selector in selectors_to_remove:
            for element in clean_soup.select(selector):
                element.decompose()
                
        # Decompose collapsed headers in hidden blocks (with '[+]')
        for h_on_h in clean_soup.select('.hiddenOnHidden'):
            h_on_h.decompose()
            
        # Clean '[-]' prefix from expanded headers
        for h_on_v in clean_soup.select('.hiddenOnVisible'):
            for string in h_on_v.find_all(string=True):
                new_text = re.sub(r'^\s*\[-\]\s*', '', string)
                string.replace_with(new_text)
                
        return clean_soup

    def _extract_course_code(self, url: str) -> str:
        """
        Extracts the course code (e.g., 'bi-osy') from the Fit-Wiki URL.
        """
        parsed = urllib.parse.urlparse(url)
        
        # Check media query param first (for attachments)
        query = urllib.parse.parse_qs(parsed.query)
        if 'media' in query:
            media_id = query['media'][0].lower()
            # Normalize to colon-separated parts
            media_parts = media_id.split(':')
            for i, part in enumerate(media_parts):
                if part in ['predmety', 'subjects'] and i + 1 < len(media_parts):
                    return media_parts[i+1].split('_')[0]
                    
        path = parsed.path
        parts = [p for p in path.split('/') if p]
        
        for i, part in enumerate(parts):
            decoded_part = urllib.parse.unquote(part).lower()
            # Remove diacritics
            decoded_part = ''.join(
                c for c in unicodedata.normalize('NFD', decoded_part)
                if unicodedata.category(c) != 'Mn'
            )
            if decoded_part in ['predmety', 'subjects'] and i + 1 < len(parts):
                next_part = urllib.parse.unquote(parts[i+1]).lower()
                # Split by underscore or colon to extract the root namespace (course code)
                course_code = next_part.split('_')[0].split(':')[0]
                return course_code
                
        # Fallback if not found in standard subjects namespace
        return "ostatni"

    def _should_download_image(self, src: str) -> bool:
        """
        Determines if an image is content (LaTeX or uploaded media) or just interface layout.
        """
        src_lower = src.lower()
        
        # Exclude common emoticons/layout images
        if 'smileys' in src_lower or 'lib/images/smileys' in src_lower:
            return False
        if 'lib/tpl' in src_lower:
            return False
        if 'logo.png' in src_lower or 'avatar' in src_lower or 'gravatar' in src_lower:
            return False
            
        # Keep LaTeX equations and wiki media uploads
        if 'latex.php' in src_lower or 'media=latex:' in src_lower:
            return True
        if 'fetch.php' in src_lower or 'media=' in src_lower or '_media/' in src_lower:
            return True
            
        return True

    def _get_full_res_image_url(self, url: str) -> str:
        """
        Transforms DokuWiki thumbnail/fetch URLs into their full-resolution counterparts
        by removing resizing query parameters (like w, h, tok).
        """
        parsed = urllib.parse.urlparse(url)
        query = urllib.parse.parse_qs(parsed.query)
        
        # Case 1: DokuWiki fetch.php utility
        if 'fetch.php' in parsed.path:
            if 'media' in query:
                media_val = query['media'][0]
                new_query = urllib.parse.urlencode({'media': media_val})
                return urllib.parse.urlunparse(parsed._replace(query=new_query))
        
        # Case 2: Direct _media rewritten paths (e.g. /_media/path/to/file.png?w=400&tok=...)
        elif '_media/' in parsed.path:
            return urllib.parse.urlunparse(parsed._replace(query=''))
                
        return url

    def _download_image(self, img_url: str, course_code: str, category: str, page_slug: str) -> Optional[str]:
        """
        Downloads a media file/LaTeX equation and saves it locally.
        Returns the relative path to be used in Markdown.
        """
        # Resolve full URL for image
        if img_url.startswith('/'):
            full_img_url = self.config.base_url + img_url
        elif img_url.startswith('http'):
            full_img_url = img_url
        else:
            full_img_url = f"{self.config.base_url}/{img_url}"
            
        # Get full resolution URL by stripping thumbnail params
        full_img_url = self._get_full_res_image_url(full_img_url)
            
        # Construct local path
        category_dir = os.path.join(self.config.markdown_dir, course_code, category)
        images_dir = os.path.join(category_dir, 'images', page_slug)
        os.makedirs(images_dir, exist_ok=True)
        
        # Determine file extension and name
        parsed = urllib.parse.urlparse(full_img_url)
        query = urllib.parse.parse_qs(parsed.query)
        
        if 'latex.php' in full_img_url or 'media=latex:' in full_img_url:
            # It's a LaTeX image
            # Try to get the actual LaTeX formula from query or use URL hash to name it
            formula = query.get('code', query.get('media', ['']))[0]
            # Replace latex: prefix
            if formula.startswith('latex:'):
                formula = formula[6:]
            # Safe filename based on hash
            img_hash = str(hash(full_img_url) & 0xffffffff)
            filename = f"latex_{img_hash}.gif"
        else:
            # Standard media file
            filename = os.path.basename(parsed.path)
            # If media parameter is used in fetch.php
            if 'media' in query:
                media_path = query['media'][0]
                filename = os.path.basename(media_path.replace(':', '/'))
            
            # Clean filename
            filename = re.sub(r'[^a-zA-Z0-9_\-\.]', '_', filename)
            if not filename or '.' not in filename:
                img_hash = str(hash(full_img_url) & 0xffffffff)
                filename = f"img_{img_hash}.png"
                
        local_path = os.path.join(images_dir, filename)
        relative_path = f"images/{page_slug}/{filename}"
        
        if os.path.exists(local_path):
            return relative_path
            
        try:
            # Fetch image
            response = requests.get(
                full_img_url,
                headers=self.config.headers,
                cookies=self.config.cookies,
                timeout=10
            )
            response.raise_for_status()
            
            with open(local_path, 'wb') as f:
                f.write(response.content)
                
            # Rate limit delay
            if self.config.delay > 0:
                time.sleep(self.config.delay)
                
            return relative_path
        except Exception as e:
            print(f"Warning: Failed to download image {full_img_url}: {e}")
            return None

    def _format_markdown_images(self, md_content: str) -> str:
        """
        Processes Markdown content to separate consecutive images with a double newline (\n\n).
        Prevents overflow issues when compiled into PDF.
        """
        # Match markdown image patterns: ![alt](url)
        # We look for consecutive image tags and ensure there's a double newline between them.
        def replace_consecutive_images(match):
            img1, spacing, img2 = match.groups()
            return f"{img1}\n\n{img2}"
            
        # Pattern matches: image, followed by vertical whitespaces, followed by another image
        pattern = re.compile(r'(\!\[.*?\]\(.*?\))(\s*)(\!\[.*?\]\(.*?\))')
        
        previous_content = ""
        while md_content != previous_content:
            previous_content = md_content
            md_content = pattern.sub(replace_consecutive_images, md_content)
            
        return md_content

    def scrape_page(self, url: str, category: str, page_title: str, course_code: Optional[str] = None) -> str:
        """
        Full page scraping pipeline: cache check, download, sanitize, download images, convert to markdown.
        Returns the path to the saved Markdown file.
        """
        page_slug = self._url_to_cache_filename(url).replace('.html', '')
        
        # Get raw HTML
        raw_html = self._get_page_html(url)
        
        # Sanitize HTML
        clean_soup = self.sanitize_html(raw_html)
        
        # Attempt to fetch raw wikitext to align LaTeX equations as text
        latex_formulas = []
        try:
            wikitext_url = url + ("&" if "?" in url else "?") + "do=export_raw"
            wikitext_response = requests.get(
                wikitext_url,
                headers=self.config.headers,
                cookies=self.config.cookies,
                timeout=10
            )
            if wikitext_response.status_code == 200:
                # Find all <latex>...</latex> blocks
                latex_formulas = re.findall(r'<latex.*?>(.*?)</latex>', wikitext_response.text, re.DOTALL)
                latex_formulas = [f.strip() for f in latex_formulas]
        except Exception as e:
            print(f"Warning: Could not fetch wikitext for LaTeX extraction: {e}")
        
        # Extract course code to separate output directories by subject
        course_code = course_code or self._extract_course_code(url)
        
        # Process and download images / substitute LaTeX formulas
        latex_idx = 0
        for img in clean_soup.find_all('img'):
            src = img.get('src')
            if not src:
                continue
                
            src_lower = src.lower()
            is_latex = 'latex.php' in src_lower or 'media=latex:' in src_lower or 'media=latex%3a' in src_lower
            
            if is_latex:
                if latex_idx < len(latex_formulas):
                    # Replace the alt text with the original LaTeX formula
                    formula = latex_formulas[latex_idx]
                    latex_idx += 1
                    # Clean newlines to keep the markdown image tag on a single line
                    clean_formula = formula.replace('\n', ' ').replace('\r', ' ').strip()
                    img['alt'] = clean_formula
                    
                # Download the image so the PDF compiler can render the formula
                local_rel_path = self._download_image(src, course_code, category, page_slug)
                if local_rel_path:
                    img['src'] = local_rel_path
                else:
                    img.decompose()
            elif self._should_download_image(src):
                local_rel_path = self._download_image(src, course_code, category, page_slug)
                if local_rel_path:
                    # Update img src to relative local path
                    img['src'] = local_rel_path
                else:
                    img.decompose() # Remove failed images to avoid broken links
            else:
                img.decompose() # Remove non-content layout images
                
        # Convert to Markdown using our custom converter to preserve HTML tables
        html_str = str(clean_soup)
        md_content = FitWikiMarkdownConverter(
            heading_style="ATX",
            bullets="-",
            strip=['script', 'style']
        ).convert(html_str)
        
        # Format consecutive images with double newlines
        md_content = self._format_markdown_images(md_content)
        
        # Prepend title
        full_md_content = f"# {page_title}\n\nSource: [{url}]({url})\n\n---\n\n{md_content}"
        
        # Save to category markdown folder
        category_dir = os.path.join(self.config.markdown_dir, course_code, category)
        os.makedirs(category_dir, exist_ok=True)
        
        md_filename = f"{page_slug}.md"
        md_path = os.path.join(category_dir, md_filename)
        
        with open(md_path, 'w', encoding='utf-8') as f:
            f.write(full_md_content)
            
        return md_path

    def scrape_courses_index(self, html_content: str) -> List[Dict[str, str]]:
        """
        Parses the subjects index page and extracts all courses.
        """
        soup = BeautifulSoup(html_content, 'html.parser')
        courses = []
        
        for a_tag in soup.find_all('a', href=True):
            href = a_tag['href']
            text = a_tag.get_text(strip=True)
            
            # Decode and normalize path
            decoded_href = urllib.parse.unquote(href)
            parsed = urllib.parse.urlparse(decoded_href)
            path = parsed.path.rstrip('/')
            
            # Check if path matches /škola/předměty/some-code
            parts = path.strip('/').split('/')
            if len(parts) == 3 and parts[0] == 'škola' and parts[1] == 'předměty':
                course_code = parts[2]
                
                if course_code in ['start', 'pomoc', 'předměty']:
                    continue
                    
                full_url = self.config.base_url + href if href.startswith('/') else href
                
                courses.append({
                    'code': course_code,
                    'title': text or course_code.upper(),
                    'url': full_url
                })
                
        # Remove duplicates, sorting by code
        seen = set()
        unique_courses = []
        for c in sorted(courses, key=lambda x: x['code']):
            if c['code'] not in seen:
                seen.add(c['code'])
                unique_courses.append(c)
                
        return unique_courses

    def get_courses(self) -> List[Dict[str, str]]:
        """
        Fetches the courses list index from the web (or cache) and parses it.
        """
        courses_url = f"{self.config.base_url}/škola/předměty"
        html = self._get_page_html(courses_url)
        return self.scrape_courses_index(html)

