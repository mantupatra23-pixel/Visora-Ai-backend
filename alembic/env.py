# alembic/env.py (snippet)
from logging.config import fileConfig
import os
from sqlalchemy import engine_from_config, pool
from alembic import context
config = context.config
fileConfig(config.config_file_name)
from models.billing import Base
target_metadata = Base.metadata
def get_url():
    return os.getenv("FARM_DATABASE_URL", "postgresql+psycopg2://postgres:postgres@localhost:5432/visora")
config.set_main_option("sqlalchemy.url", get_url())
# then usual alembic run_migrations_online code...
