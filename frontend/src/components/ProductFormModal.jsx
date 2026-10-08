import { useState } from 'react';

import Modal from './Modal.jsx';

const EMPTY = {
  sku: '',
  name: '',
  category: '',
  supplier: '',
  location: '',
  description: '',
  quantity: 0,
  reorder_level: 10,
  unit_price: 0,
};

const EDITABLE = ['sku', 'name', 'category', 'supplier', 'location', 'description', 'reorder_level', 'unit_price'];

export default function ProductFormModal({ product, categories, onSubmit, onClose }) {
  const editing = Boolean(product);
  const [form, setForm] = useState(() =>
    editing ? Object.fromEntries(EDITABLE.map((key) => [key, product[key]])) : EMPTY,
  );
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');

  const bind = (field) => ({
    name: field,
    value: form[field],
    onChange: (event) => setForm((current) => ({ ...current, [field]: event.target.value })),
  });

  const submit = async (event) => {
    event.preventDefault();
    setSaving(true);
    setError('');
    const payload = {
      ...form,
      sku: form.sku.trim().toUpperCase(),
      reorder_level: Number(form.reorder_level),
      unit_price: Number(form.unit_price),
    };
    if (editing) delete payload.quantity;
    else payload.quantity = Number(form.quantity);
    try {
      await onSubmit(payload);
    } catch (err) {
      setError(err.message);
      setSaving(false);
    }
  };

  return (
    <Modal
      eyebrow={editing ? `EDIT · ${product.sku}` : 'NEW PRODUCT'}
      title={editing ? 'Update product details' : 'Add a product to the catalogue'}
      onClose={onClose}
      size="lg"
    >
      <form onSubmit={submit} className="form-grid">
        <label>
          SKU
          <input {...bind('sku')} required pattern="[A-Za-z0-9][A-Za-z0-9\-]{2,39}" placeholder="ELEC-USBC-1M" title="3-40 letters, digits or dashes" />
        </label>
        <label>
          Category
          <input {...bind('category')} required maxLength={60} list="category-options" placeholder="Electronics" />
          <datalist id="category-options">
            {categories.map((category) => (
              <option key={category} value={category} />
            ))}
          </datalist>
        </label>
        <label className="span-2">
          Product name
          <input {...bind('name')} required maxLength={160} placeholder="USB-C charging cable (1 m)" />
        </label>
        <label>
          Supplier
          <input {...bind('supplier')} maxLength={120} placeholder="Volt Distributors" />
        </label>
        <label>
          Bin location
          <input {...bind('location')} maxLength={60} placeholder="A-01-02" />
        </label>
        {!editing && (
          <label>
            Opening stock
            <input {...bind('quantity')} type="number" min="0" step="1" required />
          </label>
        )}
        <label>
          Reorder level
          <input {...bind('reorder_level')} type="number" min="0" step="1" required />
        </label>
        <label>
          Unit price (₹)
          <input {...bind('unit_price')} type="number" min="0" step="0.01" required />
        </label>
        <label className="span-2">
          Description
          <textarea {...bind('description')} rows={2} maxLength={2000} placeholder="Optional notes for the warehouse team" />
        </label>
        {editing && (
          <p className="hint span-2">
            Quantity is changed through <b>Adjust stock</b> so that every change is recorded in the movement log.
          </p>
        )}
        {error && (
          <div className="form-error span-2" role="alert">
            {error}
          </div>
        )}
        <div className="form-actions span-2">
          <button type="button" className="ghost" onClick={onClose}>
            Cancel
          </button>
          <button className="primary" disabled={saving}>
            {saving ? 'Saving…' : editing ? 'Save changes' : 'Create product'}
          </button>
        </div>
      </form>
    </Modal>
  );
}
