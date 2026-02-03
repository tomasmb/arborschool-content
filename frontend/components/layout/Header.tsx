"use client";

import { usePathname } from "next/navigation";
import { ChevronRight } from "lucide-react";

function getBreadcrumbs(pathname: string): { label: string; href: string }[] {
  const parts = pathname.split("/").filter(Boolean);
  const breadcrumbs: { label: string; href: string }[] = [];

  let currentPath = "";
  for (const part of parts) {
    currentPath += `/${part}`;

    // Format the label
    let label = part;
    if (part === "subjects") {
      label = "Subjects";
    } else if (part === "paes-m1-2026") {
      label = "PAES M1 2026";
    } else if (part === "atoms") {
      label = "Atoms";
    } else if (part === "tests") {
      label = "Tests";
    } else if (part === "pipelines") {
      label = "Pipelines";
    } else if (part === "sync") {
      label = "Sync";
    }

    breadcrumbs.push({ label, href: currentPath });
  }

  return breadcrumbs;
}

export function Header() {
  const pathname = usePathname();
  const breadcrumbs = getBreadcrumbs(pathname);

  return (
    <header className="h-14 px-6 border-b border-border flex items-center justify-between bg-surface">
      {/* Breadcrumbs */}
      <nav className="flex items-center gap-1 text-sm">
        <span className="text-text-secondary">
          {pathname === "/" ? "Dashboard" : ""}
        </span>
        {breadcrumbs.map((crumb, index) => (
          <span key={crumb.href} className="flex items-center gap-1">
            {index > 0 && (
              <ChevronRight className="w-4 h-4 text-text-secondary" />
            )}
            <span
              className={
                index === breadcrumbs.length - 1
                  ? "text-text-primary"
                  : "text-text-secondary"
              }
            >
              {crumb.label}
            </span>
          </span>
        ))}
      </nav>

      {/* Actions */}
      <div className="flex items-center gap-2">
        {/* Placeholder for sync status / actions */}
      </div>
    </header>
  );
}
