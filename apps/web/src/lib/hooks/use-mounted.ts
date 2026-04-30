"use client";

import { useEffect, useRef, useState } from "react";

/**
 * Waits until after the first paint to set mounted=true.
 * Use for entrance animations that should not flash on hydration.
 */
export function useMounted() {
  const [mounted, setMounted] = useState(false);
  const didMount = useRef(false);

  useEffect(() => {
    if (!didMount.current) {
      didMount.current = true;
      queueMicrotask(() => setMounted(true));
    }
  }, []);

  return mounted;
}
