"use client";

import { createContext, useContext, useEffect, ReactNode, useReducer, useCallback, useRef } from "react";
import { api, ApiError } from "@/lib/api";

export interface Tenant {
  id: number;
  name: string;
  slug: string;
  domain?: string;
  status: "active" | "inactive" | "suspended";
  subscription_plan: string;
  created_at?: string;
}

export interface TenantSettings {
  theme?: "light" | "dark" | "system";
  logo_url?: string;
  primary_color?: string;
  academic_year?: string;
  grading_scale?: Record<string, { min: number; max: number }>;
  attendance_threshold?: number;
  [key: string]: unknown;
}

export interface TenantContextType {
  tenant: Tenant | null;
  settings: TenantSettings;
  isLoading: boolean;
  error: string | null;
  refetchTenant: () => Promise<void>;
  updateSettings: (newSettings: Partial<TenantSettings>) => Promise<void>;
}

interface TenantState {
  tenant: Tenant | null;
  settings: TenantSettings;
  isLoading: boolean;
  error: string | null;
}

type TenantAction =
  | { type: "SET_TENANT"; payload: { tenant: Tenant; settings: TenantSettings } }
  | { type: "SET_LOADING"; payload: boolean }
  | { type: "SET_ERROR"; payload: string }
  | { type: "UPDATE_SETTINGS"; payload: Partial<TenantSettings> }
  | { type: "CLEAR_ERROR" };

function tenantReducer(state: TenantState, action: TenantAction): TenantState {
  switch (action.type) {
    case "SET_TENANT":
      return {
        ...state,
        tenant: action.payload.tenant,
        settings: action.payload.settings,
        isLoading: false,
        error: null,
      };
    case "SET_LOADING":
      return { ...state, isLoading: action.payload };
    case "SET_ERROR":
      return { ...state, isLoading: false, error: action.payload };
    case "UPDATE_SETTINGS":
      return {
        ...state,
        settings: { ...state.settings, ...action.payload },
      };
    case "CLEAR_ERROR":
      return { ...state, error: null };
    default:
      return state;
  }
}

const TenantContext = createContext<TenantContextType | undefined>(undefined);

/**
 * Extract tenant slug from hostname
 * Supports formats:
 * - subdomain.domain.com -> subdomain
 * - localhost:3000 -> null (development)
 * - domain.com -> null (main domain)
 */
function extractTenantSlug(): string | null {
  if (typeof window === "undefined") {
    return null;
  }

  const hostname = window.location.hostname;

  // Development: localhost
  if (hostname === "localhost" || hostname === "127.0.0.1") {
    // Check for tenant in query params for development
    const params = new URLSearchParams(window.location.search);
    return params.get("tenant");
  }

  // Production: extract subdomain
  const parts = hostname.split(".");

  // Need at least 3 parts for subdomain (e.g., school.platform.com)
  if (parts.length >= 3) {
    const subdomain = parts[0];
    // Exclude common non-tenant subdomains
    if (!["www", "api", "admin", "app"].includes(subdomain)) {
      return subdomain;
    }
  }

  return null;
}

interface TenantResponse {
  id: number;
  name: string;
  slug: string;
  domain?: string;
  status: string;
  subscription_plan: string;
  settings: TenantSettings;
  created_at?: string;
}

export function TenantProvider({ children }: { children: ReactNode }) {
  const [state, dispatch] = useReducer(tenantReducer, {
    tenant: null,
    settings: {},
    isLoading: true,
    error: null,
  });

  const initRef = useRef(false);

  const fetchTenant = useCallback(async () => {
    dispatch({ type: "SET_LOADING", payload: true });

    try {
      const slug = extractTenantSlug();

      if (!slug) {
        // No tenant slug found - might be main domain or development
        dispatch({ type: "SET_LOADING", payload: false });
        return;
      }

      // Fetch tenant info from API
      const response = await api.get<TenantResponse>(`/api/tenants/${slug}`, undefined);

      const tenant: Tenant = {
        id: response.id,
        name: response.name,
        slug: response.slug,
        domain: response.domain,
        status: response.status as Tenant["status"],
        subscription_plan: response.subscription_plan,
        created_at: response.created_at,
      };

      dispatch({
        type: "SET_TENANT",
        payload: {
          tenant,
          settings: response.settings || {},
        },
      });
    } catch (err) {
      const apiError = err as ApiError;
      if (apiError.status === 404) {
        dispatch({ type: "SET_ERROR", payload: "School not found. Please check the URL." });
      } else {
        dispatch({ type: "SET_ERROR", payload: "Failed to load school information." });
      }
    }
  }, []);

  useEffect(() => {
    if (initRef.current) return;
    initRef.current = true;
    fetchTenant();
  }, [fetchTenant]);

  const refetchTenant = useCallback(async () => {
    await fetchTenant();
  }, [fetchTenant]);

  const updateSettings = useCallback(async (newSettings: Partial<TenantSettings>) => {
    if (!state.tenant) {
      throw new Error("No tenant loaded");
    }

    try {
      // Update settings via API
      await api.patch(`/api/tenants/${state.tenant.slug}/settings`, newSettings);

      // Update local state
      dispatch({ type: "UPDATE_SETTINGS", payload: newSettings });
    } catch (err) {
      const apiError = err as ApiError;
      throw new Error(apiError.message || "Failed to update settings");
    }
  }, [state.tenant]);

  return (
    <TenantContext.Provider
      value={{
        tenant: state.tenant,
        settings: state.settings,
        isLoading: state.isLoading,
        error: state.error,
        refetchTenant,
        updateSettings,
      }}
    >
      {children}
    </TenantContext.Provider>
  );
}

export function useTenant() {
  const context = useContext(TenantContext);
  if (context === undefined) {
    throw new Error("useTenant must be used within a TenantProvider");
  }
  return context;
}
