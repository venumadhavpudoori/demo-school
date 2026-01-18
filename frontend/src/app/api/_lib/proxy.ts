import { NextRequest, NextResponse } from "next/server";

const BACKEND_URL = process.env.BACKEND_URL || "http://localhost:8000";

export async function proxyRequest(
  request: NextRequest,
  path: string,
  method: string = "GET"
) {
  try {
    const authHeader = request.headers.get("authorization");
    const tenantIdHeader = request.headers.get("x-tenant-id");
    const url = new URL(request.url);
    const queryString = url.search;
    
    const fetchOptions: RequestInit = {
      method,
      headers: {
        "Content-Type": "application/json",
        ...(authHeader && { Authorization: authHeader }),
        ...(tenantIdHeader && { "X-Tenant-ID": tenantIdHeader }),
      },
    };

    if (method !== "GET" && method !== "HEAD") {
      try {
        const body = await request.json();
        fetchOptions.body = JSON.stringify(body);
      } catch {
        // No body or invalid JSON
      }
    }

    const response = await fetch(`${BACKEND_URL}${path}${queryString}`, fetchOptions);
    
    if (response.status === 204) {
      return new NextResponse(null, { status: 204 });
    }

    const data = await response.json();
    return NextResponse.json(data, { status: response.status });
  } catch (error) {
    console.error("Proxy error:", error);
    return NextResponse.json(
      { error: { code: "SERVER_ERROR", message: "Failed to connect to server" } },
      { status: 500 }
    );
  }
}
