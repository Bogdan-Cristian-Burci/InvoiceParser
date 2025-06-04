<?php

use App\Http\Controllers\BillController;
use App\Http\Controllers\DeliveryController;
use App\Http\Controllers\ProductController;
use Illuminate\Support\Facades\Route;

Route::apiResource('bills', BillController::class);
Route::apiResource('deliveries', DeliveryController::class);
Route::apiResource('products', ProductController::class);

Route::post('bills/scan-pdf', [BillController::class, 'scanPdf']);
Route::post('bills/test-coordinate-parsing', [BillController::class, 'testCoordinateBasedParsing']);