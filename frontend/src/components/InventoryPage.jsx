import { useMemo, useState } from 'react';
import { AlertTriangle, Check, CheckCircle2, ChevronDown, Download, Edit3, Filter, Package, Plus, Search, ShieldAlert, SlidersHorizontal, Trash2, Truck, Wrench } from 'lucide-react';

const CATEGORY_LABELS = {
  controller: 'Controller', sensor: 'Sensor', passive: 'Passive', power: 'Power', actuator: 'Actuator',
  wiring: 'Wiring', display: 'Display', enclosure: 'Enclosure', mechanical: 'Mechanical', other: 'Other',
};
const STATUS_LABELS = { verified: 'Verified', needs_testing: 'Needs testing', unverified: 'Unverified', quarantined: 'Quarantined' };
const number = new Intl.NumberFormat('en-IN', { maximumFractionDigits: 0 });

export default function InventoryPage({ inventory, onAdd, onEdit, onDelete, onVerify }) {
  const [search, setSearch] = useState('');
  const [category, setCategory] = useState('all');
  const [status, setStatus] = useState('all');
  const [viewMode, setViewMode] = useState('table');
  const [busyId, setBusyId] = useState(null);

  const filtered = useMemo(() => inventory.filter(item => {
    const term = search.trim().toLowerCase();
    const haystack = [item.name, item.component_type, item.source, item.notes, ...(item.tags || [])].join(' ').toLowerCase();
    return (!term || haystack.includes(term)) && (category === 'all' || item.category === category) && (status === 'all' || item.status === status);
  }), [inventory, search, category, status]);

  const units = inventory.reduce((sum, item) => sum + item.quantity, 0);
  const verified = inventory.filter(item => item.quantity > 0 && item.status === 'verified').reduce((sum, item) => sum + item.quantity, 0);
  const testing = inventory.filter(item => item.quantity > 0 && item.status === 'needs_testing').reduce((sum, item) => sum + item.quantity, 0);
  const quarantined = inventory.filter(item => item.status === 'quarantined').length;

  async function verify(item) {
    setBusyId(item.id);
    try { await onVerify(item); } finally { setBusyId(null); }
  }

  return <div className="page-stack inventory-page">
    <div className="page-intro-row">
      <div><div className="eyebrow">YOUR CIRCULAR MATERIALS LIBRARY</div><h1>Inventory, made useful.</h1><p>Know what you have, what is safe to reuse, and what still needs a bench test.</p></div>
      <button className="btn btn-forest" onClick={onAdd}><Plus size={17}/> Add component</button>
    </div>

    <div className="inventory-stat-row">
      <div className="inventory-stat"><div className="inventory-stat-icon"><Package size={18}/></div><div><span>Tracked stock units</span><strong>{number.format(units)}</strong><small>{inventory.length} component records</small></div></div>
      <div className="inventory-stat"><div className="inventory-stat-icon verified-stat"><CheckCircle2 size={18}/></div><div><span>Ready to reuse</span><strong>{number.format(verified)}</strong><small>Human-verified stock</small></div></div>
      <div className="inventory-stat"><div className="inventory-stat-icon testing-stat"><Wrench size={18}/></div><div><span>Needs testing</span><strong>{number.format(testing)}</strong><small>Not eligible for build logs yet</small></div></div>
      <div className="inventory-stat"><div className="inventory-stat-icon safety-stat"><ShieldAlert size={18}/></div><div><span>Quarantined records</span><strong>{number.format(quarantined)}</strong><small>Excluded from recommendations</small></div></div>
    </div>

    <section className="panel-card inventory-panel">
      <div className="inventory-toolbar">
        <div className="inventory-search"><Search size={17}/><input value={search} onChange={e => setSearch(e.target.value)} placeholder="Search components, tags, source…" aria-label="Search inventory"/>{search && <button onClick={() => setSearch('')} className="search-clear">Clear</button>}</div>
        <div className="inventory-filters"><a className="btn btn-outline-forest btn-sm export-button" href="/api/exports/inventory.csv" download><Download size={13}/> Export CSV</a><div className="filter-select-wrap"><Filter size={14}/><select aria-label="Filter by category" value={category} onChange={e => setCategory(e.target.value)}><option value="all">All categories</option>{Object.entries(CATEGORY_LABELS).map(([v, l]) => <option key={v} value={v}>{l}</option>)}</select><ChevronDown size={13}/></div><div className="filter-select-wrap"><SlidersHorizontal size={14}/><select aria-label="Filter by verification status" value={status} onChange={e => setStatus(e.target.value)}><option value="all">All states</option>{Object.entries(STATUS_LABELS).map(([v, l]) => <option key={v} value={v}>{l}</option>)}</select><ChevronDown size={13}/></div><div className="view-toggle"><button className={viewMode === 'table' ? 'active' : ''} onClick={() => setViewMode('table')} title="Table view">List</button><button className={viewMode === 'grid' ? 'active' : ''} onClick={() => setViewMode('grid')} title="Card view">Grid</button></div></div>
      </div>
      <div className="inventory-table-heading"><div><h3>Component stock</h3><p>{filtered.length} record{filtered.length === 1 ? '' : 's'} match your filters</p></div><span className="live-pill"><span/> LIVE INVENTORY</span></div>
      {filtered.length === 0 ? <div className="empty-inventory"><div className="empty-plan-art"><Search size={25}/></div><h3>No components found</h3><p>Try another search or clear your filters. New parts can be added manually.</p><button className="btn btn-outline-forest" onClick={() => { setSearch(''); setCategory('all'); setStatus('all'); }}>Clear filters</button></div> : viewMode === 'table' ? <div className="table-responsive inventory-table-wrap"><table className="table inventory-table align-middle mb-0"><thead><tr><th>Component</th><th>Category</th><th>Stock</th><th>Condition / source</th><th>Verification</th><th className="text-end">Actions</th></tr></thead><tbody>{filtered.map(item => <tr key={item.id} className={item.status === 'quarantined' ? 'quarantined-row' : ''}>
        <td><div className="component-cell"><div className={`component-thumb thumb-${item.category}`}>{item.status === 'quarantined' ? <ShieldAlert size={18}/> : <Package size={18}/>}</div><div className="component-cell-copy"><strong>{item.name}</strong><small>{item.component_type.replaceAll('_', ' ')}{item.voltage_v != null ? ` · ${item.voltage_v}V` : ''}</small>{item.tags?.length > 0 && <div className="tag-line">{item.tags.slice(0, 3).map(tag => <span key={tag}>{tag}</span>)}</div>}</div></div></td>
        <td><span className="category-label">{CATEGORY_LABELS[item.category] || item.category}</span></td>
        <td><span className={`stock-count ${item.quantity === 0 ? 'stock-empty' : ''}`}>{item.quantity}</span><small className="stock-unit">{item.quantity === 1 ? 'unit' : 'units'}</small></td>
        <td><div className="condition-cell"><span className={`condition-dot condition-${item.condition}`}/><span>{item.condition[0].toUpperCase() + item.condition.slice(1)}</span></div><small className="source-text">{item.source}</small>{item.mass_g != null && <small className="source-text">{item.mass_g} g each</small>}</td>
        <td><span className={`status-pill status-table pill-${item.status === 'verified' ? 'verified' : item.status === 'needs_testing' ? 'testing' : item.status === 'quarantined' ? 'quarantine' : 'unverified'}`}>{item.status === 'verified' && <Check size={12}/>} {STATUS_LABELS[item.status]}</span>{item.status === 'quarantined' && <small className="safety-excluded">Excluded from plans</small>}{item.status === 'needs_testing' && <button className="text-action table-verify" disabled={busyId === item.id} onClick={() => verify(item)}>{busyId === item.id ? 'Saving…' : 'Mark tested'}</button>}</td>
        <td><div className="row-actions"><button className="row-icon-action" onClick={() => onEdit(item)} title="Edit component" aria-label={`Edit ${item.name}`}><Edit3 size={15}/></button>{item.status !== 'verified' && item.status !== 'quarantined' && <button className="row-icon-action action-verify" disabled={busyId === item.id} onClick={() => verify(item)} title="Mark verified" aria-label={`Verify ${item.name}`}><CheckCircle2 size={15}/></button>}<button className="row-icon-action action-delete" onClick={() => onDelete(item)} title="Delete component" aria-label={`Delete ${item.name}`}><Trash2 size={15}/></button></div></td>
      </tr>)}</tbody></table></div> : <div className="inventory-grid">{filtered.map(item => <article className={`inventory-item-card ${item.status === 'quarantined' ? 'quarantine-card' : ''}`} key={item.id}><div className="inventory-item-card-top"><div className={`component-thumb thumb-${item.category}`}>{item.status === 'quarantined' ? <ShieldAlert size={18}/> : <Package size={18}/>}</div><span className={`status-pill pill-${item.status === 'verified' ? 'verified' : item.status === 'needs_testing' ? 'testing' : item.status === 'quarantined' ? 'quarantine' : 'unverified'}`}>{STATUS_LABELS[item.status]}</span></div><h3>{item.name}</h3><p>{CATEGORY_LABELS[item.category]} · {item.component_type.replaceAll('_', ' ')}</p><div className="item-card-metrics"><span><strong>{item.quantity}</strong> units</span><span>{item.mass_g != null ? `${item.mass_g} g each` : 'Mass unknown'}</span></div><div className="tag-line">{(item.tags || []).slice(0, 4).map(tag => <span key={tag}>{tag}</span>)}</div>{item.status === 'quarantined' && <div className="quarantine-warning"><AlertTriangle size={14}/>Do not use or disassemble</div>}<div className="item-card-actions"><button className="btn btn-light btn-sm" onClick={() => onEdit(item)}><Edit3 size={14}/> Edit</button>{item.status !== 'verified' && item.status !== 'quarantined' && <button className="btn btn-outline-forest btn-sm" onClick={() => verify(item)}><Check size={14}/> Verify</button>}<button className="btn btn-light btn-sm text-danger" onClick={() => onDelete(item)}><Trash2 size={14}/></button></div></article>)}</div>}
      <div className="inventory-footer"><div><Truck size={15}/><span>Source and condition travel with every component record.</span></div><span>Last refreshed just now</span></div>
    </section>
    <div className="safety-banner"><ShieldAlert size={18}/><div><strong>Safety gate stays on.</strong><span>Quarantined components never enter a generated bill of materials. Never open mains adapters, CRT displays, or battery packs; route hazardous e-waste to an approved handler.</span></div></div>
  </div>;
}
