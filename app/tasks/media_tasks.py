from app.core.celery_app import celery_app
from app.db.mongodb import create_client, get_database_from_client
from app.repositories.media_repository import MediaRepository
from app.services.media_service import MediaService


@celery_app.task(
    bind=True,
    max_retries=2,
    autoretry_for=(Exception,),
    retry_backoff=True
)
def download_video_task(self, url: str, target_format: str, quality_profile: str):
    """
    Celery task để download và convert video YouTube (SYNC version).

    Args:
        url: URL của video YouTube
        target_format: Định dạng đích (mp3, mp4, wav, webm)
        quality_profile: Chất lượng (320k, 1080p, etc.)

    Returns:
        dict: Kết quả conversion (file_path, download_url, etc.)

    Raises:
        Retry: Nếu lỗi → retry 2 lần với backoff
    """
    task_id = self.request.id

    # SYNC execution - no async loop needed
    client = create_client()
    try:
        db = get_database_from_client(client)
        repo = MediaRepository(db["media_tasks"])
        service = MediaService(repo)
        return service.process_download_sync(task_id, url, target_format, quality_profile)
    except Exception as e:
        # Auto retry với exponential backoff
        raise self.retry(exc=e, countdown=10)
    finally:
        client.close()
