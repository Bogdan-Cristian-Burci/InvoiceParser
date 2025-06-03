<?php

namespace App\Http\Resources;

use App\Models\Product;
use Illuminate\Http\Request;
use Illuminate\Http\Resources\Json\JsonResource;

/** @mixin Product */
class ProductResource extends JsonResource
{
    public function toArray(Request $request): array
    {
        return [
            'id' => $this->id,
            'product_code' => $this->product_code,
            'description' => $this->description,
            'material' => $this->material,
            'unit_of_measure' => $this->unit_of_measure,
            'quantity' => $this->quantity,
            'unit_price' => $this->unit_price,
            'total_price' => $this->total_price,
            'width_cm' => $this->width_cm,
            'created_at' => $this->created_at,
            'updated_at' => $this->updated_at,

            'delivery_id' => $this->delivery_id,

            'delivery' => new DeliveryResource($this->whenLoaded('delivery')),
        ];
    }
}
