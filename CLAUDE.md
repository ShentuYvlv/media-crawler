# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

MediaCrawler is a multi-platform Chinese social media crawler framework supporting 7 platforms: XiaoHongShu (xhs), Douyin (dy), Bilibili (bili), Kuaishou (ks), Weibo (wb), Baidu Tieba (tieba), and Zhihu (zhihu).

## Commands

### Setup
```bash
cd MediaCrawler
uv sync                          # Install dependencies
uv run playwright install        # Install browser drivers
```

### Running the Crawler
```bash
# Show help
uv run main.py --help

# Search mode (keyword search)
uv run main.py --platform xhs --lt qrcode --type search

# Detail mode (specific post IDs)
uv run main.py --platform xhs --lt qrcode --type detail

# Creator mode (creator homepage)
uv run main.py --platform xhs --lt qrcode --type creator

# With storage options
uv run main.py --platform xhs --lt qrcode --type search --save_data_option sqlite
uv run main.py --platform xhs --lt qrcode --type search --save_data_option excel

# Initialize database
uv run main.py --init_db sqlite    # or mysql, postgres
```

### Testing
```bash
uv run pytest                      # Run all tests
uv run pytest test/test_db_sync.py # Run specific test
```

### Code Quality
```bash
pre-commit install                 # Install hooks
pre-commit run --all-files         # Run on all files
```

### Bilibili Standalone Spider
```bash
source venv/bin/activate
python bilibili_spider/search_cli.py "关键词" --num 20 --excel-name output
```

## Architecture

### Core Pattern: Factory + Abstract Base Classes
- `CrawlerFactory` (main.py) creates platform-specific crawlers
- `AbstractCrawler`, `AbstractLogin`, `AbstractStore` (base/base_crawler.py) define contracts
- Each platform implements these in `media_platform/<platform>/`

### Key Directories
| Directory | Purpose |
|-----------|---------|
| `config/` | Platform-specific and base configuration (pydantic settings) |
| `media_platform/` | Platform crawler implementations (core.py, client.py, login.py) |
| `store/` | Data storage implementations per platform |
| `model/` | Pydantic data models for each platform |
| `database/` | SQLAlchemy ORM models and session management |
| `cache/` | Abstract cache interface with local/redis implementations |
| `proxy/` | Proxy IP pool management with multiple providers |
| `tools/` | Browser launcher, CDP utilities, captcha handling |
| `libs/` | JavaScript signature generation (douyin.js, zhihu.js) |

### Login Types
- `qrcode` - QR code scan (recommended)
- `phone` - Phone number + SMS
- `cookie` - Manual cookie input

### Crawler Types
- `search` - Keyword-based search
- `detail` - Specific post IDs from config
- `creator` - Creator profile crawling

### Storage Options
- `csv`, `json`, `jsonl` - File-based
- `excel` - Excel format
- `sqlite`, `mysql`, `postgres`, `mongodb` - Database

## Configuration

Copy `.env.example` to `.env` and configure:
- Database credentials (MySQL, Redis, MongoDB, PostgreSQL)
- Proxy provider keys (Wandou, Kuaidaili)

Key settings in `config/base_config.py`:
- `PLATFORM` - Target platform code
- `KEYWORDS` - Comma-separated search keywords
- `CRAWLER_MAX_NOTES_COUNT` - Max posts per crawl
- `ENABLE_CDP_MODE` - Use Chrome DevTools Protocol (default: True)
- `HEADLESS` - Headless browser mode
- `ENABLE_GET_COMMENTS` - Crawl comments
- `ENABLE_IP_PROXY` - Enable proxy rotation

## Important Notes

- **Node.js v16+ required** for Douyin and Zhihu signature generation
- **CDP mode** connects to real Chrome/Edge for better anti-detection
- Login state persisted in `browser_data/` - delete to switch accounts
- Output data stored in `data/` directory
- License: Non-commercial learning only
