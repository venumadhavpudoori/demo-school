"use client";

import { createContext, useContext, useState, useEffect, useCallback, ReactNode, useRef } from "react";
import { api, ApiError, TokenPair } from "@/lib/api";

export interface User {
  id: number;
  email: string;
  role: "admin" | "teacher" | "student" | "parent" | "super_admin";
  profile_data: Record<string, unknown>;
  is_active: boolean;
  tenant_id?: number;
}

export interface AuthContextType {
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  error: string | null;
  login: (email: string, password: string) => Promise<void>;
  logout: () => void;
  refreshToken: () => Promise<boolean>;
  clearError: () => void;
}

interface LoginResponse extends TokenPair {
  user_id: number;
  tenant_id: number;
  role: string;
}

// Demo mode flag - set to true to enable login without backend
const DEMO_MODE = process.env.NEXT_PUBLIC_DEMO_MODE === "true";

// Demo users for testing
const DEMO_USERS: Record<string, User> = {
  "admin@demo.com": {
    id: 1,
    email: "admin@demo.com",
    role: "admin",
    profile_data: { first_name: "Admin", last_name: "User" },
    is_active: true,
    tenant_id: 1,
  },
  "teacher@demo.com": {
    id: 2,
    email: "teacher@demo.com",
    role: "teacher",
    profile_data: { first_name: "Teacher", last_name: "User" },
    is_active: true,
    tenant_id: 1,
  },
  "student@demo.com": {
    id: 3,
    email: "student@demo.com",
    role: "student",
    profile_data: { first_name: "Student", last_name: "User" },
    is_active: true,
    tenant_id: 1,
  },
  "parent@demo.com": {
    id: 4,
    email: "parent@demo.com",
    role: "parent",
    profile_data: { first_name: "Parent", last_name: "User" },
    is_active: true,
    tenant_id: 1,
  },
};

// Storage key for demo user
const DEMO_USER_KEY = "erp_demo_user";

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const initRef = useRef(false);

  // Check for existing session on mount
  useEffect(() => {
    if (initRef.current) return;
    initRef.current = true;

    const initAuth = async () => {
      // Demo mode: check for stored demo user
      if (DEMO_MODE) {
        try {
          const storedUser = localStorage.getItem(DEMO_USER_KEY);
          if (storedUser) {
            setUser(JSON.parse(storedUser));
          }
        } catch {
          // Ignore localStorage errors
        }
        setIsLoading(false);
        return;
      }

      // Set up unauthorized callback
      api.setOnUnauthorized(() => {
        setUser(null);
        api.clearTokens();
      });

      // Check if we have tokens
      if (!api.hasTokens()) {
        setIsLoading(false);
        return;
      }

      // Try to get current user
      try {
        const currentUser = await api.get<User>("/api/auth/me");
        setUser(currentUser);
      } catch (err) {
        // Token might be expired, try refresh
        const refreshed = await api.attemptTokenRefresh();
        if (refreshed) {
          try {
            const currentUser = await api.get<User>("/api/auth/me");
            setUser(currentUser);
          } catch {
            // Still failed, clear tokens
            api.clearTokens();
          }
        } else {
          api.clearTokens();
        }
      } finally {
        setIsLoading(false);
      }
    };

    initAuth();
  }, []);

  const login = useCallback(async (email: string, password: string) => {
    setError(null);
    setIsLoading(true);

    try {
      // Demo mode: authenticate with demo users
      if (DEMO_MODE) {
        // Simulate network delay
        await new Promise(resolve => setTimeout(resolve, 500));
        
        const demoUser = DEMO_USERS[email.toLowerCase()];
        if (demoUser && password.length >= 8) {
          localStorage.setItem(DEMO_USER_KEY, JSON.stringify(demoUser));
          setUser(demoUser);
          setIsLoading(false);
          return;
        } else {
          const err: ApiError = {
            code: "AUTH_ERROR",
            message: "Invalid credentials. Try admin@demo.com with any 8+ char password.",
          };
          setError(err.message);
          setIsLoading(false);
          throw err;
        }
      }

      const response = await api.post<LoginResponse>("/api/auth/login", {
        email,
        password,
      });

      // Store tokens and tenant ID
      api.setTokens({
        access_token: response.access_token,
        refresh_token: response.refresh_token,
        token_type: response.token_type,
        tenant_id: response.tenant_id,
      });

      // Fetch full user profile
      const currentUser = await api.get<User>("/api/auth/me");
      setUser(currentUser);
    } catch (err) {
      const apiError = err as ApiError;
      setError(apiError.message || "Login failed. Please check your credentials.");
      throw err;
    } finally {
      setIsLoading(false);
    }
  }, []);

  const logout = useCallback(() => {
    setUser(null);
    setError(null);
    
    // Demo mode: clear demo user from storage
    if (DEMO_MODE) {
      try {
        localStorage.removeItem(DEMO_USER_KEY);
      } catch {
        // Ignore localStorage errors
      }
    } else {
      api.clearTokens();
    }
  }, []);

  const refreshToken = useCallback(async (): Promise<boolean> => {
    try {
      const success = await api.attemptTokenRefresh();
      if (!success) {
        setUser(null);
        return false;
      }

      // Refresh user data
      try {
        const currentUser = await api.get<User>("/api/auth/me");
        setUser(currentUser);
      } catch {
        // Failed to get user, but token refresh succeeded
      }

      return true;
    } catch {
      setUser(null);
      return false;
    }
  }, []);

  const clearError = useCallback(() => {
    setError(null);
  }, []);

  return (
    <AuthContext.Provider
      value={{
        user,
        isAuthenticated: !!user,
        isLoading,
        error,
        login,
        logout,
        refreshToken,
        clearError,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
}
