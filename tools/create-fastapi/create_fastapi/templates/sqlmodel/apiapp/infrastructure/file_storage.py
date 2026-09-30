import os
import uuid
import shutil
from fastapi import UploadFile
from pathlib import Path

UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

class File:
    def __init__(
        self,
        collection_name=None,
        file_id=None,
    ):
        self.collection_name = collection_name or "default"
        self.file_id = file_id or str(uuid.uuid4())
        
        self.collection_dir = UPLOAD_DIR / self.collection_name
        self.collection_dir.mkdir(exist_ok=True)
        
        self.file_path = self.collection_dir / self.file_id

    async def put(self, data: UploadFile) -> str:
        with open(self.file_path, "wb") as buffer:
            shutil.copyfileobj(data.file, buffer)
        return self.file_id

    def get_path(self) -> str:
        return str(self.file_path)

    async def delete(self):
        if self.file_path.exists():
            os.remove(self.file_path)
