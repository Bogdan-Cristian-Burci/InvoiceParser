<?php

namespace App\Services;

use App\Models\Bill;
use App\Models\Delivery;
use App\Models\Product;
use Carbon\Carbon;
use GuzzleHttp\Client;
use GuzzleHttp\Psr7\Request;
use Illuminate\Support\Facades\DB;
use Illuminate\Support\Facades\Log;
use Smalot\PdfParser\Parser;

class InvoicePdfScannerService
{
    protected Parser $parser;
    protected Client $httpClient;
    protected ?string $veryfiClientId;
    protected ?string $veryfiApiKey;
    protected array $patterns;
    protected array $companyPatterns;

    public function __construct()
    {
        $this->parser = new Parser();
        $this->httpClient = new Client();
        $this->veryfiClientId = config('services.veryfi.client_id', 'vrfWOWPYoHxtYOHS9Z9RukyEiLuSsg2mxWWVMvP');
        $this->veryfiApiKey = config('services.veryfi.api_key', 'apikey bogdanburci81:632e114f8e74483a419208a265714107');

        $this->initializePatterns();
    }

    protected function initializePatterns(): void
    {
        $this->patterns = [
            'document_number' => '/N°\s*doc:\s*([A-Z]+\s*\/\s*\d+)/i',
            'document_date' => '/Del:\s*(\d{2}-\d{2}-\d{4})/i',
            'client_code' => '/Cliente:\s*([A-Z0-9]+)/i',
            'vat_number' => '/P\.IVA\s*UE:\s*([A-Z0-9]+)/i',
            'total_amount' => '/Tot\s*importo:\s*\(\s*EUR\s*\)\s*([\d,\.]+)/i',
            'packages' => '/Numero\s*colli:\s*(\d+)/i',
            'net_weight' => '/Peso\s*netto\s*\(\s*KG\s*\):\s*([\d,\.]+)/i',
            'gross_weight' => '/Peso\s*lordo\s*\(\s*KG\s*\):\s*([\d,\.]+)/i',
            'shipping_terms' => '/Porto:\s*([A-Z\s\-]+)/i',
            'currency' => '/Divisa:\s*([A-Z]+)/i',
            // Alternative patterns for the specific invoice format
            'invoice_number_alt' => '/nr\.\s*(\d+)/i',
            'total_amount_alt' => '/(\d+(?:\.\d+)?)\s*€/i',
            'packages_alt' => '/(\d+)\s*colli/i',
            'net_weight_alt' => '/\((\d+(?:\.\d+)?)\s*Kg_N/i',
            'gross_weight_alt' => '/(\d+(?:\.\d+)?)\s*Kg_B\)/i',
            'date_alt' => '/(\d{4}\.\d{2}\.\d{2})/i',
        ];

        $this->companyPatterns = [
            'company_name' => '/([A-Za-z\s]+S\.r\.l\.?\s*a\s*Socio\s*Unico)/i',
            'capital' => '/Capitale\s*Sociale\s*Euro\s*([\d,\.]+)/i',
            'registration' => '/Iscrizione\s*Registro\s*Società\s*n\.\s*(\d+)/i',
            'address' => '/(\d{5}\s+[A-Za-z\s\-]+)/i',
            'phone' => '/Telefono\s*([\d\s]+)/i',
            'fax' => '/Telefax\s*([\d\s]+)/i',
        ];
    }

    public function extractRawText(string $pdfPath): string
    {
        $pdf = $this->parser->parseFile($pdfPath);
        return $pdf->getText();
    }

    public function scanAndPopulate(string $pdfPath): array
    {
        // Try Python parser service first
        try {
            $pythonData = $this->extractWithPythonParser($pdfPath);
            if ($pythonData) {
                return $this->createEntitiesFromPythonData($pythonData);
            }
        } catch (\Exception $e) {
            Log::warning('Python parser failed, falling back to basic extraction: ' . $e->getMessage());
        }

        // Fallback to basic PDF text extraction
        $pdf = $this->parser->parseFile($pdfPath);
        $text = $pdf->getText();

        return DB::transaction(function () use ($text) {
            $billData = $this->extractBillData($text);
            $bill = Bill::create($billData);

            $deliveryData = $this->extractDeliveryData($text);
            $deliveryData['bill_id'] = $bill->id;
            $delivery = Delivery::create($deliveryData);

            $productsData = $this->extractProductsData($text);
            $products = [];
            foreach ($productsData as $productData) {
                $productData['delivery_id'] = $delivery->id;
                $products[] = Product::create($productData);
            }

            return [
                'bill' => $bill,
                'delivery' => $delivery,
                'products' => $products,
            ];
        });
    }

    public function extractWithPythonParser(string $pdfPath): ?array
    {
        $pythonParserUrl = env('PYTHON_PARSER_URL', 'http://python-parser:5000');

        try {
            $response = $this->httpClient->post($pythonParserUrl . '/parse-invoice', [
                'multipart' => [
                    [
                        'name'     => 'file',
                        'contents' => fopen($pdfPath, 'r'),
                        'filename' => basename($pdfPath)
                    ]
                ],
                'timeout' => 120
            ]);

            $responseBody = $response->getBody()->getContents();
            Log::info('Python Parser Response: ' . $responseBody);

            $data = json_decode($responseBody, true);

            if (isset($data['success']) && $data['success']) {
                return $data['data'];
            }

            Log::error('Python parser returned error: ' . ($data['message'] ?? 'Unknown error'));
            return null;

        } catch (\Exception $e) {
            Log::error('Python Parser Error: ' . $e->getMessage());
            throw $e;
        }
    }

    protected function createEntitiesFromPythonData(array $pythonData): array
    {
        return DB::transaction(function () use ($pythonData) {
            // Extract bill data from Python parser response
            $billData = $pythonData['bill'] ?? [];

            // Convert date format if needed
            if (isset($billData['bill_date']) && preg_match('/\d{2}-\d{2}-\d{4}/', $billData['bill_date'])) {
                try {
                    $billData['bill_date'] = Carbon::createFromFormat('d-m-Y', $billData['bill_date'])->format('Y-m-d');
                } catch (\Exception $e) {
                    Log::warning('Date parsing failed: ' . $e->getMessage());
                    $billData['bill_date'] = now()->format('Y-m-d');
                }
            }

            $bill = Bill::create($billData);

            // Handle multiple deliveries
            $deliveries = [];
            $products = [];
            $deliveriesData = $pythonData['deliveries'] ?? [];
            
            // If no deliveries found, try old single delivery format for backward compatibility
            if (empty($deliveriesData) && isset($pythonData['delivery'])) {
                $deliveriesData = [$pythonData['delivery']];
            }

            foreach ($deliveriesData as $deliveryData) {
                $deliveryData['bill_id'] = $bill->id;

                // Convert delivery date format if needed
                if (isset($deliveryData['ddt_date']) && preg_match('/\d{2}-\d{2}-\d{4}/', $deliveryData['ddt_date'])) {
                    try {
                        $deliveryData['ddt_date'] = Carbon::createFromFormat('d-m-Y', $deliveryData['ddt_date'])->format('Y-m-d');
                    } catch (\Exception $e) {
                        Log::warning('DDT Date parsing failed: ' . $e->getMessage());
                        $deliveryData['ddt_date'] = now()->format('Y-m-d');
                    }
                }

                $delivery = Delivery::create($deliveryData);
                $deliveries[] = $delivery;

                // Extract products associated with this delivery
                $deliveryProducts = $deliveryData['products'] ?? [];
                foreach ($deliveryProducts as $productData) {
                    $productData['delivery_id'] = $delivery->id;
                    $products[] = Product::create($productData);
                }
            }

            // Also handle products at the top level (backward compatibility)
            $topLevelProducts = $pythonData['products'] ?? [];
            foreach ($topLevelProducts as $productData) {
                // Associate with the first delivery if available
                $deliveryId = !empty($deliveries) ? $deliveries[0]->id : null;
                $productData['delivery_id'] = $deliveryId;
                $products[] = Product::create($productData);
            }

            return [
                'bill' => $bill,
                'deliveries' => $deliveries,
                'delivery' => $deliveries[0] ?? null, // For backward compatibility
                'products' => $products,
                'parser_data' => $pythonData
            ];
        });
    }

    protected function extractBillData(string $text): array
    {
        $normalizedText = $this->normalizeText($text);
        $data = [];

        // Extract document number
        $data['bill_number'] = $this->extractValue($normalizedText, ['document_number', 'invoice_number_alt']) ?? 'N/A';

        // Extract date
        $dateValue = $this->extractValue($normalizedText, ['document_date', 'date_alt']);
        if ($dateValue) {
            try {
                if (strpos($dateValue, '-') !== false) {
                    $data['bill_date'] = Carbon::createFromFormat('d-m-Y', $dateValue)->format('Y-m-d');
                } else {
                    $data['bill_date'] = Carbon::createFromFormat('Y.m.d', $dateValue)->format('Y-m-d');
                }
            } catch (\Exception $e) {
                Log::warning('Date parsing failed: ' . $e->getMessage());
                $data['bill_date'] = now()->format('Y-m-d');
            }
        } else {
            $data['bill_date'] = now()->format('Y-m-d');
        }

        // Extract customer code
        $data['customer_code'] = $this->extractValue($normalizedText, ['client_code']) ?? $this->extractCustomerCodeFallback($normalizedText);

        $data['currency'] = $this->extractValue($normalizedText, ['currency']) ?? 'EUR';

        // Extract customer name
        $data['customer_name'] = $this->extractCustomerName($normalizedText);
        $data['customer_address'] = $this->extractCustomerAddress($normalizedText);

        // Extract amounts and weights
        $totalAmount = $this->extractValue($normalizedText, ['total_amount', 'total_amount_alt']);
        $data['total_amount'] = $totalAmount ? $this->parseNumericValue($totalAmount) : 0.00;

        $packages = $this->extractValue($normalizedText, ['packages', 'packages_alt']);
        $data['package_count'] = $packages ? intval($packages) : 1;

        $netWeight = $this->extractValue($normalizedText, ['net_weight', 'net_weight_alt']);
        $data['net_weight_kg'] = $netWeight ? $this->parseNumericValue($netWeight) : 0.00;

        $grossWeight = $this->extractValue($normalizedText, ['gross_weight', 'gross_weight_alt']);
        $data['gross_weight_kg'] = $grossWeight ? $this->parseNumericValue($grossWeight) : 0.00;
        $data['shipping_term'] = $this->extractValue($normalizedText, ['shipping_terms']) ?? 'Standard';

        return $data;
    }

    protected function normalizeText(string $text): string
    {
        // Remove extra whitespace and normalize
        $text = preg_replace('/\s+/', ' ', $text);
        // Fix common OCR issues
        $text = str_replace(['€', '°'], ['€', '°'], $text);
        return trim($text);
    }

    protected function extractValue(string $text, array $patternKeys): ?string
    {
        foreach ($patternKeys as $key) {
            if (isset($this->patterns[$key])) {
                if (preg_match($this->patterns[$key], $text, $matches)) {
                    return trim($matches[1]);
                }
            }
        }
        return null;
    }

    protected function parseNumericValue(string $value): float
    {
        // Handle European number format (comma as decimal separator)
        $cleaned = str_replace([' ', '.'], ['', ''], $value);
        $cleaned = str_replace(',', '.', $cleaned);
        return floatval($cleaned);
    }

    protected function extractCustomerCodeFallback(string $text): string
    {
        if (preg_match('/([A-Z]+\d+)/', $text, $matches)) {
            return substr($matches[1], 0, 50);
        }
        return 'N/A';
    }

    protected function extractCustomerName(string $text): string
    {
        // Look for client section
        if (preg_match('/Spett\.le:\s*(.*?)(?=LISTA|$)/s', $text, $matches)) {
            $clientText = trim($matches[1]);
            $lines = array_filter(explode("\n", $clientText));
            if (!empty($lines)) {
                return substr(trim($lines[0]), 0, 255);
            }
        }

        // Fallback pattern
        if (preg_match('/S\.C\.\s*([^_\n]+)/', $text, $matches)) {
            return substr(trim($matches[1]), 0, 255);
        }

        return 'Unknown Customer';
    }

    protected function extractCustomerAddress(string $text): string
    {
        // Look for client section and extract address lines
        if (preg_match('/Spett\.le:\s*(.*?)(?=LISTA|$)/s', $text, $matches)) {
            $clientText = trim($matches[1]);
            $lines = array_filter(explode("\n", $clientText));
            if (count($lines) > 1) {
                $addressParts = array_slice($lines, 1, 3); // Take next 2-3 lines as address
                return substr(implode(', ', array_map('trim', $addressParts)), 0, 500);
            }
        }

        return 'N/A';
    }

    protected function extractDeliveryData(string $text): array
    {
        $data = [];

        if (preg_match('/([A-Z0-9]+\s+\d+)/', $text, $matches)) {
            $data['ddt_number'] = substr($matches[1], 0, 100);
        } else {
            $data['ddt_number'] = 'N/A';
        }

        if (preg_match('/(\d{4}\.\d{2}\.\d{2})/', $text, $matches)) {
            $data['ddt_date'] = Carbon::createFromFormat('Y.m.d', $matches[1])->format('Y-m-d');
        } else {
            $data['ddt_date'] = now()->format('Y-m-d');
        }

        $possibleCodes = [];
        if (preg_match_all('/([A-Z]{2,3}\d+\.\d+\.\d+(?:\.\d+)?)/', $text, $matches)) {
            $possibleCodes = $matches[1];
        }

        if (count($possibleCodes) >= 1) {
            $data['model_code'] = substr($possibleCodes[0], 0, 100);
        } else {
            $data['model_code'] = 'N/A';
        }

        if (count($possibleCodes) >= 2) {
            $data['model_internal_code'] = substr($possibleCodes[1], 0, 100);
        } else {
            $data['model_internal_code'] = 'N/A';
        }

        if (preg_match('/([A-Z]{2,}(?:\s+[A-Z]+)*)\s*(?:Interno|adesivo)/', $text, $matches)) {
            $data['model_label'] = substr(trim($matches[1]), 0, 100);
        } else {
            $data['model_label'] = 'N/A';
        }

        return $data;
    }

    protected function extractProductsData(string $text): array
    {
        $products = [];

        if (preg_match('/([A-Z]{3}\d+\.\d+\.\d+\.\d+)/', $text, $matches)) {
            $product = [];
            $product['product_code'] = substr($matches[1], 0, 100);

            if (preg_match('/Interno\s+adesivo\s*-\s*([^_]+)/', $text, $descMatches)) {
                $product['description'] = trim($descMatches[1]);
            } else {
                $product['description'] = 'N/A';
            }

            if (preg_match('/(\d+%\s*[^_]+)/', $text, $materialMatches)) {
                $product['material'] = trim($materialMatches[1]);
            } else {
                $product['material'] = 'N/A';
            }

            if (preg_match('/\b(MT|KG|PZ|M)\b/', $text, $unitMatches)) {
                $product['unit_of_measure'] = substr($unitMatches[1], 0, 10);
            } else {
                $product['unit_of_measure'] = 'PZ';
            }

            if (preg_match('/(\d+\.\d+)000/', $text, $qtyMatches)) {
                $product['quantity'] = floatval($qtyMatches[1]);
            } else {
                $product['quantity'] = 1.0;
            }

            if (preg_match('/(\d+\.\d+)000.*?(\d+\.\d+)000/', $text, $priceMatches)) {
                $product['unit_price'] = floatval($priceMatches[2] ?? $priceMatches[1]);
            } else {
                $product['unit_price'] = 0.0;
            }

            if (preg_match('/(\d+\.\d+)(?!\d)/', $text, $totalMatches)) {
                $product['total_price'] = floatval($totalMatches[1]);
            } else {
                $product['total_price'] = 0.0;
            }

            if (preg_match('/(\d{2,3})(?=\s|$)/', $text, $widthMatches)) {
                $product['width_cm'] = intval($widthMatches[1]);
            }

            $products[] = $product;
        }

        // If no products found, create a default one
        if (empty($products)) {
            $products[] = [
                'product_code' => 'N/A',
                'description' => 'Unknown Product',
                'material' => 'N/A',
                'unit_of_measure' => 'PZ',
                'quantity' => 1.0,
                'unit_price' => 0.0,
                'total_price' => 0.0,
                'width_cm' => null,
            ];
        }

        return $products;
    }
}
