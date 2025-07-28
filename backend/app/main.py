from fastapi import FastAPI, UploadFile, File
import csv
import os
import redis
from app.tasks import sync_mentions_to_db


REDIS_URL = os.environ.get("REDIS_URL", "redis://mentions-graph-redis:6379/0")
redis_client = redis.StrictRedis.from_url(REDIS_URL, decode_responses=True)


app = FastAPI(title="Efficient Mention Graph Storage")


@app.post("/upload_csv")
async def upload_csv(file: UploadFile = File(...)):
    reader = csv.reader((line.decode("utf-8") for line in file.file))
    next(reader)
    count = 0
    rows = []
    for row in reader:
        data, timestamp, username = row
        rows.append({"data": data, "timestamp": timestamp, "username": username})
        count += 1
    sync_mentions_to_db.delay(rows)
    return {"message": f"Processed {count} rows from the CSV file."}
