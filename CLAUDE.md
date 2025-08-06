# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository Overview

御坂网络弹幕服务 (Misaka Danmu Server) is a self-hosted danmaku (bullet comment) aggregation and management service. It provides a private API compatible with the dandanplay specification, scraping danmaku from major Chinese video platforms and serving them through a modern web interface and REST API.

## Architecture Overview

### Core Components
- **FastAPI Backend**: RESTful API service with async operations (`src/main.py`)
- **MySQL Database**: Persistent storage with aiomysql for async operations
- **Web UI**: Vanilla JavaScript single-page application (`static/`)
- **Scrapers**: Modular scrapers for different video platforms (`src/scrapers/`)
- **Background Jobs**: APScheduler-based task system (`src/jobs/`)
- **Webhook Integration**: Media server integration (`src/webhook/`)

### Key Services
- **DanDanPlay API Compatibility**: Full compatibility layer (`src/dandan_api.py`)
- **Multi-source Scraping**: Bilibili, Tencent, iQiyi, Youku scrapers
- **Metadata Integration**: TMDB, TVDB, Bangumi, Douban, IMDb APIs
- **User Management**: JWT-based authentication with token system
- **Automation**: Webhook support for Sonarr, Radarr, Emby integration

### Configuration System
- **Hierarchical Config**: Environment variables > .env file > YAML > defaults
- **Pydantic Models**: Type-safe configuration with validation (`src/config.py`)
- **Environment Prefix**: All env vars use `DANMUAPI_` prefix
- **YAML Config**: Located at `config/config.yml`

## Development Commands

### UV-based Python Development (Recommended)
```bash
# Install uv if not already installed
curl -LsSf https://astral.sh/uv/install.sh | sh

# Create virtual environment and install dependencies
uv sync

# Install with development dependencies
uv sync --group dev

# Run application directly
uv run python -m src.main

# Run with custom uvicorn settings
uv run uvicorn src.main:app --host 127.0.0.1 --port 7768 --reload

# Run tests
uv run pytest

# Code formatting and linting
uv run black .
uv run isort .
uv run flake8 src/
uv run mypy src/

# Add new dependencies
uv add package_name
uv add --group dev package_name  # for dev dependencies

# Remove dependencies
uv remove package_name

# Update dependencies
uv sync --upgrade
```

### Legacy pip Development (Alternative)
```bash
# Install dependencies
pip install -r requirements.txt

# Run application directly
python -m src.main

# Run with custom uvicorn settings
uvicorn src.main:app --host 127.0.0.1 --port 7768 --reload
```

### Docker Development
```bash
# Build and run with Docker Compose (now uses uv)
docker-compose up -d

# View application logs
docker logs danmu-api

# Build image manually (now uses uv internally)
docker build -t misaka_danmu_server .

# Run with custom port mapping
docker run -p 7768:7768 misaka_danmu_server
```

### Database Management
```bash
# MySQL connection (from container environment variables)
# Host: 127.0.0.1 (or mysql container name)
# Port: 3306
# Database: danmuapi
# User: danmuapi
```

## Project Structure

### Source Code (`src/`)
- `main.py` - FastAPI application entry point with lifespan management
- `config.py` - Pydantic settings with YAML and environment variable support
- `database.py` - MySQL connection pool and async operations
- `models.py` - Pydantic data models for API requests/responses
- `crud.py` - Database CRUD operations for all entities
- `dandan_api.py` - DanDanPlay API compatibility layer
- `security.py` - JWT authentication and user management
- `scheduler.py` - APScheduler configuration and job management

### API Modules (`src/api/`)
- `ui.py` - Web interface API endpoints
- `tmdb_api.py` - The Movie Database integration
- `bangumi_api.py` - Bangumi.moe integration
- `tvdb_api.py` - TheTVDB integration
- `douban_api.py` - Douban integration
- `imdb_api.py` - IMDb integration
- `webhook_api.py` - Webhook endpoint handlers

### Scrapers (`src/scrapers/`)
- `base.py` - Abstract base class for all scrapers
- `bilibili.py` - Bilibili platform scraper
- `tencent.py` - Tencent Video scraper
- `iqiyi.py` - iQiyi platform scraper
- `youku.py` - Youku platform scraper

### Background Jobs (`src/jobs/`)
- `base.py` - Base job class with common functionality
- `tmdb_auto_map.py` - Automatic TMDB metadata mapping

### Webhook Integration (`src/webhook/`)
- `base.py` - Base webhook handler
- `emby.py` - Emby media server integration
- `tasks.py` - Webhook processing tasks

### Frontend (`static/`)
- `index.html` - Single-page application entry point
- `css/` - Modular CSS stylesheets
- `js/` - JavaScript modules for UI functionality

## Key Features

### Authentication System
- JWT-based user authentication with configurable expiration
- API token system for third-party client access
- Bcrypt password hashing with secure defaults
- Admin user auto-creation on first startup

### Danmaku Processing
- Multi-source scraping with priority and enable/disable controls
- Fuzzy string matching for accurate media identification
- Automatic metadata enrichment from multiple sources
- Smart caching to reduce API calls and improve performance

### Web Management Interface
- Search and manual danmaku import
- Media library and episode management
- API token creation and management
- Search source configuration and prioritization
- Background task monitoring and system logs

### Integration Capabilities
- DanDanPlay API compatibility for existing clients
- Webhook support for automated media server integration
- Configurable external API keys for metadata services
- Docker-based deployment with health checks

## Configuration

### Environment Variables
All configuration uses the `DANMUAPI_` prefix:
```bash
# Server configuration
DANMUAPI_SERVER__HOST=127.0.0.1
DANMUAPI_SERVER__PORT=7768

# Database configuration
DANMUAPI_DATABASE__HOST=127.0.0.1
DANMUAPI_DATABASE__PORT=3306
DANMUAPI_DATABASE__USER=danmuapi
DANMUAPI_DATABASE__PASSWORD=your_password
DANMUAPI_DATABASE__NAME=danmuapi

# JWT configuration
DANMUAPI_JWT__SECRET_KEY=your_secret_key
DANMUAPI_JWT__ALGORITHM=HS256
DANMUAPI_JWT__ACCESS_TOKEN_EXPIRE_MINUTES=1440

# Admin configuration
DANMUAPI_ADMIN__INITIAL_USER=admin
DANMUAPI_ADMIN__INITIAL_PASSWORD=auto_generated
```

### Default Ports and URLs
- **Application Port**: 7768
- **Web UI**: http://localhost:7768
- **API Endpoint**: http://localhost:7768/api/{token}
- **DanDanPlay Compatible**: http://localhost:7768/api/{token}/api/v2

## Deployment Notes

### Docker Deployment
- Uses non-root user (appuser:appgroup) for security
- Multi-stage build optimized for production
- Configurable PUID/PGID for file permissions
- Health checks and restart policies configured

### Database Requirements
- MySQL 8.1+ with utf8mb4 charset
- Required database: `danmuapi`
- Required user with full database permissions
- Connection pooling handled by aiomysql

### Security Considerations
- JWT tokens with configurable expiration
- API rate limiting through token system
- Non-root container execution
- Secure password hashing with bcrypt 4.0+
- Environment variable based secret management