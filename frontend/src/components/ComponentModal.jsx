import { useEffect, useRef, useState } from 'react';
import { AlertTriangle, Camera, Check, LoaderCircle, Save, X } from 'lucide-react';

const CATEGORIES = [
  ['controller', 'Controller'], ['sensor', 'Sensor'], ['passive', 'Passive component'],
  ['power', 'Power'], ['actuator', 'Actuator'], ['wiring', 'Wiring'], ['display', 'Display / indicator'],
  ['enclosure', 'Enclosure'], ['mechanical', 'Mechanical'], ['other', 'Other'],
];
const STATUSES = [['verified', 'Verified'], ['needs_testing', 'Needs testing'], ['unverified', 'Unverified'], ['quarantined', 'Quarantined']];
const CONDITIONS = [['excellent', 'Excellent'], ['good', 'Good'], ['fair', 'Fair'], ['unknown', 'Unknown']];

const emptyForm = {
  name: '', category: 'other', component_type: 'general', quantity: '1', status: 'unverified', condition: 'unknown',
  source: 'Student parts box', mass_g: '', estimated_new_cost: '', embodied_carbon_kg: '', factor_source: '',
  voltage_v: '', interface: '', tags: '', notes: '',
};

export default function ComponentModal({ open, item, onClose, onSave, api }) {
  const [form, setForm] = useState(emptyForm);
  const [saving, setSaving] = useState(false);
  const [scanning, setScanning] = useState(false);
  const [image, setImage] = useState(null);
  const [scanNotice, setScanNotice] = useState('');
  const [error, setError] = useState('');
  const imageInput = useRef(null);

  useEffect(() => {
    if (!open) return;
    if (item) {
      setForm({
        ...emptyForm, ...item,
        quantity: String(item.quantity ?? 0), mass_g: item.mass_g ?? '', estimated_new_cost: item.estimated_new_cost ?? '',
        embodied_carbon_kg: item.embodied_carbon_kg ?? '', voltage_v: item.voltage_v ?? '',
        tags: (item.tags || []).join(', '), factor_source: item.factor_source || '',
      });
    } else {
      setForm(emptyForm);
    }
    setImage(null); setError(''); setScanNotice(''); setSaving(false); setScanning(false);
  }, [open, item]);

  if (!open) return null;

  const change = (key, value) => setForm(current => ({ ...current, [key]: value }));

  const handleScan = async () => {
    if (!image) { setError('Choose an image first.'); return; }
    setScanning(true); setError(''); setScanNotice('');
    try {
      const body = new FormData(); body.append('file', image);
      const result = await api('/ai/scan', { method: 'POST', body });
      setForm(current => ({
        ...current,
        name: result.name || current.name,
        category: CATEGORIES.some(([v]) => v === result.category) ? result.category : current.category,
        component_type: result.component_type || current.component_type,
        voltage_v: result.likely_voltage_v ?? current.voltage_v,
        interface: result.interface || current.interface,
        tags: Array.isArray(result.tags) ? result.tags.join(', ') : current.tags,
        notes: [current.notes, result.notes, result.safety_flags?.length ? `AI safety flags: ${result.safety_flags.join(', ')}` : ''].filter(Boolean).join('\n'),
        status: 'unverified', condition: 'unknown',
      }));
      setScanNotice(`AI suggestion (${result.confidence || 'unknown'} confidence). Please verify the component identity, ratings and pinout before use.`);
    } catch (e) {
      setError(e.message || 'Image scan failed. You can add the component manually.');
    } finally { setScanning(false); }
  };

  const handleSubmit = async (event) => {
    event.preventDefault(); setSaving(true); setError('');
    const numeric = (value) => value === '' || value === null || value === undefined ? null : Number(value);
    const payload = {
      name: form.name.trim(), category: form.category, component_type: form.component_type.trim() || 'general',
      quantity: Number(form.quantity), status: form.status, condition: form.condition, source: form.source.trim() || 'Unknown source',
      mass_g: numeric(form.mass_g), estimated_new_cost: numeric(form.estimated_new_cost),
      embodied_carbon_kg: numeric(form.embodied_carbon_kg), factor_source: form.factor_source.trim() || null,
      voltage_v: numeric(form.voltage_v), interface: form.interface.trim() || null,
      tags: form.tags.split(',').map(t => t.trim().toLowerCase()).filter(Boolean), notes: form.notes.trim(),
    };
    try { await onSave(payload, item?.id); onClose(); }
    catch (e) { setError(e.message || 'Could not save component.'); }
    finally { setSaving(false); }
  };

  return <div className="modal-backdrop-custom" role="presentation" onMouseDown={e => { if (e.target === e.currentTarget) onClose(); }}>
    <section className="component-modal" role="dialog" aria-modal="true" aria-labelledby="component-modal-title">
      <div className="modal-heading">
        <div><div className="eyebrow">INVENTORY WORKSPACE</div><h2 id="component-modal-title">{item ? 'Edit component' : 'Add a component'}</h2><p>Record what you have. Unknown specifications can stay blank.</p></div>
        <button className="icon-button" onClick={onClose} aria-label="Close modal"><X size={18}/></button>
      </div>
      <form onSubmit={handleSubmit} className="component-form">
        <div className="scan-strip">
          <div className="scan-icon"><Camera size={19}/></div>
          <div className="scan-copy"><strong>Identify from a photo <span className="optional-tag">OPTIONAL AI</span></strong><span>Image recognition suggests fields; it never verifies electrical ratings.</span>
            {image && <small className="selected-file">{image.name}</small>}
          </div>
          <input ref={imageInput} type="file" accept="image/png,image/jpeg,image/webp,image/gif" hidden onChange={e => setImage(e.target.files?.[0] || null)}/>
          <button type="button" className="btn btn-outline-forest btn-sm" onClick={() => imageInput.current?.click()}>Choose photo</button>
          {image && <button type="button" className="btn btn-forest btn-sm" onClick={handleScan} disabled={scanning}>{scanning ? <LoaderCircle className="spin" size={14}/> : <Camera size={14}/>} Scan</button>}
        </div>
        {scanNotice && <div className="inline-notice"><AlertTriangle size={15}/><span>{scanNotice}</span></div>}
        {error && <div className="alert alert-danger py-2 small">{error}</div>}
        <div className="form-section-label">Identity & inventory</div>
        <div className="row g-3">
          <div className="col-md-7"><label className="form-label">Component name *</label><input required minLength="2" maxLength="120" className="form-control" value={form.name} onChange={e => change('name', e.target.value)} placeholder="e.g. Capacitive soil moisture sensor"/></div>
          <div className="col-md-5"><label className="form-label">Category *</label><select className="form-select" value={form.category} onChange={e => change('category', e.target.value)}>{CATEGORIES.map(([v, label]) => <option value={v} key={v}>{label}</option>)}</select></div>
          <div className="col-md-4"><label className="form-label">Quantity *</label><input required type="number" min="0" max="100000" className="form-control" value={form.quantity} onChange={e => change('quantity', e.target.value)}/></div>
          <div className="col-md-4"><label className="form-label">Verification state</label><select className="form-select" value={form.status} onChange={e => change('status', e.target.value)}>{STATUSES.map(([v, label]) => <option key={v} value={v}>{label}</option>)}</select></div>
          <div className="col-md-4"><label className="form-label">Condition</label><select className="form-select" value={form.condition} onChange={e => change('condition', e.target.value)}>{CONDITIONS.map(([v, label]) => <option key={v} value={v}>{label}</option>)}</select></div>
          <div className="col-md-6"><label className="form-label">Component type</label><input className="form-control" value={form.component_type} onChange={e => change('component_type', e.target.value)} placeholder="e.g. soil_moisture"/></div>
          <div className="col-md-6"><label className="form-label">Source / origin</label><input className="form-control" value={form.source} onChange={e => change('source', e.target.value)} placeholder="e.g. broken plant monitor"/></div>
        </div>
        <div className="form-section-label mt-4">Specifications & impact factors <span className="muted-inline">All optional unless known</span></div>
        <div className="row g-3">
          <div className="col-md-4"><label className="form-label">Mass per unit (g)</label><input type="number" min="0" step="0.01" className="form-control" value={form.mass_g} onChange={e => change('mass_g', e.target.value)} placeholder="e.g. 12"/></div>
          <div className="col-md-4"><label className="form-label">Replacement cost (₹)</label><input type="number" min="0" step="0.01" className="form-control" value={form.estimated_new_cost} onChange={e => change('estimated_new_cost', e.target.value)} placeholder="e.g. 180"/></div>
          <div className="col-md-4"><label className="form-label">Embodied carbon (kg CO₂e)</label><input type="number" min="0" step="0.0001" className="form-control" value={form.embodied_carbon_kg} onChange={e => change('embodied_carbon_kg', e.target.value)} placeholder="Needs source"/></div>
          <div className="col-md-4"><label className="form-label">Voltage (V)</label><input type="number" min="0" step="0.1" className="form-control" value={form.voltage_v} onChange={e => change('voltage_v', e.target.value)} placeholder="e.g. 3.3"/></div>
          <div className="col-md-4"><label className="form-label">Interface / pinout</label><input className="form-control" value={form.interface} onChange={e => change('interface', e.target.value)} placeholder="e.g. I2C, Analog"/></div>
          <div className="col-md-4"><label className="form-label">Impact factor source</label><input className="form-control" value={form.factor_source} onChange={e => change('factor_source', e.target.value)} placeholder="URL / study / assumption"/></div>
          <div className="col-12"><label className="form-label">Search tags <span className="muted-inline">Comma separated</span></label><input className="form-control" value={form.tags} onChange={e => change('tags', e.target.value)} placeholder="arduino, sensor, 3.3v"/></div>
          <div className="col-12"><label className="form-label">Notes, test results & safety checks</label><textarea rows="3" maxLength="2000" className="form-control" value={form.notes} onChange={e => change('notes', e.target.value)} placeholder="What is known? What still needs testing?"/></div>
        </div>
        <div className="modal-footer-custom"><span className="form-footnote"><AlertTriangle size={14}/> Never mark a part verified from an image alone.</span><div className="d-flex gap-2"><button type="button" className="btn btn-light" onClick={onClose}>Cancel</button><button type="submit" className="btn btn-forest" disabled={saving}>{saving ? <LoaderCircle className="spin" size={16}/> : <Save size={16}/>} {item ? 'Save changes' : 'Add to inventory'}</button></div></div>
      </form>
    </section>
  </div>;
}
