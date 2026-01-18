import { NextRequest } from "next/server";
import { proxyRequest } from "../../_lib/proxy";

export async function POST(request: NextRequest) {
  return proxyRequest(request, "/api/attendance/mark", "POST");
}
