<?php

namespace App\Http\Resources;

use App\Models\Bill;
use Illuminate\Http\Request;
use Illuminate\Http\Resources\Json\JsonResource;

/** @mixin Bill */
class BillResource extends JsonResource
{
    public function toArray(Request $request): array
    {
        return [
            'id' => $this->id,
            'bill_number' => $this->bill_number,
            'bill_date' => $this->bill_date,
            'customer_code' => $this->customer_code,
            'customer_name' => $this->customer_name,
            'customer_address' => $this->customer_address,
            'total_amount' => $this->total_amount,
            'currency' => $this->currency,
            'package_count' => $this->package_count,
            'net_weight_kg' => $this->net_weight_kg,
            'gross_weight_kg' => $this->gross_weight_kg,
            'shipping_term' => $this->shipping_term,
            'created_at' => $this->created_at,
            'updated_at' => $this->updated_at,
        ];
    }
}
