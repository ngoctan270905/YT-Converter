# AGENTS.md - YouTube Converter Backend

## Architecture Overview
- **FastAPI** async web framework with **Celery** for background media processing tasks
- **Redis** as Celery broker/backend and progress cache
- **MongoDB** for task persistence and metadata
- **yt-dlp** + **ffmpeg** for video download/conversion (paths configured via env)
- Async-first design with `asyncio.create_subprocess_exec` for external commands

## Key Components
- `app/api/v1/endpoints/media.py`: REST endpoints (`/info`, `/convert`, `/task/{id}`, `/download/{id}`)
- `app/services/media_service.py`: Business logic, progress tracking, file management
- `app/tasks/media_tasks.py`: Celery tasks for async processing
- `app/repositories/media_repository.py`: MongoDB operations
- `app/schemas/media.py`: Pydantic models with validation (enums for formats/qualities, URL regex)

## Critical Workflows
- **Start services**: `celery -A app.core.celery_app worker -l info -Q default,media,maintenance --pool=solo` + `celery -A app.core.celery_app beat --loglevel=info`
- **Testing**: `pytest` with `conftest.py` providing async httpx client fixture
- **File handling**: UUID-based filenames in `static/downloads/`, auto-cleanup after 24h via scheduled Celery task

## References
- **Development Rules**: See `AI_spec/AI_prompt_base.md` for async patterns, RORO, security, testing, deployment
- **Feature Specs**: See `AI_spec/SPEC_XXX/` for specific feature requirements and implementation details
