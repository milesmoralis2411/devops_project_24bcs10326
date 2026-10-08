import { useState } from 'react';

import { formatNumber, REASONS, signed } from '../lib/format.js';
import Modal from './Modal.jsx';

const OPTIONS = ['RESTOCK', 'SALE', 'RETURN', 'DAMAGE', 'ADJUSTMENT'];

export default function AdjustStockModal({ product, initialReason = 'RESTOCK', onSubmit, onClose }) {
  const [reason, setReason] = useState(initialReason);
  const [direction, setDirection] = useState('in');
  const [amount, setAmount] = useState('');
  const [note, setNote] = useState('');
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');

  const flow = REASONS[reason].direction === 'any' ? direction : REASONS[reason].direction;
  const units = Math.max(0, Math.floor(Number(amount) || 0));
  const change = flow === 'in' ? units : -units;
  const after = product.quantity + change;
  const invalid = units === 0 || after < 0;

  const submit = async (event) => {
    event.preventDefault();
    if (invalid) return;
    setSaving(true);
    setError('');
    try {
      await onSubmit({ change, reason, note: note.trim() });
    } catch (err) {
      setError(err.message);
      setSaving(false);
    }
  };

  return (
    <Modal eyebrow={`ADJUST STOCK · ${product.sku}`} title={product.name} onClose={onClose}>
      <form onSubmit={submit} className="form-grid">
        <label className="span-2">
          Movement type
          <select value={reason} onChange={(event) => setReason(event.target.value)}>
            {OPTIONS.map((option) => (
              <option key={option} value={option}>
                {REASONS[option].label}
              </option>
            ))}
          </select>
        </label>
        {reason === 'ADJUSTMENT' && (
          <div className="segmented span-2" role="radiogroup" aria-label="Direction">
            {[
              ['in', 'Add units'],
              ['out', 'Remove units'],
            ].map(([value, label]) => (
              <button
                type="button"
                key={value}
                role="radio"
                aria-checked={direction === value}
                className={direction === value ? 'selected' : ''}
                onClick={() => setDirection(value)}
              >
                {label}
              </button>
            ))}
          </div>
        )}
        <label>
          Units
          <input type="number" min="1" step="1" required value={amount} onChange={(event) => setAmount(event.target.value)} placeholder="0" />
        </label>
        <div className="preview" aria-live="polite">
          <span>On hand</span>
          <strong>
            {formatNumber(product.quantity)} <i>→</i> <em className={after < 0 ? 'negative' : ''}>{formatNumber(after)}</em>
          </strong>
          <small>{units ? `${signed(change)} units` : 'Enter a quantity'}</small>
        </div>
        <label className="span-2">
          Reference / note
          <input value={note} maxLength={255} onChange={(event) => setNote(event.target.value)} placeholder="e.g. PO-2041, invoice INV-88, cycle count" />
        </label>
        {after < 0 && (
          <div className="form-error span-2" role="alert">
            Only {formatNumber(product.quantity)} units are available.
          </div>
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
          <button className="primary" disabled={saving || invalid}>
            {saving ? 'Recording…' : 'Record movement'}
          </button>
        </div>
      </form>
    </Modal>
  );
}
