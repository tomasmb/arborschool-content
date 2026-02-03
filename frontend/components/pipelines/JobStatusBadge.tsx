import { Clock, Loader2, CheckCircle2, XCircle, X } from "lucide-react";
import { JobStatus } from "@/lib/api";

type Status = JobStatus["status"];

const statusConfig: Record<Status, { icon: typeof Clock; color: string; bg: string }> = {
  pending: { icon: Clock, color: "text-text-secondary", bg: "bg-white/5" },
  running: { icon: Loader2, color: "text-accent", bg: "bg-accent/10" },
  completed: { icon: CheckCircle2, color: "text-success", bg: "bg-success/10" },
  failed: { icon: XCircle, color: "text-error", bg: "bg-error/10" },
  cancelled: { icon: X, color: "text-text-secondary", bg: "bg-white/5" },
};

export function JobStatusBadge({ status }: { status: Status }) {
  const { icon: Icon, color, bg } = statusConfig[status];
  return (
    <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs ${color} ${bg}`}>
      <Icon className={`w-3 h-3 ${status === "running" ? "animate-spin" : ""}`} />
      {status}
    </span>
  );
}
