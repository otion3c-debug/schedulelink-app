"use client";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";

type User = {
  email: string;
  full_name: string | null;
  timezone: string;
  booking_slug: string;
};

type Calendar = {
  id: string;
  provider: string;
  provider_account_email: string;
  is_primary: boolean;
  is_active: boolean;
  last_sync_at: string | null;
};

const TIMEZONES = [
  "America/New_York","America/Chicago","America/Denver","America/Los_Angeles",
  "Europe/London","Europe/Berlin","Europe/Paris","Asia/Tokyo","Australia/Sydney","UTC"
];

export default function SettingsPage() {
  const [user, setUser] = useState<User | null>(null);
  const [calendars, setCalendars] = useState<Calendar[]>([]);
  const [saving, setSaving] = useState(false);
  const [savedAt, setSavedAt] = useState<string | null>(null);

  async function refresh() {
    const [u, c] = await Promise.all([
      api<User>("/users/me"),
      api<{ calendars: Calendar[] }>("/calendars"),
    ]);
    setUser(u);
    setCalendars(c.calendars);
  }

  useEffect(() => { refresh(); }, []);

  async function saveProfile() {
    if (!user) return;
    setSaving(true);
    try {
      const next = await api<User>("/users/me", {
        method: "PATCH",
        body: JSON.stringify({
          full_name: user.full_name,
          timezone: user.timezone,
          booking_slug: user.booking_slug,
        }),
      });
      setUser(next);
      setSavedAt(new Date().toLocaleTimeString());
    } catch (e: any) {
      alert(e.message || "Save failed");
    } finally {
      setSaving(false);
    }
  }

  async function connectGoogle() {
    try {
      const data = await api<{ authorization_url: string }>("/calendars/connect/google", {
        method: "POST",
      });
      window.location.href = data.authorization_url;
    } catch (e: any) {
      alert(e.message || "Could not start connection");
    }
  }

  async function connectMicrosoft() {
    try {
      const data = await api<{ authorization_url: string }>("/calendars/connect/microsoft", {
        method: "POST",
      });
      window.location.href = data.authorization_url;
    } catch (e: any) {
      alert(e.message || "Could not start connection");
    }
  }

  async function setPrimary(id: string) {
    try {
      await api(`/calendars/${id}/set-primary`, { method: "POST" });
      refresh();
    } catch (e: any) {
      alert(e.message || "Failed");
    }
  }

  async function disconnect(id: string) {
    if (!confirm("Disconnect this calendar?")) return;
    try {
      await api(`/calendars/${id}`, { method: "DELETE" });
      refresh();
    } catch (e: any) {
      alert(e.message || "Failed");
    }
  }

  if (!user) return <div className="text-gray-500">Loading…</div>;

  return (
    <div className="space-y-10">
      <section>
        <h1 className="h2">Settings</h1>
      </section>

      <section className="card p-4">
        <h2 className="font-semibold text-lg">Profile</h2>
        <div className="grid md:grid-cols-2 gap-4 mt-3">
          <div>
            <label className="label">Email</label>
            <input className="input bg-gray-50" value={user.email} disabled />
          </div>
          <div>
            <label className="label">Full name</label>
            <input
              className="input"
              value={user.full_name || ""}
              onChange={(e) => setUser({ ...user, full_name: e.target.value })}
            />
          </div>
          <div>
            <label className="label">Timezone</label>
            <select
              className="input"
              value={user.timezone}
              onChange={(e) => setUser({ ...user, timezone: e.target.value })}
            >
              {TIMEZONES.map((tz) => (
                <option key={tz}>{tz}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="label">Booking slug</label>
            <input
              className="input"
              value={user.booking_slug}
              onChange={(e) => setUser({ ...user, booking_slug: e.target.value })}
            />
            <p className="text-xs text-gray-500 mt-1">Your link: /{user.booking_slug}</p>
          </div>
        </div>
        <div className="mt-4">
          <button onClick={saveProfile} disabled={saving} className="btn-primary">
            {saving ? "Saving…" : "Save profile"}
          </button>
          {savedAt && <span className="ml-3 text-sm text-secondary-600">Saved at {savedAt}</span>}
        </div>
      </section>

      <section className="card p-4">
          <div className="flex items-center justify-between gap-2">
            <h2 className="font-semibold text-lg">Calendars</h2>
            <div className="flex gap-2">
              <button onClick={connectGoogle} className="btn-primary text-sm">+ Connect Google</button>
              <button
                onClick={connectMicrosoft}
                className="inline-flex items-center justify-center px-4 py-2 rounded-lg font-medium text-sm bg-white border border-gray-300 text-gray-800 hover:bg-gray-50 transition-colors"
              >
                + Connect Outlook
              </button>
            </div>
          </div>
        {calendars.length === 0 ? (
          <p className="muted mt-3 text-sm">No calendars connected. Connect one to start taking bookings that write to your calendar.</p>
        ) : (
          <div className="mt-3 divide-y divide-gray-100">
            {calendars.map((c) => (
              <div key={c.id} className="py-3 flex items-center justify-between">
                <div>
                  <div className="font-medium capitalize">{c.provider} · {c.provider_account_email}</div>
                  <div className="text-xs text-gray-500">
                    {c.is_primary ? "Primary" : "Secondary"} · {c.is_active ? "active" : "inactive"}
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  {!c.is_primary && (
                    <button onClick={() => setPrimary(c.id)} className="btn-secondary text-sm">Make primary</button>
                  )}
                  <button onClick={() => disconnect(c.id)} className="text-sm text-red-600 hover:underline">
                    Disconnect
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </section>
    </div>
  );
}
