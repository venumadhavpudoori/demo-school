"use client";

import { useEffect } from "react";
import { FallbackUI } from "@/components/FallbackUI";

export default function AdminError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    console.error("Admin error:", error);
  }, [error]);

  return (
    <FallbackUI
      type="error"
      title="Admin Panel Error"
      description="Something went wrong while loading the admin panel."
      showRetry
      showHome
      onRetry={reset}
    />
  );
}
