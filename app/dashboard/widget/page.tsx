"use client";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";

type WidgetSettings = {
  primary_color: string;
  secondary_color: string;
  font_family: string;
  show_branding: boolean;
  custom_header_text: string | null;
  custom_footer_text: string | null;
  embed_code: string;
};

type EmbedInfo = {
  embed_code: string;
  iframe_code: string;
  instructions: string;
};

export default function WidgetPage() {
  const [settings, setSettings] = useState<WidgetSettings | null>(null);
  const [embed, setEmbed] = useState<EmbedInfo | null>(null);
  const [saving, setSaving] = useState(false);
  const [savedAt, setSavedAt] = useState<string | null>(null);
  const [me, setMe] = useState<{ booking_slug: string } | null>(null);

  useEffect(() => {
    (async () => {
      const [s, e, u] = await Promise.all([
        api<WidgetSettings>("/widget/settings"),
        api<EmbedInfo>("/widget/embed-code"),
        api<{ booking_slug: string }>("/users/me"),
      ]);
      setSettings(s);
      setEmbed(e);
      setMe(u);
    })();
  }, []);

  async function save() {
    if (!settings) return;
    setSaving(true);
    try {
      const next = await api<WidgetSettings>("/widget/settings", {
        method: "PUT",
        body: JSON.stringify({
          primary_color: settings.primary_color,
          secondary_color: settings.secondary_color,
          show_branding: settings.show_branding,
          custom_header_text: settings.custom_header_text,
          custom_footer_text: settings.custom_footer_text,
        }),
      });
      setSettings(next);
      setSavedAt(new Date().toLocaleTimeString());
    } catch (e: any) {
      alert(e.message || "Save failed");
    } finally {
      setSaving(false);
    }
  }

  if (!settings || !embed || !me) return <div className="text-gray-500">Loading…</div>;

  const previewUrl = typeof window !== "undefined"
    ? `${window.location.origin}/embed/${me.booking_slug}`
    : "";

  return (
    <div className="grid lg:grid-cols-2 gap-8">
      <div>
        <h1 className="h2">Widget</h1>
        <p className="muted mt-1">Customize how your booking widget looks.</p>

        <div className="card p-4 mt-6 space-y-4">
          <div>
            <label className="label">Primary color</label>
            <input
              type="color"
              value={settings.primary_color}
              onChange={(e) => setSettings({ ...settings, primary_color: e.target.value })}
              className="h-10 w-20 rounded border border-gray-200"
            />
            <span className="ml-3 text-sm text-gray-600">{settings.primary_color}</span>
          </div>
          <div>
            <label className="label">Header text (optional)</label>
            <input
              type="text"
              className="input"
              placeholder="Book a 30-min consultation"
              value={settings.custom_header_text || ""}
              onChange={(e) => setSettings({ ...settings, custom_header_text: e.target.value })}
            />
          </div>
          <div>
            <label className="label">Footer text (optional)</label>
            <input
              type="text"
              className="input"
              placeholder="Questions? Email us at hello@example.com"
              value={settings.custom_footer_text || ""}
              onChange={(e) => setSettings({ ...settings, custom_footer_text: e.target.value })}
            />
          </div>
          <label className="flex items-center gap-2 text-sm">
            <input
              type="checkbox"
              checked={settings.show_branding}
              onChange={(e) => setSettings({ ...settings, show_branding: e.target.checked })}
            />
            Show &quot;Powered by ScheduleLink&quot; (Pro/Pro+ can disable)
          </label>
          <button onClick={save} disabled={saving} className="btn-primary">
            {saving ? "Saving…" : "Save widget"}
          </button>
          {savedAt && <span className="ml-3 text-sm text-secondary-600">Saved at {savedAt}</span>}
        </div>

        <div className="card p-4 mt-6">
          <h3 className="font-semibold">Embed code</h3>
          <p className="muted text-sm">{embed.instructions}</p>
          <div className="mt-3">
            <label className="label">Script tag (recommended)</label>
            <textarea
              readOnly
              value={embed.embed_code}
              className="input h-20 font-mono text-xs"
            />
            <button
              onClick={() => navigator.clipboard.writeText(embed.embed_code)}
              className="btn-secondary text-sm mt-2"
            >Copy</button>
          </div>
          <div className="mt-3">
            <label className="label">Iframe</label>
            <textarea
              readOnly
              value={embed.iframe_code}
              className="input h-20 font-mono text-xs"
            />
            <button
              onClick={() => navigator.clipboard.writeText(embed.iframe_code)}
              className="btn-secondary text-sm mt-2"
            >Copy</button>
          </div>
        </div>
      </div>

      <div>
        <h2 className="font-semibold">Preview</h2>
        <p className="muted text-sm mt-1">Live preview of your booking widget.</p>
        <div className="card mt-3 overflow-hidden">
          <iframe
            src={previewUrl}
            className="w-full"
            style={{ height: 700, border: 0 }}
            title="Widget preview"
          />
        </div>
      </div>
    </div>
  );
}
