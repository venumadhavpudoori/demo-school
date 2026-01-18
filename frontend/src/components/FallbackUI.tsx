"use client";

import React from "react";
import {
  AlertTriangle,
  RefreshCw,
  Home,
  WifiOff,
  ServerCrash,
  FileQuestion,
  ShieldAlert,
  Clock,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

export type FallbackType =
  | "error"
  | "network"
  | "server"
  | "notFound"
  | "unauthorized"
  | "timeout"
  | "maintenance";

interface FallbackConfig {
  icon: React.ElementType;
  title: string;
  description: string;
  iconBgClass: string;
  iconClass: string;
}

const fallbackConfig: Record<FallbackType, FallbackConfig> = {
  error: {
    icon: AlertTriangle,
    title: "Something went wrong",
    description:
      "An unexpected error occurred. Please try again or contact support if the problem persists.",
    iconBgClass: "bg-destructive/10",
    iconClass: "text-destructive",
  },
  network: {
    icon: WifiOff,
    title: "No internet connection",
    description: "Please check your internet connection and try again.",
    iconBgClass: "bg-orange-100 dark:bg-orange-900/20",
    iconClass: "text-orange-600 dark:text-orange-400",
  },
  server: {
    icon: ServerCrash,
    title: "Server error",
    description:
      "Our servers are experiencing issues. Please try again later.",
    iconBgClass: "bg-red-100 dark:bg-red-900/20",
    iconClass: "text-red-600 dark:text-red-400",
  },
  notFound: {
    icon: FileQuestion,
    title: "Page not found",
    description:
      "The page you're looking for doesn't exist or has been moved.",
    iconBgClass: "bg-blue-100 dark:bg-blue-900/20",
    iconClass: "text-blue-600 dark:text-blue-400",
  },
  unauthorized: {
    icon: ShieldAlert,
    title: "Access denied",
    description: "You don't have permission to access this resource.",
    iconBgClass: "bg-yellow-100 dark:bg-yellow-900/20",
    iconClass: "text-yellow-600 dark:text-yellow-400",
  },
  timeout: {
    icon: Clock,
    title: "Request timed out",
    description:
      "The request took too long to complete. Please try again.",
    iconBgClass: "bg-purple-100 dark:bg-purple-900/20",
    iconClass: "text-purple-600 dark:text-purple-400",
  },
  maintenance: {
    icon: ServerCrash,
    title: "Under maintenance",
    description:
      "We're performing scheduled maintenance. Please check back soon.",
    iconBgClass: "bg-gray-100 dark:bg-gray-800",
    iconClass: "text-gray-600 dark:text-gray-400",
  },
};

interface FallbackUIProps {
  type?: FallbackType;
  title?: string;
  description?: string;
  showRetry?: boolean;
  showHome?: boolean;
  showReload?: boolean;
  onRetry?: () => void;
  className?: string;
}

/**
 * FallbackUI component displays user-friendly error states
 * with appropriate icons, messages, and action buttons.
 */
export function FallbackUI({
  type = "error",
  title,
  description,
  showRetry = true,
  showHome = true,
  showReload = false,
  onRetry,
  className = "",
}: FallbackUIProps) {
  const config = fallbackConfig[type];
  const Icon = config.icon;

  const handleRetry = () => {
    if (onRetry) {
      onRetry();
    } else {
      window.location.reload();
    }
  };

  const handleGoHome = () => {
    window.location.href = "/";
  };

  const handleReload = () => {
    window.location.reload();
  };

  return (
    <div
      className={`min-h-[400px] flex items-center justify-center p-4 ${className}`}
    >
      <Card className="max-w-lg w-full">
        <CardHeader className="text-center">
          <div
            className={`mx-auto mb-4 p-3 ${config.iconBgClass} rounded-full w-fit`}
          >
            <Icon className={`h-8 w-8 ${config.iconClass}`} />
          </div>
          <CardTitle className="text-xl">{title || config.title}</CardTitle>
          <CardDescription>
            {description || config.description}
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex flex-col sm:flex-row gap-2 justify-center">
            {showRetry && (
              <Button variant="default" onClick={handleRetry}>
                <RefreshCw className="h-4 w-4 mr-2" />
                Try Again
              </Button>
            )}
            {showReload && (
              <Button variant="outline" onClick={handleReload}>
                <RefreshCw className="h-4 w-4 mr-2" />
                Reload Page
              </Button>
            )}
            {showHome && (
              <Button variant="ghost" onClick={handleGoHome}>
                <Home className="h-4 w-4 mr-2" />
                Go Home
              </Button>
            )}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

/**
 * Inline fallback for smaller error states within components
 */
interface InlineFallbackProps {
  message?: string;
  onRetry?: () => void;
  className?: string;
}

export function InlineFallback({
  message = "Failed to load content",
  onRetry,
  className = "",
}: InlineFallbackProps) {
  return (
    <div
      className={`flex flex-col items-center justify-center p-6 text-center ${className}`}
    >
      <AlertTriangle className="h-8 w-8 text-muted-foreground mb-2" />
      <p className="text-sm text-muted-foreground mb-3">{message}</p>
      {onRetry && (
        <Button variant="outline" size="sm" onClick={onRetry}>
          <RefreshCw className="h-3 w-3 mr-1" />
          Retry
        </Button>
      )}
    </div>
  );
}

/**
 * Empty state fallback for when there's no data
 */
interface EmptyStateFallbackProps {
  icon?: React.ElementType;
  title?: string;
  description?: string;
  action?: {
    label: string;
    onClick: () => void;
  };
  className?: string;
}

export function EmptyStateFallback({
  icon: Icon = FileQuestion,
  title = "No data found",
  description = "There's nothing here yet.",
  action,
  className = "",
}: EmptyStateFallbackProps) {
  return (
    <div
      className={`flex flex-col items-center justify-center p-8 text-center ${className}`}
    >
      <div className="p-3 bg-muted rounded-full mb-4">
        <Icon className="h-8 w-8 text-muted-foreground" />
      </div>
      <h3 className="text-lg font-medium mb-1">{title}</h3>
      <p className="text-sm text-muted-foreground mb-4 max-w-sm">
        {description}
      </p>
      {action && <Button onClick={action.onClick}>{action.label}</Button>}
    </div>
  );
}

/**
 * Full page error fallback for critical errors
 */
interface FullPageFallbackProps {
  type?: FallbackType;
  title?: string;
  description?: string;
}

export function FullPageFallback({
  type = "error",
  title,
  description,
}: FullPageFallbackProps) {
  return (
    <div className="min-h-screen flex items-center justify-center bg-background">
      <FallbackUI
        type={type}
        title={title}
        description={description}
        showRetry
        showHome
        showReload
      />
    </div>
  );
}
