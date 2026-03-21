"use client";
import { useState } from "react";
import { API_BASE } from "@/lib/api";

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
    avgAtt: data.students.length
      ? (data.students.reduce((acc, s) => acc + (Number(s.average_attendance) ?? Number(s.attendance) ?? 0), 0) / data.students.length).toFixed(1)
      : 0,
  };

  async function handleUpload() {
    if (!file) return;
    const formData = new FormData();
    formData.append("file", file);
    try {
      const res = await fetch(`${API_BASE}/api/academic/upload-data`, { method: "POST", body: formData });
      const json = await res.json().catch(() => ({}));
      if (!res.ok) {
        const msg = typeof json.detail === "string" ? json.detail : JSON.stringify(json.detail ?? "Upload failed");
        alert("Upload failed: " + msg);
        return;
      }
      alert("Database Refreshed. Ready for AI Diagnostic.");
    } catch (err) {
      console.error("Upload error:", err);
      alert(
        `Could not reach the backend at ${API_BASE}. ` +
        "Ensure the backend is running (e.g. uvicorn on port 8005 or docker compose up)."
      );
    }
  }

  async function handleRunAI() {
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/api/academic/analyze-class`);
      const json = await res.json();
      console.log("AI Data Received:", json);
      setData({
        students: Array.isArray(json.students) ? json.students : [],
        analysis: Array.isArray(json.analysis) ? json.analysis : [],
      });
    } catch (err) {
      console.error("Run AI failed:", err);
      alert(
        `Could not reach the backend at ${API_BASE}. ` +
        "Ensure the backend is running (e.g. uvicorn on port 8005 or docker compose up)."
      );
      setData({ students: [], analysis: [] });
    } finally {
      setLoading(false);
    }
  }

  function riskBadgeClass(level: string | undefined) {
    if (level === "High") return "bg-red-100 text-red-700 border-red-200";
    if (level === "Medium") return "bg-orange-100 text-orange-700 border-orange-200";
    return "bg-emerald-100 text-emerald-700 border-emerald-200";
  }

  async function handleSend() {
    setSending(true);
    try {
      const res = await fetch(`${API_BASE}/api/academic/send-interventions`, { method: "POST" });
      const json = await res.json();
      alert(`Success: ${json.emails_sent} Intervention emails sent by AI Agent.`);
    } catch (err) {
      console.error("Send error:", err);
      alert(
        `Could not reach the backend at ${API_BASE}. ` +
        "Ensure the backend is running (e.g. uvicorn on port 8005 or docker compose up)."
      );
    } finally {
      setSending(false);
    }
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
          <button
            onClick={handleRunAI}
            disabled={loading}
            className="bg-indigo-600 text-white px-6 py-2 rounded-2xl font-bold inline-flex items-center gap-2 disabled:opacity-70 disabled:cursor-wait"
          >
            {loading && (
              <span
                className="inline-block h-4 w-4 animate-spin rounded-full border-2 border-white border-t-transparent"
                aria-hidden
              />
            )}
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
              <th className="p-6 text-[10px] font-black uppercase text-slate-400">Student Name</th>
              <th className="p-6 text-[10px] font-black uppercase text-slate-400">Overall Attendance</th>
              <th className="p-6 text-[10px] font-black uppercase text-slate-400">At Risk Subjects</th>
              <th className="p-6 text-[10px] font-black uppercase text-slate-400">Overall Risk Level</th>
              <th className="p-6 text-[10px] font-black uppercase text-slate-400">AI Analysis</th>
              <th className="p-6 text-[10px] font-black uppercase text-slate-400">Action</th>
            </tr>
          </thead>
          <tbody>
            {data.students.map((s) => {
              const ai = getAI(s.student_id);
              const displayName = s.student_name ?? s.name ?? s.student_id;
              const failing = (s.failing_subjects ?? []) as string[];
              const lowAtt = (s.low_attendance_subjects ?? []) as string[];
              const att = Number(s.average_attendance ?? s.attendance) ?? 0;
              const attBelow75 = att > 0 && att < 75;
              const parts: string[] = [];
              if (failing.length) parts.push(`Failing: ${failing.join(", ")}`);
              if (lowAtt.length) parts.push(`Low attendance in: ${lowAtt.join(", ")}`);
              const atRiskStr = parts.length ? parts.join(". ") : "None";
              const hasRisk = failing.length > 0 || lowAtt.length > 0;
              const analysisText = ai?.analysis ?? "—";
              return (
                <tr key={s.student_id} className="border-b border-slate-50 hover:bg-slate-50/50 transition-all">
                  <td className="p-6">
                    <div className="font-bold text-slate-900">{displayName}</div>
                    <div className="text-[10px] text-slate-400">{s.student_id}</div>
                  </td>
                  <td className="p-6">
                    <span
                      className={`font-black ${attBelow75 ? "text-red-600" : "text-slate-800"}`}
                      title={attBelow75 ? "Ineligible for End-Sems" : undefined}
                    >
                      {att}%
                    </span>
                    {attBelow75 && (
                      <span
                        className="ml-2 inline-block px-2 py-0.5 text-[9px] font-bold uppercase bg-red-100 text-red-700 rounded border border-red-200"
                        title="Overall attendance below 75% — ineligible for End-Semester examinations"
                      >
                        Ineligible for End-Sems
                      </span>
                    )}
                  </td>
                  <td className="p-6">
                    <span className={`text-sm font-medium ${hasRisk ? "text-red-600" : "text-slate-500"}`}>
                      {atRiskStr}
                    </span>
                  </td>
                  <td className="p-6">
                    <span
                      className={`px-3 py-1 rounded-lg text-[10px] font-black uppercase border ${riskBadgeClass(ai?.risk_level)}`}
                    >
                      {ai?.risk_level ?? "—"}
                    </span>
                  </td>
                  <td
                    className="p-6"
                    style={{
                      whiteSpace: "pre-wrap",
                      minWidth: 250,
                      textAlign: "left",
                    }}
                  >
                    <p className="text-xs text-slate-600" title={analysisText}>
                      {analysisText}
                    </p>
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
              );
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