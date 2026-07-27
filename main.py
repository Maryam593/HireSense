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

allowed_origins = [
    origin.strip()
    for origin in os.environ.get("FRONTEND_ORIGINS", "http://localhost:5173").split(",")
    if origin.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# MongoDB se connect ho rahe hain
client = MongoClient(os.environ.get("MONGO_URI", "mongodb://localhost:27017/"))
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

@app.get("/debug-mongo")
def debug_mongo():
    import socket, ssl, time
    host = os.environ.get("MONGO_URI", "").split("@")[-1].split("/")[0].split(",")[0] or "ac-zpx2nta-shard-00-00.zohxkil.mongodb.net"
    results = {"openssl_version": ssl.OPENSSL_VERSION, "target_host": host}

    try:
        ctx = ssl.create_default_context()
        start = time.time()
        with socket.create_connection((host, 27017), timeout=10) as sock:
            with ctx.wrap_socket(sock, server_hostname=host) as ssock:
                results["raw_tls_default"] = {"ok": True, "version": ssock.version(), "elapsed": time.time() - start}
    except Exception as e:
        results["raw_tls_default"] = {"ok": False, "error": str(e)}

    try:
        ctx2 = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        ctx2.minimum_version = ssl.TLSVersion.TLSv1_2
        ctx2.maximum_version = ssl.TLSVersion.TLSv1_2
        with socket.create_connection((host, 27017), timeout=10) as sock:
            with ctx2.wrap_socket(sock, server_hostname=host) as ssock:
                results["raw_tls_forced_1_2"] = {"ok": True, "version": ssock.version()}
    except Exception as e:
        results["raw_tls_forced_1_2"] = {"ok": False, "error": str(e)}

    try:
        result = client.admin.command("ping")
        results["pymongo_ping"] = {"ok": True, "result": result}
    except Exception as e:
        results["pymongo_ping"] = {"ok": False, "error": str(e)}

    return results

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
