"use client";

import { startTransition, useCallback, useEffect, useRef, useState } from "react";
import type { AppRouterInstance } from "next/dist/shared/lib/app-router-context.shared-runtime";

type UseUnsavedChangesGuardOptions = {
  currentUrl: string;
  isDirty: boolean;
  router: AppRouterInstance;
};

export function useUnsavedChangesGuard({
  currentUrl,
  isDirty,
  router,
}: Readonly<UseUnsavedChangesGuardOptions>) {
  const [isConfirmOpen, setConfirmOpen] = useState(false);
  const pendingNavigationRef = useRef<(() => void) | null>(null);
  const cancelNavigationRef = useRef<(() => void) | null>(null);
  const stableUrlRef = useRef(currentUrl);

  useEffect(() => {
    if (!isDirty) {
      stableUrlRef.current = currentUrl;
    }
  }, [currentUrl, isDirty]);

  const openNavigationConfirm = useCallback((onConfirm: () => void, onCancel?: () => void) => {
    pendingNavigationRef.current = onConfirm;
    cancelNavigationRef.current = onCancel ?? null;
    setConfirmOpen(true);
  }, []);

  const attemptNavigation = useCallback(
    (onConfirm: () => void, onCancel?: () => void) => {
      if (!isDirty) {
        onConfirm();
        return;
      }
      openNavigationConfirm(onConfirm, onCancel);
    },
    [isDirty, openNavigationConfirm],
  );

  useEffect(() => {
    const handleBeforeUnload = (event: BeforeUnloadEvent) => {
      if (!isDirty) {
        return;
      }
      event.preventDefault();
      event.returnValue = "";
    };
    window.addEventListener("beforeunload", handleBeforeUnload);
    return () => window.removeEventListener("beforeunload", handleBeforeUnload);
  }, [isDirty]);

  useEffect(() => {
    const handlePopState = () => {
      if (!isDirty) {
        return;
      }
      const nextUrl = `${window.location.pathname}${window.location.search}`;
      if (nextUrl === stableUrlRef.current) {
        return;
      }
      window.history.pushState(null, "", stableUrlRef.current);
      openNavigationConfirm(() => {
        startTransition(() => {
          router.push(nextUrl);
        });
      });
    };
    window.addEventListener("popstate", handlePopState);
    return () => window.removeEventListener("popstate", handlePopState);
  }, [isDirty, openNavigationConfirm, router]);

  return {
    attemptNavigation,
    handleDialogClose: () => {
      const cancelAction = cancelNavigationRef.current;
      pendingNavigationRef.current = null;
      cancelNavigationRef.current = null;
      setConfirmOpen(false);
      cancelAction?.();
    },
    handleDialogConfirm: () => {
      const pendingAction = pendingNavigationRef.current;
      pendingNavigationRef.current = null;
      cancelNavigationRef.current = null;
      setConfirmOpen(false);
      pendingAction?.();
    },
    isConfirmOpen,
  };
}
