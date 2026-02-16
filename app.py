from fastapi import FastAPI, UploadFile, File
import os, shutil

app = FastAPI()

def run_ingest(path: str):
    """Ingest the dataset from the given file path."""
    pass

@app.post("/dataset/upload")
async def upload_dataset(file: UploadFile = File(...)):
    os.makedirs("data", exist_ok=True)
    path = os.path.join("data", "Samip Gajurel Interns Tracking Sheet - Sheet1.csv")
    with open(path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    run_ingest(path)
    return {"message": "Dataset uploaded and ingested successfully"}
