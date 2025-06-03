<?php

namespace App\Http\Requests;

use Illuminate\Foundation\Http\FormRequest;

class DeliveryRequest extends FormRequest
{
    public function rules(): array
    {
        return [
            'ddt_number' => ['required'],
            'ddt_date' => ['required', 'date'],
            'model_code' => ['required'],
            'model_internal_code' => ['required'],
            'model_label' => ['required'],
            'bill_id' => ['required', 'exists:bills'],
        ];
    }

    public function authorize(): bool
    {
        return true;
    }
}
