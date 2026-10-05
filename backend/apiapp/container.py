"""Composition root: picks the repository implementations from MONGODB_URI (empty = memory, W2; set = MongoDB, W6)
and wires the services. Shared by the API process and the worker process."""

from dataclasses import dataclass, field

from loguru import logger

from .core.config import Settings
from .infrastructure.database import BeanieClient
from .infrastructure.storage import ImageStorage
from .modules.inspections.repository import InspectionRepo, MemoryInspectionRepo, MongoInspectionRepo
from .modules.inspections.use_case import InspectionService
from .modules.layouts.repository import LayoutRepo, MemoryLayoutRepo, MongoLayoutRepo
from .modules.layouts.use_case import LayoutService
from .modules.model_bundles.repository import (
    MemoryModelBundleRepo,
    MemoryWorkerStatusRepo,
    ModelBundleRepo,
    MongoModelBundleRepo,
    MongoWorkerStatusRepo,
    WorkerStatusRepo,
)
from .modules.uploads.repository import MemoryUploadRepo, MongoUploadRepo, UploadRepo
from .modules.uploads.use_case import UploadService


@dataclass
class Container:
    settings: Settings
    storage: ImageStorage
    uploads: UploadRepo
    inspections: InspectionRepo
    layouts: LayoutRepo
    worker_status: WorkerStatusRepo
    model_bundles: ModelBundleRepo
    db: BeanieClient | None = None
    upload_service: UploadService = field(init=False)
    layout_service: LayoutService = field(init=False)
    inspection_service: InspectionService = field(init=False)

    def __post_init__(self) -> None:
        self.upload_service = UploadService(self.settings, self.storage, self.uploads)
        self.layout_service = LayoutService(self.layouts)
        self.inspection_service = InspectionService(self.settings, self.inspections, self.upload_service,
                                                    self.layout_service)

    async def close(self) -> None:
        if self.db is not None:
            await self.db.close()


async def build_container(settings: Settings, *, seed_layouts: bool = True) -> Container:
    storage = ImageStorage(settings.STORAGE_ROOT)
    storage.init()
    if settings.memory_mode:
        logger.info("storage mode: memory (MONGODB_URI empty)")
        c = Container(settings, storage, MemoryUploadRepo(), MemoryInspectionRepo(), MemoryLayoutRepo(),
                      MemoryWorkerStatusRepo(), MemoryModelBundleRepo())
    else:
        logger.info("storage mode: mongodb")
        db = BeanieClient()
        await db.init_beanie(settings)
        c = Container(settings, storage, MongoUploadRepo(), MongoInspectionRepo(), MongoLayoutRepo(),
                      MongoWorkerStatusRepo(), MongoModelBundleRepo(), db=db)
    if seed_layouts:
        await c.layout_service.seed(settings.LAYOUTS_DIR)
    return c
