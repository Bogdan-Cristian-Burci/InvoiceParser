import './bootstrap';

import React, { useState, useEffect } from 'react';
import ReactDOM from 'react-dom/client';
import InvoiceUpload from './components/InvoiceUpload';
import ProductsTable from './components/ProductsTable';
import { invoiceApi } from './services/api';

function App() {
    const [products, setProducts] = useState([]);
    const [loading, setLoading] = useState(true);
    const [successMessage, setSuccessMessage] = useState('');

    const loadProducts = async () => {
        setLoading(true);
        try {
            const productsData = await invoiceApi.getProductsWithRelations();
            setProducts(productsData);
        } catch (error) {
            console.error('Error loading products:', error);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        loadProducts();
    }, []);

    const handleUploadSuccess = async (response) => {
        // Handle the debug response format
        if (response.raw_text) {
            setSuccessMessage(`PDF text extracted successfully! Text length: ${response.text_length} characters.`);
            console.log('Extracted PDF text:', response.raw_text);
        } else {
            setSuccessMessage(`Invoice processed successfully! Created ${response.data.products_count} products.`);
            await loadProducts();
        }
        
        // Clear success message after 5 seconds
        setTimeout(() => setSuccessMessage(''), 5000);
    };

    return (
        <div className="min-h-screen bg-gradient-to-br from-gray-50 to-gray-100">
            {successMessage && (
                <div className="bg-green-600 text-white">
                    <div className="max-w-4xl mx-auto px-6 py-4">
                        <div className="flex items-center">
                            <svg className="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                            </svg>
                            <span className="font-medium">{successMessage}</span>
                        </div>
                    </div>
                </div>
            )}

            <div className="py-8">
                <InvoiceUpload onUploadSuccess={handleUploadSuccess} />

                {products.length > 0 && (
                    <div className="max-w-4xl mx-auto px-6 mt-8">
                        <div className="bg-white rounded-xl shadow-lg border border-gray-200">
                            <div className="p-6 border-b border-gray-200">
                                <h2 className="text-2xl font-bold text-gray-900">Extracted Products</h2>
                                <p className="text-gray-600 mt-1">
                                    {products.length === 0 
                                        ? 'No products uploaded yet. Upload an invoice PDF to see the extracted data.' 
                                        : `${products.length} product${products.length !== 1 ? 's' : ''} found`
                                    }
                                </p>
                            </div>
                            <div className="p-6">
                                {loading ? (
                                    <div className="text-center py-8">
                                        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto"></div>
                                        <p className="text-gray-500 mt-4">Loading products...</p>
                                    </div>
                                ) : (
                                    <ProductsTable products={products} />
                                )}
                            </div>
                        </div>
                    </div>
                )}
            </div>
        </div>
    );
}

const root = ReactDOM.createRoot(document.getElementById('app'));
root.render(<App />);
