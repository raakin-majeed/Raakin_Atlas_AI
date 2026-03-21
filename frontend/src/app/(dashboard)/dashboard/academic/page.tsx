"use client";
import { useMemo, useState } from "react";

type StudentRow = { student_id: string; name: string; attendance: number };
type RiskRow = { student_id: string; risk_level: string; recovery_plan: string; email_content?: string };

export default function AcademicRiskMonitoringPage() {
  const [file, setFile] = useState<File | null>(null);
  const [students, setStudents] = useState<StudentRow[]>([]);
  const [risks, setRisks] = useState<RiskRow[]>([]);
  const [loading, setLoading] = useState(false);
  const [selectedEmail, setSelectedEmail] = useState<string | null>(null);

  const stats = useMemo(() => {
    const total = students.length;
    const highRisk = risks.filter(r => r.risk_level === "High").length;
    const avgAtt = total ? (students.reduce((acc, s) => acc + (s.attendance || 0), 0) / total).toFixed(1) : 0;
    return { total, highRisk, avgAtt };
  }, [students, risks]);

  const riskMap = useMemo(() => {
    const map = new Map<string, RiskRow>();
    risks.forEach(r => map.set(r.student_id, r));
    return map;
  }, [risks]);

  async function handleUpload() {
    if (!file) return;
    setLoading(true);
    const formData = new FormData();
    formData.append("file", file);
    await fetch("http://localhost:5000/api/academic/upload-data", { method: "POST", body: formData });
    setLoading(false);
    alert("File uploaded and database cleared for fresh session.");
  }

  async function handleAnalyze() {
    setLoading(true);
    const res = await fetch("http://localhost:5000/api/academic/analyze-class");
    const data = await res.json();
    setStudents(data.students || []);
    setRisks(data.analysis || []);
    setLoading(false);
  }

  return (
    <div className="p-8 space-y-8 bg-slate-50 min-h-screen">
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-bold text-slate-900">Atlas Academic Oversight</h1>
          <p className="text-slate-500">AI-powered student success monitoring</p>
        </div>
        <div className="flex gap-3 bg-white p-3 rounded-xl shadow-sm border">
          <input type="file" onChange={(e) => setFile(e.target.files?.[0] ?? null)} className="text-sm self-center" />
          <button onClick={handleUpload} disabled={loading} className="bg-blue-600 text-white px-5 py-2 rounded-lg hover:bg-blue-700 disabled:opacity-50">Upload</button>
          <button onClick={handleAnalyze} disabled={loading} className="bg-indigo-600 text-white px-5 py-2 rounded-lg hover:bg-indigo-700 disabled:opacity-50">Run AI</button>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="bg-white p-6 rounded-2xl shadow-sm border-t-4 border-blue-500">
          <p className="text-sm font-semibold text-slate-500 uppercase">Total Enrolled</p>
          <p className="text-3xl font-bold text-slate-900">{stats.total}</p>
        </div>
        <div className="bg-white p-6 rounded-2xl shadow-sm border-t-4 border-red-500">
          <p className="text-sm font-semibold text-slate-500 uppercase">High Risk</p>
          <p className="text-3xl font-bold text-red-600">{stats.highRisk}</p>
        </div>
        <div className="bg-white p-6 rounded-2xl shadow-sm border-t-4 border-emerald-500">
          <p className="text-sm font-semibold text-slate-500 uppercase">Avg Attendance</p>
          <p className="text-3xl font-bold text-slate-900">{stats.avgAtt}%</p>
        </div>
      </div>

      <div className="bg-white rounded-2xl shadow-xl overflow-hidden border border-slate-200">
        <table className="min-w-full divide-y divide-slate-200">
          <thead className="bg-slate-50">
            <tr>
              <th className="px-6 py-4 text-left text-xs font-bold text-slate-500 uppercase">Student Info</th>
              <th className="px-6 py-4 text-left text-xs font-bold text-slate-500 uppercase">Attendance</th>
              <th className="px-6 py-4 text-left text-xs font-bold text-slate-500 uppercase">Risk Level</th>
              <th className="px-6 py-4 text-left text-xs font-bold text-slate-500 uppercase">AI Recovery Plan</th>
              <th className="px-6 py-4 text-right text-xs font-bold text-slate-500 uppercase">Action</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {students.map((s) => {
              const r = riskMap.get(s.student_id);
              return (
                <tr key={s.student_id} className="hover:bg-slate-50 transition-colors">
                  <td className="px-6 py-4">
                    <div className="font-bold text-slate-900">{s.name}</div>
                    <div className="text-xs text-slate-400">{s.student_id}</div>
                  </td>
                  <td className="px-6 py-4 text-sm font-medium">{s.attendance}%</td>
                  <td className="px-6 py-4">
                    <span className={`px-3 py-1 rounded-full text-[10px] font-black uppercase ${
                      r?.risk_level === 'High' ? 'bg-red-100 text-red-700' : 'bg-green-100 text-green-700'
                    }`}>{r?.risk_level || 'Pending'}</span>
                  </td>
                  <td className="px-6 py-4 text-sm text-slate-600 italic">{r?.recovery_plan || "Awaiting analysis..."}</td>
                  <td className="px-6 py-4 text-right">
                    <button onClick={() => setSelectedEmail(r?.email_content || null)} className="text-indigo-600 font-bold text-sm hover:underline">Draft Email</button>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {selectedEmail && (
        <div className="fixed inset-0 bg-slate-900/60 backdrop-blur-sm flex items-center justify-center p-4 z-50">
          <div className="bg-white rounded-3xl p-10 max-w-xl w-full shadow-2xl transform transition-all">
            <h2 className="text-2xl font-black text-slate-900 mb-6">Student Intervention Draft</h2>
            <div className="bg-slate-50 p-6 rounded-2xl border border-slate-200 text-slate-700 leading-relaxed font-serif">
              {selectedEmail}
            </div>
            <button onClick={() => setSelectedEmail(null)} className="mt-8 w-full bg-slate-900 text-white py-4 rounded-2xl font-bold hover:shadow-lg transition-all">Dismiss Preview</button>
          </div>
        </div>
      )}
    </div>
  );
}