import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

/**
 * Merge Tailwind CSS classes with clsx.
 */
export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

/**
 * Format a number as a percentage string.
 */
export function formatPercent(value: number): string {
  return `${value.toFixed(1)}%`;
}

/**
 * Format eje name for display.
 */
export function formatEje(eje: string): string {
  const names: Record<string, string> = {
    numeros: "Números",
    algebra_y_funciones: "Álgebra y Funciones",
    geometria: "Geometría",
    probabilidad_y_estadistica: "Probabilidad y Estadística",
  };
  return names[eje] || eje;
}

/**
 * Get color class for eje.
 */
export function getEjeColor(eje: string): string {
  const colors: Record<string, string> = {
    numeros: "text-blue-400",
    algebra_y_funciones: "text-purple-400",
    geometria: "text-green-400",
    probabilidad_y_estadistica: "text-orange-400",
  };
  return colors[eje] || "text-gray-400";
}

/**
 * Get background color class for eje.
 */
export function getEjeBgColor(eje: string): string {
  const colors: Record<string, string> = {
    numeros: "bg-blue-500/10",
    algebra_y_funciones: "bg-purple-500/10",
    geometria: "bg-green-500/10",
    probabilidad_y_estadistica: "bg-orange-500/10",
  };
  return colors[eje] || "bg-gray-500/10";
}
