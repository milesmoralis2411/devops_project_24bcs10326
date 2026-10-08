import { REASONS, signed, timeAgo } from '../lib/format.js';

export default function MovementsView({ movements, loading }) {
  return (
    <section className="panel">
      <div className="panel-head">
        <div>
          <h2>Movement log</h2>
          <p className="muted">Immutable audit trail of every stock change (latest 100)</p>
        </div>
      </div>
      {loading ? (
        <div className="skeleton-list" aria-busy="true">
          {Array.from({ length: 6 }, (_, i) => (
            <div key={i} className="skeleton-row" />
          ))}
        </div>
      ) : (
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>When</th>
                <th>Product</th>
                <th>Type</th>
                <th className="num">Change</th>
                <th className="num hide-sm">On hand after</th>
                <th className="hide-md">Reference</th>
              </tr>
            </thead>
            <tbody>
              {movements.map((movement) => (
                <tr key={movement.id}>
                  <td title={new Date(movement.created_at).toLocaleString()}>{timeAgo(movement.created_at)}</td>
                  <td>
                    <div className="product-cell">
                      <b>{movement.product_name}</b>
                      <small>
                        <code>{movement.product_sku}</code>
                      </small>
                    </div>
                  </td>
                  <td>
                    <span className="tag">{REASONS[movement.reason].label}</span>
                  </td>
                  <td className={`num change ${movement.change > 0 ? 'in' : 'out'}`}>{signed(movement.change)}</td>
                  <td className="num hide-sm">{movement.quantity_after}</td>
                  <td className="hide-md muted">{movement.note || '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
          {!movements.length && <div className="empty">No stock movements recorded yet.</div>}
        </div>
      )}
    </section>
  );
}
