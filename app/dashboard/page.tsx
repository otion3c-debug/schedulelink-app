"use client";
import useSWR from "swr";
import Link from "next/link";
import { fetcher, API_URL } from "@/lib/api";
import PricingTierBanner from "@/components/PricingTierBanner";
import type { Tier } from "@/components/PricingCards";

type User = {
  id: string;
  email: string;
  full_name: string | null;
  booking_slug: string;
  subscription_tier: Tier;
  bookings_used_this_month: number;
  booking_limit: number;
};

type BookingsResp = { bookings: any[]; total: number };

export default function DashboardHome() {
  const { data: user } = useSWR<User>("/users/me", fetcher);
  const { data: bookings } = useSWR<BookingsResp>("/bookings?status=confirmed&limit=5", fetcher);

  if (!user) return <div className="text-gray-500">Loading…</div>;

  const bookingUrl =
    typeof window !== "undefined"
      ? `${window.location.origin}/${user.booking_slug}`
      : `/${user.booking_slug}`;

  return (
    <div>
      <h1 className="h2">Welcome{user.full_name ? `, ${user.full_name.split(" ")[0]}` : ""}.</h1>
      <p className="muted mt-1">Your booking page is live at:</p>
      <div className="card p-4 mt-3 flex items-center justify-between">
        <code className="text-primary-600 text-sm">{bookingUrl}</code>
        <button
          onClick={() => navigator.clipboard.writeText(bookingUrl)}
          className="btn-secondary text-sm"
        >Copy link</button>
      </div>

      <div className="grid md:grid-cols-3 gap-4 mt-8">
        <div className="card p-4">
          <div className="muted text-xs uppercase tracking-wide">Bookings this month</div>
          <div className="text-3xl font-bold mt-1">
            {user.bookings_used_this_month}
            {user.subscription_tier === "free" ? `/${user.booking_limit}` : ""}
          </div>
        </div>
        <div className="card p-4">
          <div className="muted text-xs uppercase tracking-wide">Plan</div>
          <div className="text-3xl font-bold mt-1 capitalize">{user.subscription_tier.replace("_", " ")}</div>
        </div>
        <div className="card p-4">
          <div className="muted text-xs uppercase tracking-wide">Booking link</div>
          <div className="text-base font-mono mt-2 truncate">/{user.booking_slug}</div>
        </div>
      </div>

      <div className="mt-10">
        <h2 className="text-xl font-semibold mb-3">Upcoming bookings</h2>
        {bookings && bookings.bookings.length > 0 ? (
          <div className="card divide-y divide-gray-100">
            {bookings.bookings.slice(0, 5).map((b) => (
              <div key={b.id} className="p-4 flex items-center justify-between">
                <div>
                  <div className="font-medium">{b.attendee_name}</div>
                  <div className="text-sm text-gray-500">{b.attendee_email}</div>
                </div>
                <div className="text-right text-sm text-gray-700">
                  <div>{new Date(b.start_time).toLocaleString()}</div>
                  <div className="text-gray-500">{b.duration_minutes} min</div>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="card p-6 text-center text-gray-500">
            No upcoming bookings yet. Share your <Link href="/dashboard/widget" className="text-primary-600">booking link</Link> or{" "}
            <Link href="/dashboard/widget" className="text-primary-600">embed the widget</Link>.
          </div>
        )}
      </div>

      <PricingTierBanner
        currentTier={user.subscription_tier}
        bookingsUsed={user.bookings_used_this_month}
        bookingLimit={user.booking_limit}
      />
    </div>
  );
}
