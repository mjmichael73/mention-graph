import logging
import os
import re
from datetime import datetime, timezone
from collections import defaultdict

import redis
from app.celery_app import celery
from app.database import SessionLocal
from app.models import Edge, Node
from sqlalchemy.dialects.postgresql import insert
from itertools import islice

# Configure SQLAlchemy logger to suppress batch statement logs
sqlalchemy_logger = logging.getLogger("sqlalchemy.engine")
sqlalchemy_logger.setLevel(logging.WARNING)
sqlalchemy_logger.propagate = False  # Prevent logs from propagating to parent loggers

# Redis setup
REDIS_URL = os.getenv("REDIS_URL", "redis://mentions-graph-redis:6379/0")
redis_client = redis.StrictRedis.from_url(REDIS_URL, decode_responses=True)

mention_pattern = re.compile(r"@(\w+)")

# Configure logging
logger = logging.getLogger(__name__)


def chunked(iterable, chunk_size):
    """Yield chunks of the given iterable with the specified size."""
    iterator = iter(iterable)
    while chunk := list(islice(iterator, chunk_size)):
        yield chunk

def process_batch_mentions(db, rows, batch_size=10000):
    """
    Insert/update nodes & edges in batch with chunked edge upserts.
    rows: list of {"username": str, "mentions": [str, ...]}
    batch_size: number of edges per chunk
    """
    # Collect all users
    all_usernames = []
    for r in rows:
        all_usernames.append(r["username"])
        all_usernames.extend(r["mentions"])

    unique_users = list(set(all_usernames))

    # Bulk insert nodes (idempotent)
    stmt_nodes = insert(Node).values([{"username": u} for u in unique_users])
    stmt_nodes = stmt_nodes.on_conflict_do_nothing(index_elements=["username"])
    db.execute(stmt_nodes)
    db.commit()
    logger.info(f"Inserted/updated {len(unique_users)} nodes.")

    # Map username → id
    user_map = {
        n.username: n.id
        for n in db.query(Node).filter(Node.username.in_(unique_users)).all()
    }

    # Prepare edges with aggregation
    now = datetime.now(timezone.utc)
    edge_dict = defaultdict(int)  # (source_id, target_id) → weight
    for r in rows:
        src_id = user_map[r["username"]]
        for target in r["mentions"]:
            tgt_id = user_map[target]
            edge_dict[(src_id, tgt_id)] += 1

    # Convert aggregated edges to rows
    edge_rows = [
        {
            "source_id": src_id,
            "target_id": tgt_id,
            "weight": weight,
            "last_updated": now,
        }
        for (src_id, tgt_id), weight in edge_dict.items()
    ]

    # Bulk upsert edges in chunks
    total_edges = len(edge_rows)
    logger.info(f"Processing {total_edges} unique edges in chunks of {batch_size}.")
    for i, chunk in enumerate(chunked(edge_rows, batch_size)):
        stmt_edges = insert(Edge).values(chunk)
        stmt_edges = stmt_edges.on_conflict_do_update(
            index_elements=["source_id", "target_id"],
            set_={"weight": Edge.weight + stmt_edges.excluded.weight, "last_updated": now},
        )
        try:
            db.execute(stmt_edges)
            db.commit()
            logger.info(f"Successfully processed edge chunk {i + 1} ({len(chunk)} edges).")
        except Exception as e:
            logger.error(f"Error inserting edge chunk {i + 1}: {str(e)}")
            db.rollback()
            return f"Error inserting edge chunk {i + 1}: {str(e)}"

    return f"Successfully inserted/updated {total_edges} unique edges in {i + 1} chunks."

@celery.task
def sync_mentions_to_db(rows):
    logger.info("Syncing mentions to database...")
    db = SessionLocal()
    try:
        batch_data = []
        for r in rows:
            mentions = mention_pattern.findall(r["data"])
            if mentions:
                batch_data.append({"username": r["username"], "mentions": mentions})
        if batch_data:
            result = process_batch_mentions(db, batch_data)
            logger.info(result)
            return result
        else:
            logger.info("No mentions found to process.")
            return "No mentions found to process."
    except Exception as e:
        logger.error(f"Error processing mentions: {str(e)}")
        db.rollback()
        return f"Error processing mentions: {str(e)}"
    finally:
        db.close()