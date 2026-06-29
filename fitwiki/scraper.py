import os
import re
import time
import urllib.parse
import unicodedata
from typing import List, Dict, Any, Optional
import requests
from bs4 import BeautifulSoup
from markdownify import markdownify as md

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
                
                # Exclude administrative dokuwiki links or external links
                if 'do=' in full_url or 'id=' not in full_url and 'fit-wiki.cz' not in full_url:
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
        Dynamically detects material category based on URL patterns.
        """
        decoded_url = urllib.parse.unquote(url.lower())
        
        if 'zkouska' in decoded_url or 'zkouška' in decoded_url:
            return 'zkouska'
        elif 'test1' in decoded_url or 'test-1' in decoded_url:
            return 'test1'
        elif 'test2' in decoded_url or 'test-2' in decoded_url:
            return 'test2'
        elif 'test-a' in decoded_url or 'testa' in decoded_url:
            return 'test-a'
        elif 'test' in decoded_url:
            return 'testy'
        else:
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
            cookies=self.config.cookies
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
        
        # Find main content container in DokuWiki (usually div.page or inside div#dokuwiki__content)
        content_div = soup.select_one('div.page')
        if not content_div:
            content_div = soup.select_one('#dokuwiki__content')
        if not content_div:
            content_div = soup.body if soup.body else soup
            
        # Create a new clean BeautifulSoup object from the content
        clean_soup = BeautifulSoup(str(content_div), 'html.parser')
        
        # Remove non-content elements
        selectors_to_remove = [
            'div.toc', 'div#dw__toc',                # Table of Contents
            'form.btn_secedit', 'div.secedit',       # Section Edit buttons
            'div#discussion__section', 'div.discussion', # Discussions
            'div.breadcrumbs', 'div.pageId',         # Navigation breadcrumbs & page ID
            'div.style-buttons',                     # Fastwiki markers
            'span.editbutton',                       # Edit buttons
            'a.fn_back'                              # Footnote back links
        ]
        
        for selector in selectors_to_remove:
            for element in clean_soup.select(selector):
                element.decompose()
                
        return clean_soup

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

    def _download_image(self, img_url: str, category: str, page_slug: str) -> Optional[str]:
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
        category_dir = os.path.join(self.config.markdown_dir, category)
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
                cookies=self.config.cookies
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

    def scrape_page(self, url: str, category: str, page_title: str) -> str:
        """
        Full page scraping pipeline: cache check, download, sanitize, download images, convert to markdown.
        Returns the path to the saved Markdown file.
        """
        page_slug = self._url_to_cache_filename(url).replace('.html', '')
        
        # Get raw HTML
        raw_html = self._get_page_html(url)
        
        # Sanitize HTML
        clean_soup = self.sanitize_html(raw_html)
        
        # Process and download images
        for img in clean_soup.find_all('img'):
            src = img.get('src')
            if not src:
                continue
                
            if self._should_download_image(src):
                local_rel_path = self._download_image(src, category, page_slug)
                if local_rel_path:
                    # Update img src to relative local path
                    img['src'] = local_rel_path
                else:
                    img.decompose() # Remove failed images to avoid broken links
            else:
                img.decompose() # Remove non-content layout images
                
        # Convert to Markdown using markdownify
        # We specify convert=['img', 'a', 'p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'table', 'ul', 'ol', 'li', 'strong', 'em', 'code', 'pre', 'br']
        # to ensure markdownify parses tables properly.
        html_str = str(clean_soup)
        md_content = md(
            html_str,
            heading_style="ATX",
            bullets="-",
            strip=['script', 'style']
        )
        
        # Format consecutive images with double newlines
        md_content = self._format_markdown_images(md_content)
        
        # Prepend title
        full_md_content = f"# {page_title}\n\nSource: [{url}]({url})\n\n---\n\n{md_content}"
        
        # Save to category markdown folder
        category_dir = os.path.join(self.config.markdown_dir, category)
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

