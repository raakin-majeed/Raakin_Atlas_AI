"use client";

import { useMemo, useState } from "react";

type StudentRow = {
  student_id: string;
  name: string;
  attendance: number | null;
};

type RiskRow = {
  student_id: string;
  risk_level: string;
  recovery_plan: string;
};

export default function AcademicRiskMonitoringPage() {
  const [file, setFile] = useState<File | null>(null);
  const [students, setStudents] = useState<StudentRow[]>([]);
  const [risks, setRisks] = useState<RiskRow[]>([]);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState("");

  const riskMap = useMemo(() => {
    const map = new Map<string, RiskRow>();
    for (const risk of risks) map.set(risk.student_id, risk);
    return map;
  }, [risks]);

  async function handleUpload() {
    if (!file) return;
    setLoading(true);
    setMessage("");
    try {
      const formData = new FormData();
      formData.append("file", file);
      const res = await fetch("http://localhost:5000/api/academic/upload-data", {
        method: "POST",
        body: formData,
      });
      if (!res.ok) throw new Error(await res.text());
      setMessage("Upload successful.");
    } catch (error) {
      setMessage(`Upload failed: ${error instanceof Error ? error.message : "Unknown error"}`);
    } finally {
      setLoading(false);
    }
  }

  async function handleAnalyzeClass() {
    setLoading(true);
    setMessage("");
    try {
      const res = await fetch("http://localhost:5000/api/academic/analyze-class");
      if (!res.ok) throw new Error(await res.text());
      const data = await res.json();
      setStudents(Array.isArray(data.students) ? data.students : []);
      setRisks(Array.isArray(data.analysis) ? data.analysis : []);
      if (data.message) setMessage(String(data.message));
    } catch (error) {
      setMessage(`Analyze failed: ${error instanceof Error ? error.message : "Unknown error"}`);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-semibold text-slate-900">Academic Risk Monitoring</h1>

      <div className="flex items-center gap-3">
        <input
          type="file"
          accept=".xlsx"
          onChange={(e) => setFile(e.target.files?.[0] ?? null)}
          className="text-sm"
        />
        <button
          type="button"
          onClick={handleUpload}
          disabled={!file || loading}
          className="px-4 py-2 rounded bg-blue-600 text-white disabled:opacity-50"
        >
          Upload
        </button>
        <button
          type="button"
          onClick={handleAnalyzeClass}
          disabled={loading}
          className="px-4 py-2 rounded bg-purple-600 text-white disabled:opacity-50"
        >
          Analyze Class
        </button>
      </div>

      {message && <p className="text-sm text-slate-700">{message}</p>}

      <div className="overflow-auto border rounded bg-white">
        <table className="min-w-full text-sm">
          <thead className="bg-slate-50">
            <tr>
              <th className="px-3 py-2 text-left">Student ID</th>
              <th className="px-3 py-2 text-left">Name</th>
              <th className="px-3 py-2 text-left">Attendance</th>
              <th className="px-3 py-2 text-left">Risk Level</th>
              <th className="px-3 py-2 text-left">Recovery Plan</th>
            </tr>
          </thead>
          <tbody>
            {students.map((student, index) => {
              const risk = riskMap.get(student.student_id);
              return (
                <tr key={`${student.student_id}-${index}`} className={risk?.risk_level === "High" ? "bg-red-50" : ""}>
                  <td className="px-3 py-2">{student.student_id}</td>
                  <td className="px-3 py-2">{student.name}</td>
                  <td className="px-3 py-2">{student.attendance ?? "-"}</td>
                  <td className="px-3 py-2">{risk?.risk_level ?? "-"}</td>
                  <td className="px-3 py-2">{risk?.recovery_plan ?? "-"}</td>
                </tr>
              );
            })}
            {students.length === 0 && (
              <tr>
                <td className="px-3 py-8 text-center text-slate-500" colSpan={5}>
                  No results yet.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
