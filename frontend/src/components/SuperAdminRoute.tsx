"use client";

import { useEffect, ReactNode } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/context/AuthContext";

interface SuperAdminRouteProps {
  children: ReactNode;
  /** Custom redirect path when not authenticated. Defaults to /login */
  loginPath?: string;
  /** Custom redirect path when not authorized. Defaults to /unauthorized */
  unauthorizedPath?: string;
  /** Custom loading component */
  loadingComponent?: ReactNode;
  /** Callback when access is denied */
  onAccessDenied?: (reason: "unauthenticated" | "unauthorized") => void;
}

/**
 * Default loading spinner component
 */
function DefaultLoadingSpinner() {
  return (
    <div className="flex min-h-screen items-center justify-center">
      <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent" />
    </div>
  );
}

/**
 * SuperAdminRoute component that wraps pages requiring super_admin role.
 * This is a specialized version of ProtectedRoute that only allows super_admin users.
 * 
 * Usage:
 * ```tsx
 * <SuperAdminRoute>
 *   <AdminDashboardPage />
 * </SuperAdminRoute>
 * ```
 */
export function SuperAdminRoute({
  children,
  loginPath = "/login",
  unauthorizedPath = "/unauthorized",
  loadingComponent,
  onAccessDenied,
}: SuperAdminRouteProps) {
  const { user, isAuthenticated, isLoading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    // Wait for auth to initialize
    if (isLoading) return;

    // Not authenticated - redirect to login
    if (!isAuthenticated) {
      onAccessDenied?.("unauthenticated");
      // Store the current path for redirect after login
      const currentPath = window.location.pathname + window.location.search;
      const redirectUrl = `${loginPath}?redirect=${encodeURIComponent(currentPath)}`;
      router.replace(redirectUrl);
      return;
    }

    // Check for super_admin role
    if (user && user.role !== "super_admin") {
      onAccessDenied?.("unauthorized");
      router.replace(unauthorizedPath);
    }
  }, [isLoading, isAuthenticated, user, loginPath, unauthorizedPath, router, onAccessDenied]);

  // Show loading state while checking auth
  if (isLoading) {
    return <>{loadingComponent || <DefaultLoadingSpinner />}</>;
  }

  // Not authenticated - show nothing while redirecting
  if (!isAuthenticated) {
    return null;
  }

  // Check super_admin role
  if (user && user.role !== "super_admin") {
    return null;
  }

  // Authorized - render children
  return <>{children}</>;
}

/**
 * Higher-order component version of SuperAdminRoute
 */
export function withSuperAdminRoute<P extends object>(
  Component: React.ComponentType<P>,
  options: Omit<SuperAdminRouteProps, "children"> = {}
) {
  return function SuperAdminProtectedComponent(props: P) {
    return (
      <SuperAdminRoute {...options}>
        <Component {...props} />
      </SuperAdminRoute>
    );
  };
}

/**
 * Hook to check if current user is a super admin
 */
export function useIsSuperAdmin(): boolean {
  const { user } = useAuth();
  return user?.role === "super_admin";
}
