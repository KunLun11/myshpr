"use client";

import { useEffect } from "react";

import { refreshSession } from "@/lib/auth-client";

const REFRESH_INTERVAL_MS = 10 * 60 * 1000;

/**
 * Keeps the short-lived access cookie fresh while the tab is open.
 * Refresh tokens rotate, so calls are serialized in `refreshSession`.
 */
export function SessionKeeper() {
  useEffect(() => {
    let lastRefresh = Date.now();

    const refresh = () => {
      lastRefresh = Date.now();
      void refreshSession();
    };

    const onVisibilityChange = () => {
      if (document.visibilityState === "visible" && Date.now() - lastRefresh > REFRESH_INTERVAL_MS) {
        refresh();
      }
    };

    const timer = window.setInterval(refresh, REFRESH_INTERVAL_MS);
    document.addEventListener("visibilitychange", onVisibilityChange);

    return () => {
      window.clearInterval(timer);
      document.removeEventListener("visibilitychange", onVisibilityChange);
    };
  }, []);

  return null;
}
