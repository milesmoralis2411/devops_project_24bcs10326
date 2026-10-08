// Thin wrapper around fetch. All calls are relative (/api/...): the browser never needs
// to know the backend's internal hostname - Nginx or the Ingress routes the request.
const BASE = '/api';

export class ApiError extends Error {
  constructor(message, status) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
  }
}

export function errorMessage(body, status) {
  const detail = body?.detail;
  if (typeof detail === 'string') return detail;
  if (Array.isArray(detail) && detail.length) {
    // FastAPI validation errors: [{loc: [...], msg: "..."}]
    return detail
      .map((item) => {
        const field = item.loc?.filter((part) => part !== 'body').join('.');
        const msg = String(item.msg ?? 'invalid value').replace(/^Value error, /, '');
        return field ? `${field}: ${msg}` : msg;
      })
      .join('; ');
  }
  return `Request failed (HTTP ${status})`;
}

async function request(path, { method = 'GET', body } = {}) {
  let response;
  try {
    response = await fetch(`${BASE}${path}`, {
      method,
      headers: body ? { 'Content-Type': 'application/json' } : undefined,
      body: body ? JSON.stringify(body) : undefined,
    });
  } catch {
    throw new ApiError('Cannot reach the StockPilot API', 0);
  }
  if (response.status === 204) return null;
  const payload = await response.json().catch(() => null);
  if (!response.ok) throw new ApiError(errorMessage(payload, response.status), response.status);
  return payload;
}

export const api = {
  info: () => request('/info'),
  stats: () => request('/stats'),
  categories: () => request('/categories'),
  products: () => request('/products'),
  recentMovements: (limit = 20) => request(`/movements?limit=${limit}`),
  productMovements: (id) => request(`/products/${id}/movements`),
  createProduct: (data) => request('/products', { method: 'POST', body: data }),
  updateProduct: (id, data) => request(`/products/${id}`, { method: 'PUT', body: data }),
  deleteProduct: (id) => request(`/products/${id}`, { method: 'DELETE' }),
  adjustStock: (id, data) => request(`/products/${id}/adjustments`, { method: 'POST', body: data }),
};
