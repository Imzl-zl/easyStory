import { AuthForm } from "@/features/auth/components/auth-form";

export const dynamic = "force-dynamic";

export default function RegisterPage() {
  return <AuthForm mode="register" />;
}
