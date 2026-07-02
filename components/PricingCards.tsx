"use client";
import { useState } from "react";
import { api } from "@/lib/api";

export type Tier = "free" | "pro" | "pro_plus";

export const TIERS = [
  {
    id: "free" as Tier,
    name: "Free",
    price: "$0",
    cadence: "/month",
    features: [
      "5 bookings per month",
      "Google or Microsoft Calendar",
      "Embeddable widget",
      "Email confirmations",
    ],
  },
  {
    id: "pro" as Tier,
    name: "Pro",
    price: "$5",
    cadence: "/month",
    highlighted: true,
    features: [
      "Unlimited bookings",
      "Google + Microsoft Calendar",
      "Custom branding",
      "Remove ScheduleLink badge",
      "Priority support",
    ],
  },
  {
    id: "pro_plus" as Tier,
    name: "Pro+",
    price: "$7",
    cadence: "/month",
    features: [
      "Everything in Pro",
      "Email reminders to attendees",
      "Custom booking durations",
      "Buffer times between bookings",
    ],
  },
];

export default function PricingCards({
  currentTier,
  bookingsUsed,
  bookingLimit,
  inDashboard = false,
}: {
  currentTier?: Tier;
  bookingsUsed?: number;
  bookingLimit?: number;
  inDashboard?: boolean;
}) {
  const [loading, setLoading] = useState<Tier | null>(null);

  async function startCheckout(tier: Tier) {
    setLoading(tier);
    try {
      const data = await api<{ checkout_url: string }>("/subscription/checkout", {
        method: "POST",
        body: JSON.stringify({ tier }),
      });
      window.location.href = data.checkout_url;
    } catch (e: any) {
      alert(e.message || "Checkout failed. Please contact support.");
      setLoading(null);
    }
  }

  return (
    <div className="grid md:grid-cols-3 gap-6">
      {TIERS.map((t) => {
        const isCurrent = currentTier === t.id;
        return (
          <div
            key={t.id}
            className={`card p-6 flex flex-col ${
              t.highlighted ? "ring-2 ring-primary-500" : ""
            }`}
          >
            <div className="flex items-baseline justify-between">
              <h3 className="text-xl font-bold text-gray-900">{t.name}</h3>
              {isCurrent && (
                <span className="text-xs font-semibold text-primary-600 bg-primary-50 px-2 py-1 rounded-full">
                  Current
                </span>
              )}
            </div>
            <div className="mt-4">
              <span className="text-4xl font-bold text-gray-900">{t.price}</span>
              <span className="text-gray-500">{t.cadence}</span>
            </div>
            {isCurrent && t.id === "free" && bookingsUsed != null && bookingLimit != null && (
              <div className="mt-2 text-sm text-gray-600">
                {bookingsUsed}/{bookingLimit} bookings used
              </div>
            )}
            <ul className="mt-6 space-y-2 text-sm flex-1">
              {t.features.map((f) => (
                <li key={f} className="flex items-start gap-2">
                  <span className="text-secondary-500 mt-0.5">✓</span>
                  <span>{f}</span>
                </li>
              ))}
            </ul>
            <div className="mt-6">
              {t.id === "free" ? (
                <button
                  className="btn-secondary w-full"
                  disabled
                >
                  {isCurrent ? "Current plan" : "Free forever"}
                </button>
              ) : isCurrent ? (
                <button className="btn-secondary w-full" disabled>
                  Current plan
                </button>
              ) : inDashboard ? (
                <button
                  className="btn-primary w-full"
                  onClick={() => startCheckout(t.id)}
                  disabled={loading !== null}
                >
                  {loading === t.id ? "Loading…" : "Upgrade"}
                </button>
              ) : (
                <a href="/login" className="btn-primary w-full">
                  Get started
                </a>
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
}
