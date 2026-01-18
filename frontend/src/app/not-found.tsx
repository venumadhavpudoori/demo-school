"use client";

import { FullPageFallback } from "@/components/FallbackUI";

export default function NotFound() {
  return (
    <FullPageFallback
      type="notFound"
      title="Page not found"
      description="The page you're looking for doesn't exist or has been moved."
    />
  );
}
