<?php

namespace App\Http\Requests;

use Illuminate\Foundation\Http\FormRequest;

class ProductRequest extends FormRequest
{
    public function rules(): array
    {
        return [
            'product_code' => ['required'],
            'description' => ['required'],
            'material' => ['required'],
            'unit_of_measure' => ['required'],
            'quantity' => ['required', 'numeric'],
            'unit_price' => ['required', 'numeric'],
            'total_price' => ['required', 'numeric'],
            'width_cm' => ['nullable', 'integer'],
            'delivery_id' => ['required', 'exists:deliveries'],
        ];
    }

    public function authorize(): bool
    {
        return true;
    }
}
