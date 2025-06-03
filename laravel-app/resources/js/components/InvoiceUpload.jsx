import '../bootstrap';
import React, { useState, useRef } from 'react';
import { invoiceApi } from '../services/api';

// SVG Icon Components
const UploadIcon = () => (
    <svg className="w-8 h-8 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
    </svg>
);

const SuccessIcon = () => (
    <svg className="w-8 h-8 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
    </svg>
);

const ErrorIcon = () => (
    <svg className="w-5 h-5 text-red-600 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
    </svg>
);

const Spinner = () => (
    <svg className="animate-spin -ml-1 mr-3 h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
    </svg>
);

const InvoiceUpload = ({ onUploadSuccess }) => {
    const [file, setFile] = useState(null);
    const [uploading, setUploading] = useState(false);
    const [error, setError] = useState(null);
    const [dragActive, setDragActive] = useState(false);
    const fileInputRef = useRef(null);

    const validateFile = (file) => {
        if (!file) return false;
        if (file.type !== 'application/pdf') {
            setError('Please select a valid PDF file');
            return false;
        }
        if (file.size > 10 * 1024 * 1024) {
            setError('File size must be less than 10MB');
            return false;
        }
        return true;
    };

    const handleFileChange = (e) => {
        const selectedFile = e.target.files[0];
        if (validateFile(selectedFile)) {
            setFile(selectedFile);
            setError(null);
        } else {
            setFile(null);
        }
    };

    const handleDrag = (e) => {
        e.preventDefault();
        e.stopPropagation();
        setDragActive(e.type === 'dragenter' || e.type === 'dragover');
    };

    const handleDrop = (e) => {
        e.preventDefault();
        e.stopPropagation();
        setDragActive(false);
        const droppedFile = e.dataTransfer.files[0];
        if (validateFile(droppedFile)) {
            setFile(droppedFile);
            setError(null);
        } else {
            setFile(null);
        }
    };

    const handleUpload = async () => {
        if (!file) {
            setError('Please select a PDF file');
            return;
        }
        setUploading(true);
        setError(null);
        const formData = new FormData();
        formData.append('pdf', file);
        try {
            const response = await invoiceApi.scanPdf(formData);
            onUploadSuccess(response.data);
            setFile(null);
            if (fileInputRef.current) fileInputRef.current.value = '';
        } catch (err) {
            console.error('Upload error:', err.response?.data);
            const errorMsg = err.response?.data?.error || err.response?.data?.message || 'Error uploading file';
            const validationErrors = err.response?.data?.errors;
            let fullError = errorMsg;
            if (validationErrors) {
                fullError += '\nValidation errors: ' + Object.values(validationErrors).flat().join(', ');
            }
            setError(fullError);
        } finally {
            setUploading(false);
        }
    };

    const openFileDialog = () => fileInputRef.current?.click();

    const handleRemoveFile = (e) => {
        e.stopPropagation();
        setFile(null);
        if (fileInputRef.current) fileInputRef.current.value = '';
    };

    return (
        <div className="max-w-4xl mx-auto p-6">
            <div className="bg-white rounded-xl shadow-lg border border-gray-200">
                <div className="p-8">
                    <div className="text-center mb-8">
                        <h1 className="text-3xl font-bold text-gray-900 mb-2">Invoice Scanner</h1>
                        <p className="text-gray-600">Upload PDF invoices and view extracted product data</p>
                    </div>
                    <div
                        onDragEnter={handleDrag}
                        onDragLeave={handleDrag}
                        onDragOver={handleDrag}
                        onDrop={handleDrop}
                        onClick={openFileDialog}
                        className={`
                            relative border-2 border-dashed rounded-xl p-12 text-center cursor-pointer transition-all duration-200
                            ${dragActive ? 'border-blue-400 bg-blue-50' : 'border-gray-300 hover:border-gray-400 hover:bg-gray-50'}
                            ${file ? 'border-green-400 bg-green-50' : ''}
                        `}
                    >
                        <input
                            ref={fileInputRef}
                            type="file"
                            accept=".pdf"
                            onChange={handleFileChange}
                            className="hidden"
                        />
                        <div className="space-y-4">
                            {!file ? (
                                <>
                                    <div className="mx-auto w-16 h-16 bg-gray-100 rounded-full flex items-center justify-center">
                                        <UploadIcon />
                                    </div>
                                    <div>
                                        <p className="text-xl font-medium text-gray-900">Drop your PDF invoice here</p>
                                        <p className="text-gray-500 mt-1">or click to browse files</p>
                                    </div>
                                    <p className="text-sm text-gray-400">Maximum file size: 10MB</p>
                                </>
                            ) : (
                                <>
                                    <div className="mx-auto w-16 h-16 bg-green-100 rounded-full flex items-center justify-center">
                                        <SuccessIcon />
                                    </div>
                                    <div>
                                        <p className="text-lg font-medium text-gray-900">{file.name}</p>
                                        <p className="text-gray-500">{(file.size / 1024 / 1024 || 0).toFixed(2)} MB</p>
                                    </div>
                                    <button
                                        onClick={handleRemoveFile}
                                        className="text-sm text-red-600 hover:text-red-800 underline"
                                    >
                                        Remove file
                                    </button>
                                </>
                            )}
                        </div>
                    </div>
                    {error && (
                        <div className="mt-6 p-4 bg-red-50 border border-red-200 rounded-lg">
                            <div className="flex items-center">
                                <ErrorIcon />
                                <p className="text-red-800 font-medium">{error}</p>
                            </div>
                        </div>
                    )}
                    {file && (
                        <div className="mt-6">
                            <button
                                onClick={handleUpload}
                                disabled={uploading}
                                className={`
                                    w-full py-4 px-6 rounded-lg text-white font-semibold text-lg transition-all duration-200
                                    ${uploading
                                    ? 'bg-gray-400 cursor-not-allowed'
                                    : 'bg-blue-600 hover:bg-blue-700 active:bg-blue-800 shadow-lg hover:shadow-xl'
                                }
                                `}
                            >
                                {uploading ? (
                                    <div className="flex items-center justify-center">
                                        <Spinner />
                                        Processing Invoice...
                                    </div>
                                ) : (
                                    'Upload and Process Invoice'
                                )}
                            </button>
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
};

export default InvoiceUpload;
