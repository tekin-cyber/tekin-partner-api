# CLAUDE.md — tekin-partner-api

## Project Overview

Data repository providing official tax sources and a whitelist for GPT-based verification of the **DBA Deutschland–Türkei** (Double Taxation Agreement between Germany and Turkey). This is **not** a web application or API server — it is a structured collection of JSON data files consumed by downstream AI/GPT systems for tax compliance checks.

Primary language of content: German (with Turkish tax data). Code automation: Python 3.11.

## Repository Structure

```
tekin-partner-api/
├── bfh/            # Bundesfinanzhof (Federal Tax Court) case law — auto-updated
├── bmf/            # Bundesfinanzministerium (Federal Finance Ministry) documents — auto-updated
├── datev/          # DATEV/DMS export format metadata
├── dba/            # DBA Germany-Turkey evaluation rules and logic
├── finance/        # Exchange rates (EUR-TRY)
├── gib/            # Turkish Revenue Administration (GİB) tax rates
├── law/            # German tax law references (EStG)
├── oecd/           # OECD Model Tax Convention commentary
├── policy/         # Whitelist of approved official sources
├── world/          # World Bank / IMF economic indicators
└── .github/
    ├── scripts/    # Python automation (update_sources.py)
    └── workflows/  # GitHub Actions (weekly RSS feed updates)
```

Each domain directory contains one JSON file with structured data.

## Key Files

| File | Purpose |
|------|---------|
| `dba/evaluate.json` | Core DBA evaluation rules (income types, conditions, methods, articles) |
| `policy/whitelist.json` | Approved publishers and domains for source verification |
| `law/estg.json` | Relevant EStG (income tax law) section references |
| `gib/taxrates.json` | Turkish corporate, withholding, and income tax rates |
| `oecd/commentary.json` | OECD model convention article excerpts |
| `finance/exchange.json` | Current EUR-TRY exchange rate |
| `world/indicators.json` | GDP, tax ratio, and inflation data (DE & TR) |
| `datev/export.json` | Standardized export format for accounting systems |
| `bfh/cases.json` | BFH case law (auto-updated weekly from RSS) |
| `bmf/latest.json` | BMF publications (auto-updated weekly from RSS) |
| `.github/scripts/update_sources.py` | RSS feed fetcher for BMF & BFH data |

## Automation

### GitHub Actions Workflow (`update_feeds.yml`)

- **Schedule**: Every Sunday at 06:00 UTC
- **Trigger**: Also supports manual `workflow_dispatch`
- **What it does**: Runs `update_sources.py` to fetch the latest 10 entries from BMF and BFH RSS feeds, writes them as JSON, and auto-commits
- **Runtime**: Python 3.11 with `feedparser` and `requests`
- **Auto-commit user**: `AutoUpdater <actions@github.com>`

## Development Guidelines

### Data Conventions

- **File format**: JSON with UTF-8 encoding (`ensure_ascii=False`)
- **Indentation**: 2 spaces in all JSON files
- **Filenames**: snake_case (e.g., `taxrates.json`, `exchange.json`)
- **Content language**: German for descriptions, explanations, and legal references; English for JSON keys
- **Structure**: Each domain directory contains exactly one JSON file
- **References**: Use official article/section numbers as identifiers (e.g., `"Art. 15 Abs. 1 DBA"`, `"§34c EStG"`)

### Adding New Data

1. Create a new directory named after the domain (lowercase, short)
2. Add a single JSON file with a descriptive snake_case name
3. Include `source` or `source_url` fields for traceability
4. If the source is an official publisher, add it to `policy/whitelist.json`

### Modifying the Update Script

- Script location: `.github/scripts/update_sources.py`
- Keep `max_items` reasonable (default: 10) to avoid bloating the repo
- Always use `ensure_ascii=False` and UTF-8 encoding for proper German/Turkish character support (ü, ö, ä, ş, ğ, İ)
- Use `os.makedirs(..., exist_ok=True)` before writing files

### Commit Messages

- Follow the established pattern: `Add <filename> with <brief description>`
- Auto-update commits use: `Auto-update BMF and BFH data`
- Write in English for commit messages

## No Build/Test/Lint Commands

This is a data repository. There are no:
- Build steps
- Test suites
- Linting or formatting tools
- Package managers (no `package.json`, `requirements.txt` at root)

The only executable code is `.github/scripts/update_sources.py`, which can be run locally with:

```bash
pip install feedparser requests
python .github/scripts/update_sources.py
```

## Important Context

- The data serves as a **ground truth layer** for AI/GPT-based tax compliance verification
- All sources must be from officially approved publishers listed in `policy/whitelist.json`
- The DBA evaluation rules in `dba/evaluate.json` encode German-Turkish double taxation treaty logic (183-day rule, exemption with progression reservation, etc.)
- Data accuracy is critical — these files inform real tax assessments
