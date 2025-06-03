<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration {
    public function up(): void
    {
        Schema::create('products', function (Blueprint $table) {
            $table->id();
            $table->unsignedBigInteger('delivery_id');
            $table->string('product_code', 100);
            $table->text('description');
            $table->text('material');
            $table->string('unit_of_measure', 10);
            $table->decimal('quantity', 10, 5);
            $table->decimal('unit_price', 10, 5);
            $table->decimal('total_price', 10, 2);
            $table->integer('width_cm')->nullable();
            $table->timestamps();
            $table->softDeletes();

            $table->foreign('delivery_id')
                ->references('id')->on('deliveries')
                ->onDelete('cascade');
        });
    }

    public function down(): void
    {
        Schema::dropIfExists('products');
    }
};
