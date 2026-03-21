import { AuthForm } from "@/features/auth/components/auth-form";

export const dynamic = "force-dynamic";

export default function LoginPage() {
  return <AuthForm mode="login" />;
}
