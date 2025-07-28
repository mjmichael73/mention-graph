from fastapi import FastAPI, UploadFile, File
import csv


app = FastAPI(title="Efficient Mention Graph Storage")


@app.post("/upload_csv")
async def upload_csv(file: UploadFile = File(...)):
    reader = csv.reader((line.decode("utf-8") for line in file.file))
    next(reader)  # Skip header row
    count = 0
    for row in reader:
        data, timestamp, username = row
        count += 1
    return {"message": f"Processed {count} rows from the CSV file."}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
