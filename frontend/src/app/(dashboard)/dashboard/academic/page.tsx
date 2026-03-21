"use client";
import { useState } from "react";

export default function AcademicAgentPage() {
  const [file, setFile] = useState<File | null>(null);
  const [data, setData] = useState<{students: any[], analysis: any[]}>({ students: [], analysis: [] });
  const [loading, setLoading] = useState(false);
  const [sending, setSending] = useState(false);
  const [selectedEmail, setSelectedEmail] = useState<string | null>(null);

  // Helper to find AI results for a student
  const getAI = (sid: string) => data.analysis.find(a => a.student_id === sid);

  const stats = {
    total: data.students.length,
    highRisk: data.analysis.filter(a => a.risk_level === "High").length,
    avgAtt: data.students.length ? (data.students.reduce((acc, s) => acc + s.attendance, 0) / data.students.length).toFixed(1) : 0
  };

  async function handleUpload() {
    if (!file) return;
    const formData = new FormData();
    formData.append("file", file);
    await fetch("http://localhost:5000/api/academic/upload-data", { method: "POST", body: formData });
    alert("Database Refreshed. Ready for AI Diagnostic.");
  }

  async function handleRunAI() {
    setLoading(true);
    const res = await fetch("http://localhost:5000/api/academic/analyze-class");
    const json = await res.json();
    setData(json);
    setLoading(false);
  }

  async function handleSend() {
    setSending(true);
    const res = await fetch("http://localhost:5000/api/academic/send-interventions", { method: "POST" });
    const json = await res.json();
    setSending(false);
    alert(`Success: ${json.emails_sent} Intervention emails sent by AI Agent.`);
  }

  return (
    <div className="p-8 bg-slate-50 min-h-screen">
      <div className="flex justify-between items-end mb-10">
        <div>
          <h1 className="text-4xl font-black text-slate-900 tracking-tighter uppercase">Atlas Agent</h1>
          <p className="text-slate-500 font-medium">Predictive Cause Analysis & Outreach</p>
        </div>
        <div className="flex gap-3 bg-white p-3 rounded-3xl shadow-sm border border-slate-100">
          <input type="file" onChange={e => setFile(e.target.files?.[0] || null)} className="text-sm self-center" />
          <button onClick={handleUpload} className="bg-slate-900 text-white px-6 py-2 rounded-2xl font-bold">Upload</button>
          <button onClick={handleRunAI} className="bg-indigo-600 text-white px-6 py-2 rounded-2xl font-bold">
            {loading ? "Analyzing..." : "Run AI Diagnostic"}
          </button>
          {data.analysis.length > 0 && (
            <button onClick={handleSend} className="bg-emerald-600 text-white px-6 py-2 rounded-2xl font-bold shadow-lg shadow-emerald-100 animate-bounce-short">
              {sending ? "Sending..." : "Execute Outreach"}
            </button>
          )}
        </div>
      </div>

      <div className="grid grid-cols-3 gap-6 mb-8">
        <div className="bg-white p-8 rounded-[40px] shadow-sm border border-slate-200">
            <span className="text-slate-400 text-xs font-black uppercase tracking-widest">Enrolled</span>
            <div className="text-4xl font-black text-slate-900">{stats.total}</div>
        </div>
        <div className="bg-white p-8 rounded-[40px] shadow-sm border border-slate-200 border-b-red-500 border-b-4">
            <span className="text-red-400 text-xs font-black uppercase tracking-widest">High Risk</span>
            <div className="text-4xl font-black text-red-600">{stats.highRisk}</div>
        </div>
        <div className="bg-white p-8 rounded-[40px] shadow-sm border border-slate-200 border-b-indigo-500 border-b-4">
            <span className="text-slate-400 text-xs font-black uppercase tracking-widest">Avg Attendance</span>
            <div className="text-4xl font-black text-slate-900">{stats.avgAtt}%</div>
        </div>
      </div>

      <div className="bg-white rounded-[40px] shadow-sm border border-slate-200 overflow-hidden">
        <table className="w-full text-left border-collapse">
          <thead className="bg-slate-50 border-b border-slate-100">
            <tr>
              <th className="p-6 text-[10px] font-black uppercase text-slate-400">Student Info</th>
              <th className="p-6 text-[10px] font-black uppercase text-slate-400">Attendance</th>
              <th className="p-6 text-[10px] font-black uppercase text-slate-400">AI Persona</th>
              <th className="p-6 text-[10px] font-black uppercase text-slate-400">Risk Status</th>
              <th className="p-6 text-[10px] font-black uppercase text-slate-400">Action</th>
            </tr>
          </thead>
          <tbody>
            {data.students.map((s) => {
              const ai = getAI(s.student_id);
              return (
                <tr key={s.student_id} className="border-b border-slate-50 hover:bg-slate-50/50 transition-all">
                  <td className="p-6">
                    <div className="font-bold text-slate-900">{s.name}</div>
                    <div className="text-[10px] text-slate-400">{s.student_id}</div>
                  </td>
                  <td className="p-6">
                    <div className="font-black text-slate-700">{s.attendance}%</div>
                    <div className="w-24 h-1.5 bg-slate-100 rounded-full mt-1 overflow-hidden">
                        <div className={`h-full ${s.attendance < 75 ? 'bg-red-500' : 'bg-emerald-500'}`} style={{width: `${s.attendance}%`}}></div>
                    </div>
                  </td>
                  <td className="p-6">
                    <span className="bg-indigo-50 text-indigo-700 px-4 py-1.5 rounded-full text-xs font-bold italic border border-indigo-100">
                        {ai?.persona || "Pending..."}
                    </span>
                  </td>
                  <td className="p-6">
                    <span className={`px-3 py-1 rounded-lg text-[10px] font-black uppercase ${ai?.risk_level === 'High' ? 'bg-red-100 text-red-600' : 'bg-emerald-100 text-emerald-600'}`}>
                        {ai?.risk_level || "Analyzing..."}
                    </span>
                  </td>
                  <td className="p-6">
                    <button 
                        onClick={() => setSelectedEmail(ai?.email_content)} 
                        disabled={!ai}
                        className="text-[10px] font-black text-slate-400 hover:text-indigo-600 underline uppercase transition-all"
                    >
                        Preview Draft
                    </button>
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>

      {selectedEmail && (
        <div className="fixed inset-0 bg-slate-900/60 backdrop-blur-md flex items-center justify-center p-6 z-50">
          <div className="bg-white p-12 rounded-[50px] max-w-2xl w-full shadow-2xl">
            <h2 className="text-2xl font-black text-slate-900 mb-6">AI Agent Outreach</h2>
            <div className="bg-slate-50 p-8 rounded-3xl italic text-slate-600 font-serif leading-relaxed border-l-8 border-indigo-500">
              "{selectedEmail}"
            </div>
            <button 
                onClick={() => setSelectedEmail(null)} 
                className="mt-8 w-full bg-slate-900 text-white py-4 rounded-2xl font-bold hover:bg-black transition-all"
            >
                Close Preview
            </button>
          </div>
        </div>
      )}
    </div>
  );
}