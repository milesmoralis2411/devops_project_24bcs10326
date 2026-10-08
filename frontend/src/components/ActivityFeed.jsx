import { REASONS, signed, timeAgo } from '../lib/format.js';

export default function ActivityFeed({ movements, onViewAll }) {
  return (
    <section className="panel side-panel">
      <div className="panel-head">
        <div>
          <h2>Recent activity</h2>
          <p className="muted">Latest stock movements</p>
        </div>
        {onViewAll && (
          <button className="link" onClick={onViewAll}>
            View all
          </button>
        )}
      </div>
      {movements.length ? (
        <ul className="feed">
          {movements.map((movement) => {
            const reason = REASONS[movement.reason];
            return (
              <li key={movement.id}>
                <span className={`feed-icon ${movement.change > 0 ? 'in' : 'out'}`} aria-hidden="true">
                  {reason.icon}
                </span>
                <div>
                  <b>
                    {reason.label}: {signed(movement.change)} × {movement.product_name}
                  </b>
                  <small>
                    {movement.note ? `${movement.note} · ` : ''}
                    {timeAgo(movement.created_at)}
                  </small>
                </div>
              </li>
            );
          })}
        </ul>
      ) : (
        <div className="empty compact">No stock movements yet.</div>
      )}
    </section>
  );
}
