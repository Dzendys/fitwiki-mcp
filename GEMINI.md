# Technická dokumentace: Fit-Wiki Scraper & PDF Compiler

Nástroj pro automatizovanou extrakci obsahu stránek předmětů z platformy Fit-Wiki, stahování obrázků/LaTeX rovnic a export do formátu Markdown a PDF.

## 1. Systémové požadavky
- Python 3.x
- Virtuální prostředí (venv)
- Systémové písmo DejaVu Sans (pro správné vykreslení českých znaků v PDF)
- Závislosti: `requests`, `beautifulsoup4`, `markdownify`, `markdown`, `xhtml2pdf` a pomocné knihovny.

## 2. Instalace a příprava
Pro instalaci bez nutnosti kompilace systémových grafických knihoven (jako Cairo/Pango) postupujte následovně:
```bash
python3 -m venv venv
# Instalace základních knihoven a Markdown parseru
./venv/bin/pip install beautifulsoup4 markdownify requests markdown
# Instalace PDF kompilátoru bez těžkých Cairo závislostí
./venv/bin/pip install xhtml2pdf --no-deps
./venv/bin/pip install pyhanko asn1crypto
```

## 3. Konfigurace vstupů
Pro úspěšný běh jsou vyžadovány:
1. **Autentizace a stažení indexu**: Python skript (`index_page.py`) obsahující platné cookies (`DokuWiki`, `DW...`) a hlavičky. Spuštěním se stáhne hlavní stránka předmětu a uloží se jako `index-page.html`.
2. **Scrapovací skript**: Hlavní nástroj (`scraper.py`), který jako vstup využívá vytvořený `index-page.html` pro extrakci odkazů na jednotlivé podstránky.
3. **PDF konvertor**: Doplňkový nástroj (`convert_to_pdf.py`), který z vygenerovaných Markdownů sestaví PDF soubory.

## 4. Pipeline zpracování
Proces probíhá v pěti fázích:

### A. Extrakce URL
Identifikace relevantních odkazů na podstránky uvnitř kontejnerů s třídou `hiddenBody` na indexové stránce.

### B. Perzistentní Cache (Složka `cache/`)
- Ověření existence lokální kopie HTML podstránky před síťovým požadavkem.
- Stažení chybějících stránek s využitím nakonfigurovaných cookies a časovou prodlevou (1s) pro prevenci limitace ze strany serveru.

### C. Sanitizace a Dynamická Kategorizace
- Odstranění non-content elementů (TOC, edit tlačítka, diskuze, fastwiki markery).
- **Adaptivní třídění**: Skript dynamicky detekuje kategorie materiálů na základě vzorů v URL (např. `zkouska`, `test1`, `test2`, `test-a`). Pokud vzor není jednoznačně rozpoznán, materiál je zařazen do kategorie `ostatni`.

### D. Konverze do Markdown (Složka `markdown_output/<kategorie>/`)
- **Stahování obrázků**: Skript detekuje obrázky. Filtruje pryč rozvržení (loga, avatar, smajlíky), ale **uchovává a stahuje LaTeX rovnice** (gif generovaný přes `fetch.php?media=latex:...` nebo `latex.php`) a uživatelské obrázky.
- Ukládá obrázky do `markdown_output/<kategorie>/images/<slug_stránky>/` s časovou prodlevou (1s) a cachováním.
- Upravuje `src` obrázků na relativní cesty a převádí HTML do Markdownu pomocí `markdownify`.
- **Formátování obrázků**: Skript zajišťuje, že po sobě jdoucí obrázky v Markdownu jsou odděleny dvojitým odřádkováním (`\n\n`), což brání jejich řazení vedle sebe a případnému přetečení mimo stránku. Výstupy se uloží do příslušné kategorie.

### E. Export do PDF (Složka `pdfs/`)
- Skript `convert_to_pdf.py` načte Markdown soubory a převede je do HTML s povolenou podporou tabulek a bloků kódu.
- Využívá knihovnu `xhtml2pdf` a definuje cestu k systémovým písmům (`DejaVuSans.ttf`, `DejaVuSans-Bold.ttf` a `DejaVuSansMono.ttf`) přes `@font-face` pravidla pro bezchybné zobrazení českých znaků (např. písmene `Ř`).
- **Styling a rozložení**: Obrázky jsou stylovány jako blokové elementy (`display: block; margin: 10pt auto;`), čímž se docílí jejich vycentrování a vertikálního skládání pod sebe bez ořezu.
- Vytvoří lehké a pro LLM čistě čitelné PDF dokumenty bez rušivých záhlaví a zápatí.

## 5. Spuštění a Interakce
1. Stažení indexu:
   ```bash
   ./venv/bin/python index_page.py
   ```
2. Spuštění scraperu:
   ```bash
   ./venv/bin/python scraper.py
   ```
   *Uživatel interaktivně vybere kategorie ke stažení (např. zadáním `1,2` nebo `all`).*
3. Export do PDF:
   ```bash
   ./venv/bin/python convert_to_pdf.py
   ```

## 6. Datová struktura
- `cache/`: Archiv surových HTML souborů podstránek.
- `markdown_output/`: Výsledné dokumenty ve formátu `.md` a jejich lokální obrázky.
- `pdfs/`: Výsledné lehké PDF dokumenty pro archivaci a další zpracování LLM.