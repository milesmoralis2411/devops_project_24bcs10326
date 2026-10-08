import { formatCompactCurrency, formatCurrency, formatNumber } from '../lib/format.js';

function Kpi({ label, value, hint, icon, tone }) {
  return (
    <article className={`kpi tone-${tone}`}>
      <span className="kpi-icon" aria-hidden="true">
        {icon}
      </span>
      <div>
        <p>{label}</p>
        <strong>{value}</strong>
        <small>{hint}</small>
      </div>
    </article>
  );
}

export default function KpiCards({ stats }) {
  const needsAttention = stats.low_stock + stats.out_of_stock;
  return (
    <section className="kpis" aria-label="Inventory KPIs">
      <Kpi
        label="Products"
        value={formatNumber(stats.total_products)}
        hint={`${stats.categories.length} categories`}
        icon="▦"
        tone="teal"
      />
      <Kpi label="Units on hand" value={formatNumber(stats.total_units)} hint="Across all bin locations" icon="◫" tone="blue" />
      <Kpi
        label="Inventory value"
        value={formatCompactCurrency(stats.inventory_value)}
        hint={formatCurrency(stats.inventory_value)}
        icon="₹"
        tone="violet"
      />
      <Kpi
        label="Needs reorder"
        value={formatNumber(needsAttention)}
        hint={`${stats.out_of_stock} out of stock · ${stats.low_stock} low`}
        icon="!"
        tone={needsAttention ? 'amber' : 'teal'}
      />
    </section>
  );
}
