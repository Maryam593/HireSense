import { useState } from 'react';
import './App.css';
import axios from 'axios';

function App() {
  const [files, setFiles] = useState<File[]>([]);

  const handleUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFiles = e.target.files;
    if (selectedFiles) {
      setFiles(Array.from(selectedFiles)); // Convert FileList to array
    }
  };

  const handleSubmit = async () => {
    const formData = new FormData();
    files.forEach((file) => {
      formData.append("file", file); // 👈 match this key with UploadFile = File(...) in FastAPI
    });
  
    try {
      const response = await axios.post("http://localhost:8000/uploadfile", formData, {
        headers: {
          "Content-Type": "multipart/form-data",
        },
      });
  
      console.log("Upload successful:", response.data);
    } catch (error) {
      console.error("Upload error:", error);
    }
  };
  

  const fileTypeIcons: { [key: string]: string } = {
    pdf: '📕',
    image: '🖼️',
    audio: '🎵',
    video: '🎬',
  };

  const getFileIcons = (type: string) => {
    for (const key in fileTypeIcons) {
      if (type.includes(key)) return fileTypeIcons[key];
    }
    return '📁';
  };

  return (
    <div className='min-h-screen flex flex-col items-center justify-center bg-gray-100 px-4 py-10'>
      <h1 className='text-3xl font-bold text-gray-800 mb-6'>Upload Files</h1>

      <label
        htmlFor='file-upload'
        className='h-60 w-96 border-2 border-dashed border-gray-400 bg-white rounded-lg shadow-md flex items-center justify-center flex-col transition duration-300 hover:border-blue-500 hover:bg-blue-50 cursor-pointer text-center'
      >
        <p className='text-gray-500 text-lg mb-2'>Drag & Drop your files here</p>
        <span className='text-sm text-blue-600'>or click to browse</span>
        <input
          id='file-upload'
          type='file'
          multiple
          className='hidden'
          onChange={handleUpload}
        />
      </label>

      {files.length > 0 && (
        <div className='mt-6 w-full max-w-md space-y-4'>
          {files.map((file, index) => (
            <div key={index} className='bg-white border rounded-md shadow-sm p-4 flex items-center gap-4'>
              <span className='text-2xl'>{getFileIcons(file.type)}</span>
              <div>
                <p className='font-medium'>{file.name}</p>
                <p className='text-sm text-gray-500'>{file.type || 'Unknown type'}</p>
              </div>
            </div>
          ))}

          <div className='bg-green-200 text-green-900 text-center p-3 rounded font-semibold'>
            {files.length} file{files.length > 1 ? 's' : ''} selected.
          </div>

          <button
            onClick={handleSubmit}
            className='w-full bg-blue-600 text-white font-semibold py-2 px-4 rounded hover:bg-blue-700 transition'
          >
            Submit Files
          </button>
        </div>
      )}
    </div>
  );
}

export default App;
