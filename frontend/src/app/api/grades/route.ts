import { NextRequest } from "next/server";
import { proxyRequest } from "../_lib/proxy";

export async function GET(request: NextRequest) {
  return proxyRequest(request, "/api/grades", "GET");
}

export async function POST(request: NextRequest) {
  return proxyRequest(request, "/api/grades", "POST");
}
