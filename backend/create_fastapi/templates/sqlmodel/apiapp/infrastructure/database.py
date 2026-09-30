import importlib
import pkgutil
from typing import AsyncGenerator
from inspect import getmembers, isclass
from loguru import logger
from sqlmodel import SQLModel, create_engine
from sqlalchemy.ext.asyncio import create_async_engine
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlalchemy.orm import sessionmaker

class DatabaseClient:
    def __init__(self):
        self.engine = None
        self.session_maker = None
        self.settings = None

    async def init_db(self, settings):
        """Initialize SQLModel with PostgreSQL connection"""
        try:
            self.settings = settings
            logger.info(f"Connecting to Database: {settings.DATABASE_URI}")

            # Create async engine
            self.engine = create_async_engine(
                settings.DATABASE_URI, 
                echo=settings.DEBUG,
                future=True,
                pool_size=20,
                max_overflow=10,
                pool_pre_ping=True,
            )

            # Create session maker
            self.session_maker = sessionmaker(
                self.engine, class_=AsyncSession, expire_on_commit=False
            )

            # Gather SQLModel models dynamically so they are registered with SQLModel.metadata
            models = self._gather_models()

            if not models:
                logger.warning("No SQLModel models found")
            else:
                logger.info(f"Initialized database with {len(models)} models")

            # Create all tables (in a real app, use Alembic migrations instead)
            async with self.engine.begin() as conn:
                await conn.run_sync(SQLModel.metadata.create_all)

            logger.info("Database initialization successful")

        except Exception as e:
            logger.error(f"Database initialization failed: {e}")
            raise

    def _gather_models(self) -> list:
        """
        Dynamically gather all SQLModel models from the modules
        """
        models = []

        # Import the main modules package
        try:
            import apiapp.modules
            modules_package = apiapp.modules
        except ImportError:
            logger.warning("Could not import apiapp.modules package")
            return models

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
                    # Check if it's a SQLModel (but not the base SQLModel class)
                    if (
                        issubclass(obj, SQLModel)
                        and obj is not SQLModel
                        and obj.__module__ == model_module_name
                    ):
                        logger.debug(
                            f"Found SQLModel: {name} in {model_module_name}"
                        )
                        models.append(obj)

            except ImportError as e:
                logger.debug(f"No model module found for {module_name}: {e}")
                continue
            except Exception as e:
                logger.warning(f"Error scanning module {module_name}: {e}")
                continue

        return models

    async def close(self):
        """Close Database connection"""
        if self.engine:
            await self.engine.dispose()
            logger.info("Database connection closed")

    async def ping(self) -> bool:
        """Check database connection"""
        try:
            if self.engine:
                async with self.engine.begin() as conn:
                    from sqlalchemy import text
                    await conn.execute(text("SELECT 1"))
                return True
            return False
        except Exception as e:
            logger.error(f"Database ping failed: {e}")
            return False


# Global db client instance
db_client = DatabaseClient()


async def init_db(settings):
    """Initialize DB with settings"""
    await db_client.init_db(settings)


async def close_db():
    """Close DB connection"""
    await db_client.close()


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Dependency to provide the DB session"""
    async with db_client.session_maker() as session:
        yield session
