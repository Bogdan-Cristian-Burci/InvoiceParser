<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration {
    public function up(): void
    {
        Schema::create('deliveries', function (Blueprint $table) {
            $table->id();
            $table->string('ddt_series')->nullable();
            $table->string('ddt_number')->nullable();
            $table->date('ddt_date')->nullable();
            $table->string('ddt_reason')->nullable();
            $table->string('model_number')->nullable();
            $table->string('model_name')->nullable();
            $table->string('order_series')->nullable();
            $table->string('order_number')->nullable();
            $table->string('product_name')->nullable();
            $table->text('product_properties')->nullable();
            $table->unsignedBigInteger('bill_id');
            $table->timestamps();
            $table->softDeletes();

            $table->foreign('bill_id')
                ->references('id')->on('bills')
                ->onDelete('cascade');
    }

    public function down(): void
    {
        Schema::dropIfExists('deliveries');
    }
};
