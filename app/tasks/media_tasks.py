import asyncio
from app.core.celery_app import celery_app
from app.db.mongodb import connect_to_mongo, get_database, close_mongo_connection, create_client, \
    get_database_from_client
from app.repositories.media_repository import MediaRepository
from app.services.media_service import MediaService

@celery_app.task(
    bind=True,
    max_retries=2,
    autoretry_for=(Exception,),
    retry_backoff=True
)
def download_video_task(self, url: str, target_format: str, quality_profile: str):
    task_id = self.request.id

    async def run():
        client = create_client()  # tạo client trong loop hiện tại
        try:
            db = get_database_from_client(client)
            repo = MediaRepository(db["media_tasks"])
            service = MediaService(repo)
            return await service.process_download(task_id, url, target_format, quality_profile)
        finally:
            await client.close()

    try:
        return asyncio.run(run())
    except Exception as e:
        raise self.retry(exc=e, countdown=10)