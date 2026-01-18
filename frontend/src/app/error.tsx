"use client";

import { useEffect } from "react";
import { FullPageFallback } from "@/components/FallbackUI";

export default function GlobalError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    // Log the error to an error reporting service
    console.error("Global error:", error);
  }, [error]);

  return (
    <FullPageFallback
      type="error"
      title="Something went wrong"
      description="An unexpected error occurred. Please try again or contact support if the problem persists."
    />
  );
}
