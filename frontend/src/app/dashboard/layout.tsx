"use client";

import { DashboardLayout } from "@/components/layout";
import { ProtectedRoute } from "@/components/ProtectedRoute";
import { ErrorBoundary } from "@/components/ErrorBoundary";
import { FallbackUI } from "@/components/FallbackUI";

export default function DashboardLayoutWrapper({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <ProtectedRoute>
      <DashboardLayout>
        <ErrorBoundary
          fallback={
            <FallbackUI
              type="error"
              title="Dashboard Error"
              description="Something went wrong while loading this page. Please try again."
              showRetry
              showHome
            />
          }
        >
          {children}
        </ErrorBoundary>
      </DashboardLayout>
    </ProtectedRoute>
  );
}
