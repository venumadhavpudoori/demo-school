import { NextRequest } from "next/server";
import { proxyRequest } from "../../../_lib/proxy";

export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ teacherId: string }> }
) {
  const { teacherId } = await params;
  return proxyRequest(request, `/api/timetable/teacher/${teacherId}`, "GET");
}
