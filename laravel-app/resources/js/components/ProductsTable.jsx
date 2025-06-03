import React, { useMemo } from 'react';
import {
    useReactTable,
    getCoreRowModel,
    getSortedRowModel,
    getFilteredRowModel,
    flexRender,
} from '@tanstack/react-table';

const ProductsTable = ({ products = [] }) => {
    const columns = useMemo(() => [
        {
            header: 'Bill Info',
            columns: [
                {
                    accessorKey: 'bill.bill_number',
                    header: 'Bill #',
                    cell: ({ getValue }) => (
                        <span className="font-mono text-sm">{getValue() || '-'}</span>
                    ),
                },
                {
                    accessorKey: 'bill.bill_date',
                    header: 'Date',
                    cell: ({ getValue }) => (
                        <span className="text-sm">{getValue() || '-'}</span>
                    ),
                },
                {
                    accessorKey: 'bill.customer_name',
                    header: 'Customer',
                    cell: ({ getValue }) => (
                        <span className="text-sm font-medium">{getValue() || '-'}</span>
                    ),
                },
                {
                    accessorKey: 'bill.total_amount',
                    header: 'Bill Total',
                    cell: ({ getValue }) => {
                        const value = getValue();
                        const numValue = typeof value === 'number' ? value : parseFloat(value);
                        const displayValue = isNaN(numValue) ? 0 : numValue;
                        return (
                            <span className="text-sm font-medium text-green-600">
                                €{displayValue.toFixed(2)}
                            </span>
                        );
                    },
                },
            ],
        },
        {
            header: 'Delivery Info',
            columns: [
                {
                    accessorKey: 'delivery.ddt_number',
                    header: 'DDT #',
                    cell: ({ getValue }) => (
                        <span className="font-mono text-sm">{getValue() || '-'}</span>
                    ),
                },
                {
                    accessorKey: 'delivery.model_code',
                    header: 'Model Code',
                    cell: ({ getValue }) => (
                        <span className="font-mono text-xs">{getValue() || '-'}</span>
                    ),
                },
                {
                    accessorKey: 'delivery.model_label',
                    header: 'Model',
                    cell: ({ getValue }) => (
                        <span className="text-sm">{getValue() || '-'}</span>
                    ),
                },
            ],
        },
        {
            header: 'Product Details',
            columns: [
                {
                    accessorKey: 'product_code',
                    header: 'Product Code',
                    cell: ({ getValue }) => (
                        <span className="font-mono text-xs">{getValue() || '-'}</span>
                    ),
                },
                {
                    accessorKey: 'description',
                    header: 'Description',
                    cell: ({ getValue }) => (
                        <span className="text-sm">{getValue() || '-'}</span>
                    ),
                },
                {
                    accessorKey: 'material',
                    header: 'Material',
                    cell: ({ getValue }) => (
                        <span className="text-sm">{getValue() || '-'}</span>
                    ),
                },
                {
                    accessorKey: 'quantity',
                    header: 'Qty',
                    cell: ({ getValue }) => (
                        <span className="text-sm">{getValue() || '0'}</span>
                    ),
                },
                {
                    accessorKey: 'unit_of_measure',
                    header: 'Unit',
                    cell: ({ getValue }) => (
                        <span className="text-sm">{getValue() || '-'}</span>
                    ),
                },
                {
                    accessorKey: 'unit_price',
                    header: 'Unit Price',
                    cell: ({ getValue }) => {
                        const value = getValue();
                        const numValue = typeof value === 'number' ? value : parseFloat(value);
                        const displayValue = isNaN(numValue) ? 0 : numValue;
                        return (
                            <span className="text-sm">€{displayValue.toFixed(2)}</span>
                        );
                    },
                },
                {
                    accessorKey: 'total_price',
                    header: 'Total',
                    cell: ({ getValue }) => {
                        const value = getValue();
                        const numValue = typeof value === 'number' ? value : parseFloat(value);
                        const displayValue = isNaN(numValue) ? 0 : numValue;
                        return (
                            <span className="text-sm font-medium text-blue-600">
                                €{displayValue.toFixed(2)}
                            </span>
                        );
                    },
                },
                {
                    accessorKey: 'width_cm',
                    header: 'Width (cm)',
                    cell: ({ getValue }) => (
                        <span className="text-sm">{getValue() || '-'}</span>
                    ),
                },
            ],
        },
    ], []);

    const table = useReactTable({
        data: products,
        columns,
        getCoreRowModel: getCoreRowModel(),
        getSortedRowModel: getSortedRowModel(),
        getFilteredRowModel: getFilteredRowModel(),
    });

    if (!products.length) {
        return (
            <div className="text-center py-8">
                <p className="text-gray-500">No products uploaded yet. Upload an invoice PDF to see the extracted data.</p>
            </div>
        );
    }

    return (
        <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200">
                    <thead className="bg-gray-50">
                        {table.getHeaderGroups().map(headerGroup => (
                            <tr key={headerGroup.id}>
                                {headerGroup.headers.map(header => (
                                    <th
                                        key={header.id}
                                        className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:bg-gray-100"
                                        onClick={header.column.getToggleSortingHandler()}
                                    >
                                        <div className="flex items-center space-x-1">
                                            <span>
                                                {header.isPlaceholder
                                                    ? null
                                                    : flexRender(header.column.columnDef.header, header.getContext())
                                                }
                                            </span>
                                            <span className="text-gray-400">
                                                {{
                                                    asc: '↑',
                                                    desc: '↓',
                                                }[header.column.getIsSorted()] ?? '↕'}
                                            </span>
                                        </div>
                                    </th>
                                ))}
                            </tr>
                        ))}
                    </thead>
                    <tbody className="bg-white divide-y divide-gray-200">
                        {table.getRowModel().rows.map(row => (
                            <tr key={row.id} className="hover:bg-gray-50">
                                {row.getVisibleCells().map(cell => (
                                    <td key={cell.id} className="px-4 py-4 whitespace-nowrap">
                                        {flexRender(cell.column.columnDef.cell, cell.getContext())}
                                    </td>
                                ))}
                            </tr>
                        ))}
                    </tbody>
                </table>
        </div>
    );
};

export default ProductsTable;