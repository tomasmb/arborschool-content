"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { ChevronRight, Home } from "lucide-react";
import { ReactNode } from "react";

/**
 * Format a URL segment into a readable label.
 * Handles course IDs, test IDs, and common path segments.
 */
function formatSegment(segment: string, context?: string): string {
  // Known static segments
  const staticLabels: Record<string, string> = {
    courses: "Courses",
    subjects: "Subjects",
    atoms: "Atoms",
    tests: "Tests",
    standards: "Standards",
    settings: "Settings",
    pipelines: "Pipelines",
    sync: "Sync",
  };

  if (staticLabels[segment]) {
    return staticLabels[segment];
  }

  // Course ID pattern: paes-m1-2026, paes-m2-2026, etc.
  const courseMatch = segment.match(/^(paes)-?(m\d+)-?(\d{4})$/i);
  if (courseMatch) {
    const [, , level, year] = courseMatch;
    return `PAES ${level.toUpperCase()} ${year}`;
  }

  // Test ID pattern: prueba-invierno-2025, etc.
  const testMatch = segment.match(/^prueba-(\w+)-(\d{4})$/i);
  if (testMatch) {
    const [, type, year] = testMatch;
    const typeFormatted = type.charAt(0).toUpperCase() + type.slice(1);
    return `Prueba ${typeFormatted} ${year}`;
  }

  // Fallback: capitalize and replace hyphens with spaces
  return segment
    .split("-")
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(" ");
}

interface Breadcrumb {
  label: string;
  href: string;
  isCurrent: boolean;
}

function getBreadcrumbs(pathname: string): Breadcrumb[] {
  const parts = pathname.split("/").filter(Boolean);
  const breadcrumbs: Breadcrumb[] = [];

  let currentPath = "";
  for (let i = 0; i < parts.length; i++) {
    const part = parts[i];
    currentPath += `/${part}`;

    // Determine context from previous segment
    const prevPart = i > 0 ? parts[i - 1] : undefined;

    const label = formatSegment(part, prevPart);
    const isCurrent = i === parts.length - 1;

    breadcrumbs.push({ label, href: currentPath, isCurrent });
  }

  return breadcrumbs;
}

interface HeaderProps {
  mobileMenuButton?: ReactNode;
}

export function Header({ mobileMenuButton }: HeaderProps) {
  const pathname = usePathname();
  const breadcrumbs = getBreadcrumbs(pathname);

  return (
    <header className="h-14 px-4 md:px-6 border-b border-border flex items-center justify-between bg-surface">
      {/* Left side: Mobile menu + breadcrumbs */}
      <div className="flex items-center gap-2">
        {mobileMenuButton}

        {/* Breadcrumbs */}
        <nav className="flex items-center gap-1 text-sm">
          {/* Home link */}
          <Link
            href="/"
            className="text-text-secondary hover:text-text-primary transition-colors hidden sm:flex items-center"
          >
            <Home className="w-4 h-4" />
          </Link>

          {breadcrumbs.map((crumb, index) => (
            <span key={crumb.href} className="flex items-center gap-1">
              <ChevronRight className="w-4 h-4 text-text-secondary hidden sm:block" />
              {/* On mobile, only show the last breadcrumb */}
              {crumb.isCurrent ? (
                <span className="text-text-primary font-medium">
                  {crumb.label}
                </span>
              ) : (
                <Link
                  href={crumb.href}
                  className="text-text-secondary hover:text-text-primary transition-colors hidden sm:inline"
                >
                  {crumb.label}
                </Link>
              )}
            </span>
          ))}

          {/* Mobile: only show current breadcrumb */}
          {breadcrumbs.length > 0 && (
            <span className="text-text-primary font-medium sm:hidden">
              {breadcrumbs[breadcrumbs.length - 1].label}
            </span>
          )}
        </nav>
      </div>

      {/* Right side: Reserved for future actions */}
      <div className="flex items-center gap-2" />
    </header>
  );
}
