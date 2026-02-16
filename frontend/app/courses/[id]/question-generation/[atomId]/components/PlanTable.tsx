"use client";

import {
  ListChecks,
  CheckCircle2,
  XCircle,
} from "lucide-react";
import { cn } from "@/lib/utils";
import type { PlanSlot, GeneratedItem } from "@/lib/api-types-question-gen";
import { DifficultyBadge } from "./EnrichmentSection";
import { CollapsibleSection, formatTag, formatContext } from "./shared";

interface PlanTableProps {
  slots: PlanSlot[];
  generatedItems: GeneratedItem[] | null;
  onSlotClick: (slotIndex: number) => void;
}

export function PlanTable({
  slots,
  generatedItems,
  onSlotClick,
}: PlanTableProps) {
  // Build a set of generated slot indices for status display
  const generatedSlots = new Set(
    generatedItems?.map((item) => item.slot_index) ?? [],
  );

  // Difficulty distribution summary
  const distribution = { easy: 0, medium: 0, hard: 0 };
  for (const slot of slots) {
    if (slot.difficulty_level in distribution) {
      distribution[slot.difficulty_level as keyof typeof distribution]++;
    }
  }

  const subtitle = `${slots.length} slots — ${distribution.easy}E / ${distribution.medium}M / ${distribution.hard}H`;

  return (
    <CollapsibleSection
      icon={ListChecks}
      title="Generation Plan"
      subtitle={subtitle}
      defaultExpanded
    >
      <div className="overflow-x-auto">
          <table className="w-full min-w-[700px]">
            <thead>
              <tr className="border-t border-b border-border text-left text-[11px] text-text-secondary uppercase tracking-wide">
                <th className="px-3 py-2 font-medium w-12">#</th>
                <th className="px-3 py-2 font-medium">Difficulty</th>
                <th className="px-3 py-2 font-medium">Component</th>
                <th className="px-3 py-2 font-medium">Skeleton</th>
                <th className="px-3 py-2 font-medium">Context</th>
                <th className="px-3 py-2 font-medium">Numbers</th>
                <th className="px-3 py-2 font-medium">Exemplar</th>
                <th className="px-3 py-2 font-medium">Distance</th>
                <th className="px-3 py-2 font-medium text-center w-16">
                  Status
                </th>
              </tr>
            </thead>
            <tbody>
              {slots.map((slot) => (
                <SlotRow
                  key={slot.slot_index}
                  slot={slot}
                  generated={generatedSlots.has(slot.slot_index)}
                  onClick={onSlotClick}
                />
              ))}
            </tbody>
          </table>
        </div>
      </CollapsibleSection>
  );
}


// ---------------------------------------------------------------------------
// Single slot row
// ---------------------------------------------------------------------------

function SlotRow({
  slot,
  generated,
  onClick,
}: {
  slot: PlanSlot;
  generated: boolean;
  onClick: (slotIndex: number) => void;
}) {
  return (
    <tr
      onClick={() => generated && onClick(slot.slot_index)}
      className={cn(
        "border-b border-border text-xs transition-colors",
        generated
          ? "hover:bg-white/5 cursor-pointer"
          : "opacity-60",
      )}
    >
      <td className="px-3 py-2 text-text-secondary font-mono">
        {slot.slot_index}
      </td>
      <td className="px-3 py-2">
        <DifficultyBadge level={slot.difficulty_level} />
      </td>
      <td className="px-3 py-2 text-text-secondary">
        {formatTag(slot.component_tag)}
      </td>
      <td className="px-3 py-2 font-mono text-text-secondary">
        {slot.operation_skeleton_ast}
      </td>
      <td className="px-3 py-2 text-text-secondary">
        {formatContext(slot.surface_context)}
      </td>
      <td className="px-3 py-2 text-text-secondary">
        {formatContext(slot.numbers_profile)}
      </td>
      <td className="px-3 py-2 text-text-secondary">
        {slot.target_exemplar_id ?? "\u2014"}
      </td>
      <td className="px-3 py-2 text-text-secondary">
        {slot.distance_level ?? "\u2014"}
      </td>
      <td className="px-3 py-2 text-center">
        {generated ? (
          <CheckCircle2 className="w-3.5 h-3.5 text-success inline-block" />
        ) : (
          <XCircle className="w-3.5 h-3.5 text-error/50 inline-block" />
        )}
      </td>
    </tr>
  );
}


