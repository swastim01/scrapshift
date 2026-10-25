import { useMemo } from 'react';
import { Area, AreaChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis } from 'recharts';
import { ArrowDownRight, ArrowRight, ArrowUpRight, Boxes, Check, CheckCircle2, ChevronRight, CircleHelp, Clock3, Leaf, Package, Plus, Recycle, ShieldCheck, Sparkles, Sprout, TrendingUp, Wrench } from 'lucide-react';

const INR = new Intl.NumberFormat('en-IN', { maximumFractionDigits: 0 });
const number = new Intl.NumberFormat('en-IN');

export default function DashboardPage({ dashboard, impact, inventory, onNavigate, onAdd, onPlan, onReset, loading }) {
  const summary = dashboard?.summary;
  const monthly = impact?.monthly || [];
  const categoryData = dashboard?.inventory_by_category || [];
  const maxUnits = Math.max(...categoryData.map(x => x.units), 1);
  const safeItems = inventory.filter(x => x.quantity > 0 && x.status === 'verified');
  const nextAction = useMemo(() => {
    const needing = inventory.filter(x => x.quantity > 0 && x.status === 'needs_testing');
    if (needing.length) return { type: 'test', title: `${needing.length} component ${needing.length === 1 ? 'needs' : 'records need'} a bench test`, sub: 'Verify known-good parts to unlock more build options.', action: 'Review inventory' };
    const available = (dashboard?.recommended_projects || []).find(p => p.readiness_pct > 0);
    if (available) return { type: 'build', title: `${available.name} is your next circular build`, sub: `${available.readiness_pct}% of required parts are already verified and available.`, action: 'Open planner' };
    return { type: 'add', title: 'Seed your inventory with salvaged parts', sub: 'The planner works best when it knows what is already in your parts box.', action: 'Add a component' };
  }, [inventory, dashboard]);

  if (!summary) return <div className="page-loading">Loading your circular workspace…</div>;

  return <div className="page-stack dashboard-page">
    <section className="dashboard-hero">
      <div className="hero-decor hero-decor-one"/><div className="hero-decor hero-decor-two"/>
      <div className="hero-left"><div className="hero-eyebrow"><span className="hero-pulse"/> THE CIRCULAR DESIGN WORKSPACE</div><h1>Make more.<br/><em>Buy less.</em></h1><p>Turn salvaged electronics into useful prototypes. Design around what you already own, then measure what you kept in use.</p><div className="hero-actions"><button className="btn btn-white" onClick={onPlan}><Sparkles size={16}/> Start a build plan <ArrowRight size={15}/></button><button className="hero-link-button" onClick={() => onNavigate('inventory')}>Explore inventory <ChevronRight size={15}/></button></div><div className="hero-footnote"><ShieldCheck size={15}/> Designed for safe, verified low-voltage reuse.</div></div>
      <div className="hero-right"><div className="orbit orbit-one"/><div className="orbit orbit-two"/><div className="hero-core"><Recycle size={45}/><span>REUSE<br/>BY DESIGN</span></div><div className="float-chip float-chip-one"><span className="float-chip-icon"><Package size={14}/></span><span><strong>{number.format(summary.tracked_units)}</strong><small>parts tracked</small></span></div><div className="float-chip float-chip-two"><span className="float-chip-icon leaf-float"><Leaf size={14}/></span><span><strong>{summary.reused_mass_kg.toFixed(3)} kg</strong><small>material reused*</small></span></div><div className="orbit-node node-one"><Sprout size={17}/></div><div className="orbit-node node-two"><Wrench size={16}/></div></div>
    </section>

    {summary.demo_build_count > 0 && <div className="demo-data-notice"><span className="demo-tag">DEMO DATA</span><span>One clearly labelled sample build is included so the impact ledger can be previewed. Your real completed builds are stored separately and marked in history.</span></div>}

    <div className="section-topline"><div><div className="eyebrow">YOUR WORKSPACE AT A GLANCE</div><h2>Impact starts with inventory.</h2></div><span className="last-updated"><span/> Live from your local database</span></div>
    <div className="metric-grid">
      <MetricCard label="Component records" value={number.format(summary.component_skus)} helper={`${number.format(summary.tracked_units)} total stock units`} icon={<Boxes size={19}/>} accent="forest" trend="Inventory"/>
      <MetricCard label="Ready to reuse" value={number.format(summary.verified_units)} helper={`${number.format(summary.needs_testing_units)} units need a test`} icon={<CheckCircle2 size={19}/>} accent="mint" trend="Verified only"/>
      <MetricCard label="Material reused" value={`${summary.reused_mass_kg.toFixed(3)} kg`} helper={`${number.format(summary.reused_component_count)} recorded units`} icon={<Recycle size={19}/>} accent="blue" trend="Completed builds"/>
      <MetricCard label="Purchase cost proxy" value={`₹${INR.format(summary.avoided_purchase_cost)}`} helper="Estimated replacement cost, not cash savings" icon={<TrendingUp size={19}/>} accent="amber" trend="Modelled"/>
    </div>

    <div className="dashboard-main-grid">
      <section className="panel-card impact-chart-card"><div className="card-heading-row"><div><div className="eyebrow">CIRCULARITY OVER TIME</div><h3>Reuse ledger</h3><p>Material weight logged after completed builds.</p></div><button className="btn btn-light btn-sm" onClick={() => onNavigate('impact')}>View impact <ArrowRight size={14}/></button></div>
        {monthly.length ? <><div className="chart-summary-line"><strong>{summary.reused_mass_kg.toFixed(3)} <small>kg</small></strong><span><Leaf size={14}/> Recorded reuse mass</span></div><div className="dashboard-chart"><ResponsiveContainer width="100%" height="100%"><AreaChart data={monthly} margin={{ top: 12, right: 8, left: -22, bottom: 0 }}><defs><linearGradient id="reuseFill" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor="#2d7b62" stopOpacity={0.22}/><stop offset="95%" stopColor="#2d7b62" stopOpacity={0.015}/></linearGradient></defs><CartesianGrid strokeDasharray="3 5" vertical={false} stroke="#e9eee9"/><XAxis dataKey="month" tickFormatter={v => { const d = new Date(`${v}-02T12:00:00`); return d.toLocaleDateString('en', { month: 'short' }); }} tickLine={false} axisLine={false} tick={{ fill: '#839088', fontSize: 11 }}/><Tooltip formatter={(value, name) => [`${Number(value).toFixed(1)} g`, 'Reuse mass']} labelFormatter={v => v}/><Area type="monotone" dataKey="mass_g" stroke="#2d7b62" fill="url(#reuseFill)" strokeWidth={2.5} activeDot={{ r: 4, strokeWidth: 0 }}/></AreaChart></ResponsiveContainer></div><div className="chart-legend"><span><i className="legend-line"/> Material reused (g)</span><span className="chart-caption">{monthly.some(m => m.demo_builds) ? 'Includes demo entries, labelled in the impact ledger' : 'Based on completed builds only'}</span></div></> : <div className="chart-empty"><div className="empty-plan-art"><Leaf size={24}/></div><strong>Your first reuse event starts the chart.</strong><span>Log a completed build after the physical prototype has been tested.</span><button className="btn btn-outline-forest btn-sm" onClick={onPlan}>Create a build plan</button></div>}
      </section>
      <section className="panel-card category-card"><div className="card-heading-row"><div><div className="eyebrow">INVENTORY MIX</div><h3>What's in your parts box?</h3><p>Stock units by component category.</p></div><button className="tiny-link" onClick={() => onNavigate('inventory')}>View all <ChevronRight size={14}/></button></div><div className="category-list">{categoryData.slice(0, 6).map(item => <div className="category-item" key={item.category}><div className="category-item-top"><span>{prettyCategory(item.category)}</span><strong>{item.units}</strong></div><div className="category-bar"><span style={{ width: `${Math.max(3, item.units / maxUnits * 100)}%` }}/></div><small>{item.sku_count} {item.sku_count === 1 ? 'component record' : 'component records'}</small></div>)}</div>{categoryData.length === 0 && <p className="muted-copy">Add your first salvaged component to see the stock mix.</p>}<button className="category-add-link" onClick={onAdd}><Plus size={15}/> Add a component <ArrowRight size={14}/></button></section>
    </div>

    <div className="dashboard-lower-grid">
      <section className="panel-card recommendations-card"><div className="card-heading-row"><div><div className="eyebrow">INVENTORY-AWARE IDEAS</div><h3>Build something circular.</h3><p>Starter projects ranked by the verified parts you already have.</p></div><button className="tiny-link" onClick={onPlan}>Open planner <ChevronRight size={14}/></button></div><div className="recommendation-list">{(dashboard.recommended_projects || []).slice(0, 3).map((project, index) => <button className="recommendation-item" key={project.id} onClick={() => onPlan(project.id)}><div className={`recommendation-icon rec-${project.color}`}><ProjectIcon id={project.icon}/></div><div className="recommendation-copy"><div className="recommendation-title-line"><strong>{project.name}</strong>{project.can_build_now && <span className="mini-ready-badge"><Check size={11}/> Ready</span>}</div><p>{project.summary}</p><div className="recommendation-meta"><span>{project.difficulty}</span><span>·</span><span>{project.duration}</span></div></div><div className="recommendation-score"><strong>{project.readiness_pct}%</strong><span>parts ready</span><div className="recommendation-progress"><span style={{ width: `${project.readiness_pct}%` }}/></div></div><ChevronRight className="recommendation-chevron" size={17}/></button>)}</div></section>
      <section className="next-action-card"><div className="next-action-top"><div className="next-action-orbit"><Sparkles size={20}/></div><span className="next-action-label">RECOMMENDED NEXT STEP</span></div><div className="next-action-body"><span className={`next-action-kicker kicker-${nextAction.type}`}>{nextAction.type === 'test' ? 'QUALITY GATE' : nextAction.type === 'build' ? 'DESIGN OPPORTUNITY' : 'GET STARTED'}</span><h3>{nextAction.title}</h3><p>{nextAction.sub}</p></div><button className="btn btn-white w-100" onClick={() => nextAction.type === 'add' ? onAdd() : onNavigate(nextAction.type === 'test' ? 'inventory' : 'planner')}>{nextAction.action} <ArrowRight size={15}/></button><div className="next-action-foot"><ShieldCheck size={14}/> Verification comes before reuse.</div></section>
    </div>

    <div className="dashboard-bottom-note"><CircleHelp size={15}/><span><strong>Impact integrity:</strong> material counts come from completed build logs. Carbon estimates appear only when factor coverage is complete; demo factors are illustrative and should be replaced with cited sources.</span><button onClick={() => onNavigate('impact')}>Read methodology <ChevronRight size={14}/></button></div>
  </div>;
}

function MetricCard({ label, value, helper, icon, accent, trend }) {
  return <article className="metric-card"><div className={`metric-icon metric-${accent}`}>{icon}</div><div className="metric-top-line"><span>{label}</span><span className="metric-chip">{trend}</span></div><strong className="metric-value">{value}</strong><span className="metric-helper">{helper}</span></article>;
}
function prettyCategory(cat) { return cat.charAt(0).toUpperCase() + cat.slice(1).replaceAll('_', ' '); }
function ProjectIcon({ id }) { if (id === 'sprout') return <Sprout size={19}/>; if (id === 'cloud-sun') return <Sparkles size={18}/>; if (id === 'droplets') return <Leaf size={18}/>; if (id === 'lamp-desk') return <Wrench size={18}/>; return <ShieldCheck size={18}/>; }
