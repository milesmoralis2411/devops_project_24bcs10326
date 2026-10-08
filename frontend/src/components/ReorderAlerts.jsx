import { formatNumber, STATUS_LABELS } from '../lib/format.js';

export default function ReorderAlerts({ products, onRestock }) {
  const alerts = products
    .filter((product) => product.stock_status !== 'IN_STOCK')
    .sort((a, b) => a.quantity / Math.max(a.reorder_level, 1) - b.quantity / Math.max(b.reorder_level, 1))
    .slice(0, 5);

  return (
    <section className="panel side-panel">
      <div className="panel-head">
        <div>
          <h2>Reorder alerts</h2>
          <p className="muted">Products at or below their reorder level</p>
        </div>
      </div>
      {alerts.length ? (
        <ul className="alerts">
          {alerts.map((product) => (
            <li key={product.id}>
              <span className={`status-dot ${product.stock_status.toLowerCase()}`} aria-hidden="true" />
              <div>
                <b>{product.name}</b>
                <small>
                  {STATUS_LABELS[product.stock_status]} · {formatNumber(product.quantity)} left, reorder at{' '}
                  {formatNumber(product.reorder_level)}
                </small>
              </div>
              <button className="small" onClick={() => onRestock(product)}>
                Restock
              </button>
            </li>
          ))}
        </ul>
      ) : (
        <div className="empty compact">All products are above their reorder level. 🎉</div>
      )}
    </section>
  );
}
