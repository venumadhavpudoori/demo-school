export interface RequestOptions {
  method?: "GET" | "POST" | "PUT" | "DELETE" | "PATCH";
  body?: unknown;
  headers?: Record<string, string>;
  params?: Record<string, string | number | boolean | undefined>;
  skipAuth?: boolean;
}

export interface ApiError {
  code: string;
  message: string;
  details?: Array<{ field: string; message: string }>;
  status?: number;
}

export interface TokenPair {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

// Storage keys
const ACCESS_TOKEN_KEY = "erp_access_token";
const REFRESH_TOKEN_KEY = "erp_refresh_token";
const TENANT_ID_KEY = "erp_tenant_id";

class ApiClient {
  private baseUrl: string;
  private accessToken: string | null = null;
  private refreshToken: string | null = null;
  private tenantId: string | null = null;
  private refreshPromise: Promise<boolean> | null = null;
  private onUnauthorized: (() => void) | null = null;

  constructor(baseUrl: string = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000") {
    this.baseUrl = baseUrl;
    // Load tokens from storage on initialization (client-side only)
    if (typeof window !== "undefined") {
      this.loadTokensFromStorage();
    }
  }

  /**
   * Load tokens from localStorage
   */
  loadTokensFromStorage(): void {
    try {
      this.accessToken = localStorage.getItem(ACCESS_TOKEN_KEY);
      this.refreshToken = localStorage.getItem(REFRESH_TOKEN_KEY);
      this.tenantId = localStorage.getItem(TENANT_ID_KEY);
    } catch {
      // localStorage not available
    }
  }

  /**
   * Save tokens to localStorage
   */
  private saveTokensToStorage(): void {
    try {
      if (this.accessToken) {
        localStorage.setItem(ACCESS_TOKEN_KEY, this.accessToken);
      } else {
        localStorage.removeItem(ACCESS_TOKEN_KEY);
      }
      if (this.refreshToken) {
        localStorage.setItem(REFRESH_TOKEN_KEY, this.refreshToken);
      } else {
        localStorage.removeItem(REFRESH_TOKEN_KEY);
      }
      if (this.tenantId) {
        localStorage.setItem(TENANT_ID_KEY, this.tenantId);
      } else {
        localStorage.removeItem(TENANT_ID_KEY);
      }
    } catch {
      // localStorage not available
    }
  }

  /**
   * Set the access token for authenticated requests
   */
  setAccessToken(token: string): void {
    this.accessToken = token;
    this.saveTokensToStorage();
  }

  /**
   * Set the refresh token for token refresh
   */
  setRefreshToken(token: string): void {
    this.refreshToken = token;
    this.saveTokensToStorage();
  }

  /**
   * Set both tokens at once (typically after login)
   */
  setTokens(tokens: TokenPair & { tenant_id?: number }): void {
    this.accessToken = tokens.access_token;
    this.refreshToken = tokens.refresh_token;
    if (tokens.tenant_id) {
      this.tenantId = String(tokens.tenant_id);
    }
    this.saveTokensToStorage();
  }

  /**
   * Clear all tokens (typically on logout)
   */
  clearTokens(): void {
    this.accessToken = null;
    this.refreshToken = null;
    this.tenantId = null;
    this.saveTokensToStorage();
  }

  /**
   * Get the current access token
   */
  getAccessToken(): string | null {
    return this.accessToken;
  }

  /**
   * Get the current refresh token
   */
  getRefreshToken(): string | null {
    return this.refreshToken;
  }

  /**
   * Check if user has tokens (may be expired)
   */
  hasTokens(): boolean {
    return !!this.accessToken;
  }

  /**
   * Set callback for unauthorized responses (401)
   */
  setOnUnauthorized(callback: () => void): void {
    this.onUnauthorized = callback;
  }

  /**
   * Build URL with query parameters
   */
  private buildUrl(endpoint: string, params?: Record<string, string | number | boolean | undefined>): string {
    const url = new URL(`${this.baseUrl}${endpoint}`);
    if (params) {
      Object.entries(params).forEach(([key, value]) => {
        if (value !== undefined) {
          url.searchParams.append(key, String(value));
        }
      });
    }
    return url.toString();
  }

  /**
   * Attempt to refresh the access token
   */
  async attemptTokenRefresh(): Promise<boolean> {
    // If already refreshing, wait for that promise
    if (this.refreshPromise) {
      return this.refreshPromise;
    }

    if (!this.refreshToken) {
      return false;
    }

    this.refreshPromise = (async () => {
      try {
        const response = await fetch(`${this.baseUrl}/api/auth/refresh`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({ refresh_token: this.refreshToken }),
        });

        if (!response.ok) {
          this.clearTokens();
          return false;
        }

        const data: TokenPair = await response.json();
        this.setTokens(data);
        return true;
      } catch {
        this.clearTokens();
        return false;
      } finally {
        this.refreshPromise = null;
      }
    })();

    return this.refreshPromise;
  }

  /**
   * Make an API request with automatic token refresh on 401
   */
  async request<T>(endpoint: string, options: RequestOptions = {}): Promise<T> {
    const { method = "GET", body, headers = {}, params, skipAuth = false } = options;

    // Always reload tokens from storage on each request to ensure we have latest values
    if (typeof window !== "undefined") {
      this.loadTokensFromStorage();
    }

    const requestHeaders: Record<string, string> = {
      "Content-Type": "application/json",
      ...headers,
    };

    if (!skipAuth && this.accessToken) {
      requestHeaders["Authorization"] = `Bearer ${this.accessToken}`;
    }

    // Add tenant ID header if available
    if (this.tenantId) {
      requestHeaders["X-Tenant-ID"] = this.tenantId;
    }

    const url = this.buildUrl(endpoint, params);

    let response: Response;
    try {
      response = await fetch(url, {
        method,
        headers: requestHeaders,
        body: body ? JSON.stringify(body) : undefined,
      });
    } catch (fetchError) {
      // Network error or fetch failed
      const error: ApiError = {
        code: "NETWORK_ERROR",
        message: "Unable to connect to server. Please check your connection.",
        status: 0,
      };
      throw error;
    }

    // Handle 401 - attempt token refresh and retry
    if (response.status === 401 && !skipAuth && this.refreshToken) {
      const refreshed = await this.attemptTokenRefresh();
      if (refreshed) {
        // Retry the request with new token
        requestHeaders["Authorization"] = `Bearer ${this.accessToken}`;
        try {
          response = await fetch(url, {
            method,
            headers: requestHeaders,
            body: body ? JSON.stringify(body) : undefined,
          });
        } catch (fetchError) {
          const error: ApiError = {
            code: "NETWORK_ERROR",
            message: "Unable to connect to server. Please check your connection.",
            status: 0,
          };
          throw error;
        }
      } else {
        // Refresh failed, trigger unauthorized callback
        this.onUnauthorized?.();
        const error: ApiError = {
          code: "UNAUTHORIZED",
          message: "Session expired. Please log in again.",
          status: 401,
        };
        throw error;
      }
    }

    if (!response.ok) {
      let errorData: Record<string, unknown> = {};
      try {
        errorData = await response.json();
      } catch {
        // Response body is not JSON or empty
      }
      
      // Extract error message from various response formats
      let errorMessage = "An unexpected error occurred";
      let errorCode = this.getErrorCodeFromStatus(response.status);
      
      if (errorData.error && typeof errorData.error === "object") {
        const errObj = errorData.error as Record<string, unknown>;
        errorMessage = (errObj.message as string) || errorMessage;
        errorCode = (errObj.code as string) || errorCode;
      } else if (errorData.detail) {
        if (typeof errorData.detail === "string") {
          errorMessage = errorData.detail;
        } else if (typeof errorData.detail === "object") {
          const detailObj = errorData.detail as Record<string, unknown>;
          if (detailObj.error && typeof detailObj.error === "object") {
            const errObj = detailObj.error as Record<string, unknown>;
            errorMessage = (errObj.message as string) || errorMessage;
            errorCode = (errObj.code as string) || errorCode;
          }
        }
      } else if (errorData.message) {
        errorMessage = errorData.message as string;
      }
      
      const error: ApiError = {
        code: errorCode,
        message: errorMessage,
        details: (errorData.error as Record<string, unknown>)?.details as ApiError["details"],
        status: response.status,
      };
      throw error;
    }

    // Handle 204 No Content
    if (response.status === 204) {
      return undefined as T;
    }

    try {
      return await response.json();
    } catch {
      // Response body is not valid JSON
      return undefined as T;
    }
  }

  /**
   * Get error code from HTTP status
   */
  private getErrorCodeFromStatus(status: number): string {
    switch (status) {
      case 400:
        return "BAD_REQUEST";
      case 401:
        return "UNAUTHORIZED";
      case 403:
        return "FORBIDDEN";
      case 404:
        return "NOT_FOUND";
      case 409:
        return "CONFLICT";
      case 422:
        return "VALIDATION_ERROR";
      case 429:
        return "RATE_LIMITED";
      case 500:
        return "SERVER_ERROR";
      default:
        return "UNKNOWN_ERROR";
    }
  }

  /**
   * GET request
   */
  async get<T>(endpoint: string, params?: Record<string, string | number | boolean | undefined>): Promise<T> {
    return this.request<T>(endpoint, { method: "GET", params });
  }

  /**
   * POST request
   */
  async post<T>(endpoint: string, data?: unknown): Promise<T> {
    return this.request<T>(endpoint, { method: "POST", body: data });
  }

  /**
   * PUT request
   */
  async put<T>(endpoint: string, data: unknown): Promise<T> {
    return this.request<T>(endpoint, { method: "PUT", body: data });
  }

  /**
   * PATCH request
   */
  async patch<T>(endpoint: string, data: unknown): Promise<T> {
    return this.request<T>(endpoint, { method: "PATCH", body: data });
  }

  /**
   * DELETE request
   */
  async delete(endpoint: string): Promise<void> {
    return this.request<void>(endpoint, { method: "DELETE" });
  }
}

// Export a singleton instance
export const api = new ApiClient();

// Export the class for testing or custom instances
export { ApiClient };
