"use client";
import useSWR from "swr";
import { fetcher, api } from "@/lib/api";
import PricingCards, { Tier } from "@/components/PricingCards";

type Subscription = {
  tier: Tier;
  status: string;
  bookings_used_this_month: number;
  booking_limit: number;
  billing_cycle_start: string | null;
  stripe_customer_id: string | null;
};

export default function BillingPage() {
  const { data: sub } = useSWR<Subscription>("/subscription", fetcher);

  async function openPortal() {
    try {
      const data = await api<{ portal_url: string }>("/subscription/portal", { method: "POST" });
      window.location.href = data.portal_url;
    } catch (e: any) {
      alert(e.message || "Portal unavailable");
    }
  }

  if (!sub) return <div className="text-gray-500">Loading…</div>;

  return (
    <div>
      <h1 className="h2">Billing</h1>
      <div className="card p-4 mt-6">
        <div className="text-sm text-gray-500">Current plan</div>
        <div className="text-2xl font-bold capitalize mt-1">{sub.tier.replace("_", " ")}</div>
        <div className="text-sm text-gray-600 mt-1">
          Status: {sub.status}
          {sub.tier === "free" && (
            <> · {sub.bookings_used_this_month}/{sub.booking_limit} bookings used this month</>
          )}
        </div>
        {sub.stripe_customer_id && (
          <button onClick={openPortal} className="btn-secondary mt-3 text-sm">
            Manage subscription in Stripe
          </button>
        )}
      </div>

      <div className="mt-10">
        <h2 className="text-xl font-semibold">Plans</h2>
        <div className="mt-4">
          <PricingCards
            currentTier={sub.tier}
            bookingsUsed={sub.bookings_used_this_month}
            bookingLimit={sub.booking_limit}
            inDashboard
          />
        </div>
      </div>
    </div>
  );
}
