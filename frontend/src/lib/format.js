const currency = new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 2 });
const compactCurrency = new Intl.NumberFormat('en-IN', {
  style: 'currency',
  currency: 'INR',
  notation: 'compact',
  maximumFractionDigits: 1,
});
const number = new Intl.NumberFormat('en-IN');

export const formatCurrency = (value) => currency.format(value ?? 0);
export const formatCompactCurrency = (value) => compactCurrency.format(value ?? 0);
export const formatNumber = (value) => number.format(value ?? 0);

export const STATUS_LABELS = {
  IN_STOCK: 'In stock',
  LOW_STOCK: 'Low stock',
  OUT_OF_STOCK: 'Out of stock',
};

export const REASONS = {
  INITIAL: { label: 'Opening stock', icon: '★', direction: 'in' },
  RESTOCK: { label: 'Restock', icon: '↓', direction: 'in' },
  RETURN: { label: 'Customer return', icon: '↩', direction: 'in' },
  SALE: { label: 'Sale', icon: '↑', direction: 'out' },
  DAMAGE: { label: 'Damaged / write-off', icon: '✕', direction: 'out' },
  ADJUSTMENT: { label: 'Stock count adjustment', icon: '±', direction: 'any' },
};

export function signed(value) {
  return value > 0 ? `+${formatNumber(value)}` : formatNumber(value);
}

export function timeAgo(isoDate, now = Date.now()) {
  const seconds = Math.max(0, Math.round((now - new Date(isoDate).getTime()) / 1000));
  if (seconds < 45) return 'just now';
  const minutes = Math.round(seconds / 60);
  if (minutes < 60) return `${minutes} min ago`;
  const hours = Math.round(minutes / 60);
  if (hours < 24) return `${hours} hr${hours === 1 ? '' : 's'} ago`;
  const days = Math.round(hours / 24);
  return `${days} day${days === 1 ? '' : 's'} ago`;
}

/** Fill level of the stock bar: reorder level sits at 40% so "low" is visually obvious. */
export function stockFill(quantity, reorderLevel) {
  if (quantity <= 0) return 0;
  const target = Math.max(reorderLevel, 1) * 2.5;
  return Math.min(100, Math.round((quantity / target) * 100));
}

export function shortSha(sha) {
  if (!sha || sha === 'dev') return 'dev';
  return sha.slice(0, 7);
}
