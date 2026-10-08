import { useCallback, useEffect, useMemo, useState } from 'react';

import ActivityFeed from './components/ActivityFeed.jsx';
import AdjustStockModal from './components/AdjustStockModal.jsx';
import CategoryBreakdown from './components/CategoryBreakdown.jsx';
import ConfirmDialog from './components/ConfirmDialog.jsx';
import KpiCards from './components/KpiCards.jsx';
import MovementsView from './components/MovementsView.jsx';
import ProductFormModal from './components/ProductFormModal.jsx';
import ProductTable from './components/ProductTable.jsx';
import ReorderAlerts from './components/ReorderAlerts.jsx';
import Sidebar from './components/Sidebar.jsx';
import Toasts from './components/Toasts.jsx';
import { api } from './lib/api.js';
import { REASONS, signed } from './lib/format.js';

const EMPTY_STATS = {
  total_products: 0,
  total_units: 0,
  inventory_value: 0,
  in_stock: 0,
  low_stock: 0,
  out_of_stock: 0,
  categories: [],
};
const REFRESH_MS = 30_000;

const TITLES = {
  dashboard: ['WAREHOUSE / OVERVIEW', 'Inventory dashboard', 'Live stock levels, reorder alerts and recent movements.'],
  products: ['WAREHOUSE / CATALOGUE', 'Products', 'Search, filter and manage every SKU in the warehouse.'],
  movements: ['WAREHOUSE / AUDIT', 'Movement log', 'Every receipt, sale, return and write-off, newest first.'],
};

function greeting() {
  const hour = new Date().getHours();
  if (hour < 12) return 'Good morning';
  if (hour < 17) return 'Good afternoon';
  return 'Good evening';
}

export default function App() {
  const [view, setView] = useState('dashboard');
  const [data, setData] = useState({ products: [], stats: EMPTY_STATS, movements: [], categories: [] });
  const [info, setInfo] = useState(null);
  const [loading, setLoading] = useState(true);
  const [loaded, setLoaded] = useState(false);
  const [error, setError] = useState('');
  const [filters, setFilters] = useState({ search: '', status: 'ALL', category: '' });
  const [modal, setModal] = useState(null);
  const [toasts, setToasts] = useState([]);

  const notify = useCallback((message, tone = 'success') => {
    const id = crypto.randomUUID?.() ?? String(Math.random());
    setToasts((current) => [...current, { id, message, tone }]);
    setTimeout(() => setToasts((current) => current.filter((toast) => toast.id !== id)), 4000);
  }, []);

  const load = useCallback(async () => {
    try {
      const [products, stats, movements, categories] = await Promise.all([
        api.products(),
        api.stats(),
        api.recentMovements(100),
        api.categories(),
      ]);
      setData({ products, stats, movements, categories });
      setError('');
      setLoaded(true);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
    api.info().then(setInfo).catch(() => setInfo(null));
    const timer = setInterval(() => document.visibilityState === 'visible' && load(), REFRESH_MS);
    return () => clearInterval(timer);
  }, [load]);

  const visibleProducts = useMemo(() => {
    const term = filters.search.trim().toLowerCase();
    return data.products.filter(
      (product) =>
        (filters.status === 'ALL' || product.stock_status === filters.status) &&
        (!filters.category || product.category === filters.category) &&
        (!term || [product.sku, product.name, product.supplier, product.location].some((v) => v.toLowerCase().includes(term))),
    );
  }, [data.products, filters]);

  const alertCount = data.stats.low_stock + data.stats.out_of_stock;
  const closeModal = () => setModal(null);

  const afterChange = async (message) => {
    closeModal();
    notify(message);
    await load();
  };

  const saveProduct = async (payload) => {
    if (modal.product) {
      const updated = await api.updateProduct(modal.product.id, payload);
      await afterChange(`Saved changes to ${updated.name}`);
    } else {
      const created = await api.createProduct(payload);
      await afterChange(`Added ${created.name} (${created.sku})`);
    }
  };

  const adjustStock = async (payload) => {
    const { product, movement } = await api.adjustStock(modal.product.id, payload);
    await afterChange(`${REASONS[movement.reason].label}: ${signed(movement.change)} × ${product.name} — ${product.quantity} on hand`);
  };

  const deleteProduct = async () => {
    await api.deleteProduct(modal.product.id);
    await afterChange(`Deleted ${modal.product.name}`);
  };

  const [eyebrow, title, subtitle] = TITLES[view];
  const table = (
    <ProductTable
      products={visibleProducts}
      totalCount={data.products.length}
      loading={loading}
      categories={data.categories}
      filters={filters}
      onFiltersChange={setFilters}
      onAdjust={(product) => setModal({ type: 'adjust', product })}
      onEdit={(product) => setModal({ type: 'edit', product })}
      onDelete={(product) => setModal({ type: 'delete', product })}
    />
  );

  return (
    <div className="app">
      <Sidebar view={view} onNavigate={setView} alertCount={alertCount} info={info} apiOnline={loaded && !error} />

      <main className="main">
        <header className="page-head">
          <div>
            <p className="eyebrow">{eyebrow}</p>
            <h1>{view === 'dashboard' ? `${greeting()} 👋` : title}</h1>
            <p className="muted">{subtitle}</p>
          </div>
          <div className="head-actions">
            {view !== 'movements' && (
              <input
                type="search"
                className="search"
                placeholder="Search SKU, product, supplier…"
                aria-label="Search products"
                value={filters.search}
                onChange={(event) => setFilters((current) => ({ ...current, search: event.target.value }))}
              />
            )}
            <button className="primary" onClick={() => setModal({ type: 'create' })}>
              <span aria-hidden="true">＋</span> New product
            </button>
          </div>
        </header>

        {error && (
          <div className="alert" role="alert">
            <span>
              ⚠ {error}. {loaded ? 'Showing the last data we received.' : 'Check that the backend and PostgreSQL are running.'}
            </span>
            <button className="small" onClick={load}>
              Retry
            </button>
          </div>
        )}

        {view === 'dashboard' && (
          <>
            <KpiCards stats={data.stats} />
            <div className="insights">
              <ReorderAlerts products={data.products} onRestock={(product) => setModal({ type: 'adjust', product, reason: 'RESTOCK' })} />
              <ActivityFeed movements={data.movements.slice(0, 5)} onViewAll={() => setView('movements')} />
              <CategoryBreakdown categories={data.stats.categories} total={data.stats.inventory_value} />
            </div>
            {table}
          </>
        )}
        {view === 'products' && table}
        {view === 'movements' && <MovementsView movements={data.movements} loading={loading} />}

        <footer className="footer">
          StockPilot · FastAPI + React + PostgreSQL · shipped by GitHub Actions to Kubernetes
        </footer>
      </main>

      {(modal?.type === 'create' || modal?.type === 'edit') && (
        <ProductFormModal product={modal.product} categories={data.categories} onSubmit={saveProduct} onClose={closeModal} />
      )}
      {modal?.type === 'adjust' && (
        <AdjustStockModal product={modal.product} initialReason={modal.reason} onSubmit={adjustStock} onClose={closeModal} />
      )}
      {modal?.type === 'delete' && (
        <ConfirmDialog
          title={`Delete ${modal.product.name}?`}
          message={`This removes ${modal.product.sku} and its full movement history. This cannot be undone.`}
          onConfirm={deleteProduct}
          onClose={closeModal}
        />
      )}
      <Toasts toasts={toasts} onDismiss={(id) => setToasts((current) => current.filter((toast) => toast.id !== id))} />
    </div>
  );
}
