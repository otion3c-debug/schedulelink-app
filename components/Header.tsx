"use client";
import Link from "next/link";
import { useEffect, useState } from "react";
import { getToken, clearTokens } from "@/lib/api";

export default function Header() {
  const [authed, setAuthed] = useState(false);
  useEffect(() => setAuthed(!!getToken()), []);
  return (
    <header className="border-b border-gray-100 bg-white/80 backdrop-blur sticky top-0 z-30">
      <div className="max-w-6xl mx-auto px-6 h-16 flex items-center justify-between">
        <Link href="/" className="font-bold text-xl tracking-tight">
          Schedule<span className="text-primary-500">Link</span>
        </Link>
        <nav className="hidden md:flex items-center gap-6 text-sm text-gray-600">
          <Link href="/#features" className="hover:text-gray-900">Features</Link>
          <Link href="/pricing" className="hover:text-gray-900">Pricing</Link>
          <Link href="/privacy" className="hover:text-gray-900">Privacy</Link>
          <Link href="/terms" className="hover:text-gray-900">Terms</Link>
        </nav>
        <div className="flex items-center gap-2">
          {authed ? (
            <>
              <Link href="/dashboard" className="btn-secondary">Dashboard</Link>
              <button
                onClick={() => { clearTokens(); window.location.href = "/"; }}
                className="btn-ghost text-sm"
              >Sign out</button>
            </>
          ) : (
            <>
              <Link href="/login" className="btn-secondary text-sm">Sign in</Link>
              <Link href="/login" className="btn-primary text-sm">Get started</Link>
            </>
          )}
        </div>
      </div>
    </header>
  );
}
