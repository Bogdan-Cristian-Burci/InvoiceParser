<?php

namespace App\Http\Controllers;

use App\Http\Requests\BillRequest;
use App\Http\Resources\BillResource;
use App\Models\Bill;
use App\Models\Delivery;
use App\Models\Product;
use Illuminate\Foundation\Auth\Access\AuthorizesRequests;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\Http;
use Illuminate\Support\Facades\DB;
use Illuminate\Support\Facades\Log;

class BillController extends Controller
{
    use AuthorizesRequests;

    public function index()
    {
        return BillResource::collection(Bill::all());
    }

    public function store(BillRequest $request)
    {
        return new BillResource(Bill::create($request->validated()));
    }

    public function show(Bill $bill)
    {
        return new BillResource($bill);
    }

    public function update(BillRequest $request, Bill $bill)
    {
        $bill->update($request->validated());

        return new BillResource($bill);
    }

    public function destroy(Bill $bill)
    {
        $bill->delete();

        return response()->json();
    }

    public function scanPdf(Request $request)
    {
        try {
            $request->validate([
                'pdf' => 'required|file|mimes:pdf|max:10240',
            ]);
        } catch (\Illuminate\Validation\ValidationException $e) {
            return response()->json([
                'message' => 'Validation failed',
                'errors' => $e->errors(),
            ], 422);
        }

        try {
            // Get the uploaded file
            $pdfFile = $request->file('pdf');
            
            // Call Python service for coordinate-based PDF parsing
            $pythonServiceUrl = config('services.python_pdf_parser.url', 'http://localhost:5000');
            
            $response = Http::timeout(60)
                ->attach('file', file_get_contents($pdfFile->getRealPath()), $pdfFile->getClientOriginalName())
                ->post($pythonServiceUrl . '/parse-invoice-coordinate-based');
            
            if (!$response->successful()) {
                Log::error('Python PDF parser service failed', [
                    'status' => $response->status(),
                    'body' => $response->body()
                ]);
                
                return response()->json([
                    'message' => 'PDF processing service unavailable',
                    'error' => 'Failed to connect to PDF parser service',
                ], 503);
            }
            
            $parsedData = $response->json();
            
            // Log the complete JSON response from Python service
            Log::info('Coordinate-based extraction response received', [
                'status_code' => $response->status(),
                'response_data' => $parsedData,
                'file_name' => $pdfFile->getClientOriginalName(),
                'extraction_method' => $parsedData['data']['extraction_method'] ?? 'unknown',
                'row_detection_method' => $parsedData['data']['row_detection_method'] ?? 'unknown',
                'success' => $parsedData['success'] ?? false,
                'products_extracted' => count($parsedData['data']['products'] ?? []),
                'table_found' => $parsedData['data']['debug_info']['table_found'] ?? false,
                'headers_detected' => $parsedData['data']['debug_info']['headers_detected'] ?? false
            ]);
            
            if (!$parsedData['success']) {
                return response()->json([
                    'message' => 'Failed to parse PDF',
                    'error' => $parsedData['error'] ?? 'Unknown error',
                ], 422);
            }
            
            // Process the parsed data and create models
            $result = $this->createModelsFromParsedData($parsedData['data']);
            
            // Log successful model creation
            Log::info('Coordinate-based extraction models created successfully', [
                'file_name' => $pdfFile->getClientOriginalName(),
                'bill_id' => $result['bill']->id,
                'delivery_id' => $result['delivery']->id,
                'products_count' => count($result['products']),
                'extraction_method' => $parsedData['data']['extraction_method'] ?? 'unknown',
                'row_detection_method' => $parsedData['data']['row_detection_method'] ?? 'unknown',
                'total_amount' => $result['bill']->total_amount,
                'products' => collect($result['products'])->map(function($product) {
                    return [
                        'id' => $product->id,
                        'product_code' => $product->product_code,
                        'description' => $product->description,
                        'quantity' => $product->quantity,
                        'unit_price' => $product->unit_price,
                        'total_price' => $product->total_price
                    ];
                })->toArray()
            ]);
            
            return response()->json([
                'message' => 'Invoice processed successfully',
                'data' => [
                    'bill_id' => $result['bill']->id,
                    'delivery_id' => $result['delivery']->id,
                    'products_count' => count($result['products']),
                    'extraction_method' => $parsedData['data']['extraction_method'] ?? 'unknown'
                ],
                'parsed_data' => config('app.debug') ? $parsedData['data'] : null,
            ], 201);
            
        } catch (\Exception $e) {
            Log::error('Error in PDF scanning', [
                'error' => $e->getMessage(),
                'trace' => $e->getTraceAsString()
            ]);
            
            return response()->json([
                'message' => 'Error processing PDF',
                'error' => $e->getMessage(),
                'trace' => config('app.debug') ? $e->getTraceAsString() : null,
            ], 422);
        }
    }

    public function testCoordinateBasedParsing(Request $request)
    {
        try {
            $request->validate([
                'pdf' => 'required|file|mimes:pdf|max:10240',
            ]);
        } catch (\Illuminate\Validation\ValidationException $e) {
            return response()->json([
                'message' => 'Validation failed',
                'errors' => $e->errors(),
            ], 422);
        }

        try {
            // Get the uploaded file
            $pdfFile = $request->file('pdf');
            
            // Call Python service for coordinate-based PDF parsing
            $pythonServiceUrl = config('services.python_pdf_parser.url', 'http://localhost:5000');
            
            $response = Http::timeout(60)
                ->attach('file', file_get_contents($pdfFile->getRealPath()), $pdfFile->getClientOriginalName())
                ->post($pythonServiceUrl . '/parse-invoice-coordinate-based');
            
            if (!$response->successful()) {
                Log::error('Python coordinate-based parser failed', [
                    'status' => $response->status(),
                    'body' => $response->body()
                ]);
                
                return response()->json([
                    'message' => 'Coordinate-based parsing service unavailable',
                    'error' => 'Failed to connect to coordinate-based parser service',
                ], 503);
            }
            
            $parsedData = $response->json();
            
            // Log the complete JSON response from Python service
            Log::info('Coordinate-based parsing response received', [
                'status_code' => $response->status(),
                'response_data' => $parsedData,
                'file_name' => $pdfFile->getClientOriginalName()
            ]);
            
            return response()->json([
                'message' => 'Coordinate-based parsing test completed',
                'data' => $parsedData,
            ], 200);
            
        } catch (\Exception $e) {
            Log::error('Error in coordinate-based parsing test', [
                'error' => $e->getMessage(),
                'trace' => $e->getTraceAsString()
            ]);
            
            return response()->json([
                'message' => 'Error in coordinate-based parsing test',
                'error' => $e->getMessage(),
                'trace' => config('app.debug') ? $e->getTraceAsString() : null,
            ], 422);
        }
    }

    protected function createModelsFromParsedData(array $data): array
    {
        return DB::transaction(function () use ($data) {
            // Create Bill
            $billData = $data['bill'];
            $bill = Bill::create([
                'bill_number' => $billData['bill_number'] ?? 'N/A',
                'bill_date' => $this->parseDate($billData['bill_date'] ?? null),
                'customer_code' => $billData['customer_code'] ?? 'N/A',
                'customer_name' => $billData['customer_name'] ?? 'Unknown Customer',
                'customer_address' => $billData['customer_address'] ?? 'N/A',
                'total_amount' => $billData['total_amount'] ?? 0.0,
                'package_count' => $billData['package_count'] ?? 1,
                'net_weight_kg' => $billData['net_weight_kg'] ?? 0.0,
                'gross_weight_kg' => $billData['gross_weight_kg'] ?? 0.0,
                'currency' => $billData['currency'] ?? 'EUR',
                'shipping_term' => $billData['shipping_term'] ?? 'Standard',
            ]);

            // Create Delivery
            $deliveryData = $data['delivery'];
            $delivery = Delivery::create([
                'bill_id' => $bill->id,
                'ddt_number' => $deliveryData['ddt_number'] ?? 'N/A',
                'ddt_date' => $this->parseDate($deliveryData['ddt_date'] ?? null),
                'model_code' => $deliveryData['model_code'] ?? 'N/A',
                'model_internal_code' => $deliveryData['model_internal_code'] ?? 'N/A',
                'model_label' => $deliveryData['model_label'] ?? 'N/A',
            ]);

            // Create Products
            $products = [];
            $productsData = $data['products'] ?? [];
            
            foreach ($productsData as $productData) {
                $products[] = Product::create([
                    'delivery_id' => $delivery->id,
                    'product_code' => $productData['product_code'] ?? 'N/A',
                    'description' => $productData['description'] ?? 'Unknown Product',
                    'material' => $productData['material'] ?? 'N/A',
                    'unit_of_measure' => $productData['unit_of_measure'] ?? 'PZ',
                    'quantity' => $productData['quantity'] ?? 1.0,
                    'unit_price' => $productData['unit_price'] ?? 0.0,
                    'total_price' => $productData['total_price'] ?? 0.0,
                    'width_cm' => $productData['width_cm'],
                ]);
            }

            return [
                'bill' => $bill,
                'delivery' => $delivery,
                'products' => $products,
            ];
        });
    }

    /**
     * Parse date from various formats to Y-m-d format
     */
    protected function parseDate($dateString): string
    {
        if (empty($dateString)) {
            return now()->format('Y-m-d');
        }

        // Try different date formats
        $formats = [
            'd-m-Y',    // 19-05-2025
            'd/m/Y',    // 19/05/2025
            'Y-m-d',    // 2025-05-19 (already correct)
            'd.m.Y',    // 19.05.2025
            'm/d/Y',    // 05/19/2025
        ];

        foreach ($formats as $format) {
            $date = \DateTime::createFromFormat($format, $dateString);
            if ($date && $date->format($format) === $dateString) {
                return $date->format('Y-m-d');
            }
        }

        // If no format matches, try Carbon parse as fallback
        try {
            return \Carbon\Carbon::parse($dateString)->format('Y-m-d');
        } catch (\Exception $e) {
            Log::warning('Could not parse date: ' . $dateString . '. Using current date.');
            return now()->format('Y-m-d');
        }
    }
}
