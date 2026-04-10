from typing import Optional, List
from pymongo.asynchronous.collection import AsyncCollection


class MediaRepository:
    """
    Repository thao tác trực tiếp với MongoDB collection 'media_tasks'.
    Tuân thủ nghiêm ngặt repository_rules.md.
    """
    def __init__(self, collection: AsyncCollection):
        """
        Khởi tạo repository với collection được truyền từ Service/Dependency.
        """
        self.collection = collection

    async def create_task(self, data: dict) -> bool:
        """
        Thêm một bản ghi task mới.
        """
        result = await self.collection.insert_one(data)
        return result.acknowledged

    async def update_task(self, task_id: str, data: dict) -> bool:
        """
        Cập nhật thông tin task theo ID.
        """
        result = await self.collection.update_one(
            {"_id": task_id},
            {"$set": data}
        )
        return result.modified_count > 0

    async def get_task_by_id(self, task_id: str) -> Optional[dict]:
        """
        Lấy dữ liệu thô của một task.
        """
        task = await self.collection.find_one({"_id": task_id})
        if task and "_id" in task:
            task["_id"] = str(task["_id"])
        return task

    async def get_latest_tasks(self, limit: int = 20) -> List[dict]:
        """
        Lấy danh sách các task gần đây nhất.
        """
        cursor = self.collection.find().sort("created_at", -1).limit(limit)
        tasks = await cursor.to_list(length=limit)
        
        for task in tasks:
            if "_id" in task:
                task["_id"] = str(task["_id"])
        
        return tasks

    async def delete_task(self, task_id: str) -> bool:
        """
        Xóa một task khỏi database.
        """
        result = await self.collection.delete_one({"_id": task_id})
        return result.deleted_count > 0
