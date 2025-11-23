import React, { useEffect, useRef, useState } from "react";

/* App with NarrationControls moved to its own card between Chat and Shortcuts.
   Replace your existing frontend/src/App.jsx with this file.
*/

async function apiPostJSON(path, body) {
  const res = await fetch(path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  const text = await res.text();
  try {
    const data = text ? JSON.parse(text) : null;
    if (!res.ok) {
      throw new Error(`HTTP ${res.status}: ${text || JSON.stringify(data)}`);
    }
    return data;
  } catch (e) {
    throw new Error(`Failed to parse JSON from ${path}. Raw: ${text}`);
  }
}

/* Header + Footer unchanged (kept minimal) */
function Header({ dark, setDark }) {
  return (
    <header className="w-full bg-gradient-to-r from-sky-600 to-indigo-600 dark:from-slate-900 dark:to-slate-800 text-white">
      <div className="max-w-6xl mx-auto px-6 py-4 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-md bg-white/20 flex items-center justify-center shadow-sm">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" className="text-white">
              <path d="M3 7h18M3 12h18M3 17h18" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
            </svg>
          </div>
          <div>
            <div className="text-xl font-semibold tracking-tight">COMPANY RESEARCH AGENT</div>
            <div className="text-xs opacity-90">Research • Plan • Export • Ask</div>
          </div>
        </div>

        <div className="flex items-center gap-4">
          <button
            onClick={() => setDark(!dark)}
            aria-label="Toggle dark mode"
            className="flex items-center gap-2 bg-white/10 hover:bg-white/20 px-3 py-2 rounded-md"
          >
            {dark ? "Dark" : "Light"}
          </button>
        </div>
      </div>
    </header>
  );
}
function Footer() {
  return (
    <footer className="w-full border-t border-gray-200 dark:border-slate-700 mt-8">
      <div className="max-w-6xl mx-auto px-6 py-4 text-sm text-gray-600 dark:text-gray-300 flex justify-between">
        <div>© {new Date().getFullYear()} Company Research Agent</div>
        <div>Made by Varun</div>
      </div>
    </footer>
  );
}

/* Chat panel (no narration controls here anymore) */
function ChatPanel({ onSend, isLoading }) {
  const [text, setText] = useState("");
  const textareaRef = useRef();

  useEffect(() => {
    function handler(e) {
      if ((e.ctrlKey || e.metaKey) && e.key === "Enter") {
        e.preventDefault();
        if (text.trim()) {
          onSend(text.trim());
          setText("");
        }
      }
    }
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [text, onSend]);

  return (
    <div className="bg-white dark:bg-slate-800 rounded-xl shadow p-4 flex flex-col gap-4 transition-all">
      <div className="flex items-start justify-between gap-4">
        <div>
          <div className="text-lg font-semibold">Research Chat</div>
          <div className="text-xs text-gray-500 dark:text-gray-400">Type the company name or an exploratory query</div>
        </div>
        <div className="ml-auto text-xs text-gray-400">Tip: Ctrl+Enter to send</div>
      </div>

      <textarea
        ref={textareaRef}
        value={text}
        onChange={(e) => setText(e.target.value)}
        placeholder="E.g., 'Research Acme Corporation and suggest top 3 opportunities and immediate next steps.'"
        className="w-full p-3 border rounded-md resize-none h-28 dark:bg-slate-900 dark:border-slate-700 focus:outline-none focus:ring-2 focus:ring-sky-400 transition"
      />

      <div className="flex items-center justify-between gap-3">
        <div className="flex gap-2">
          <button
            onClick={() => { if (!text.trim()) return; onSend(text.trim()); setText(""); }}
            disabled={isLoading}
            className="px-4 py-2 bg-sky-600 hover:bg-sky-700 text-white rounded-md shadow-sm disabled:opacity-50"
          >
            {isLoading ? "Working…" : "Send"}
          </button>

          <button
            onClick={() => { setText(""); textareaRef.current?.focus(); }}
            className="px-3 py-2 bg-gray-100 dark:bg-slate-700 text-gray-700 dark:text-gray-200 rounded-md"
          >
            Clear
          </button>
        </div>

        {/* <div className="text-xs text-gray-500 hidden sm:block">Narration controls below</div> */}
      </div>
    </div>
  );
}

/* NEW: Narration controls in their own prominent card */
function NarrationControls({ plan, isSpeaking, isPaused, onStart, onPause, onResume, onStop, onRestart }) {
  return (
    <div className="bg-white dark:bg-slate-800 rounded-xl shadow p-4 transition">
      <div className="flex items-center justify-between mb-2">
        <div>
          <div className="text-md font-semibold">Narration Controls</div>
          <div className="text-xs text-gray-500 dark:text-gray-400">Play the generated plan.</div>
        </div>
        <div className="text-xs text-gray-400">{isSpeaking ? (isPaused ? "Paused" : "Speaking…") : "Idle"}</div>
      </div>

      <div className="flex gap-2 flex-wrap">
        <button onClick={onStart} disabled={!plan || isSpeaking} className="px-4 py-2 bg-gray-800 text-white rounded-md shadow">Start</button>
        <button onClick={onPause} disabled={!isSpeaking || isPaused} className="px-4 py-2 bg-yellow-500 text-white rounded-md">Pause</button>
        <button onClick={onResume} disabled={!isSpeaking || !isPaused} className="px-4 py-2 bg-green-600 text-white rounded-md">Resume</button>
        <button onClick={onStop} disabled={!isSpeaking && !isPaused} className="px-4 py-2 bg-red-600 text-white rounded-md">Stop</button>
        <button onClick={onRestart} disabled={!plan} className="px-4 py-2 bg-blue-600 text-white rounded-md">Restart</button>
      </div>
    </div>
  );
}

/* Plan viewer (kept polished) */
function PlanViewer({ plan, onEdit }) {
  if (!plan) {
    return (
      <div className="bg-white dark:bg-slate-800 rounded-xl shadow p-6 min-h-[280px] flex items-center justify-center">
        <div className="text-sm text-gray-500 dark:text-gray-400">No plan yet. Run a research query to generate an account plan.</div>
      </div>
    );
  }

  const sections = [
    { key: "company_overview", title: "Company Overview" },
    { key: "key_findings", title: "Key Findings" },
    { key: "pain_points", title: "Pain Points" },
    { key: "opportunities", title: "Opportunities" },
    { key: "competitors", title: "Competitors" },
    { key: "recommended_strategy", title: "Recommended Strategy" },
  ];

  return (
    <div className="bg-white dark:bg-slate-800 rounded-xl shadow p-6 transition-all">
      <div className="flex items-start justify-between gap-4 mb-4">
        <div>
          <h3 className="text-xl font-semibold">Account Plan</h3>
          <p className="text-sm text-gray-500 dark:text-gray-400">Detailed plan synthesized from research results.</p>
        </div>
        <div className="text-sm text-gray-400">
          Confidence: <span className="font-medium">{plan.confidence_estimate || "—"}</span>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
        {sections.map((s) => (
          <article key={s.key} className="bg-gray-50 dark:bg-slate-900 p-4 rounded-md border border-transparent hover:border-sky-200 dark:hover:border-slate-700 transition">
            <div className="flex items-start justify-between gap-2">
              <h4 className="text-md font-semibold">{s.title}</h4>
              {s.key !== "sources" && <button onClick={() => onEdit(s.key)} className="text-xs text-sky-600">Edit</button>}
            </div>
            <div className="mt-2 text-sm text-gray-700 dark:text-gray-300 whitespace-pre-wrap leading-relaxed">
              {plan[s.key] ? plan[s.key] : <span className="text-gray-400 italic">Not available</span>}
            </div>
          </article>
        ))}
      </div>

      <div className="mt-6">
        <h5 className="text-sm font-semibold mb-2">Sources</h5>
        {Array.isArray(plan.sources) && plan.sources.length ? (
          <ul className="list-disc ml-5 text-xs text-gray-600 dark:text-gray-300">
            {plan.sources.map((src, i) => (
              <li key={i}><a className="text-sky-600" href={src} target="_blank" rel="noreferrer">{src}</a></li>
            ))}
          </ul>
        ) : (
          <div className="text-xs text-gray-400">No sources available</div>
        )}
      </div>
    </div>
  );
}

/* Actions & QA */
function QAAndActions({ plan, onDownloadPdf }) {
  const [qaInput, setQaInput] = useState("");
  const [qaHistory, setQaHistory] = useState([]);
  const [qaLoading, setQaLoading] = useState(false);

  const askQuestion = async () => {
    if (!qaInput.trim()) return;
    if (!plan) return alert("Generate a plan first.");
    setQaLoading(true);
    try {
      const res = await apiPostJSON("/api/chat", { question: qaInput.trim(), plan });
      const answer = res?.answer || "No answer.";
      setQaHistory((h) => [...h, { question: qaInput.trim(), answer }]);
      setQaInput("");
    } catch (err) {
      alert("Chat failed: " + err.message);
    } finally {
      setQaLoading(false);
    }
  };

  return (
    <div className="bg-white dark:bg-slate-800 rounded-xl shadow p-4 flex flex-col gap-4 min-h-[280px]">
      <div className="flex items-center justify-between">
        <div>
          <h4 className="font-semibold">Actions & Q/A</h4>
          <div className="text-xs text-gray-500 dark:text-gray-400">Export PDF or ask questions about this plan</div>
        </div>
        <button onClick={onDownloadPdf} className="px-4 py-2 bg-emerald-600 hover:bg-emerald-700 text-white rounded-md">Download PDF</button>
      </div>

      <div className="mt-2">
        <div className="flex gap-2">
          <input value={qaInput} onChange={(e) => setQaInput(e.target.value)} placeholder="Ask about the plan — e.g. 'Top 3 risks?'" className="flex-1 p-2 border rounded-md dark:bg-slate-900 dark:border-slate-700" />
          <button onClick={askQuestion} disabled={qaLoading} className="px-3 py-2 bg-indigo-600 text-white rounded-md">{qaLoading ? "Thinking…" : "Ask"}</button>
        </div>
      </div>

      <div className="mt-2 overflow-auto flex-1">
        {qaHistory.length === 0 ? (
          <div className="text-xs text-gray-400">No questions yet.</div>
        ) : (
          <div className="space-y-3">
            {qaHistory.slice().reverse().map((h, i) => (
              <div key={i} className="p-3 rounded-md bg-gray-50 dark:bg-slate-900 border border-transparent hover:border-slate-700 transition">
                <div className="text-xs text-gray-500">Q: {h.question}</div>
                <div className="mt-1 text-sm">{h.answer}</div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

/* Main App */
export default function App() {
  const [plan, setPlan] = useState(null);
  const [loading, setLoading] = useState(false);
  const [editingSection, setEditingSection] = useState(null);
  const [editingValue, setEditingValue] = useState("");
  const [saving, setSaving] = useState(false);
  const [dark, setDark] = useState(() => { try { return localStorage.getItem("theme") === "dark"; } catch { return true; } });

  // narration state
  const utterRef = useRef(null);
  const [isSpeaking, setIsSpeaking] = useState(false);
  const [isPaused, setIsPaused] = useState(false);

  useEffect(() => {
    document.documentElement.classList.toggle("dark", dark);
    try { localStorage.setItem("theme", dark ? "dark" : "light"); } catch {}
  }, [dark]);

  // narration helpers
  const planTextToSpeak = (p) => {
    if (!p) return "";
    const order = ["company_overview", "key_findings", "pain_points", "opportunities", "competitors", "recommended_strategy"];
    let text = "";
    order.forEach((k) => { if (p[k]) text += `${k.replace(/_/g," ")}: ${p[k]}. `; });
    return text;
  };
  const startSpeaking = () => {
    if (!plan) return alert("No plan to speak.");
    window.speechSynthesis.cancel();
    const utter = new SpeechSynthesisUtterance(planTextToSpeak(plan));
    utter.rate = 1.0; utter.pitch = 1.0;
    utter.onstart = () => { setIsSpeaking(true); setIsPaused(false); };
    utter.onend = () => { setIsSpeaking(false); setIsPaused(false); };
    utter.onerror = () => { setIsSpeaking(false); setIsPaused(false); };
    utterRef.current = utter;
    window.speechSynthesis.speak(utter);
  };
  const pauseSpeaking = () => { if (window.speechSynthesis.speaking && !window.speechSynthesis.paused) { window.speechSynthesis.pause(); setIsPaused(true);} };
  const resumeSpeaking = () => { if (window.speechSynthesis.paused) { window.speechSynthesis.resume(); setIsPaused(false);} else if (!window.speechSynthesis.speaking) startSpeaking(); };
  const stopSpeaking = () => { window.speechSynthesis.cancel(); setIsSpeaking(false); setIsPaused(false); };
  const restartSpeaking = () => { stopSpeaking(); setTimeout(startSpeaking, 100); };

  // research -> generate plan
  const handleSend = async (query) => {
    setLoading(true);
    try {
      const res = await apiPostJSON("/api/research", { query });
      if (!res?.plan) throw new Error("Invalid response.");
      setPlan(res.plan);
    } catch (err) {
      alert("Error:\n" + err.message);
    } finally {
      setLoading(false);
    }
  };

  // edit flow
  const openEdit = (section) => { setEditingSection(section); setEditingValue(plan ? plan[section] || "" : ""); };
  const saveEdit = async (text) => {
    if (!editingSection) return;
    setSaving(true);
    try {
      const res = await apiPostJSON("/api/edit", { section: editingSection, content: text, plan });
      if (!res?.plan) throw new Error("Invalid response.");
      setPlan(res.plan);
      setEditingSection(null);
    } catch (err) {
      alert("Save failed:\n" + err.message);
    } finally { setSaving(false); }
  };

  // download pdf
  const downloadPdf = async () => {
    if (!plan) return alert("No plan to export.");
    try {
      const res = await fetch("/api/export_pdf", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ plan, filename: "account_plan.pdf" }),
      });
      if (!res.ok) throw new Error(await res.text());
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a"); a.href = url; a.download = "account_plan.pdf"; a.click(); URL.revokeObjectURL(url);
    } catch (err) {
      alert("PDF failed:\n" + err.message);
    }
  };

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-slate-900 text-slate-900 dark:text-slate-100 flex flex-col">
      <Header dark={dark} setDark={setDark} />

      <main className="flex-1 max-w-6xl mx-auto px-6 py-8 w-full">
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Left column: Chat, NarrationControls (new), Shortcuts */}
          <div className="lg:col-span-1 flex flex-col gap-4">
            <ChatPanel onSend={handleSend} isLoading={loading} />
            <NarrationControls
              plan={plan}
              isSpeaking={isSpeaking}
              isPaused={isPaused}
              onStart={startSpeaking}
              onPause={pauseSpeaking}
              onResume={resumeSpeaking}
              onStop={stopSpeaking}
              onRestart={restartSpeaking}
            />
          </div>

          {/* Right column: Plan viewer + Actions */}
          <div className="lg:col-span-2 flex flex-col gap-6">
            <PlanViewer plan={plan} onEdit={openEdit} />
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <QAAndActions plan={plan} onDownloadPdf={downloadPdf} />
            </div>
          </div>
        </div>
      </main>

      <Footer />

      {/* Edit modal */}
      {editingSection && (
        <div className="fixed inset-0 bg-black/40 z-50 flex items-center justify-center p-4">
          <div className="bg-white dark:bg-slate-800 rounded-lg w-full max-w-2xl p-6">
            <div className="flex items-center justify-between mb-3">
              <h5 className="text-lg font-semibold">Edit: {editingSection.replace(/_/g, " ")}</h5>
              <button onClick={() => setEditingSection(null)} className="text-sm text-gray-500">Close</button>
            </div>
            <textarea value={editingValue} onChange={(e) => setEditingValue(e.target.value)} rows={10} className="w-full p-3 border rounded-md dark:bg-slate-900 dark:border-slate-700" />
            <div className="mt-3 flex justify-end gap-2">
              <button onClick={() => setEditingSection(null)} className="px-3 py-2 bg-gray-100 rounded-md">Cancel</button>
              <button onClick={() => saveEdit(editingValue)} className="px-4 py-2 bg-sky-600 text-white rounded-md">{saving ? "Saving…" : "Save"}</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
