import { NextRequest } from "next/server";
import { proxyRequest } from "../../../_lib/proxy";

export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ studentId: string }> }
) {
  const { studentId } = await params;
  return proxyRequest(request, `/api/grades/report-card/${studentId}`, "GET");
}
