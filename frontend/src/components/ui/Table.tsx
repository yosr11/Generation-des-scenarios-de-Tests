import React from 'react'
import { ChevronUp, ChevronDown } from 'lucide-react'

interface TableColumn {
  key: string
  label: string
  width?: string
  sortable?: boolean
  render?: (value: any, row: any, rowIndex: number) => React.ReactNode
}

interface TableProps {
  columns: TableColumn[]
  data: any[]
  loading?: boolean
  empty?: React.ReactNode
  onRowClick?: (row: any, rowIndex: number) => void
  sortable?: boolean
}

export const Table = React.forwardRef<HTMLTableElement, TableProps>(
  (
    {
      columns,
      data,
      loading = false,
      empty,
      onRowClick,
      sortable = false,
    },
    ref
  ) => {
    const [sortKey, setSortKey] = React.useState<string | null>(null)
    const [sortOrder, setSortOrder] = React.useState<'asc' | 'desc'>('asc')

    const handleSort = (key: string) => {
      if (sortKey === key) {
        setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc')
      } else {
        setSortKey(key)
        setSortOrder('asc')
      }
    }

    let displayData = [...data]

    if (sortable && sortKey) {
      displayData.sort((a, b) => {
        const aVal = a[sortKey]
        const bVal = b[sortKey]

        if (typeof aVal === 'string') {
          return sortOrder === 'asc'
            ? aVal.localeCompare(bVal)
            : bVal.localeCompare(aVal)
        }

        return sortOrder === 'asc' ? aVal - bVal : bVal - aVal
      })
    }

    if (loading) {
      return (
        <div className="text-center py-8 text-slate-500">
          <div className="inline-block animate-spin">⌛</div>
        </div>
      )
    }

    if (displayData.length === 0) {
      return (
        <div className="text-center py-8 text-slate-500">
          {empty || 'No data available'}
        </div>
      )
    }

    return (
      <table
        ref={ref}
        className="w-full text-sm text-slate-900 border-collapse"
      >
        <thead>
          <tr className="border-b border-slate-200 bg-slate-50">
            {columns.map((column) => (
              <th
                key={column.key}
                onClick={() =>
                  column.sortable && sortable && handleSort(column.key)
                }
                className={`
                  px-6 py-3 text-left font-semibold text-slate-700
                  ${column.width ? `w-${column.width}` : ''}
                  ${column.sortable && sortable ? 'cursor-pointer hover:bg-slate-100' : ''}
                `}
                style={{ width: column.width }}
              >
                <div className="flex items-center gap-2">
                  {column.label}
                  {column.sortable && sortable && sortKey === column.key && (
                    <span>
                      {sortOrder === 'asc' ? (
                        <ChevronUp className="w-4 h-4" />
                      ) : (
                        <ChevronDown className="w-4 h-4" />
                      )}
                    </span>
                  )}
                </div>
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {displayData.map((row, rowIndex) => (
            <tr
              key={rowIndex}
              onClick={() => onRowClick && onRowClick(row, rowIndex)}
              className={`
                border-b border-slate-100 hover:bg-slate-50 transition-colors
                ${onRowClick ? 'cursor-pointer' : ''}
              `}
            >
              {columns.map((column) => (
                <td key={column.key} className="px-6 py-4">
                  {column.render
                    ? column.render(row[column.key], row, rowIndex)
                    : row[column.key]}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    )
  }
)

Table.displayName = 'Table'
