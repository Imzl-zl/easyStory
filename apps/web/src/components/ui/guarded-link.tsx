"use client";

import { startTransition } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";

type GuardedLinkProps = {
  children: React.ReactNode;
  className?: string;
  href: string;
  isDirty: boolean;
  onNavigate: (onConfirm: () => void) => void;
};

export function GuardedLink({
  children,
  className,
  href,
  isDirty,
  onNavigate,
}: Readonly<GuardedLinkProps>) {
  const router = useRouter();

  return (
    <Link
      className={className}
      href={href}
      onClick={(event) => {
        if (!isDirty || event.button !== 0 || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) {
          return;
        }
        event.preventDefault();
        onNavigate(() => {
          startTransition(() => {
            router.push(href);
          });
        });
      }}
    >
      {children}
    </Link>
  );
}
