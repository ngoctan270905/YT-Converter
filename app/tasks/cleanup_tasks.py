from pathlib import Path
import time, os
from app.core.celery_app import celery_app
from app.core.config import settings
from loguru import logger

@celery_app.task
def cleanup_old_files_task():
    download_path = Path(settings.DOWNLOADS_DIR)
    if not download_path.exists(): return "Folder not found."
    now = time.time()
    deleted_count = 0
    for file in download_path.glob("*"):
        if file.is_file() and (now - os.path.getmtime(file) > 86400):
            try: os.remove(file); deleted_count += 1
            except: pass
    return f"Deleted {deleted_count} files."