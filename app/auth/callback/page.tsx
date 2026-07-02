"use client";
import { Suspense, useEffect } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import { setTokens } from "@/lib/api";

function CallbackInner() {
  const params = useSearchParams();
  const router = useRouter();

  useEffect(() => {
    const token = params.get("token");
    const refresh = params.get("refresh") || undefined;
    if (token) {
      setTokens(token, refresh);
      router.replace("/dashboard");
    } else {
      router.replace("/login?error=missing_token");
    }
  }, [params, router]);

  return null;
}

export default function AuthCallback() {
  return (
    <div className="min-h-screen flex items-center justify-center text-gray-500">
      <Suspense fallback={<span>Signing you in…</span>}>
        <CallbackInner />
      </Suspense>
    </div>
  );
}
