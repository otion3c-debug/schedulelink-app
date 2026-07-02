"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { clearTokens } from "@/lib/api";
import AuthGuard from "@/components/AuthGuard";

const NAV = [
  { href: "/dashboard", label: "Overview" },
  { href: "/dashboard/bookings", label: "Bookings" },
  { href: "/dashboard/availability", label: "Availability" },
  { href: "/dashboard/widget", label: "Widget" },
  { href: "/dashboard/settings", label: "Settings" },
  { href: "/dashboard/billing", label: "Billing" },
];

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  return (
    <AuthGuard>
      <div className="min-h-screen flex flex-col">
        <header className="border-b border-gray-100 bg-white sticky top-0 z-30">
          <div className="max-w-6xl mx-auto px-6 h-16 flex items-center justify-between">
            <Link href="/dashboard" className="font-bold text-xl">
              Schedule<span className="text-primary-500">Link</span>
            </Link>
            <button
              onClick={() => { clearTokens(); window.location.href = "/"; }}
              className="text-sm text-gray-600 hover:text-gray-900"
            >Sign out</button>
          </div>
        </header>
        <div className="max-w-6xl w-full mx-auto px-6 py-8 flex-1 grid md:grid-cols-[200px_1fr] gap-8">
          <nav className="space-y-1 text-sm">
            {NAV.map((item) => {
              const active = pathname === item.href;
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  className={`block px-3 py-2 rounded-lg ${
                    active
                      ? "bg-primary-50 text-primary-700 font-medium"
                      : "text-gray-700 hover:bg-gray-50"
                  }`}
                >
                  {item.label}
                </Link>
              );
            })}
          </nav>
          <main>{children}</main>
        </div>
      </div>
    </AuthGuard>
  );
}
