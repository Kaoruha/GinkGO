# Upstream: Alembic CLI (数据库迁移工具)
# Downstream: MySQL Database (Ginkgo生产数据库)
# Role: Alembic环境配置 - 连接Ginkgo MySQL数据库支持在线/离线迁移模式


from logging.config import fileConfig
import sys
from pathlib import Path

from sqlalchemy import engine_from_config
from sqlalchemy import pool

from alembic import context

# Add project root to path to import ginkgo modules
project_root = Path(__file__).parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Import GCONF for database connection settings
from ginkgo.libs import GCONF

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Set the database URL from GCONF
mysql_url = (
    f"mysql+pymysql://{GCONF.MYSQLUSER}:{GCONF.MYSQLPWD}"
    f"@{GCONF.MYSQLHOST}:{GCONF.MYSQLPORT}/{GCONF.MYSQLDB}"
    f"?charset=utf8mb4"
)
config.set_main_option("sqlalchemy.url", mysql_url)

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Import all models here for autogenerate support
# We need to import all models that have tables to be migrated
target_metadata = None

# Add your model's MetaData object here for 'autogenerate' support
# Uncomment and modify as needed when creating migrations:
# from ginkgo.data.models import *
# target_metadata = SQLModel.metadata

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        compare_server_default=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            compare_server_default=True,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
