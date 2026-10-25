import { useEffect, useMemo, useState } from 'react';
import { AlertCircle, Check, CheckCircle2, ChevronRight, CircleHelp, Clock3, FlaskConical, Hammer, Leaf, LoaderCircle, Plus, RefreshCw, ShieldCheck, ShoppingBag, Sparkles, TestTube2, Wrench } from 'lucide-react';

const INR = new Intl.NumberFormat('en-IN', { maximumFractionDigits: 0 });

function statusLabel(status) {
  if (status === 'ready') return 'Ready to reuse';
  if (status === 'needs_testing') return 'Test first';
  return 'Missing';
}

function RequirementRow({ part, onVerify }) {
  const allocations = part.allocations || [];
  return <div className={`requirement-row ${part.status === 'missing' ? 'requirement-missing' : ''}`}>
    <div className={`requirement-status status-${part.status}`}>
      {part.status === 'ready' ? <Check size={16}/> : part.status === 'needs_testing' ? <TestTube2 size={16}/> : <Plus size={16}/>}
    </div>
    <div className="requirement-main">
      <div className="requirement-title-row"><strong>{part.label}</strong>{part.required && <span className="required-label">REQUIRED</span>}</div>
      {allocations.length > 0 ? <div className="allocation-list">{allocations.map((allocation, i) => <div className="allocation-chip" key={`${allocation.component_id}-${i}`}>
        <span className={`tiny-status-dot dot-${allocation.status}`}/><span>{allocation.name}</span>
        {allocation.quantity > 1 && <span className="qty-chip">×{allocation.quantity}</span>}
        {allocation.substitute && <span className="substitute-chip">Substitute</span>}
        {allocation.status === 'needs_testing' && <button className="text-action" onClick={() => onVerify(allocation.component_id)}>Mark tested</button>}
      </div>)}</div> : <p className="requirement-help">No suitable stock item found. Add one to your inventory or try a different project.</p>}
      {part.missing_quantity > 0 && <p className="missing-inline">Need {part.missing_quantity} more · {part.suggestion}</p>}
      {part.substitute && <p className="soft-warning">A category-compatible substitute was found. Confirm its electrical and mechanical compatibility before use.</p>}
    </div>
    <span className={`status-pill ${part.status === 'ready' ? 'pill-verified' : part.status === 'needs_testing' ? 'pill-testing' : 'pill-missing'}`}>{statusLabel(part.status)}</span>
  </div>;
}

export default function BuildPlanner({ templates, inventory, api, refreshAll, notify, onVerify, initialTemplateId = 'soil-monitor' }) {
  const [templateId, setTemplateId] = useState(initialTemplateId);
  const [goal, setGoal] = useState('');
  const [projectName, setProjectName] = useState('');
  const [plan, setPlan] = useState(null);
  const [planning, setPlanning] = useState(false);
  const [completing, setCompleting] = useState(false);
  const [partsPurchased, setPartsPurchased] = useState(0);
  const [showCompleteForm, setShowCompleteForm] = useState(false);
  const [notes, setNotes] = useState('');
  const [error, setError] = useState('');
  const selectedTemplate = templates.find(t => t.id === templateId);

  useEffect(() => {
    if (!plan && templates.length) {
      generate(templates.find(t => t.id === templateId)?.id || templates[0].id);
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [templates.length]);

  const allAllocations = useMemo(() => {
    const map = new Map();
    (plan?.ready_to_reuse || []).forEach(item => {
      map.set(item.component_id, (map.get(item.component_id) || 0) + item.quantity);
    });
    return [...map.entries()].map(([component_id, quantity]) => ({ component_id, quantity }));
  }, [plan]);

  async function generate(forceTemplate) {
    setPlanning(true); setError(''); setShowCompleteForm(false);
    try {
      const body = {
        template_id: forceTemplate === 'auto' ? null : (forceTemplate || templateId || null),
        goal: goal.trim() || null,
        project_name: projectName.trim() || null,
      };
      const next = await api('/plans', { method: 'POST', body: JSON.stringify(body) });
      setPlan(next);
      if (next.template_id) setTemplateId(next.template_id);
      if (!projectName.trim()) setProjectName(next.project_name);
    } catch (e) { setError(e.message || 'Could not generate a plan.'); }
    finally { setPlanning(false); }
  }

  async function handleVerify(id) {
    try {
      await onVerify(id);
      await generate(templateId);
    } catch (e) { setError(e.message || 'Could not update verification status.'); }
  }

  async function logBuild() {
    if (!plan || allAllocations.length === 0) return;
    setCompleting(true); setError('');
    try {
      const response = await api('/builds', {
        method: 'POST',
        body: JSON.stringify({
          project_name: (projectName || plan.project_name).trim(),
          template_id: plan.template_id,
          parts_reused: allAllocations,
          parts_purchased: Number(partsPurchased) || 0,
          notes: notes.trim(),
          is_demo: false,
        }),
      });
      notify(`Build logged. ${response.reused_mass_g.toFixed(1)} g of components recorded as reused.`, 'success');
      setShowCompleteForm(false); setNotes(''); setPartsPurchased(0);
      await refreshAll();
      await generate(plan.template_id);
    } catch (e) { setError(e.message || 'Could not log build.'); }
    finally { setCompleting(false); }
  }

  const projects = templates.filter(t => t.id !== '');
  if (!templates.length) return <div className="page-loading"><LoaderCircle className="spin"/> Loading build templates…</div>;

  return <div className="page-stack planner-page">
    <div className="page-intro-row">
      <div><div className="eyebrow">CIRCULAR DESIGN STUDIO</div><h1>Build with what you have.</h1><p>Start with a project goal. SCRAPSHIFT assembles a reuse-first bill of materials from your verified inventory.</p></div>
      <div className="safety-note"><ShieldCheck size={17}/><span>Low-voltage prototypes only. Always validate ratings, pinouts and insulation.</span></div>
    </div>

    <div className="planner-layout">
      <aside className="planner-left panel-card">
        <div className="section-heading"><div className="section-icon violet-icon"><Sparkles size={18}/></div><div><h3>New build plan</h3><p>Tell us what you're making.</p></div></div>
        <label className="form-label">Pick a starter blueprint</label>
        <div className="template-picker">
          {projects.map((template) => <button type="button" onClick={() => { setTemplateId(template.id); setGoal(''); }} className={`template-option ${templateId === template.id ? 'template-option-active' : ''}`} key={template.id}>
            <span className={`template-mark mark-${template.color}`}><TemplateIcon id={template.icon}/></span><span className="template-option-copy"><strong>{template.name}</strong><small>{template.difficulty} · {template.duration}</small></span>{templateId === template.id && <span className="template-selected"><Check size={14}/></span>}
          </button>)}
        </div>
        <div className="form-divider"><span>OR DESCRIBE YOUR IDEA</span></div>
        <label className="form-label" htmlFor="project-goal">What would you like to make?</label>
        <textarea id="project-goal" className="form-control goal-textarea" rows="3" maxLength="1000" placeholder="e.g. A room monitor using the sensors in my old electronics kit…" value={goal} onChange={e => setGoal(e.target.value)}/>
        <p className="field-hint">Auto-match uses a transparent local rules engine. Review the suggested template before building.</p>
        <label className="form-label mt-3" htmlFor="project-name">Project name <span className="muted-inline">Optional</span></label>
        <input id="project-name" className="form-control" maxLength="140" placeholder="e.g. Hostel plant buddy" value={projectName} onChange={e => setProjectName(e.target.value)}/>
        <button type="button" className="btn btn-forest w-100 mt-4" onClick={() => generate(goal.trim() ? 'auto' : templateId)} disabled={planning}>
          {planning ? <LoaderCircle className="spin" size={16}/> : <Sparkles size={16}/>} {planning ? 'Designing reuse-first BOM…' : 'Generate circular design'}
        </button>
        <div className="planner-note"><CircleHelp size={15}/><span>AI can suggest, but never certifies component compatibility. The compatibility match is rules-based and inventory-driven.</span></div>
      </aside>

      <main className="planner-right">
        {!plan ? <div className="empty-plan panel-card"><div className="empty-plan-art"><FlaskConical size={32}/></div><h3>Your next build starts here</h3><p>Choose a blueprint and generate a bill of materials matched to your inventory.</p></div> : <>
          <div className="plan-hero panel-card">
            <div className="plan-hero-top"><span className="micro-label"><Sparkles size={13}/> REUSE-FIRST BLUEPRINT</span><span className={`readiness-pill ${plan.can_build_now ? 'readiness-good' : 'readiness-warn'}`}>{plan.can_build_now ? <CheckCircle2 size={14}/> : <AlertCircle size={14}/>} {plan.can_build_now ? 'Build-ready' : 'Needs a few checks'}</span></div>
            <h2>{plan.project_name || selectedTemplate?.name}</h2><p className="plan-summary">{plan.summary}</p>
            <div className="plan-meta"><span><Clock3 size={14}/>{plan.duration}</span><span><Wrench size={14}/>{plan.difficulty}</span><span><BoxesIcon/>{plan.requirements.length} BOM line items</span></div>
            <div className="readiness-block"><div className="readiness-label-row"><span>Required parts ready to use</span><strong>{plan.required_readiness_pct}%</strong></div><div className="progress custom-progress"><div className="progress-bar" style={{ width: `${plan.required_readiness_pct}%` }}/></div><div className="readiness-foot"><span>{plan.required_items_ready} of {plan.required_items_total} required items verified and available</span><span>{plan.inventory_coverage_pct}% found in inventory incl. items needing tests</span></div></div>
          </div>

          <div className="plan-impact-row">
            <div className="mini-impact-card"><div className="mini-impact-icon mint-icon"><Leaf size={17}/></div><div><span>Available mass to reuse</span><strong>{plan.estimated_reuse_mass_g} <small>g</small></strong><em>verified matches only</em></div></div>
            <div className="mini-impact-card"><div className="mini-impact-icon blue-icon"><ShoppingBag size={17}/></div><div><span>Replacement cost proxy</span><strong>{plan.estimated_avoided_purchase_cost == null ? '—' : `₹${INR.format(plan.estimated_avoided_purchase_cost)}`}</strong><em>potential purchases avoided</em></div></div>
            <div className="mini-impact-card"><div className="mini-impact-icon amber-icon"><TestTube2 size={17}/></div><div><span>Needs bench testing</span><strong>{plan.parts_needing_testing.length}</strong><em>before the build</em></div></div>
          </div>

          <section className="panel-card bom-card">
            <div className="bom-heading"><div><div className="eyebrow">DESIGN OUTPUT</div><h3>Reuse-first bill of materials</h3><p>Existing parts are allocated once so the same stock is not promised to multiple BOM lines.</p></div><button className="btn btn-outline-forest btn-sm" onClick={() => generate(plan.template_id)} disabled={planning}><RefreshCw size={14}/> Refresh matches</button></div>
            <div className="bom-summary-strip"><span><span className="legend-dot dot-green"/> Verified matches</span><span><span className="legend-dot dot-amber"/> Needs testing</span><span><span className="legend-dot dot-gray"/> Missing / add</span></div>
            <div className="requirement-list">{plan.requirements.map(part => <RequirementRow key={part.key} part={part} onVerify={handleVerify}/>)}</div>
          </section>

          <section className="panel-card build-steps-card">
            <div className="section-heading"><div className="section-icon mint-icon"><Hammer size={18}/></div><div><h3>Build & verification checklist</h3><p>Use these checks before recording environmental impact.</p></div></div>
            <div className="build-steps-list">{plan.build_steps.map((step, i) => <div className="build-step" key={step}><span>{String(i + 1).padStart(2, '0')}</span><p>{step}</p></div>)}</div>
          </section>

          <div className="complete-build-panel">
            <div className="complete-build-copy"><div className="complete-build-icon"><CheckCircle2 size={21}/></div><div><h3>Built and tested this prototype?</h3><p>Record only the parts actually reused. This updates stock and adds a traceable entry to your impact ledger.</p></div></div>
            {!showCompleteForm ? <button className="btn btn-forest" onClick={() => setShowCompleteForm(true)} disabled={allAllocations.length === 0}><Check size={16}/> Log completed build</button> : <div className="complete-build-form">
              <div className="row g-3"><div className="col-md-4"><label className="form-label">New parts purchased</label><input className="form-control" type="number" min="0" max="1000" value={partsPurchased} onChange={e => setPartsPurchased(e.target.value)}/></div><div className="col-md-8"><label className="form-label">Build notes (optional)</label><input className="form-control" maxLength="2000" value={notes} onChange={e => setNotes(e.target.value)} placeholder="What worked? What needs repair?"/></div></div>
              <div className="build-submit-warning"><AlertCircle size={15}/><span>Only verified parts shown in the plan will be deducted from stock. Confirm that the prototype was physically built and tested.</span></div>
              <div className="d-flex flex-wrap gap-2 justify-content-end"><button className="btn btn-light" onClick={() => setShowCompleteForm(false)}>Cancel</button><button className="btn btn-forest" disabled={completing} onClick={logBuild}>{completing ? <LoaderCircle className="spin" size={16}/> : <CheckCircle2 size={16}/>} Confirm completed build</button></div>
            </div>}
          </div>
          {error && <div className="alert alert-danger small mb-0">{error}</div>}
          <div className="impact-disclaimer"><AlertCircle size={15}/><span>{plan.impact_estimate_note}</span></div>
        </>}
      </main>
    </div>
  </div>;
}

function TemplateIcon({ id }) {
  const className = 'template-line-icon';
  switch (id) {
    case 'sprout': return <Leaf className={className} size={18}/>;
    case 'cloud-sun': return <Sparkles className={className} size={18}/>;
    case 'droplets': return <FlaskConical className={className} size={18}/>;
    case 'lamp-desk': return <Wrench className={className} size={18}/>;
    default: return <ShieldCheck className={className} size={18}/>;
  }
}
function BoxesIcon() { return <Wrench size={14}/>; }
