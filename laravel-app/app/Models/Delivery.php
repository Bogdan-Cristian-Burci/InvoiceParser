<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Relations\BelongsTo;
use Illuminate\Database\Eloquent\SoftDeletes;

class Delivery extends Model
{
    use SoftDeletes;

    protected $fillable = [
        'ddt_series',
        'ddt_number',
        'ddt_date',
        'ddt_reason',
        'model_number',
        'model_name',
        'order_series',
        'order_number',
        'product_name',
        'product_properties',
        'bill_id'
    ];

    public function bill(): BelongsTo
    {
        return $this->belongsTo(Bill::class);
    }

    protected function casts(): array
    {
        return [
            'ddt_date' => 'date',
        ];
    }
}
