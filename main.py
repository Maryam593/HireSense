from fastapi import FastAPI, File, HTTPException, UploadFile
from pymongo import MongoClient
from fastapi.middleware.cors import CORSMiddleware
import shutil
import os
from fastapi.responses import FileResponse, JSONResponse

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # React ka origin
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# MongoDB se connect ho rahe hain
client = MongoClient("mongodb://localhost:27017/")
print("connected")
db = client['file_database']
collection = db['files']
os.makedirs("data", exist_ok=True) 
@app.post("/uploadfile")
async def create_upload_file(file: UploadFile = File(...)):
    file_location = f"data/{file.filename}" 
    with open(file_location, "wb") as f:
        shutil.copyfileobj(file.file, f)

    collection.insert_one({"filename": file.filename, "location": file_location})

    return {"filename": file.filename, "location": file_location}

#connect to collab
@app.get("/list-files")
def list_files():
    folder_path = "data"
    try:
        files = os.listdir(folder_path)
        return JSONResponse(content={"files": files})
    except FileNotFoundError:
        return JSONResponse(content={"error": "Folder not found"}, status_code=404)
    
@app.get("/download-file")
async def download_file(filename: str):
    file_path = f"data/{filename}"
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(file_path, filename=filename)