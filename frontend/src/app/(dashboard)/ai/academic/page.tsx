"use client";

import { useMemo, useState } from "react";
import { API_BASE } from "@/lib/api";

type StudentRow = {
  student_id: string;
  name: string;
  email: string;
  course: string;
  semester: string;
  subject_name: string;
  attendance: number | null;
  cia_scores: number[];
  mid_sem: number | null;
  end_sem: number | null;
};

type RiskRow = {
  student_id: string;
  risk_level: "Low" | "Medium" | "High" | string;
  recovery_plan: string;
  email_content: string;
};

export default function AcademicMonitoringPage() {
  const [file, setFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [analyzing, setAnalyzing] = useState(false);
  const [students, setStudents] = useState<StudentRow[]>([]);
  const [risks, setRisks] = useState<RiskRow[]>([]);
  const [expandedStudentId, setExpandedStudentId] = useState<string | null>(null);
  const [message, setMessage] = useState<string>("");

  const riskMap = useMemo(() => {
    const map = new Map<string, RiskRow>();
    risks.forEach((item) => map.set(item.student_id, item));
    return map;
  }, [risks]);

  async function handleUpload() {
    if (!file) return;
    setUploading(true);
    setMessage("");
    try {
      const body = new FormData();
      body.append("file", file);
      const response = await fetch(`${API_BASE}/api/academic/upload-data`, {
        method: "POST",
        body,
      });
      if (!response.ok) {
        const err = await response.text();
        throw new Error(err || "Upload failed");
      }
      setMessage("Upload successful. Run class analysis to load student table.");
    } catch (error) {
      setMessage(`Upload failed: ${error instanceof Error ? error.message : "Unknown error"}`);
    } finally {
      setUploading(false);
    }
  }

  async function handleAnalyzeClass() {
    setAnalyzing(true);
    setMessage("");
    try {
      const response = await fetch(`${API_BASE}/api/academic/analyze-class`);
      if (!response.ok) {
        const err = await response.text();
        throw new Error(err || "Analysis failed");
      }
      const data = await response.json();
      setStudents(Array.isArray(data.students) ? data.students : []);
      setRisks(Array.isArray(data.analysis) ? data.analysis : []);
      if (data.message) setMessage(String(data.message));
    } catch (error) {
      setMessage(`Analysis failed: ${error instanceof Error ? error.message : "Unknown error"}`);
    } finally {
      setAnalyzing(false);
    }
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-slate-900">Academic Monitoring</h1>
        <p className="text-slate-600 mt-1">Upload Excel records and review AI risk analysis.</p>
      </div>

      <div className="bg-white border border-slate-200 rounded-xl p-4 flex flex-wrap gap-3 items-center">
        <input
          type="file"
          accept=".xlsx,.xls"
          onChange={(e) => setFile(e.target.files?.[0] ?? null)}
          className="block text-sm text-slate-700"
        />
        <button
          onClick={handleUpload}
          disabled={!file || uploading}
          className="px-4 py-2 rounded-lg bg-blue-600 text-white disabled:opacity-50"
        >
          {uploading ? "Uploading..." : "Upload Data"}
        </button>
        <button
          onClick={handleAnalyzeClass}
          disabled={analyzing}
          className="px-4 py-2 rounded-lg bg-purple-600 text-white disabled:opacity-50"
        >
          {analyzing ? "Analyzing..." : "Analyze Class"}
        </button>
      </div>

      {message && <div className="text-sm text-slate-700">{message}</div>}

      <div className="bg-white border border-slate-200 rounded-xl overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-slate-50">
            <tr className="text-left">
              <th className="px-4 py-3">Student</th>
              <th className="px-4 py-3">Subject</th>
              <th className="px-4 py-3">Attendance</th>
              <th className="px-4 py-3">CIA</th>
              <th className="px-4 py-3">Mid / End</th>
              <th className="px-4 py-3">Risk</th>
              <th className="px-4 py-3">Recovery Plan</th>
            </tr>
          </thead>
          <tbody>
            {students.map((row, idx) => {
              const risk = riskMap.get(row.student_id);
              const highRisk = risk?.risk_level === "High";
              const expanded = expandedStudentId === row.student_id;
              return (
                <tr
                  key={`${row.student_id}-${row.subject_name}-${idx}`}
                  className={highRisk ? "bg-red-50" : "bg-white"}
                >
                  <td className="px-4 py-3">
                    <div className="font-medium text-slate-900">{row.name}</div>
                    <div className="text-xs text-slate-500">{row.student_id}</div>
                  </td>
                  <td className="px-4 py-3">{row.subject_name}</td>
                  <td className="px-4 py-3">{row.attendance ?? "-"}</td>
                  <td className="px-4 py-3">{(row.cia_scores || []).join(", ") || "-"}</td>
                  <td className="px-4 py-3">
                    {row.mid_sem ?? "-"} / {row.end_sem ?? "-"}
                  </td>
                  <td className={`px-4 py-3 font-semibold ${highRisk ? "text-red-700" : "text-slate-700"}`}>
                    {risk?.risk_level || "N/A"}
                  </td>
                  <td className="px-4 py-3">
                    <button
                      className="text-blue-600 underline"
                      onClick={() => setExpandedStudentId(expanded ? null : row.student_id)}
                      disabled={!risk?.recovery_plan}
                    >
                      {expanded ? "Hide" : "View"}
                    </button>
                    {expanded && risk && (
                      <div className="mt-2 p-3 bg-slate-100 rounded text-xs text-slate-700 whitespace-pre-wrap">
                        {risk.recovery_plan}
                      </div>
                    )}
                  </td>
                </tr>
              );
            })}
            {students.length === 0 && (
              <tr>
                <td colSpan={7} className="px-4 py-8 text-center text-slate-500">
                  Upload data and run analysis to view students.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
