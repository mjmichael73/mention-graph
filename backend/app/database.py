from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
import os
import logging


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:password@mentions-graph-db:5432/mention_graph_db",
)

engine = create_engine(
    DATABASE_URL,
    future=True,
    echo=False,
    pool_size=1000,  # Number of connections to keep open (Adjust it based on needs)
    max_overflow=10,  # Number of connections to allow beyond pool_size
    pool_timeout=30,  # Timeout for getting a connection from the pool
)

# Log pool configuration
logger.info(
    f"SQLAlchemy Engine created with pool_size={engine.pool.size()}, "
    f"max_overflow={engine.pool._max_overflow}, "
    f"pool_timeout={engine.pool._timeout}"
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()
