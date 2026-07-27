from typing import List,Optional
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from pymongo import MongoClient
from hiresense import evaluate_resumes_and_send_emails
from fastapi.middleware.cors import CORSMiddleware
import shutil
import os
from fastapi.responses import FileResponse, JSONResponse

app = FastAPI()

DATA_DIR = os.path.abspath("data")


def safe_data_path(filename: str) -> str:
    """Resolve filename against DATA_DIR, rejecting any path traversal attempt."""
    candidate = os.path.abspath(os.path.join(DATA_DIR, os.path.basename(filename)))
    if not candidate.startswith(DATA_DIR + os.sep):
        raise HTTPException(status_code=400, detail="Invalid filename")
    return candidate

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
async def create_upload_file(files: List[UploadFile] = File(...)):
    os.makedirs("data", exist_ok=True)  
    saved_files_info = []
    for file in files:
        file_location = safe_data_path(file.filename)
        with open(file_location, "wb") as f:
            shutil.copyfileobj(file.file, f)
        collection.insert_one({
            "filename": file.filename,
            "location": file_location
        })
        saved_files_info.append({
            "filename": file.filename,
            "location": file_location
        })

    return {"uploaded_files": saved_files_info}

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
    file_path = safe_data_path(filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(file_path, filename=os.path.basename(filename))

#for deleting
@app.delete("/delete-file")
async def delete_file(filename: str):
    file_path = safe_data_path(filename)

    # Check if the file exists
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found")
    
    # Attempt to delete the file
    try:
        os.remove(file_path)
        return {"message": f"File '{filename}' deleted successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error deleting file: {str(e)}")

#extracting result
@app.post('/evaluate-resumes')
async def evaluate_resumes_endpoint():
    try:
        evaluate_resumes_and_send_emails()

        return JSONResponse(
            content={"message": "Resume evaluation and email sending process initiated. Check server logs for details."},
            status_code=200
        )

    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        print(f"An error occurred: {e}")
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {str(e)}")
