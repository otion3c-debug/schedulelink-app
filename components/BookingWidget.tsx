"use client";
import { useEffect, useMemo, useState } from "react";
import { API_URL } from "@/lib/api";

type Slot = {
  start_time: string;
  end_time: string;
  date: string;
  day_name: string;
};

type UserInfo = {
  full_name: string;
  booking_slug: string;
  timezone: string;
  widget?: {
    primary_color: string;
    secondary_color: string;
    show_branding: boolean;
    custom_header_text: string | null;
    custom_footer_text: string | null;
  } | null;
};

function todayISO(offsetDays = 0) {
  const d = new Date();
  d.setDate(d.getDate() + offsetDays);
  return d.toISOString().slice(0, 10);
}

function fmtTime(iso: string) {
  const d = new Date(iso);
  return d.toLocaleTimeString([], { hour: "numeric", minute: "2-digit" });
}

function fmtDate(iso: string) {
  const [y, m, day] = iso.split("-").map(Number);
  const d = new Date(y, m - 1, day);
  return d.toLocaleDateString([], { weekday: "short", month: "short", day: "numeric" });
}

export default function BookingWidget({ slug }: { slug: string }) {
  const [user, setUser] = useState<UserInfo | null>(null);
  const [slots, setSlots] = useState<Slot[]>([]);
  const [loading, setLoading] = useState(true);
  const [duration, setDuration] = useState(30);
  const [selectedDate, setSelectedDate] = useState<string | null>(null);
  const [selectedSlot, setSelectedSlot] = useState<Slot | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [done, setDone] = useState<{ id: string } | null>(null);
  const [err, setErr] = useState<string | null>(null);

  // Form fields
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [phone, setPhone] = useState("");
  const [notes, setNotes] = useState("");

  useEffect(() => {
    (async () => {
      setLoading(true);
      try {
        const userRes = await fetch(`${API_URL}/public/users/${slug}`);
        if (!userRes.ok) throw new Error("User not found");
        const u = (await userRes.json()) as UserInfo;
        setUser(u);

        const start = todayISO();
        const end = todayISO(13);
        const res = await fetch(
          `${API_URL}/public/availability/${slug}?start_date=${start}&end_date=${end}&duration_minutes=${duration}`
        );
        if (!res.ok) throw new Error("Could not load availability");
        const data = await res.json();
        setSlots(data.available_slots);
      } catch (e: any) {
        setErr(e.message || "Failed to load");
      } finally {
        setLoading(false);
      }
    })();
  }, [slug, duration]);

  const dates = useMemo(() => {
    const set = new Set<string>();
    slots.forEach((s) => set.add(s.date));
    return Array.from(set).sort();
  }, [slots]);

  const slotsForDate = useMemo(() => {
    if (!selectedDate) return [];
    return slots.filter((s) => s.date === selectedDate);
  }, [slots, selectedDate]);

  const primary = user?.widget?.primary_color || "#3B82F6";
  const showBranding = user?.widget?.show_branding ?? true;

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (!selectedSlot || !user) return;
    setSubmitting(true);
    setErr(null);
    try {
      const tz = Intl.DateTimeFormat().resolvedOptions().timeZone || user.timezone;
      const res = await fetch(`${API_URL}/bookings`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          user_slug: user.booking_slug,
          attendee_name: name,
          attendee_email: email,
          attendee_phone: phone || null,
          start_time: selectedSlot.start_time,
          timezone: tz,
          duration_minutes: duration,
          notes: notes || null,
        }),
      });
      const body = await res.json();
      if (!res.ok) {
        const msg = body?.detail?.error?.message || body?.detail || "Booking failed";
        throw new Error(typeof msg === "string" ? msg : "Booking failed");
      }
      setDone({ id: body.id });
    } catch (e: any) {
      setErr(e.message || "Booking failed");
    } finally {
      setSubmitting(false);
    }
  }

  if (loading) {
    return <div className="p-8 text-center text-gray-500">Loading…</div>;
  }
  if (err && !user) {
    return <div className="p-8 text-center text-red-600">{err}</div>;
  }
  if (!user) return null;

  if (done) {
    return (
      <div className="p-8 text-center">
        <div className="text-3xl">✓</div>
        <h2 className="text-xl font-semibold mt-2" style={{ color: primary }}>Booking confirmed!</h2>
        <p className="text-sm text-gray-600 mt-2">
          We sent a confirmation to {email}.
        </p>
        {showBranding && (
          <div className="mt-8 text-xs text-gray-400">
            Powered by <a href="https://schedulelink.tech" className="underline">ScheduleLink</a>
          </div>
        )}
      </div>
    );
  }

  return (
    <div className="schedulelink-widget" style={{ fontFamily: "Inter, sans-serif" }}>
      <div className="text-center mb-6">
        <h2 className="text-2xl font-bold text-gray-900">
          {user.widget?.custom_header_text || `Book with ${user.full_name}`}
        </h2>
        <p className="text-sm text-gray-500 mt-1">Choose a duration and time that works for you.</p>
      </div>

      <div className="flex items-center justify-center gap-2 mb-4 text-sm">
        {[15, 30, 45, 60].map((d) => (
          <button
            key={d}
            onClick={() => { setDuration(d); setSelectedDate(null); setSelectedSlot(null); }}
            className={`px-3 py-1 rounded-full border ${
              duration === d ? "text-white" : "border-gray-200 text-gray-700 hover:bg-gray-50"
            }`}
            style={duration === d ? { background: primary, borderColor: primary } : undefined}
          >
            {d} min
          </button>
        ))}
      </div>

      {!selectedSlot ? (
        <div className="grid md:grid-cols-2 gap-4">
          <div>
            <div className="font-medium text-sm mb-2">Select a date</div>
            <div className="space-y-1 max-h-72 overflow-auto pr-1">
              {dates.length === 0 ? (
                <div className="text-sm text-gray-500">No available dates in the next 2 weeks.</div>
              ) : (
                dates.map((d) => (
                  <button
                    key={d}
                    onClick={() => setSelectedDate(d)}
                    className={`w-full text-left px-3 py-2 rounded-lg border ${
                      selectedDate === d ? "text-white" : "border-gray-200 hover:bg-gray-50"
                    }`}
                    style={selectedDate === d ? { background: primary, borderColor: primary } : undefined}
                  >
                    {fmtDate(d)}
                  </button>
                ))
              )}
            </div>
          </div>
          <div>
            <div className="font-medium text-sm mb-2">Available times</div>
            {!selectedDate ? (
              <div className="text-sm text-gray-500">Pick a date first.</div>
            ) : (
              <div className="grid grid-cols-2 gap-2 max-h-72 overflow-auto pr-1">
                {slotsForDate.map((s) => (
                  <button
                    key={s.start_time}
                    onClick={() => setSelectedSlot(s)}
                    className="px-3 py-2 rounded-lg border border-gray-200 hover:bg-gray-50 text-sm"
                  >
                    {fmtTime(s.start_time)}
                  </button>
                ))}
              </div>
            )}
          </div>
        </div>
      ) : (
        <form onSubmit={submit} className="space-y-3 max-w-md mx-auto">
          <div className="text-sm text-center text-gray-600">
            <span className="font-medium" style={{ color: primary }}>
              {fmtDate(selectedSlot.date)} · {fmtTime(selectedSlot.start_time)}
            </span>
            {" · "}
            <button
              type="button"
              onClick={() => setSelectedSlot(null)}
              className="text-gray-500 underline"
            >Change</button>
          </div>
          <div>
            <label className="label">Your name</label>
            <input className="input" required value={name} onChange={(e) => setName(e.target.value)} />
          </div>
          <div>
            <label className="label">Email</label>
            <input className="input" type="email" required value={email} onChange={(e) => setEmail(e.target.value)} />
          </div>
          <div>
            <label className="label">Phone (optional)</label>
            <input className="input" value={phone} onChange={(e) => setPhone(e.target.value)} />
          </div>
          <div>
            <label className="label">Notes (optional)</label>
            <textarea className="input h-20" value={notes} onChange={(e) => setNotes(e.target.value)} />
          </div>
          {err && <div className="text-sm text-red-600">{err}</div>}
          <button
            type="submit"
            disabled={submitting}
            className="w-full px-4 py-2 rounded-lg text-white font-medium"
            style={{ background: primary }}
          >
            {submitting ? "Booking…" : "Book appointment"}
          </button>
        </form>
      )}

      {(user.widget?.custom_footer_text || showBranding) && (
        <div className="mt-8 pt-6 border-t border-gray-100 text-center text-xs text-gray-500">
          {user.widget?.custom_footer_text}
          {showBranding && (
            <div className="mt-2 text-gray-400">
              Powered by{" "}
              <a href="https://schedulelink.tech" className="underline">ScheduleLink</a>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
