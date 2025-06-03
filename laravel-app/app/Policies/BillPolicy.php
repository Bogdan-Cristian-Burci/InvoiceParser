<?php

namespace App\Policies;

use App\Models\Bill;
use App\Models\User;
use Illuminate\Auth\Access\HandlesAuthorization;

class BillPolicy
{
    use HandlesAuthorization;

    public function viewAny(User $user): bool
    {
        return true;
    }

    public function view(User $user, Bill $bill): bool
    {
        return true;
    }

    public function create(User $user): bool
    {
        return true;
    }

    public function update(User $user, Bill $bill): bool
    {
        return true;
    }

    public function delete(User $user, Bill $bill): bool
    {
        return true;
    }

    public function restore(User $user, Bill $bill): bool
    {
    }

    public function forceDelete(User $user, Bill $bill): bool
    {
    }
}
