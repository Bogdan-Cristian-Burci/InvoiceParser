<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration {
    public function up(): void
    {
        Schema::create('bills', function (Blueprint $table) {
            $table->id();
            $table->string('bill_number', 50);
            $table->date('bill_date');
            $table->string('customer_code', 50);
            $table->string('customer_name', 255);
            $table->text('customer_address');
            $table->decimal('total_amount', 10, 5);
            $table->string('currency', 10);
            $table->integer('package_count');
            $table->decimal('net_weight_kg', 10, 2);
            $table->decimal('gross_weight_kg', 10, 2);
            $table->string('shipping_term', 50);
            $table->timestamps();
            $table->softDeletes();
        });
    }

    public function down(): void
    {
        Schema::dropIfExists('bills');
    }
};
