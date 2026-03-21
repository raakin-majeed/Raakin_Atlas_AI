"use client";

import { useMemo, useState } from "react";
import { API_BASE } from "@/lib/api";

/** Matches GET /api/academic/analyze-class `students` items (grouped by student) */
type StudentRow = {
  student_id: string;
  student_name: string;
  email?: string;
  subjects_enrolled?: number;
  failing_subjects?: string[];
  low_attendance_subjects?: string[];
  average_attendance?: number | null;
  /** Legacy */
  subject?: string;
  name?: string;
  attendance?: number | null;
};

type RiskRow = {
  student_id: string;
  risk_level: "Low" | "Medium" | "High" | string;
  analysis?: string;
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
        const json = await response.json().catch(() => ({}));
        const msg = typeof json.detail === "string" ? json.detail : JSON.stringify(json.detail ?? "Upload failed");
        throw new Error(msg);
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
      console.log("AI Data Received:", data);
      // Same shape as axios response.data: students + analysis on the parsed body
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
          className="px-4 py-2 rounded-lg bg-purple-600 text-white disabled:opacity-50 inline-flex items-center gap-2"
        >
          {analyzing && (
            <span
              className="inline-block h-4 w-4 animate-spin rounded-full border-2 border-white border-t-transparent"
              aria-hidden
            />
          )}
          {analyzing ? "Analyzing..." : "Analyze Class"}
        </button>
      </div>

      {message && <div className="text-sm text-slate-700">{message}</div>}

      <div className="bg-white border border-slate-200 rounded-xl overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-slate-50">
            <tr className="text-left">
              <th className="px-4 py-3">Student Name</th>
              <th className="px-4 py-3">Overall Attendance</th>
              <th className="px-4 py-3">At Risk Subjects</th>
              <th className="px-4 py-3">Overall Risk</th>
              <th className="px-4 py-3">AI Analysis</th>
              <th className="px-4 py-3">Recovery Plan</th>
            </tr>
          </thead>
          <tbody>
            {students.map((row, idx) => {
              const risk = riskMap.get(row.student_id);
              const level = risk?.risk_level;
              const highRisk = level === "High";
              const mediumRisk = level === "Medium";
              const expanded = expandedStudentId === row.student_id;
              const displayName = row.student_name ?? row.name ?? row.student_id;
              const failing = row.failing_subjects ?? [];
              const lowAtt = row.low_attendance_subjects ?? [];
              const parts: string[] = [];
              if (failing.length) parts.push(`Failing: ${failing.join(", ")}`);
              if (lowAtt.length) parts.push(`Low attendance in: ${lowAtt.join(", ")}`);
              const atRiskStr = parts.length ? parts.join(". ") : "—";
              const hasRisk = failing.length > 0 || lowAtt.length > 0;
              const att = Number(row.average_attendance ?? row.attendance) ?? 0;
              const attBelow75 = att > 0 && att < 75;
              const analysisText = risk?.analysis ?? "—";
              return (
                <tr
                  key={`${row.student_id}-${idx}`}
                  className={highRisk ? "bg-red-50" : mediumRisk ? "bg-orange-50/60" : "bg-white"}
                >
                  <td className="px-4 py-3">
                    <div className="font-medium text-slate-900">{displayName}</div>
                    <div className="text-xs text-slate-500">{row.student_id}</div>
                  </td>
                  <td className="px-4 py-3">
                    <span
                      className={`font-bold ${attBelow75 ? "text-red-600" : "text-slate-800"}`}
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
                  <td className={`px-4 py-3 text-sm font-medium ${hasRisk ? "text-red-600" : "text-slate-500"}`}>
                    {atRiskStr}
                  </td>
                  <td className="px-4 py-3">
                    <span
                      className={`inline-flex rounded-md px-2 py-0.5 text-xs font-semibold ${
                        level === "High"
                          ? "bg-red-100 text-red-800"
                          : level === "Medium"
                            ? "bg-orange-100 text-orange-800"
                            : "bg-slate-100 text-slate-800"
                      }`}
                    >
                      {level || "N/A"}
                    </span>
                  </td>
                  <td
                    className="px-4 py-3"
                    style={{ whiteSpace: "pre-wrap", minWidth: 250, textAlign: "left" }}
                  >
                    <p className="text-xs text-slate-700" title={analysisText}>
                      {analysisText}
                    </p>
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
                <td colSpan={6} className="px-4 py-8 text-center text-slate-500">
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
