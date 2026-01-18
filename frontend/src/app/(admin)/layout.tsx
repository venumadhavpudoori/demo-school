"use client";

import { AdminLayout } from "@/components/layout";
import { SuperAdminRoute } from "@/components/SuperAdminRoute";
import { ErrorBoundary } from "@/components/ErrorBoundary";
import { FallbackUI } from "@/components/FallbackUI";

export default function AdminLayoutWrapper({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <SuperAdminRoute>
      <AdminLayout>
        <ErrorBoundary
          fallback={
            <FallbackUI
              type="error"
              title="Admin Panel Error"
              description="Something went wrong while loading the admin panel. Please try again."
              showRetry
              showHome
            />
          }
        >
          {children}
        </ErrorBoundary>
      </AdminLayout>
    </SuperAdminRoute>
  );
}
