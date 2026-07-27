import React, { useState, useCallback } from 'react';
import './App.css';
import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

const App = () => {
  const [files, setFiles] = useState<File[]>([]);
  const [evaluationResult, setEvaluationResult] = useState<string | null>(null);
  const [evaluationError, setEvaluationError] = useState<string | null>(null);

  const handleUpload = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFiles = e.target.files;
    if (selectedFiles) {
      setFiles(Array.from(selectedFiles));
    }
  }, []);

 const handleSubmit = useCallback(async () => {
  const formData = new FormData();
  files.forEach((file) => {
    formData.append('files', file);
  });

  try {
    const response = await axios.post(`${API_BASE_URL}/uploadfile`, formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    console.log('Upload successful:', response.data);
    setFiles([]);
  } catch (error: any) {
    console.error('Upload error:', error);
    alert(`File upload failed: ${error.message || 'An error occurred'}`);
  }
}, [files]);


  const handleDelete = useCallback((filename: string) => {
    setFiles(prevFiles => prevFiles.filter(file => file.name !== filename));
  }, []);

  const handleEvaluate = async () => {
  
    try {
      const response = await axios.post(`${API_BASE_URL}/evaluate-resumes`);
      console.log('Evaluation successful:', response.data);
      setEvaluationResult(response.data.message);
    } catch (error: any) {
      console.error('Evaluation error:', error);
      if (error.response && error.response.data && error.response.data.detail) {
        setEvaluationError(error.response.data.detail);
      } else {
        setEvaluationError("An error occurred during evaluation.");
      }
    }
  };

  const fileTypeIcons: { [key: string]: string } = {
    pdf: '📕',
    image: '🖼️',
    audio: '🎵',
    video: '🎬',
  };

  const getFileIcon = (type: string) => {
    for (const key in fileTypeIcons) {
      if (type.includes(key)) return fileTypeIcons[key];
    }
    return '📁';
  };

  return (
    <div className="min-h-screen flex flex-col items-center justify-start bg-gray-100 px-4 py-10">
      <h1 className="text-3xl font-bold text-gray-800 mb-6">Upload Files</h1>

      <label
        htmlFor="file-upload"
        className="h-60 w-96 border-2 border-dashed border-gray-400 bg-white rounded-lg shadow-md flex items-center justify-center flex-col transition duration-300 hover:border-blue-500 hover:bg-blue-50 cursor-pointer text-center"
      >
        <p className="text-gray-500 text-lg mb-2">Drag & Drop your files here</p>
        <span className="text-sm text-blue-600">or click to browse</span>
        <input
          id="file-upload"
          type="file"
          multiple
          className="hidden"
          onChange={handleUpload}
        />
      </label>

      {files.length > 0 && (
        <div className="mt-6 w-full max-w-md space-y-4">
          {files.map((file, index) => (
            <div key={index} className="bg-white border rounded-md shadow-sm p-4 flex items-center gap-4">
              <span className="text-2xl">{getFileIcon(file.type)}</span>
              <div>
                <p className="font-medium">{file.name}</p>
                <p className="text-sm text-gray-500">{file.type || 'Unknown type'}</p>
              </div>
              <button
                onClick={() => handleDelete(file.name)}
                className="ml-auto text-red-500 hover:text-red-700"
              >
                Delete
              </button>
            </div>
          ))}

          <div className="bg-green-200 text-green-900 text-center p-3 rounded font-semibold">
            {files.length} file{files.length > 1 ? 's' : ''} selected.
          </div>

          <button
            onClick={handleSubmit}
            className="w-full bg-blue-600 text-white font-semibold py-2 px-4 rounded hover:bg-blue-700 transition"
          >
            Submit Files
          </button>
        </div>
      )}

      <div className="mt-8 w-full max-w-md space-y-4">
        <h2 className="text-xl font-semibold text-gray-800">Evaluate Resume</h2>
        <button
          onClick={handleEvaluate}
          className="w-full bg-green-600 text-white font-semibold py-2 px-4 rounded hover:bg-green-700 transition"
        >
          Evaluate your Resume for the Role of ASE
        </button>
        {evaluationResult && (
          <div className="mt-4 p-4 bg-gray-100 border rounded-md shadow-sm text-gray-700">
            <h3 className="font-semibold">Evaluation Result:</h3>
            <p>{evaluationResult}</p>
          </div>
        )}
        {evaluationError && (
          <div className="mt-4 bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded relative" role="alert">
            <strong className="font-bold">Error: </strong>
            <span className="block sm:inline">{evaluationError}</span>
          </div>
        )}
      </div>
    </div>
  );
};

export default App;
