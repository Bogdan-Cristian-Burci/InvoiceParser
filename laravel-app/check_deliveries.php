<?php

require_once 'vendor/autoload.php';

$client = new GuzzleHttp\Client();
$response = $client->post('http://localhost:5000/parse-invoice', [
    'multipart' => [
        [
            'name'     => 'file',
            'contents' => fopen('public/invoice/L. V._2025.05.19 - nr. 502 15473.37 €_46 colli_(297.50 Kg_N, 328 Kg_B).pdf', 'r'),
            'filename' => 'invoice.pdf'
        ]
    ],
    'timeout' => 120
]);

$responseBody = $response->getBody()->getContents();
$data = json_decode($responseBody, true);

$rawText = $data['data']['raw_text'];

// Search for missing delivery patterns
$missingDeliveries = ['3636', '3639', '3640', '3641', '3642', '3643'];

foreach ($missingDeliveries as $delivery) {
    echo "Looking for delivery: $delivery\n";
    foreach ($rawText as $pageKey => $pageText) {
        if (strpos($pageText, $delivery) !== false) {
            echo "Found $delivery in $pageKey\n";
            
            // Extract context around the delivery number
            $pos = strpos($pageText, $delivery);
            $start = max(0, $pos - 300);
            $end = min(strlen($pageText), $pos + 300);
            $context = substr($pageText, $start, $end - $start);
            
            echo "Context:\n$context\n\n";
            break;
        }
    }
}