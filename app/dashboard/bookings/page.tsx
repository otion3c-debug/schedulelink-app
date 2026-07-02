"use client";
import useSWR from "swr";
import { useState } from "react";
import { fetcher, api } from "@/lib/api";

export default function BookingsPage() {
  const [status, setStatus] = useState<string>("");
  const url = `/bookings?limit=50${status ? `&status=${status}` : ""}`;
  const { data, mutate } = useSWR<{ bookings: any[]; total: number }>(url, fetcher);

  async function cancel(id: string) {
    if (!confirm("Cancel this booking?")) return;
    try {
      await api(`/bookings/${id}`, {
        method: "DELETE",
        body: JSON.stringify({ cancellation_reason: "Cancelled by host" }),
      });
      mutate();
    } catch (e: any) {
      alert(e.message || "Cancel failed");
    }
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="h2">Bookings</h1>
        <select value={status} onChange={(e) => setStatus(e.target.value)} className="input max-w-xs">
          <option value="">All</option>
          <option value="confirmed">Confirmed</option>
          <option value="cancelled">Cancelled</option>
          <option value="completed">Completed</option>
        </select>
      </div>
      {!data ? (
        <div className="text-gray-500">Loading…</div>
      ) : data.bookings.length === 0 ? (
        <div className="card p-8 text-center text-gray-500">No bookings yet.</div>
      ) : (
        <div className="card divide-y divide-gray-100">
          {data.bookings.map((b) => (
            <div key={b.id} className="p-4 flex items-center justify-between">
              <div>
                <div className="font-medium">{b.attendee_name}</div>
                <div className="text-sm text-gray-500">
                  {b.attendee_email}
                  {b.attendee_phone ? ` · ${b.attendee_phone}` : ""}
                </div>
                {b.notes && <div className="text-sm text-gray-600 mt-1">{b.notes}</div>}
              </div>
              <div className="text-right text-sm text-gray-700">
                <div>{new Date(b.start_time).toLocaleString()}</div>
                <div className="text-gray-500">{b.duration_minutes} min · {b.timezone}</div>
                <div className={`mt-1 text-xs font-medium ${b.status === "cancelled" ? "text-red-600" : "text-secondary-600"}`}>
                  {b.status}
                </div>
                {b.status === "confirmed" && (
                  <button onClick={() => cancel(b.id)} className="text-xs text-red-600 hover:underline mt-1">
                    Cancel
                  </button>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
