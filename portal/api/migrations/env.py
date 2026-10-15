from alembic import context
from sqlalchemy import create_engine

from portal_api.config import Settings

url = context.config.get_main_option("sqlalchemy.url") or Settings().database_url

with create_engine(url).connect() as connection:
    context.configure(connection=connection, target_metadata=None)
    with context.begin_transaction():
        context.run_migrations()
