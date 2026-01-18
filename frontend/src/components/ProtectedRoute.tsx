"use client";

import { useEffect, ReactNode } from "react";
import { useRouter } from "next/navigation";
import { useAuth, User } from "@/context/AuthContext";

type UserRole = User["role"];

interface ProtectedRouteProps {
  children: ReactNode;
  /** Roles allowed to access this route. If empty, any authenticated user can access. */
  allowedRoles?: UserRole[];
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
 * ProtectedRoute component that wraps pages requiring authentication and/or specific roles.
 * 
 * Usage:
 * ```tsx
 * // Any authenticated user
 * <ProtectedRoute>
 *   <DashboardPage />
 * </ProtectedRoute>
 * 
 * // Only admins
 * <ProtectedRoute allowedRoles={["admin"]}>
 *   <AdminPage />
 * </ProtectedRoute>
 * 
 * // Admins and teachers
 * <ProtectedRoute allowedRoles={["admin", "teacher"]}>
 *   <GradesPage />
 * </ProtectedRoute>
 * ```
 */
export function ProtectedRoute({
  children,
  allowedRoles = [],
  loginPath = "/login",
  unauthorizedPath = "/unauthorized",
  loadingComponent,
  onAccessDenied,
}: ProtectedRouteProps) {
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

    // Check role-based access
    if (allowedRoles.length > 0 && user) {
      const hasRequiredRole = allowedRoles.includes(user.role);
      if (!hasRequiredRole) {
        onAccessDenied?.("unauthorized");
        router.replace(unauthorizedPath);
      }
    }
  }, [isLoading, isAuthenticated, user, allowedRoles, loginPath, unauthorizedPath, router, onAccessDenied]);

  // Show loading state while checking auth
  if (isLoading) {
    return <>{loadingComponent || <DefaultLoadingSpinner />}</>;
  }

  // Not authenticated - show nothing while redirecting
  if (!isAuthenticated) {
    return null;
  }

  // Check role authorization
  if (allowedRoles.length > 0 && user) {
    const hasRequiredRole = allowedRoles.includes(user.role);
    if (!hasRequiredRole) {
      return null;
    }
  }

  // Authorized - render children
  return <>{children}</>;
}

/**
 * Higher-order component version of ProtectedRoute
 */
export function withProtectedRoute<P extends object>(
  Component: React.ComponentType<P>,
  options: Omit<ProtectedRouteProps, "children"> = {}
) {
  return function ProtectedComponent(props: P) {
    return (
      <ProtectedRoute {...options}>
        <Component {...props} />
      </ProtectedRoute>
    );
  };
}

/**
 * Hook to check if current user has a specific role
 */
export function useHasRole(roles: UserRole | UserRole[]): boolean {
  const { user } = useAuth();

  if (!user) return false;

  const roleArray = Array.isArray(roles) ? roles : [roles];
  return roleArray.includes(user.role);
}

/**
 * Hook to check if current user has permission for an action
 * Based on the RBAC rules from the design document
 */
export function useHasPermission(permission: string): boolean {
  const { user } = useAuth();

  if (!user) return false;

  // Permission mapping based on design document Property 6
  const rolePermissions: Record<UserRole, string[]> = {
    super_admin: ["*"], // Full access to everything
    admin: [
      "tenant:*",
      "users:*",
      "students:*",
      "teachers:*",
      "classes:*",
      "sections:*",
      "attendance:*",
      "grades:*",
      "fees:*",
      "timetable:*",
      "announcements:*",
      "reports:*",
      "leave_requests:*",
    ],
    teacher: [
      "students:read",
      "students:read:assigned",
      "classes:read:assigned",
      "attendance:read",
      "attendance:write:assigned",
      "grades:read",
      "grades:write:assigned",
      "timetable:read",
      "announcements:read",
      "announcements:write",
      "leave_requests:read:own",
      "leave_requests:write:own",
    ],
    student: [
      "students:read:own",
      "attendance:read:own",
      "grades:read:own",
      "fees:read:own",
      "timetable:read",
      "announcements:read",
      "leave_requests:read:own",
      "leave_requests:write:own",
    ],
    parent: [
      "students:read:children",
      "attendance:read:children",
      "grades:read:children",
      "fees:read:children",
      "timetable:read",
      "announcements:read",
    ],
  };

  const userPermissions = rolePermissions[user.role] || [];

  // Check for wildcard permission
  if (userPermissions.includes("*")) return true;

  // Check for exact match
  if (userPermissions.includes(permission)) return true;

  // Check for category wildcard (e.g., "students:*" matches "students:read")
  const [category] = permission.split(":");
  if (userPermissions.includes(`${category}:*`)) return true;

  return false;
}
