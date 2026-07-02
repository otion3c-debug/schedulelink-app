"use client";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";

const DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"];

const TIME_OPTIONS: { value: string; label: string }[] = (() => {
  const out: { value: string; label: string }[] = [];
  for (let h = 0; h < 24; h++) {
    for (let m = 0; m < 60; m += 15) {
      const hh = String(h).padStart(2, "0");
      const mm = String(m).padStart(2, "0");
      const value = `${hh}:${mm}`;
      const ampm = h < 12 ? "AM" : "PM";
      const h12 = h % 12 === 0 ? 12 : h % 12;
      const label = `${h12}:${mm} ${ampm}`;
      out.push({ value, label });
    }
  }
  return out;
})();

type DayState = { active: boolean; start: string; end: string };

const DEFAULTS: DayState[] = [
  { active: true, start: "09:00", end: "17:00" },
  { active: true, start: "09:00", end: "17:00" },
  { active: true, start: "09:00", end: "17:00" },
  { active: true, start: "09:00", end: "17:00" },
  { active: true, start: "09:00", end: "17:00" },
  { active: false, start: "09:00", end: "17:00" },
  { active: false, start: "09:00", end: "17:00" },
];

export default function AvailabilityPage() {
  const [days, setDays] = useState<DayState[]>(DEFAULTS);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [savedAt, setSavedAt] = useState<string | null>(null);

  useEffect(() => {
    (async () => {
      try {
        const data = await api<{ rules: any[] }>("/availability");
        if (data.rules.length > 0) {
          const next = DAYS.map((_, i) => {
            const r = data.rules.find((x) => x.day_of_week === i);
            return r
              ? { active: r.is_active !== false, start: r.start_time, end: r.end_time }
              : { active: false, start: "09:00", end: "17:00" };
          });
          setDays(next);
        }
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  function update(i: number, patch: Partial<DayState>) {
    setDays((prev) => prev.map((d, idx) => (idx === i ? { ...d, ...patch } : d)));
  }

  function copyToAll() {
    const first = days.find((d) => d.active);
    if (!first) return;
    setDays((prev) => prev.map((d) => (d.active ? { ...d, start: first.start, end: first.end } : d)));
  }

  async function save() {
    setSaving(true);
    try {
      const rules = days
        .map((d, i) => ({ ...d, day: i }))
        .filter((d) => d.active && d.start < d.end)
        .map((d) => ({ day_of_week: d.day, start_time: d.start, end_time: d.end }));
      await api("/availability/bulk", { method: "PUT", body: JSON.stringify({ rules }) });
      setSavedAt(new Date().toLocaleTimeString());
    } catch (e: any) {
      alert(e.message || "Save failed");
    } finally {
      setSaving(false);
    }
  }

  if (loading) return <div className="text-gray-500">Loading…</div>;

  return (
    <div>
      <h1 className="h2">Working hours</h1>
      <p className="muted mt-1">When can people book with you? 30-second setup.</p>

      <div className="card p-4 mt-6 divide-y divide-gray-100">
        {days.map((d, i) => (
          <div key={i} className="py-3 flex items-center gap-4">
            <div className="w-28 font-medium">{DAYS[i]}</div>
            {d.active ? (
              <>
                <select
                  className="input max-w-[160px]"
                  value={d.start}
                  onChange={(e) => update(i, { start: e.target.value })}
                >
                  {TIME_OPTIONS.map((o) => (
                    <option key={o.value} value={o.value}>{o.label}</option>
                  ))}
                </select>
                <span className="text-gray-500">to</span>
                <select
                  className="input max-w-[160px]"
                  value={d.end}
                  onChange={(e) => update(i, { end: e.target.value })}
                >
                  {TIME_OPTIONS.map((o) => (
                    <option key={o.value} value={o.value}>{o.label}</option>
                  ))}
                </select>
                <button
                  onClick={() => update(i, { active: false })}
                  className="ml-auto text-sm text-gray-500 hover:text-red-600"
                >
                  Closed
                </button>
              </>
            ) : (
              <div className="flex items-center gap-3 flex-1">
                <span className="text-gray-400 italic">Closed</span>
                <button
                  onClick={() => update(i, { active: true })}
                  className="ml-auto text-sm text-primary-600 hover:underline"
                >
                  Open this day
                </button>
              </div>
            )}
          </div>
        ))}
      </div>

      <div className="mt-6 flex items-center gap-3">
        <button onClick={copyToAll} className="btn-secondary">Copy first day to all</button>
        <button onClick={save} disabled={saving} className="btn-primary">
          {saving ? "Saving…" : "Save schedule"}
        </button>
        {savedAt && <span className="text-sm text-secondary-600">Saved at {savedAt}</span>}
      </div>
    </div>
  );
}
