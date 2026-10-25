import { useState } from 'react';
import { ArrowRight, Bot, CheckCircle2, CircleHelp, Leaf, LoaderCircle, MessageSquareText, Send, ShieldCheck, Sparkles, WandSparkles } from 'lucide-react';

const STARTERS = [
  'What can I build with my current parts?',
  'How do I reuse the sensors in my old electronics kit?',
  'What should I test before reusing salvaged components?',
];

export default function AssistantPage({ api, aiConfigured, onNavigate, onSelectTemplate }) {
  const [message, setMessage] = useState('');
  const [response, setResponse] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [history, setHistory] = useState([]);

  async function ask(question) {
    const clean = question.trim(); if (!clean) return;
    setLoading(true); setError(''); setResponse(null); setMessage(clean);
    try {
      const result = await api('/assistant', { method: 'POST', body: JSON.stringify({ message: clean }) });
      setResponse(result); setHistory(items => [{ question: clean, result }, ...items].slice(0, 4));
    } catch (e) { setError(e.message || 'Assistant request failed.'); }
    finally { setLoading(false); }
  }

  return <div className="page-stack assistant-page">
    <div className="page-intro-row"><div><div className="eyebrow">YOUR CIRCULAR HARDWARE COPILOT</div><h1>Ask before you buy.</h1><p>Explore reuse ideas, surface likely matches in your inventory, and get cautious next steps for testing parts.</p></div><span className={`ai-mode-pill ${aiConfigured ? 'ai-on' : 'ai-local'}`}><span/>{aiConfigured ? 'Optional AI connected' : 'Local rules mode'}</span></div>
    <div className="assistant-layout">
      <section className="assistant-main panel-card"><div className="assistant-welcome"><div className="assistant-bot-orb"><Bot size={24}/><span className="bot-orb-spark"><Sparkles size={12}/></span></div><div><div className="eyebrow">SCRAPSHIFT ASSISTANT</div><h2>Let's make something from the parts you have.</h2><p>Ask about a build goal, a component, or how to make a design more circular.</p></div></div>
        <div className="assistant-starters"><span className="form-label">TRY ONE OF THESE</span>{STARTERS.map(s => <button key={s} onClick={() => ask(s)} disabled={loading}><span><MessageSquareText size={15}/>{s}</span><ArrowRight size={14}/></button>)}</div>
        <form className="assistant-input-form" onSubmit={e => { e.preventDefault(); ask(message); }}><textarea rows="3" maxLength="1500" className="form-control" placeholder="Describe your project idea or ask what you can reuse…" value={message} onChange={e => setMessage(e.target.value)}/><div className="assistant-submit-row"><span><ShieldCheck size={14}/> Uses your inventory context · verify all technical advice</span><button className="btn btn-forest" type="submit" disabled={loading || !message.trim()}>{loading ? <LoaderCircle className="spin" size={16}/> : <Send size={15}/>} Ask assistant</button></div></form>
        {error && <div className="alert alert-warning small mt-3">{error}</div>}
        {loading && <div className="assistant-loading"><LoaderCircle className="spin" size={19}/><span>Checking your inventory and matching project ideas…</span></div>}
        {response && <div className="assistant-response"><div className="assistant-response-heading"><div className="response-avatar"><Bot size={17}/></div><div><strong>SCRAPSHIFT recommendation</strong><small>{response.mode === 'ai' ? 'AI-assisted · technical checks required' : 'Local rules engine · based on current inventory'}</small></div><span className="response-check"><CheckCircle2 size={15}/> Ready</span></div><div className="assistant-answer">{response.answer.split('\n\n').map((paragraph, i) => <p key={i}>{paragraph.replaceAll('**', '')}</p>)}</div>{response.suggested_template_id && <button className="btn btn-outline-forest btn-sm" onClick={() => { onSelectTemplate(response.suggested_template_id); onNavigate('planner'); }}>Open this project in planner <ArrowRight size={14}/></button>}</div>}
      </section>
      <aside className="assistant-side"><div className="assistant-principle-card"><div className="principle-card-icon"><Leaf size={19}/></div><div className="eyebrow">CIRCULAR DESIGN RULE</div><h3>Inventory before ideation.</h3><p>The copilot starts with your available, verified parts—then surfaces the gaps. That helps keep reuse central instead of treating it as a dashboard afterthought.</p><div className="principle-card-footer"><CheckCircle2 size={15}/> Reuse-first by default</div></div>
        <div className="assistant-safety-card"><div className="assistant-safety-icon"><ShieldCheck size={19}/></div><h3>What this assistant won't do</h3><div><span/> Certify a component's electrical ratings from a photo</div><div><span/> Recommend opening mains adapters or battery packs</div><div><span/> Count a generated plan as environmental impact</div><div><span/> Replace datasheets, bench tests, or expert review</div></div>
        <div className="assistant-side-link"><CircleHelp size={17}/><div><strong>Need more precise matches?</strong><span>Update component tags, interface and voltage in your inventory.</span><button onClick={() => onNavigate('inventory')}>Review your inventory <ArrowRight size={13}/></button></div></div>
      </aside>
    </div>
    {history.length > 0 && <section className="panel-card assistant-history"><div className="eyebrow">RECENT QUESTIONS</div><h3>Your last few explorations</h3>{history.map((entry, i) => <button key={`${entry.question}-${i}`} onClick={() => { setMessage(entry.question); setResponse(entry.result); }}><span>{entry.question}</span><ArrowRight size={14}/></button>)}</section>}
  </div>;
}
