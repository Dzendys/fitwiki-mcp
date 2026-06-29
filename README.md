# Fit-Wiki Scraper & PDF Compiler + MCP Server

Robustní stahovač (scraper) a kompilátor PDF z platformy Fit-Wiki napsaný v Pythonu s objektově orientovaným (OOP) designem, doplněný o MCP (Model Context Protocol) server pro snadné propojení s LLM klienty (např. Claude Desktop).

---

## 💻 1. Požadavky a Instalace

Systém vyžaduje Python 3.x a systémová písma **DejaVu Sans** pro správný render českých znaků (např. písmene `Ř`) v PDF.

### Instalace závislostí:
```bash
python3 -m venv venv
# Aktivace a instalace základních balíčků a MCP
./venv/bin/pip install beautifulsoup4 markdownify requests markdown mcp
# Instalace xhtml2pdf a závislostí
./venv/bin/pip install xhtml2pdf --no-deps
./venv/bin/pip install html5lib Pillow pypdf "reportlab<5" svglib arabic-reshaper python-bidi pyhanko asn1crypto
```

---

## 📐 2. Architektura Projektu

Projekt je rozdělen do modulárního OOP balíčku `fitwiki` a samostatných spustitelných skriptů:

- **`fitwiki/` (Python modul):**
  - [`config.py`](file:///home/dzendys_/Downloads/fitwiki/fitwiki/config.py): `ScraperConfig` – načítání konfigurace z `.env`, environment proměnných nebo cookie řetězců.
  - [`scraper.py`](file:///home/dzendys_/Downloads/fitwiki/fitwiki/scraper.py): `FitWikiScraper` – stahování indexu, parsování `.hiddenBody` odkazů, stahování LaTeX rovnic a uživatelských obrázků, odstraňování nepotřebných elementů a ukládání do strukturovaných Markdownů.
  - [`pdf.py`](file:///home/dzendys_/Downloads/fitwiki/fitwiki/pdf.py): `FitWikiPDFCompiler` – parsování Markdown tabulek a bloků kódu, stylování obrázků jako bloků a převod do lehkých PDF dokumentů s DejaVu Sans fonty.
  
- **Spustitelné skripty (CLI):**
  - [`index_page.py`](file:///home/dzendys_/Downloads/fitwiki/index_page.py): Stáhne hlavní stránku předmětu do `index-page.html` (automaticky přebírá URL a cookies z `index.sh`).
  - [`scraper.py`](file:///home/dzendys_/Downloads/fitwiki/scraper.py): Interaktivně se zeptá uživatele na kategorie a postará se o stažení a převod podstránek do Markdownů.
  - [`convert_to_pdf.py`](file:///home/dzendys_/Downloads/fitwiki/convert_to_pdf.py): Zkompiluje všechny stažené Markdown dokumenty do PDF souborů.

- **MCP Server:**
  - [`mcp_server.py`](file:///home/dzendys_/Downloads/fitwiki/mcp_server.py): Vystavuje funkce scraperu a PDF kompilátoru jako nástroje (tools) pro libovolného LLM klienta.

---

## ⚙️ 3. Konfigurace a Cookies

Pro přístup na Fit-Wiki je potřeba mít platné přihlášení. Skripty podporují dva způsoby načítání cookies:
1. **Přes `index.sh` (doporučeno):** Skript `index_page.py` a interaktivní scraper automaticky přečtou přepínač `-b` nebo hlavičku `-H` z vašeho lokálního souboru `index.sh`.
2. **Přes proměnné prostředí:** Nastavením `FITWIKI_COOKIES` na hodnotu vašeho cookie řetězce (např. `DokuWiki=xyz; DW...=abc`).

---

## 🚀 4. Použití jako CLI Pipeline

1. **Stažení indexu předmětu:**
   ```bash
   ./index_page.py
   ```
   Tímto se vytvoří soubor `index-page.html`.

2. **Spuštění stahování podstránek (interaktivní):**
   ```bash
   ./scraper.py
   ```
   Vyberte kategorie (např. zadáním `1,2` nebo `all`). Výstup se uloží do složky `markdown_output/`.

3. **Export do PDF:**
   ```bash
   ./convert_to_pdf.py
   ```
   PDF soubory se vygenerují do složky `pdfs/` pod stejnými kategoriemi.

---

## 🤖 5. Nastavení MCP Serveru

Pro integraci s LLM klienty (jako např. Claude Desktop) můžete přidat následující konfiguraci do vašeho `mcp_config.json` (obvykle v `~/.config/Claude/claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "fitwiki": {
      "command": "/home/dzendys_/Downloads/fitwiki/venv/bin/python",
      "args": ["/home/dzendys_/Downloads/fitwiki/mcp_server.py"],
      "env": {
        "FITWIKI_COOKIES": "DokuWiki=7ca1i426o4t9bfaujdj4l6hov4; DW7fa065a06cb74b536c124cfbe56ac6d3=bWFydHVsZW5z%7C1%7CnPPhm83eK4SHSC41n6Io%2BPESvtdZqvlwi8yPSHbtuzk%3D"
      }
    }
  }
}
```

### Vystavené MCP Nástroje (Tools):
- `scrape_index`: Načte indexovou stránku předmětu a vypíše všechny její podstránky a kategorie.
- `scrape_page`: Stáhne a zkonvertuje konkrétní podstránku podle URL.
- `scrape_course`: Provede kompletní stažení všech stránek ve vybraných kategoriích.
- `compile_pdf`: Zkompiluje jeden Markdown soubor do PDF.
- `compile_category_pdfs`: Zkompiluje celou složku kategorie do PDF souborů.
