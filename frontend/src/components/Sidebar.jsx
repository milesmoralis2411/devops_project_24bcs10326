import { shortSha } from '../lib/format.js';

const NAV = [
  { id: 'dashboard', label: 'Dashboard', icon: '▦' },
  { id: 'products', label: 'Products', icon: '◫' },
  { id: 'movements', label: 'Movement log', icon: '⇅' },
];

const PIPELINE = ['Test', 'Build', 'Scan', 'Push', 'Deploy'];

export default function Sidebar({ view, onNavigate, alertCount, info, apiOnline }) {
  return (
    <aside className="sidebar">
      <div className="brand">
        <span className="brand-mark" aria-hidden="true">
          <svg viewBox="0 0 64 64" width="22" height="22">
            <path d="M32 13 50 23v18L32 51 14 41V23z" fill="none" stroke="currentColor" strokeWidth="5" strokeLinejoin="round" />
            <path d="M14 23l18 10 18-10M32 33v18" fill="none" stroke="currentColor" strokeWidth="5" strokeLinejoin="round" />
          </svg>
        </span>
        <div>
          <b>StockPilot</b>
          <small>Inventory control</small>
        </div>
      </div>

      <nav aria-label="Main">
        {NAV.map((item) => (
          <button
            key={item.id}
            className={view === item.id ? 'active' : ''}
            aria-current={view === item.id ? 'page' : undefined}
            onClick={() => onNavigate(item.id)}
          >
            <span aria-hidden="true">{item.icon}</span>
            <span className="nav-label">{item.label}</span>
            {item.id === 'products' && alertCount > 0 && <em className="badge">{alertCount}</em>}
          </button>
        ))}
      </nav>

      <div className="side-bottom">
        <div className="build-card">
          <div className="build-row">
            <span className={`pulse ${apiOnline ? 'online' : 'offline'}`} aria-hidden="true" />
            <b>{apiOnline ? 'API online' : 'API unreachable'}</b>
          </div>
          <dl>
            <dt>Build</dt>
            <dd>
              <code>{shortSha(info?.git_sha)}</code>
            </dd>
            <dt>Env</dt>
            <dd>{info?.environment ?? '—'}</dd>
            <dt>Version</dt>
            <dd>{info?.version ?? '—'}</dd>
          </dl>
          <ol className="pipeline" aria-label="Delivery pipeline">
            {PIPELINE.map((stage) => (
              <li key={stage}>{stage}</li>
            ))}
          </ol>
        </div>
      </div>
    </aside>
  );
}
