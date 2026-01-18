import { NextRequest } from "next/server";
import { proxyRequest } from "../../_lib/proxy";

export async function GET(request: NextRequest) {
  return proxyRequest(request, "/api/reports/grade-analysis", "GET");
}
