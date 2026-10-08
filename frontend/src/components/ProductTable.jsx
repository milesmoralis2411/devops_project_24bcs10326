import { formatCurrency, formatNumber, STATUS_LABELS, stockFill } from '../lib/format.js';

const STATUS_FILTERS = ['ALL', 'IN_STOCK', 'LOW_STOCK', 'OUT_OF_STOCK'];

export default function ProductTable({
  products,
  totalCount,
  loading,
  categories,
  filters,
  onFiltersChange,
  onAdjust,
  onEdit,
  onDelete,
}) {
  const setFilter = (key, value) => onFiltersChange({ ...filters, [key]: value });

  return (
    <section className="panel">
      <div className="panel-head">
        <div>
          <h2>Products</h2>
          <p className="muted">
            Showing {products.length} of {totalCount} SKUs
          </p>
        </div>
        <div className="toolbar">
          <div className="chips" role="tablist" aria-label="Filter by stock status">
            {STATUS_FILTERS.map((status) => (
              <button
                key={status}
                role="tab"
                aria-selected={filters.status === status}
                className={filters.status === status ? 'selected' : ''}
                onClick={() => setFilter('status', status)}
              >
                {status === 'ALL' ? 'All' : STATUS_LABELS[status]}
              </button>
            ))}
          </div>
          <select
            aria-label="Filter by category"
            value={filters.category}
            onChange={(event) => setFilter('category', event.target.value)}
          >
            <option value="">All categories</option>
            {categories.map((category) => (
              <option key={category}>{category}</option>
            ))}
          </select>
        </div>
      </div>

      {loading ? (
        <div className="skeleton-list" aria-busy="true">
          {Array.from({ length: 5 }, (_, i) => (
            <div key={i} className="skeleton-row" />
          ))}
        </div>
      ) : (
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Product</th>
                <th className="hide-sm">Category</th>
                <th>Stock</th>
                <th className="num hide-md">Unit price</th>
                <th className="num hide-md">Value</th>
                <th>Status</th>
                <th className="actions-col">
                  <span className="sr-only">Actions</span>
                </th>
              </tr>
            </thead>
            <tbody>
              {products.map((product) => (
                <tr key={product.id}>
                  <td>
                    <div className="product-cell">
                      <b>{product.name}</b>
                      <small>
                        <code>{product.sku}</code>
                        {product.supplier && ` · ${product.supplier}`}
                        {product.location && ` · Bin ${product.location}`}
                      </small>
                    </div>
                  </td>
                  <td className="hide-sm">
                    <span className="tag">{product.category}</span>
                  </td>
                  <td>
                    <div className="stock-cell">
                      <span>
                        <b>{formatNumber(product.quantity)}</b>
                        <small> / reorder at {formatNumber(product.reorder_level)}</small>
                      </span>
                      <div className={`bar ${product.stock_status.toLowerCase()}`}>
                        <i style={{ width: `${stockFill(product.quantity, product.reorder_level)}%` }} />
                      </div>
                    </div>
                  </td>
                  <td className="num hide-md">{formatCurrency(product.unit_price)}</td>
                  <td className="num hide-md">{formatCurrency(product.stock_value)}</td>
                  <td>
                    <span className={`status ${product.stock_status.toLowerCase()}`}>{STATUS_LABELS[product.stock_status]}</span>
                  </td>
                  <td className="actions-col">
                    <div className="row-actions">
                      <button className="small" onClick={() => onAdjust(product)}>
                        Adjust
                      </button>
                      <button className="icon-btn" title="Edit product" aria-label={`Edit ${product.name}`} onClick={() => onEdit(product)}>
                        ✎
                      </button>
                      <button
                        className="icon-btn danger-text"
                        title="Delete product"
                        aria-label={`Delete ${product.name}`}
                        onClick={() => onDelete(product)}
                      >
                        🗑
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {!products.length && (
            <div className="empty">
              <b>No products match these filters.</b>
              <span>Try clearing the search or choosing another status.</span>
            </div>
          )}
        </div>
      )}
    </section>
  );
}
