from motor.motor_asyncio import AsyncIOMotorGridFSBucket
import bson
from .database import beanie_client


class File:
    def __init__(
        self,
        bucket_name="fs",
        chunk_size_bytes=261120,
        write_concern=None,
        read_preference=None,
        collection_name=None,
        file_id=None,
    ):
        self.bucket_name = bucket_name
        self.chunk_size_bytes = chunk_size_bytes
        self.write_concern = write_concern
        self.read_preference = read_preference
        self.collection_name = collection_name or "fs"

        self.collection = self.collection_name
        if not self.collection.endswith("_fs"):
            self.collection = f"{self.collection}_fs"

        self.db = None
        self.fs = None
        self.file_id = file_id

    async def init(self):
        self.db = beanie_client.database
        self.fs = AsyncIOMotorGridFSBucket(
            self.db,
            bucket_name=self.bucket_name,
            chunk_size_bytes=self.chunk_size_bytes,
            write_concern=self.write_concern,
            read_preference=self.read_preference,
            collection=self.collection,
        )

    async def get_gridfs(self):
        if self.db is None or self.fs is None:
            await self.init()
        return self.fs

    async def put(self, data, metadata=None):
        metadata = metadata or {}
        fs = await self.get_gridfs()

        if isinstance(data, bytes):
            filename = metadata.get("filename", str(bson.ObjectId()))
            file_id = await fs.upload_from_stream(
                filename, data, metadata=metadata
            )
        else:
            if "filename" not in metadata and hasattr(data, "filename"):
                metadata["filename"] = data.filename
            if "content_type" not in metadata and hasattr(data, "content_type"):
                metadata["content_type"] = data.content_type

            file_id = await fs.upload_from_stream(
                getattr(data, "filename", str(bson.ObjectId())),
                data.file,
                metadata=metadata,
            )

        self.file_id = file_id
        return file_id

    async def get(self):
        fs = await self.get_gridfs()
        grid_out = await fs.open_download_stream(self.file_id)
        return grid_out

    async def delete(self):
        fs = await self.get_gridfs()
        await fs.delete(self.file_id)
