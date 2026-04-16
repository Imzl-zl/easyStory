"use client";

import { usePathname, useRouter } from "next/navigation";
import { useEffect } from "react";

import { useAuthStore } from "@/lib/stores/auth-store";

export function AuthGuard({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  const router = useRouter();
  const pathname = usePathname();
  const hasHydrated = useAuthStore((state) => state.hasHydrated);
  const token = useAuthStore((state) => state.token);

  useEffect(() => {
    if (hasHydrated && !token) {
      router.replace(`/auth/login?next=${encodeURIComponent(pathname)}`);
    }
  }, [hasHydrated, pathname, router, token]);

  if (!hasHydrated || !token) {
    return (
      <div className="flex min-h-screen items-center justify-center p-6">
        <div className="panel-shell max-w-lg p-8">
          <p className="text-sm uppercase tracking-[0.28em] text-accent-primary">登录状态</p>
          <h1 className="mt-3 font-serif text-3xl font-semibold">正在确认你的登录状态</h1>
          <p className="mt-3 text-sm leading-6 text-text-secondary">
            如果当前没有可用会话，会自动回到登录页。
          </p>
        </div>
      </div>
    );
  }

  return <>{children}</>;
}
