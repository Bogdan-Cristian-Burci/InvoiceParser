<?php

namespace App\Http\Requests;

use Illuminate\Foundation\Http\FormRequest;

class BillRequest extends FormRequest
{
    public function rules(): array
    {
        return [
            'bill_number' => ['required'],
            'bill_date' => ['required'],
            'customer_code' => ['required'],
            'customer_name' => ['required'],
            'customer_address' => ['required'],
            'total_amount' => ['required', 'numeric'],
            'currency' => ['required'],
            'package_count' => ['required', 'integer'],
            'net_weight_kg' => ['required', 'numeric'],
            'gross_weight_kg' => ['required', 'numeric'],
            'shipping_term' => ['required'],
        ];
    }

    public function authorize(): bool
    {
        return true;
    }
}
