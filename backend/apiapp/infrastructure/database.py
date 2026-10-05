import importlib
import pkgutil
from collections.abc import Sequence
from inspect import getmembers, isclass
from typing import TypeVar

import beanie
from loguru import logger
from pymongo import AsyncMongoClient

DocumentType = TypeVar("DocumentType", bound=beanie.Document)


class BeanieClient:
    def __init__(self):
        self.client = None
        self.database = None
        self.settings = None

    async def init_beanie(self, settings):
        """Initialize Beanie with MongoDB connection (MONGODB_URI; never logged, it may hold credentials)"""
        try:
            self.settings = settings
            logger.info("Connecting to MongoDB")

            # tz_aware: datetimes come back as aware UTC, same as the in-memory repositories
            self.client = AsyncMongoClient(
                settings.MONGODB_URI, tz_aware=True, serverSelectionTimeoutMS=5000
            )
            self.database = self.client.get_default_database(default=settings.MONGODB_DB)
            logger.debug(f"Using database: {self.database.name}")

            # Gather document models dynamically
            documents = self._gather_documents()

            if not documents:
                logger.warning(
                    "No document models found, Beanie initialization skipped"
                )
                return

            logger.info(f"Initializing Beanie with {len(documents)} models:")
            for document in documents:
                logger.info(f"  - {document.__name__}")

            await beanie.init_beanie(
                database=self.database,
                document_models=documents,
            )

            logger.info("Beanie initialization successful")

        except Exception as e:
            logger.error(f"Beanie initialization failed: {type(e).__name__}")
            raise

    def _gather_documents(self) -> Sequence[type[beanie.Document]]:
        """
        Dynamically gather all Beanie Document models from the modules
        """
        documents = []

        # Import the main modules package
        try:
            import apiapp.modules

            modules_package = apiapp.modules
        except ImportError:
            logger.warning("Could not import apiapp.modules package")
            return documents

        # Walk through all modules in the modules package
        for module_info in pkgutil.iter_modules(
            modules_package.__path__, f"{modules_package.__name__}."
        ):
            module_name = module_info.name
            logger.debug(f"Scanning module: {module_name}")

            try:
                # Try to import the model submodule
                model_module_name = f"{module_name}.model"
                model_module = importlib.import_module(model_module_name)

                # Get all classes from the model module
                for name, obj in getmembers(model_module, isclass):
                    # Check if it's a Beanie Document (but not the base Document class)
                    if (
                        issubclass(obj, beanie.Document)
                        and obj is not beanie.Document
                        and obj.__module__ == model_module_name
                    ):

                        logger.debug(
                            f"Found Document model: {name} in {model_module_name}"
                        )
                        documents.append(obj)

            except ImportError as e:
                # Some modules might not have a model.py file, that's okay
                logger.debug(f"No model module found for {module_name}: {e}")
                continue
            except Exception as e:
                logger.warning(f"Error scanning module {module_name}: {type(e).__name__}")
                continue

        return documents

    async def close(self):
        """Close MongoDB connection"""
        if self.client:
            await self.client.close()
            self.client = None
            logger.info("MongoDB connection closed")

    async def ping(self) -> bool:
        """Check database connection"""
        try:
            if self.client:
                await self.client.admin.command("ping")
                return True
            return False
        except Exception as e:
            logger.error(f"Database ping failed: {type(e).__name__}")
            return False
