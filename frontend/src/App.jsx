import { useCallback, useEffect, useMemo, useState } from 'react';
import { AlertCircle, ArrowRight, Boxes, CheckCircle2, ChevronDown, CircleHelp, Command, FlaskConical, History, LayoutDashboard, Leaf, LoaderCircle, MessageSquareText, Package, Plus, Recycle, Search, Settings2, ShieldCheck, Sparkles, X } from 'lucide-react';
import ComponentModal from './components/ComponentModal.jsx';
import DashboardPage from './components/DashboardPage.jsx';
import InventoryPage from './components/InventoryPage.jsx';
import BuildPlanner from './components/BuildPlanner.jsx';
import ImpactPage from './components/ImpactPage.jsx';
import AssistantPage from './components/AssistantPage.jsx';
import BuildHistoryPage from './components/BuildHistoryPage.jsx';

const API_BASE = (import.meta.env.VITE_API_URL || '/api').replace(/\/$/, '');
const NAV_ITEMS = [
  { id: 'dashboard', label: 'Overview', icon: LayoutDashboard, group: 'WORKSPACE' },
  { id: 'inventory', label: 'My inventory', icon: Boxes, countKey: 'component_skus' },
  { id: 'planner', label: 'Build planner', icon: FlaskConical, accent: true },
  { id: 'impact', label: 'Impact ledger', icon: Leaf, group: 'IMPACT' },
  { id: 'history', label: 'Build history', icon: History },
  { id: 'assistant', label: 'Circular assistant', icon: Sparkles, group: 'TOOLS' },
];
const PAGE_META = {
  dashboard: ['Overview', 'A living view of your circular workspace'],
  inventory: ['My inventory', 'Your salvaged materials, ready to be rediscovered'],
  planner: ['Build planner', 'Design around parts you already have'],
  impact: ['Impact ledger', 'Traceable outcomes, not just intentions'],
  history: ['Build history', 'Your prototypes and the parts that made them possible'],
  assistant: ['Circular assistant', 'A reuse-first copilot for your next idea'],
};

async function defaultFetch(path, options = {}) {
  const headers = new Headers(options.headers || {});
  const isForm = options.body instanceof FormData;
  if (options.body && !isForm && !headers.has('Content-Type')) headers.set('Content-Type', 'application/json');
  const response = await fetch(`${API_BASE}${path.startsWith('/') ? path : `/${path}`}`, { ...options, headers });
  if (response.status === 204) return null;
  const contentType = response.headers.get('content-type') || '';
  const data = contentType.includes('application/json') ? await response.json() : await response.text();
  if (!response.ok) {
    const detail = typeof data === 'object' ? (data.detail || data.message || JSON.stringify(data)) : data;
    throw new Error(detail || `Request failed (${response.status})`);
  }
  return data;
}

export default function App() {
  const [page, setPage] = useState('dashboard');
  const [dashboard, setDashboard] = useState(null);
  const [inventory, setInventory] = useState([]);
  const [templates, setTemplates] = useState([]);
  const [impact, setImpact] = useState(null);
  const [builds, setBuilds] = useState([]);
  const [aiStatus, setAiStatus] = useState({ configured: false });
  const [demoResetEnabled, setDemoResetEnabled] = useState(true);
  const [loading, setLoading] = useState(true);
  const [syncing, setSyncing] = useState(false);
  const [globalError, setGlobalError] = useState('');
  const [toast, setToast] = useState(null);
  const [modal, setModal] = useState({ open: false, item: null });
  const [plannerTemplate, setPlannerTemplate] = useState('');
  const [showQuickSearch, setShowQuickSearch] = useState(false);
  const [quickSearch, setQuickSearch] = useState('');

  const notify = useCallback((message, type = 'success') => {
    setToast({ message, type, nonce: Date.now() });
  }, []);

  useEffect(() => {
    if (!toast) return undefined;
    const timer = window.setTimeout(() => setToast(null), 4200);
    return () => window.clearTimeout(timer);
  }, [toast]);

  const refreshAll = useCallback(async (initial = false) => {
    if (initial) setLoading(true); else setSyncing(true);
    setGlobalError('');
    try {
      const [dashboardData, inventoryData, templateData, impactData, buildData, aiData, healthData] = await Promise.all([
        defaultFetch('/dashboard'), defaultFetch('/inventory'), defaultFetch('/templates'), defaultFetch('/impact/summary'), defaultFetch('/builds?limit=100'), defaultFetch('/ai/status'), defaultFetch('/health'),
      ]);
      setDashboard(dashboardData); setInventory(inventoryData); setTemplates(templateData); setImpact(impactData); setBuilds(buildData); setAiStatus(aiData); setDemoResetEnabled(Boolean(healthData.demo_reset_enabled));
    } catch (error) {
      setGlobalError(error.message || 'Could not connect to SCRAPSHIFT API.');
    } finally { setLoading(false); setSyncing(false); }
  }, []);

  useEffect(() => { refreshAll(true); }, [refreshAll]);

  const api = useCallback((path, options = {}) => defaultFetch(path, options), []);
  const currentTitle = PAGE_META[page]?.[0] || 'SCRAPSHIFT';
  const workspaceLabel = dashboard?.summary?.demo_only ? 'Demo workspace' : 'Maker workspace';

  const navigate = (next) => { setPage(next); setShowQuickSearch(false); };
  const openPlanner = (templateId) => { setPlannerTemplate(templateId || ''); setPage('planner'); setShowQuickSearch(false); };
  const openAdd = () => setModal({ open: true, item: null });
  const openEdit = (item) => setModal({ open: true, item });

  async function saveComponent(payload, id) {
    await api(id ? `/inventory/${id}` : '/inventory', { method: id ? 'PATCH' : 'POST', body: JSON.stringify(payload) });
    await refreshAll();
    notify(id ? 'Component updated.' : 'Component added to inventory.', 'success');
  }

  async function verifyComponent(item) {
    await api(`/inventory/${item.id}/verify`, { method: 'POST' });
    await refreshAll();
    notify(`${item.name} marked verified. Please keep a record of the bench test.`, 'success');
  }

  async function deleteComponent(item) {
    const ok = window.confirm(`Delete “${item.name}” from inventory? Historical build records will keep a name snapshot.`);
    if (!ok) return;
    try { await api(`/inventory/${item.id}`, { method: 'DELETE' }); await refreshAll(); notify('Component removed from inventory.', 'success'); }
    catch (error) { notify(error.message || 'Could not delete component.', 'error'); }
  }

  async function resetDemo() {
    const ok = window.confirm('Restore the seeded SCRAPSHIFT demo workspace? This removes all current inventory, build and impact records from this local database.');
    if (!ok) return;
    try { await api('/demo/reset', { method: 'POST' }); await refreshAll(); notify('Demo workspace restored.', 'success'); }
    catch (error) { notify(error.message || 'Could not reset the demo workspace.', 'error'); }
  }

  const quickMatches = useMemo(() => {
    const search = quickSearch.trim().toLowerCase();
    if (!search) return inventory.slice(0, 5);
    return inventory.filter(item => `${item.name} ${item.category} ${(item.tags || []).join(' ')}`.toLowerCase().includes(search)).slice(0, 7);
  }, [inventory, quickSearch]);

  if (loading) return <div className="app-loading"><div className="loading-brand"><div className="brand-mark"><Recycle size={23}/></div><span>SCRAPSHIFT</span></div><div className="loading-spinner"><LoaderCircle size={24}/></div><h2>Setting up your circular workspace</h2><p>Loading your inventory, project templates and impact ledger…</p><div className="loading-track"><span/></div></div>;

  return <div className="app-shell">
    <aside className="app-sidebar">
      <div className="brand-lockup"><div className="brand-mark"><Recycle size={22}/></div><div className="brand-wordmark"><strong>SCRAPSHIFT<span>®</span></strong><small>DESIGN CIRCULAR</small></div></div>
      <div className="workspace-switch"><div className="workspace-avatar">M</div><div className="workspace-name"><strong>{workspaceLabel}</strong><span><i/> Local-first workspace</span></div><ChevronDown size={15}/></div>
      <nav className="sidebar-nav" aria-label="Main navigation">{NAV_ITEMS.map((item, i) => <div key={item.id}>{item.group && <div className={`nav-group-label ${i !== 0 ? 'nav-group-spaced' : ''}`}>{item.group}</div>}<button className={`sidebar-nav-item ${page === item.id ? 'nav-active' : ''} ${item.accent ? 'nav-accent' : ''}`} onClick={() => item.id === 'planner' ? openPlanner() : navigate(item.id)}><item.icon size={18} strokeWidth={page === item.id ? 2.2 : 1.8}/><span>{item.label}</span>{item.id === 'inventory' && dashboard?.summary?.component_skus > 0 && <small className="nav-count">{dashboard.summary.component_skus}</small>}{item.id === 'planner' && <span className="nav-new-mark">NEW</span>}{page === item.id && <span className="nav-active-line"/>}</button></div>)}</nav>
      <div className="sidebar-bottom"><div className="sidebar-impact-widget"><div className="widget-leaf-mark"><Leaf size={17}/></div><div className="widget-label">MATERIAL REUSED</div><strong>{dashboard?.summary?.reused_mass_kg?.toFixed(3) || '0.000'} <small>kg</small></strong><div className="widget-sub">From completed builds*</div><button onClick={() => navigate('impact')}>View impact <ArrowRight size={13}/></button></div><div className="sidebar-help-row"><div className="help-bubble"><CircleHelp size={17}/></div><div><strong>Need a hand?</strong><button onClick={() => navigate('assistant')}>Ask circular assistant</button></div></div><div className="sidebar-footer"><span>SCRAPSHIFT v1.0.0</span>{demoResetEnabled && <button onClick={resetDemo} title="Restore seeded demo data">Reset demo</button>}</div></div>
    </aside>

    <main className="app-main"><header className="app-topbar"><div className="topbar-breadcrumb"><span>Workspace</span><span className="breadcrumb-divider">/</span><strong>{currentTitle}</strong>{syncing && <span className="sync-indicator"><LoaderCircle size={12}/> Syncing</span>}</div><div className="topbar-actions"><button className={`topbar-search-button ${showQuickSearch ? 'search-is-open' : ''}`} onClick={() => setShowQuickSearch(v => !v)}><Search size={16}/><span>Search components…</span><kbd>⌘ K</kbd></button><button className="topbar-icon-button" title="Circular assistant" onClick={() => navigate('assistant')}><Sparkles size={17}/></button><span className={`topbar-ai-status ${aiStatus.configured ? 'ai-connected' : ''}`}><span/>{aiStatus.configured ? 'AI connected' : 'Rules engine'}</span><div className="topbar-avatar" title="Maker workspace">M</div></div>{showQuickSearch && <div className="quick-search-popover"><div className="quick-search-field"><Search size={16}/><input autoFocus value={quickSearch} onChange={e => setQuickSearch(e.target.value)} placeholder="Search your salvaged components…"/><button onClick={() => { setQuickSearch(''); setShowQuickSearch(false); }}><X size={15}/></button></div><div className="quick-search-results"><div className="quick-search-label">{quickSearch ? 'MATCHING INVENTORY' : 'RECENT COMPONENTS'}</div>{quickMatches.length ? quickMatches.map(item => <button key={item.id} onClick={() => { navigate('inventory'); setShowQuickSearch(false); setQuickSearch(item.name); }}><span className="quick-search-item-icon"><Package size={15}/></span><span><strong>{item.name}</strong><small>{item.quantity} in stock · {item.status.replaceAll('_', ' ')}</small></span><ArrowRight size={14}/></button>) : <div className="quick-search-empty">No component matches found.</div>}<button className="quick-search-all" onClick={() => { navigate('inventory'); setShowQuickSearch(false); }}>Open full inventory <ArrowRight size={14}/></button></div></div>}</header>
      {globalError && <div className="api-error-banner"><AlertCircle size={17}/><div><strong>Couldn't load your workspace.</strong><span>{globalError}. Check that the FastAPI backend is running on port 8000.</span></div><button onClick={() => refreshAll(true)}><LoaderCircle size={14}/> Retry</button></div>}
      <div className="app-content">{page === 'dashboard' && <DashboardPage dashboard={dashboard} impact={impact} inventory={inventory} onNavigate={navigate} onAdd={openAdd} onPlan={openPlanner} onReset={resetDemo} loading={loading}/>}{page === 'inventory' && <InventoryPage inventory={inventory} onAdd={openAdd} onEdit={openEdit} onDelete={deleteComponent} onVerify={verifyComponent}/>}{page === 'planner' && <BuildPlanner key={plannerTemplate || 'default-planner'} templates={templates} inventory={inventory} api={api} refreshAll={refreshAll} notify={notify} onVerify={verifyComponent} initialTemplateId={plannerTemplate || 'soil-monitor'} />}{page === 'impact' && <ImpactPage impact={impact} onNavigate={navigate}/>}{page === 'assistant' && <AssistantPage api={api} aiConfigured={aiStatus.configured} onNavigate={navigate} onSelectTemplate={openPlanner} />}{page === 'history' && <BuildHistoryPage builds={builds} onNavigate={navigate}/>}
      </div>
      <footer className="app-footer"><span>© 2026 SCRAPSHIFT</span><span><i/> Local database · Your build logs stay in your workspace</span><button onClick={() => navigate('impact')}>Impact methodology <ArrowRight size={12}/></button></footer>
    </main>

    <ComponentModal open={modal.open} item={modal.item} onClose={() => setModal({ open: false, item: null })} onSave={saveComponent} api={api}/>
    {toast && <div className={`toast-notification toast-${toast.type}`} role="status"><span className="toast-icon">{toast.type === 'success' ? <CheckCircle2 size={18}/> : <AlertCircle size={18}/>}</span><span>{toast.message}</span><button onClick={() => setToast(null)} aria-label="Dismiss notification"><X size={15}/></button></div>}
  </div>;
}
