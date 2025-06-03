<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\SoftDeletes;

class Bill extends Model
{
    use SoftDeletes;

    protected $fillable = [
        'bill_number',
        'bill_date',
        'customer_code',
        'customer_name',
        'customer_address',
        'total_amount',
        'currency',
        'package_count',
        'net_weight_kg',
        'gross_weight_kg',
        'shipping_term',
    ];
}
