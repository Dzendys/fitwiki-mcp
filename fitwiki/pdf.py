import os
import re
from typing import List, Optional
import markdown
from bs4 import BeautifulSoup
from xhtml2pdf import pisa

from .config import ScraperConfig

class FitWikiPDFCompiler:
    """
    Object-Oriented PDF Compiler for Fit-Wiki markdown files.
    """
    def __init__(self, config: ScraperConfig):
        self.config = config
        os.makedirs(self.config.pdf_dir, exist_ok=True)
        
        # Look for DejaVu Sans fonts in standard Linux locations
        self.font_paths = self._find_dejavu_fonts()

    def _find_dejavu_fonts(self) -> dict:
        """
        Finds DejaVu Sans fonts on the system.
        """
        standard_dirs = [
            "/usr/share/fonts/truetype/dejavu",
            "/usr/share/fonts/dejavu",
            "/usr/share/fonts/TTF"
        ]
        
        fonts = {
            'regular': 'DejaVuSans.ttf',
            'bold': 'DejaVuSans-Bold.ttf',
            'mono': 'DejaVuSansMono.ttf'
        }
        
        found_fonts = {}
        for style, filename in fonts.items():
            found = False
            for d in standard_dirs:
                path = os.path.join(d, filename)
                if os.path.exists(path):
                    found_fonts[style] = path
                    found = True
                    break
            if not found:
                # Fallback to local workspace or search
                found_fonts[style] = filename  # xhtml2pdf will try to find it in path or failback
                
        return found_fonts

    def get_html_template(self, content_html: str) -> str:
        """
        Wraps content in an HTML template with styles and Czech fonts registered.
        """
        # Build font face declarations
        font_styles = []
        if os.path.exists(self.font_paths['regular']):
            font_styles.append(f"""
                @font-face {{
                    font-family: 'DejaVu';
                    src: url('{self.font_paths['regular']}');
                }}
            """)
        if os.path.exists(self.font_paths['bold']):
            font_styles.append(f"""
                @font-face {{
                    font-family: 'DejaVu';
                    src: url('{self.font_paths['bold']}');
                    font-weight: bold;
                }}
            """)
        if os.path.exists(self.font_paths['mono']):
            font_styles.append(f"""
                @font-face {{
                    font-family: 'DejaVuMono';
                    src: url('{self.font_paths['mono']}');
                }}
            """)
            
        font_declarations = "\n".join(font_styles)
        font_family_main = "'DejaVu', sans-serif" if font_styles else "sans-serif"
        font_family_mono = "'DejaVuMono', monospace" if font_styles else "monospace"

        return f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <style>
        {font_declarations}
        
        @page {{
            size: a4;
            margin: 1.5cm;
        }}
        
        body {{
            font-family: {font_family_main};
            font-size: 10pt;
            line-height: 1.5;
            color: #222222;
        }}
        
        h1, h2, h3, h4, h5, h6 {{
            font-weight: bold;
            color: #111111;
            margin-top: 18pt;
            margin-bottom: 8pt;
            page-break-after: avoid;
        }}
        
        h1 {{
            font-size: 20pt;
            border-bottom: 0.5pt solid #cccccc;
            padding-bottom: 5pt;
            margin-top: 0pt;
        }}
        
        h2 {{
            font-size: 15pt;
            border-bottom: 0.2pt solid #dddddd;
            padding-bottom: 3pt;
        }}
        
        h3 {{
            font-size: 12pt;
        }}
        
        p {{
            margin-top: 0pt;
            margin-bottom: 10pt;
            text-align: justify;
        }}
        
        a {{
            color: #0066cc;
            text-decoration: none;
        }}
        
        /* Table formatting */
        table {{
            width: 100%;
            border-collapse: collapse;
            margin: 12pt 0;
            page-break-inside: auto;
        }}
        
        tr {{
            page-break-inside: avoid;
            page-break-after: auto;
        }}
        
        th, td {{
            border: 0.5pt solid #cccccc;
            padding: 6pt 8pt;
            text-align: left;
            font-size: 9.5pt;
        }}
        
        th {{
            background-color: #f5f5f5;
            font-weight: bold;
        }}
        
        /* Lists */
        ul, ol {{
            margin-top: 0pt;
            margin-bottom: 10pt;
            padding-left: 20pt;
        }}
        
        li {{
            margin-bottom: 4pt;
        }}
        
        /* Code blocks */
        pre, code {{
            font-family: {font_family_mono};
            font-size: 9pt;
        }}
        
        code {{
            background-color: #f7f7f7;
            padding: 1pt 3pt;
            border-radius: 2pt;
            border: 0.2pt solid #dddddd;
        }}
        
        pre {{
            background-color: #f7f7f7;
            border: 0.5pt solid #dddddd;
            padding: 8pt 10pt;
            margin: 12pt 0;
            white-space: pre-wrap;
            page-break-inside: avoid;
        }}
        
        pre code {{
            background-color: transparent;
            border: none;
            padding: 0;
        }}
        
        /* Images */
        img {{
            display: block;
            margin: 12pt auto;
            max-width: 100%;
            height: auto;
            page-break-inside: avoid;
        }}
        
        /* Horizontal rule */
        hr {{
            border: none;
            border-top: 0.5pt solid #cccccc;
            margin: 15pt 0;
        }}
        
        /* Quote blocks */
        blockquote {{
            margin: 12pt 0;
            padding-left: 10pt;
            border-left: 3pt solid #cccccc;
            color: #555555;
            font-style: italic;
        }}
    </style>
</head>
<body>
    {content_html}
</body>
</html>
"""

    def compile_file(self, md_path: str, pdf_path: str) -> bool:
        """
        Compiles a single Markdown file to a PDF document.
        """
        try:
            if not os.path.exists(md_path):
                print(f"Error: Markdown file {md_path} does not exist.")
                return False
                
            with open(md_path, 'r', encoding='utf-8') as f:
                md_text = f.read()
                
            # Convert Markdown to HTML
            # Using 'extra' for tables, code blocks, etc.
            raw_html = markdown.markdown(md_text, extensions=['extra'])
            
            # Resolve relative image paths to absolute paths
            soup = BeautifulSoup(raw_html, 'html.parser')
            for img in soup.find_all('img'):
                src = img.get('src')
                if src and not src.startswith('http') and not os.path.isabs(src):
                    # Resolve relative to markdown file directory
                    abs_src = os.path.abspath(os.path.join(os.path.dirname(md_path), src))
                    img['src'] = abs_src
                    
            content_html = str(soup)
            full_html = self.get_html_template(content_html)
            
            # Create PDF
            with open(pdf_path, 'wb') as pdf_file:
                pisa_status = pisa.CreatePDF(
                    full_html,
                    dest=pdf_file
                )
                
            return not pisa_status.err
        except Exception as e:
            print(f"Error compiling PDF {pdf_path}: {e}")
            return False

    def compile_category(self, category: str) -> List[str]:
        """
        Compiles all Markdown files within a category folder.
        Returns a list of created PDF paths.
        """
        category_md_dir = os.path.join(self.config.markdown_dir, category)
        if not os.path.exists(category_md_dir):
            print(f"Warning: Category folder {category_md_dir} does not exist.")
            return []
            
        category_pdf_dir = os.path.join(self.config.pdf_dir, category)
        os.makedirs(category_pdf_dir, exist_ok=True)
        
        pdf_paths = []
        for file in os.listdir(category_md_dir):
            if file.endswith('.md'):
                md_path = os.path.join(category_md_dir, file)
                pdf_filename = file.replace('.md', '.pdf')
                pdf_path = os.path.join(category_pdf_dir, pdf_filename)
                
                print(f"Compiling {file} to PDF...")
                success = self.compile_file(md_path, pdf_path)
                if success:
                    pdf_paths.append(pdf_path)
                    
        return pdf_paths
