import axios from 'axios';

const api = axios.create({
    baseURL: '/api',
    headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
    },
});

export const invoiceApi = {
    scanPdf: (formData) => api.post('/bills/scan-pdf', formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
    }),
    
    getProducts: () => api.get('/products'),
    getBills: () => api.get('/bills'),
    getDeliveries: () => api.get('/deliveries'),
    
    getProductsWithRelations: async () => {
        try {
            const [productsResponse, billsResponse, deliveriesResponse] = await Promise.all([
                api.get('/products'),
                api.get('/bills'),
                api.get('/deliveries')
            ]);
            
            const products = productsResponse.data.data || [];
            const bills = billsResponse.data.data || [];
            const deliveries = deliveriesResponse.data.data || [];
            
            // Map products with their related bill and delivery data
            return products.map(product => {
                const delivery = deliveries.find(d => d.id === product.delivery_id);
                const bill = bills.find(b => b.id === delivery?.bill_id);
                
                return {
                    ...product,
                    delivery: delivery || {},
                    bill: bill || {}
                };
            });
        } catch (error) {
            console.error('Error fetching products with relations:', error);
            return [];
        }
    }
};

export default api;