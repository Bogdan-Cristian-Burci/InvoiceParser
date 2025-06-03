<?php

namespace App\Http\Resources;

use App\Models\Delivery;
use Illuminate\Http\Request;
use Illuminate\Http\Resources\Json\JsonResource;

/** @mixin Delivery */
class DeliveryResource extends JsonResource
{
    public function toArray(Request $request): array
    {
        return [
            'id' => $this->id,
            'ddt_number' => $this->ddt_number,
            'ddt_date' => $this->ddt_date,
            'model_code' => $this->model_code,
            'model_internal_code' => $this->model_internal_code,
            'model_label' => $this->model_label,
            'created_at' => $this->created_at,
            'updated_at' => $this->updated_at,

            'bill_id' => $this->bill_id,

            'bill' => new BillResource($this->whenLoaded('bill')),
        ];
    }
}
