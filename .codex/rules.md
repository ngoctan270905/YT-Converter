# Codex Rules for YouTube Converter Backend

## Overview
Backend for YouTube video conversion using FastAPI, Celery, Redis, MongoDB.

## Guidelines
- Async/await for all I/O.
- RORO with Pydantic models.
- Security: URL regex, enum formats.
- Progress: Redis keys, yt-dlp parsing.
- Errors: UnifiedResponse, Loguru.

## Examples
- Endpoint: Inject service, return UnifiedResponse.
- Task: @celery_app.task(bind=True).
- Schema: model_validator.

See AGENTS.md for more.
