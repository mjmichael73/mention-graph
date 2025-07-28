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
from sqlalchemy.sql import text

# Configure SQLAlchemy logger
sqlalchemy_logger = logging.getLogger("sqlalchemy.engine")
sqlalchemy_logger.setLevel(logging.WARNING)
sqlalchemy_logger.propagate = False

# Redis setup (for Celery broker, not locking)
REDIS_URL = os.getenv("REDIS_URL", "redis://mentions-graph-redis:6379/0")
redis_client = redis.StrictRedis.from_url(REDIS_URL, decode_responses=True)

mention_pattern = re.compile(r"@(\w+)")
logger = logging.getLogger(__name__)


def chunked(iterable, chunk_size):
    iterator = iter(iterable)
    while chunk := list(islice(iterator, chunk_size)):
        yield chunk


def process_batch_mentions(db, rows, task_id, batch_size=10000):
    # Acquire locks on Nodes and Edges tables in ACCESS EXCLUSIVE mode
    db.execute(text("LOCK TABLE nodes IN ACCESS EXCLUSIVE MODE;"))
    db.execute(text("LOCK TABLE edges IN ACCESS EXCLUSIVE MODE;"))
    logger.info(f"Task {task_id}: Acquired locks on Nodes and Edges tables")
    try:
        all_usernames = []
        for r in rows:
            all_usernames.append(r["username"])
            all_usernames.extend(r["mentions"])
        unique_users = sorted(set(all_usernames))
        stmt_nodes = insert(Node).values([{"username": u} for u in unique_users])
        stmt_nodes = stmt_nodes.on_conflict_do_nothing(index_elements=["username"])
        db.execute(stmt_nodes)
        db.commit()

        # Fetch node IDs
        user_map = {
            n.username: n.id
            for n in db.query(Node).filter(Node.username.in_(unique_users)).all()
        }

        if len(user_map) != len(unique_users):
            return "Error: Missing usernames in user_map"
        
        # Collect and sort edge pairs
        edge_pairs = set()
        for r in rows:
            src_id = user_map.get(r["username"])
            if src_id is None:
                return f"Error: Username {r['username']} not found"
            for target in r["mentions"]:
                tgt_id = user_map.get(target)
                if tgt_id is None:
                    return f"Error: Mention {target} not found"
                edge_pairs.add((src_id, tgt_id))
        edge_pairs = sorted(edge_pairs)
        now = datetime.now(timezone.utc)
        edge_dict = defaultdict(int)
        for r in rows:
            src_id = user_map[r["username"]]
            for target in r["mentions"]:
                tgt_id = user_map[target]
                edge_dict[(src_id, tgt_id)] += 1
        edge_rows = [
            {
                "source_id": src_id,
                "target_id": tgt_id,
                "weight": weight,
                "last_updated": now,
            }
            for (src_id, tgt_id), weight in edge_dict.items()
        ]
        for i, chunk in enumerate(chunked(edge_rows, batch_size)):
            stmt_edges = insert(Edge).values(chunk)
            stmt_edges = stmt_edges.on_conflict_do_update(
                constraint="uq_source_target",
                set_={
                    "weight": Edge.weight + stmt_edges.excluded.weight,
                    "last_updated": now,
                },
            )
            db.execute(stmt_edges)
            logger.info(
                f"Task {task_id}: Processed edge chunk {i + 1} ({len(chunk)} edges)"
            )
        db.commit()
    except Exception as e:
        logger.error(f"Failed syncing edges to DB. {str(e)}")
        db.rollback()
        raise


@celery.task(bind=True, max_retries=3, retry_backoff=True)
def sync_mentions_to_db(self, rows):
    logger.info(f"Task {self.request.id} started processing {len(rows)} rows...")
    db = SessionLocal()
    try:
        batch_data = []
        for r in rows:
            mentions = mention_pattern.findall(r["data"])
            if mentions:
                batch_data.append({"username": r["username"], "mentions": mentions})
        if batch_data:
            result = process_batch_mentions(db, batch_data, task_id=self.request.id)
            logger.info(f"Task {self.request.id}: {result}")
            return result
        else:
            logger.info(f"Task {self.request.id}: No mentions found to process.")
            return "No mentions found to process."
    except Exception as e:
        logger.error(f"Task {self.request.id} failed: {str(e)}")
        db.rollback()
        raise
    finally:
        try:
            db.close()
        except Exception as e:
            logger.warning(
                f"Task {self.request.id}: Error closing database session: {str(e)}"
            )
