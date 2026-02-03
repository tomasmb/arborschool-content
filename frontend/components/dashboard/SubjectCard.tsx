"use client";

import Link from "next/link";
import { ArrowRight, CheckCircle2, Circle } from "lucide-react";
import { type SubjectBrief } from "@/lib/api";
import { cn, formatPercent } from "@/lib/utils";

interface SubjectCardProps {
  subject: SubjectBrief;
}

export function SubjectCard({ subject }: SubjectCardProps) {
  const { stats } = subject;

  const StatusIcon = ({ done }: { done: boolean }) =>
    done ? (
      <CheckCircle2 className="w-4 h-4 text-success" />
    ) : (
      <Circle className="w-4 h-4 text-text-secondary" />
    );

  return (
    <div className="bg-surface border border-border rounded-lg p-6 hover:border-accent/50 transition-colors">
      {/* Header */}
      <div className="flex items-start justify-between mb-4">
        <div>
          <h3 className="font-semibold text-lg">{subject.name}</h3>
          <p className="text-text-secondary text-sm">{subject.year}</p>
        </div>
      </div>

      {/* Knowledge Graph Pipeline Status */}
      <div className="space-y-2 mb-4">
        <div className="flex items-center gap-2 text-sm">
          <StatusIcon done={stats.temario_exists} />
          <span className={stats.temario_exists ? "text-text-primary" : "text-text-secondary"}>
            Temario
          </span>
        </div>
        <div className="flex items-center gap-2 text-sm">
          <StatusIcon done={stats.standards_count > 0} />
          <span className={stats.standards_count > 0 ? "text-text-primary" : "text-text-secondary"}>
            Standards ({stats.standards_count})
          </span>
        </div>
        <div className="flex items-center gap-2 text-sm">
          <StatusIcon done={stats.atoms_count > 0} />
          <span className={stats.atoms_count > 0 ? "text-text-primary" : "text-text-secondary"}>
            Atoms ({stats.atoms_count})
          </span>
        </div>
      </div>

      {/* Divider */}
      <div className="border-t border-border my-4" />

      {/* Tests & Questions Stats */}
      <div className="grid grid-cols-2 gap-4 mb-4">
        <div>
          <p className="text-2xl font-semibold">{stats.tests_count}</p>
          <p className="text-text-secondary text-xs">Tests</p>
        </div>
        <div>
          <p className="text-2xl font-semibold">{stats.questions_count}</p>
          <p className="text-text-secondary text-xs">Questions</p>
        </div>
        <div>
          <p className="text-2xl font-semibold">{stats.variants_count}</p>
          <p className="text-text-secondary text-xs">Variants</p>
        </div>
        <div>
          <p className="text-2xl font-semibold">{formatPercent(stats.tagging_completion)}</p>
          <p className="text-text-secondary text-xs">Tagged</p>
        </div>
      </div>

      {/* Action - Updated to /courses/ */}
      <Link
        href={`/courses/${subject.id}`}
        className={cn(
          "flex items-center justify-center gap-2 w-full py-2 px-4",
          "bg-accent/10 text-accent rounded-lg text-sm font-medium",
          "hover:bg-accent/20 transition-colors"
        )}
      >
        Enter
        <ArrowRight className="w-4 h-4" />
      </Link>
    </div>
  );
}
