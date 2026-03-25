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
          <p className="text-sm uppercase tracking-[0.28em] text-[var(--accent-ink)]">认证</p>
          <h1 className="mt-3 font-serif text-3xl font-semibold">正在校验工作台访问权限</h1>
          <p className="mt-3 text-sm leading-6 text-[var(--text-secondary)]">
            当前页面需要 bearer token。若本地没有有效会话，将自动返回登录页。
          </p>
        </div>
      </div>
    );
  }

  return <>{children}</>;
}
