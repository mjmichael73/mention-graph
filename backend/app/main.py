from fastapi import FastAPI, UploadFile, File
import csv
from app.tasks import sync_mentions_to_db


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
