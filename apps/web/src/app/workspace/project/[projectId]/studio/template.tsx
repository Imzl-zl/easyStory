"use client";

import { useEffect, useState } from "react";

export default function StudioTemplate({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    queueMicrotask(() => setMounted(true));
  }, []);

  return (
    <div
      className="h-full"
      style={{
        opacity: mounted ? 1 : 0,
        transform: mounted ? "scale(1)" : "scale(0.985)",
        filter: mounted ? "blur(0px)" : "blur(6px)",
        transition:
          "opacity 0.55s cubic-bezier(0.22, 1, 0.36, 1), transform 0.55s cubic-bezier(0.22, 1, 0.36, 1), filter 0.45s cubic-bezier(0.22, 1, 0.36, 1)",
        willChange: "opacity, transform, filter",
      }}
    >
      {children}
    </div>
  );
}
