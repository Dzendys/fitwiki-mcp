import os
from typing import Dict, Any
from dotenv import load_dotenv

# Load environment variables from .env file if it exists
load_dotenv()


class ScraperConfig:
    """
    Configuration class for the Fit-Wiki Scraper and PDF Compiler.
    """
    def __init__(
        self,
        cookies: Dict[str, str] = None,
        base_url: str = "https://fit-wiki.cz",
        cache_dir: str = "cache",
        markdown_dir: str = "markdown_output",
        pdf_dir: str = "pdfs",
        delay: float = 1.0,
        headers: Dict[str, str] = None
    ):
        self.cookies = cookies or {}
        self.base_url = base_url.rstrip('/')
        
        # Determine the project root absolute path
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        
        # Resolve directories to absolute paths
        self.cache_dir = cache_dir if os.path.isabs(cache_dir) else os.path.join(project_root, cache_dir)
        self.markdown_dir = markdown_dir if os.path.isabs(markdown_dir) else os.path.join(project_root, markdown_dir)
        self.pdf_dir = pdf_dir if os.path.isabs(pdf_dir) else os.path.join(project_root, pdf_dir)
        self.delay = delay
        
        self.headers = headers or {
            'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
            'accept-language': 'en-US,en;q=0.7',
            'cache-control': 'max-age=0',
            'priority': 'u=0, i',
            'sec-ch-ua': '"Not;A=Brand";v="8", "Chromium";v="150", "Brave";v="150"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Linux"',
            'sec-fetch-dest': 'document',
            'sec-fetch-mode': 'navigate',
            'sec-fetch-site': 'same-origin',
            'sec-fetch-user': '?1',
            'sec-gpc': '1',
            'upgrade-insecure-requests': '1',
            'user-agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/150.0.0.0 Safari/537.36'
        }

    @classmethod
    def from_cookie_string(cls, cookie_str: str, **kwargs) -> 'ScraperConfig':
        """
        Parses a cookie string (e.g., 'DokuWiki=abc; DW...=xyz') into a ScraperConfig instance.
        """
        cookies = {}
        if cookie_str:
            for item in cookie_str.split(';'):
                item = item.strip()
                if '=' in item:
                    k, v = item.split('=', 1)
                    cookies[k.strip()] = v.strip()
        return cls(cookies=cookies, **kwargs)

    @classmethod
    def from_env(cls, **kwargs) -> 'ScraperConfig':
        """
        Loads configuration from environment variables.
        """
        cookie_str = os.environ.get("FITWIKI_COOKIES", "")
        base_url = os.environ.get("FITWIKI_BASE_URL", "https://fit-wiki.cz")
        delay_str = os.environ.get("FITWIKI_DELAY", "1.0")
        try:
            delay = float(delay_str)
        except ValueError:
            delay = 1.0
            
        return cls.from_cookie_string(
            cookie_str=cookie_str,
            base_url=base_url,
            delay=delay,
            **kwargs
        )
