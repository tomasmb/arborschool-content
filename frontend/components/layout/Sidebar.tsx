"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard,
  BookOpen,
  Layers,
  FileText,
  Settings,
  ArrowLeft,
  Menu,
  X,
  GraduationCap,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { useEffect } from "react";

interface SidebarProps {
  isOpen?: boolean;
  onClose?: () => void;
}

export function Sidebar({ isOpen = true, onClose }: SidebarProps) {
  const pathname = usePathname();

  // Close mobile sidebar when route changes
  useEffect(() => {
    if (onClose) onClose();
  }, [pathname, onClose]);

  // Determine if we're inside a course
  const courseMatch = pathname.match(/^\/courses\/([^/]+)/);
  const courseId = courseMatch ? courseMatch[1] : null;
  const isInsideCourse = !!courseId;

  // Course navigation items (shown when inside a course)
  const courseNavItems = courseId
    ? [
        { href: `/courses/${courseId}`, label: "Overview", icon: BookOpen, exact: true },
        { href: `/courses/${courseId}/standards`, label: "Standards", icon: GraduationCap },
        { href: `/courses/${courseId}/atoms`, label: "Atoms", icon: Layers },
        { href: `/courses/${courseId}/tests`, label: "Tests", icon: FileText },
        { href: `/courses/${courseId}/settings`, label: "Settings", icon: Settings },
      ]
    : [];

  // Dashboard navigation (shown when on dashboard)
  const dashboardNavItems = [
    { href: "/", label: "Dashboard", icon: LayoutDashboard, exact: true },
  ];

  const navItems = isInsideCourse ? courseNavItems : dashboardNavItems;

  // Format course ID for display (e.g., "paes-m1-2026" -> "PAES M1 2026")
  const formatCourseId = (id: string) => {
    return id
      .split("-")
      .map((part) => {
        if (part.match(/^m\d+$/i)) return part.toUpperCase();
        if (part.match(/^\d+$/)) return part;
        return part.charAt(0).toUpperCase() + part.slice(1);
      })
      .join(" ");
  };

  return (
    <>
      {/* Mobile backdrop */}
      {isOpen && onClose && (
        <div
          className="fixed inset-0 bg-black/50 z-40 lg:hidden"
          onClick={onClose}
        />
      )}

      {/* Sidebar */}
      <aside
        className={cn(
          "fixed lg:static inset-y-0 left-0 z-50 w-64 bg-surface border-r border-border flex flex-col",
          "transform transition-transform duration-200 ease-in-out lg:transform-none",
          isOpen ? "translate-x-0" : "-translate-x-full lg:translate-x-0"
        )}
      >
        {/* Logo */}
        <div className="h-14 px-4 flex items-center justify-between border-b border-border">
          <Link href="/" className="flex items-center gap-2">
            <div className="w-8 h-8 bg-accent rounded-lg flex items-center justify-center">
              <span className="text-white font-bold text-sm">A</span>
            </div>
            <span className="font-semibold text-text-primary">
              Arbor Content
            </span>
          </Link>
          {/* Mobile close button */}
          {onClose && (
            <button
              onClick={onClose}
              className="lg:hidden p-1 hover:bg-white/10 rounded transition-colors"
            >
              <X className="w-5 h-5" />
            </button>
          )}
        </div>

        {/* Navigation */}
        <nav className="flex-1 p-3 space-y-1 overflow-y-auto">
          {/* Back to Dashboard (when inside course) */}
          {isInsideCourse && (
            <>
              <Link
                href="/"
                className={cn(
                  "flex items-center gap-3 px-3 py-2 rounded-lg text-sm",
                  "text-text-secondary hover:text-text-primary hover:bg-white/5 transition-colors"
                )}
              >
                <ArrowLeft className="w-4 h-4" />
                Dashboard
              </Link>

              {/* Course header */}
              <div className="px-3 py-3 mt-2">
                <p className="text-xs text-text-secondary uppercase tracking-wide mb-1">
                  Course
                </p>
                <p className="font-semibold text-sm">
                  {formatCourseId(courseId)}
                </p>
              </div>

              <div className="border-t border-border my-2" />
            </>
          )}

          {/* Nav items */}
          {navItems.map((item) => {
            const isActive = item.exact
              ? pathname === item.href
              : pathname.startsWith(item.href);
            const Icon = item.icon;

            return (
              <Link
                key={item.href}
                href={item.href}
                className={cn(
                  "flex items-center gap-3 px-3 py-2 rounded-lg text-sm transition-colors",
                  isActive
                    ? "bg-accent/10 text-accent"
                    : "text-text-secondary hover:text-text-primary hover:bg-white/5"
                )}
              >
                <Icon className="w-4 h-4" />
                {item.label}
              </Link>
            );
          })}
        </nav>

        {/* Footer */}
        <div className="p-4 border-t border-border">
          <p className="text-xs text-text-secondary">v0.1.0</p>
        </div>
      </aside>
    </>
  );
}

// Mobile menu button component
export function MobileMenuButton({ onClick }: { onClick: () => void }) {
  return (
    <button
      onClick={onClick}
      className="lg:hidden p-2 hover:bg-white/10 rounded-lg transition-colors"
    >
      <Menu className="w-5 h-5" />
    </button>
  );
}
