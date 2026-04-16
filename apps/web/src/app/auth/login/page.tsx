import { Suspense } from "react";

import { AuthForm } from "@/features/auth/components/auth-form";

export const dynamic = "force-dynamic";

export default function LoginPage() {
  return (
    <Suspense fallback={<AuthLoading />}>
      <AuthForm mode="login" />
    </Suspense>
  );
}

function AuthLoading() {
  return (
    <main className="flex min-h-screen items-center justify-center p-6">
      <div className="panel-shell max-w-lg p-8">
        <p className="text-sm uppercase tracking-[0.28em] text-accent-primary">easyStory</p>
        <h1 className="mt-3 font-serif text-3xl font-semibold">正在加载</h1>
        <p className="mt-3 text-sm leading-6 text-text-secondary">请稍候...</p>
      </div>
    </main>
  );
}
