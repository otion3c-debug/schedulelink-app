"use client";
import { TIERS, Tier } from "./PricingCards";
import Link from "next/link";

export default function PricingTierBanner({
  currentTier,
  bookingsUsed,
  bookingLimit,
}: {
  currentTier: Tier;
  bookingsUsed: number;
  bookingLimit: number;
}) {
  return (
    <div className="card p-4 mt-12 grid md:grid-cols-3 gap-4 text-sm">
      {TIERS.map((t) => {
        const isCurrent = t.id === currentTier;
        return (
          <div key={t.id} className={`p-3 rounded-lg ${isCurrent ? "bg-primary-50 ring-1 ring-primary-200" : ""}`}>
            <div className="flex items-baseline justify-between">
              <span className="font-semibold text-gray-900">{t.name}</span>
              {isCurrent && <span className="text-xs text-primary-600 font-medium">Current</span>}
            </div>
            <div className="mt-1 text-gray-600">{t.price}{t.cadence}</div>
            {isCurrent && t.id === "free" && (
              <div className="mt-1 text-xs text-gray-500">{bookingsUsed}/{bookingLimit} bookings used</div>
            )}
            {!isCurrent && (
              <Link href="/dashboard/billing" className="text-primary-600 text-xs font-medium mt-1 inline-block">
                Upgrade →
              </Link>
            )}
          </div>
        );
      })}
    </div>
  );
}
