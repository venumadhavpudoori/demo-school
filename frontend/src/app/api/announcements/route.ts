import { NextRequest } from "next/server";
import { proxyRequest } from "../_lib/proxy";

export async function GET(request: NextRequest) {
  return proxyRequest(request, "/api/announcements", "GET");
}

export async function POST(request: NextRequest) {
  return proxyRequest(request, "/api/announcements", "POST");
}
