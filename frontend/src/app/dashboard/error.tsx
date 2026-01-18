"use client";

import { useEffect } from "react";
import { FallbackUI } from "@/components/FallbackUI";

export default function DashboardError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    console.error("Dashboard error:", error);
  }, [error]);

  return (
    <FallbackUI
      type="error"
      title="Dashboard Error"
      description="Something went wrong while loading this page."
      showRetry
      showHome
      onRetry={reset}
    />
  );
}
