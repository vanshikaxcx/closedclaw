import { ChevronDown, ChevronUp } from 'lucide-react';
import { useMemo, useState } from 'react';
import { cn } from '@/lib/utils';
import { EmptyState } from '@/src/components/ui/EmptyState';
import { LoadingSkeleton } from '@/src/components/ui/LoadingSkeleton';

export interface DataTableColumn<T> {
  key: string;
  header: string;
  width?: string;
  sortable?: boolean;
  render?: (value: unknown, row: T) => React.ReactNode;
}

export interface DataTablePagination {
  page: number;
  pageSize: number;
  total: number;
  onPageChange: (page: number) => void;
}

export interface DataTableFilter {
  id: string;
  label: string;
  node: React.ReactNode;
}

interface DataTableProps<T extends Record<string, unknown>> {
  columns: Array<DataTableColumn<T>>;
  data: T[];
  loading?: boolean;
  emptyState?: React.ReactNode;
  onRowClick?: (row: T) => void;
  pagination?: DataTablePagination;
  filters?: DataTableFilter[];
  rowKey?: (row: T, index: number) => string;
}

type SortState = { key: string; direction: 'asc' | 'desc' } | null;

export function DataTable<T extends Record<string, unknown>>({
  columns,
  data,
  loading = false,
  emptyState,
  onRowClick,
  pagination,
  filters,
  rowKey,
}: DataTableProps<T>) {
  const [sortState, setSortState] = useState<SortState>(null);

  const sortedData = useMemo(() => {
    if (!sortState) {
      return data;
    }

    const next = [...data];
    next.sort((left, right) => {
      const a = left[sortState.key as keyof T];
      const b = right[sortState.key as keyof T];

      if (typeof a === 'number' && typeof b === 'number') {
        return sortState.direction === 'asc' ? a - b : b - a;
      }

      const leftText = String(a ?? '').toLowerCase();
      const rightText = String(b ?? '').toLowerCase();
      if (leftText < rightText) {
        return sortState.direction === 'asc' ? -1 : 1;
      }
      if (leftText > rightText) {
        return sortState.direction === 'asc' ? 1 : -1;
      }
      return 0;
    });

    return next;
  }, [data, sortState]);

  const pageData = useMemo(() => {
    if (!pagination) {
      return sortedData;
    }

    const start = (pagination.page - 1) * pagination.pageSize;
    return sortedData.slice(start, start + pagination.pageSize);
  }, [pagination, sortedData]);

  const setSort = (column: DataTableColumn<T>) => {
    if (!column.sortable) {
      return;
    }

    setSortState((current) => {
      if (!current || current.key !== column.key) {
        return { key: column.key, direction: 'asc' };
      }
      if (current.direction === 'asc') {
        return { key: column.key, direction: 'desc' };
      }
      return null;
    });
  };

  const renderValue = (row: T, column: DataTableColumn<T>) => {
    const value = row[column.key as keyof T];
    if (column.render) {
      return column.render(value, row);
    }
    return String(value ?? '-');
  };

  if (loading) {
    return <LoadingSkeleton variant="table-row" count={6} />;
  }

  if (!pageData.length) {
    return (
      <>
        {filters?.length ? <div className="mb-3 flex flex-wrap gap-3">{filters.map((filter) => <div key={filter.id}>{filter.node}</div>)}</div> : null}
        {emptyState ?? <EmptyState icon="generic" title="No records yet" description="Once data is available it will appear here." />}
      </>
    );
  }

  const totalPages = pagination ? Math.max(1, Math.ceil(pagination.total / pagination.pageSize)) : 1;

  return (
    <div>
      {filters?.length ? <div className="mb-3 flex flex-wrap gap-3">{filters.map((filter) => <div key={filter.id}>{filter.node}</div>)}</div> : null}

      <div className="hidden overflow-x-auto rounded-2xl border border-[#E5E7EB] bg-white md:block">
        <table className="min-w-full text-left">
          <thead className="bg-[#f7faff]">
            <tr>
              {columns.map((column) => (
                <th
                  key={column.key}
                  style={column.width ? { width: column.width } : undefined}
                  className={cn('px-4 py-3 text-xs font-bold uppercase tracking-[0.1em] text-slate-500', column.sortable && 'cursor-pointer select-none')}
                  onClick={() => setSort(column)}
                >
                  <span className="inline-flex items-center gap-1">
                    {column.header}
                    {column.sortable ? (
                      sortState?.key === column.key ? (
                        sortState.direction === 'asc' ? <ChevronUp size={14} /> : <ChevronDown size={14} />
                      ) : (
                        <ChevronDown size={14} className="opacity-40" />
                      )
                    ) : null}
                  </span>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {pageData.map((row, index) => (
              <tr
                key={rowKey ? rowKey(row, index) : `${index}`}
                className={cn('border-t border-[#E5E7EB]', onRowClick ? 'cursor-pointer transition hover:bg-[#f8fbff]' : '')}
                onClick={() => onRowClick?.(row)}
              >
                {columns.map((column) => (
                  <td key={column.key} className="px-4 py-3 text-sm text-slate-700">
                    {renderValue(row, column)}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="space-y-3 md:hidden">
        {pageData.map((row, index) => (
          <button
            key={rowKey ? rowKey(row, index) : `${index}`}
            type="button"
            onClick={() => onRowClick?.(row)}
            className={cn(
              'paytm-surface w-full p-4 text-left',
              onRowClick ? 'transition hover:bg-[#f8fbff]' : 'cursor-default',
            )}
          >
            {columns.map((column) => (
              <div key={column.key} className="flex items-start justify-between gap-3 border-b border-dashed border-slate-200 py-2 last:border-b-0">
                <p className="text-[11px] font-bold uppercase tracking-wide text-slate-500">{column.header}</p>
                <div className="max-w-[62%] text-right text-sm text-slate-700">{renderValue(row, column)}</div>
              </div>
            ))}
          </button>
        ))}
      </div>

      {pagination ? (
        <div className="mt-3 flex items-center justify-between text-sm text-slate-600">
          <span>
            Page {pagination.page} of {totalPages}
          </span>
          <div className="flex gap-2">
            <button
              type="button"
              className="rounded-full border border-[#d1daea] px-3 py-1 disabled:opacity-50"
              onClick={() => pagination.onPageChange(Math.max(1, pagination.page - 1))}
              disabled={pagination.page <= 1}
            >
              Prev
            </button>
            <button
              type="button"
              className="rounded-full border border-[#d1daea] px-3 py-1 disabled:opacity-50"
              onClick={() => pagination.onPageChange(Math.min(totalPages, pagination.page + 1))}
              disabled={pagination.page >= totalPages}
            >
              Next
            </button>
          </div>
        </div>
      ) : null}
    </div>
  );
}
