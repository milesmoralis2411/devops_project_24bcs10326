import { formatCompactCurrency, formatNumber } from '../lib/format.js';

export default function CategoryBreakdown({ categories, total }) {
  const sorted = [...categories].sort((a, b) => b.value - a.value);
  return (
    <section className="panel side-panel">
      <div className="panel-head">
        <div>
          <h2>Value by category</h2>
          <p className="muted">Share of total inventory value</p>
        </div>
      </div>
      {sorted.length ? (
        <ul className="breakdown">
          {sorted.map((category) => {
            const share = total ? Math.round((category.value / total) * 100) : 0;
            return (
              <li key={category.category}>
                <div className="breakdown-label">
                  <b>{category.category}</b>
                  <span>
                    {formatCompactCurrency(category.value)} · {formatNumber(category.units)} units
                  </span>
                </div>
                <div className="bar neutral" role="img" aria-label={`${share}% of inventory value`}>
                  <i style={{ width: `${Math.max(share, 2)}%` }} />
                </div>
              </li>
            );
          })}
        </ul>
      ) : (
        <div className="empty compact">Add products to see the breakdown.</div>
      )}
    </section>
  );
}
