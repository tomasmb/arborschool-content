# Task 05: Frontend - Test Detail Page

> **Type**: Implementation Task
> **Prerequisites**: [04-api-endpoints.md](./04-api-endpoints.md) completed
> **Estimated Sessions**: 2-3

## Context

Update the test detail page to show enrichment/validation status and add new actions
for enrichment, validation, and sync.

## Acceptance Criteria

- [ ] Questions table shows "Enriched" and "Validated" columns
- [ ] Pipeline status bar includes "Enriched" and "Validated" stages
- [ ] Actions menu has "Enrich Feedback", "Run Validation", "Sync Test" options
- [ ] EnrichmentModal shows cost estimate and progress
- [ ] ValidationModal shows progress and detailed results
- [ ] TestSyncModal shows diff preview before sync
- [ ] All modals handle errors gracefully

---

## Files to Modify

- `frontend/app/courses/[id]/tests/[testId]/page.tsx`

## Files to Create

- `frontend/components/pipelines/EnrichmentModal.tsx`
- `frontend/components/pipelines/ValidationModal.tsx`
- `frontend/components/pipelines/TestSyncModal.tsx`

---

## 5.1 Update Questions Table

Add two new columns to the questions table:

| Q# | Split | QTI | Final | Tagged | Atoms | **Enriched** | **Validated** | Variants |
|----|-------|-----|-------|--------|-------|--------------|---------------|----------|
| Q1 | ✓ | ✓ | ✓ | ✓ | 2 | ✓ | ✓ | 3 |
| Q2 | ✓ | ✓ | ✓ | ✓ | 1 | ✓ | ✗ | 0 |
| Q3 | ✓ | ✓ | ✓ | ✗ | - | - | - | 0 |

### Implementation

```tsx
// In questions table columns definition
const columns = [
  // ... existing columns
  {
    header: "Enriched",
    cell: ({ row }) => (
      <StatusIcon 
        status={row.is_enriched} 
        disabled={!row.is_tagged}
        tooltip={row.is_enriched ? "Feedback added" : "No feedback yet"}
      />
    )
  },
  {
    header: "Validated",
    cell: ({ row }) => (
      <StatusIcon 
        status={row.is_validated} 
        disabled={!row.is_enriched}
        tooltip={
          row.is_validated 
            ? "Ready to sync" 
            : row.validation_failed 
              ? "Validation failed" 
              : "Not validated"
        }
      />
    )
  },
  // ... rest of columns
];
```

---

## 5.2 Update Pipeline Status Bar

Add "Enriched" and "Validated" stages:

```
┌────────┐   ┌────────┐   ┌────────┐   ┌────────┐   ┌──────────┐   ┌───────────┐
│  Split │ → │  QTI   │ → │ Final  │ → │ Tagged │ → │ Enriched │ → │ Validated │
│   45   │   │   45   │   │   45   │   │  40/45 │   │   30/45  │   │   25/45   │
└────────┘   └────────┘   └────────┘   └────────┘   └──────────┘   └───────────┘
```

### Implementation

```tsx
// Update PipelineStatusBar component
interface PipelineStats {
  split_count: number;
  qti_count: number;
  finalized_count: number;
  tagged_count: number;
  enriched_count: number;  // NEW
  validated_count: number; // NEW
  total: number;
}

const PipelineStatusBar = ({ stats }: { stats: PipelineStats }) => (
  <div className="flex gap-2">
    <PipelineStage label="Split" count={stats.split_count} total={stats.total} />
    <PipelineArrow />
    <PipelineStage label="QTI" count={stats.qti_count} total={stats.total} />
    <PipelineArrow />
    <PipelineStage label="Final" count={stats.finalized_count} total={stats.total} />
    <PipelineArrow />
    <PipelineStage label="Tagged" count={stats.tagged_count} total={stats.total} />
    <PipelineArrow />
    <PipelineStage label="Enriched" count={stats.enriched_count} total={stats.total} />
    <PipelineArrow />
    <PipelineStage label="Validated" count={stats.validated_count} total={stats.total} />
  </div>
);
```

---

## 5.3 Update Actions Menu

```tsx
<ActionsMenu>
  <ActionItem 
    icon={RefreshCw} 
    label="Regenerate QTI" 
    disabled={stats.split_count === 0} 
  />
  <ActionItem 
    icon={Tag} 
    label="Regenerate Tags" 
    disabled={stats.finalized_count === 0} 
  />
  <Separator />
  {/* NEW ACTIONS */}
  <ActionItem 
    icon={MessageSquarePlus} 
    label="Enrich Feedback" 
    disabled={stats.tagged_count === 0}
    onClick={() => setEnrichmentModalOpen(true)}
  />
  <ActionItem 
    icon={ShieldCheck} 
    label="Run Validation" 
    disabled={stats.enriched_count === 0}
    onClick={() => setValidationModalOpen(true)}
  />
  <Separator />
  <ActionItem 
    icon={Sparkles} 
    label="Generate Variants" 
    disabled={stats.tagged_count === 0} 
  />
  <Separator />
  <ActionItem 
    icon={Upload} 
    label="Sync Test to DB" 
    disabled={stats.validated_count === 0}
    onClick={() => setSyncModalOpen(true)}
  />
</ActionsMenu>
```

---

## 5.4 EnrichmentModal Component

```tsx
// frontend/components/pipelines/EnrichmentModal.tsx
"use client";

import { useState } from "react";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group";
import { Progress } from "@/components/ui/progress";

interface EnrichmentModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  testId: string;
  subjectId: string;
  stats: {
    tagged_count: number;
    enriched_count: number;
  };
}

type EnrichmentStep = "configure" | "progress" | "results";

export function EnrichmentModal({ 
  open, 
  onOpenChange, 
  testId, 
  subjectId,
  stats 
}: EnrichmentModalProps) {
  const [step, setStep] = useState<EnrichmentStep>("configure");
  const [selection, setSelection] = useState<"all" | "unenriched" | "specific">("all");
  const [jobId, setJobId] = useState<string | null>(null);
  const [progress, setProgress] = useState({ completed: 0, total: 0, failed: 0 });
  const [results, setResults] = useState<any[]>([]);

  const questionsToProcess = selection === "all" 
    ? stats.tagged_count 
    : stats.tagged_count - stats.enriched_count;
  
  const estimatedCost = questionsToProcess * 0.024; // $0.024 per question

  const startEnrichment = async () => {
    const response = await fetch(
      `/api/subjects/${subjectId}/tests/${testId}/enrich`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          all_tagged: selection === "all",
          skip_already_enriched: selection === "unenriched"
        })
      }
    );
    const data = await response.json();
    setJobId(data.job_id);
    setStep("progress");
    pollProgress(data.job_id);
  };

  const pollProgress = async (jid: string) => {
    // Poll every 2 seconds until complete
    const interval = setInterval(async () => {
      const response = await fetch(
        `/api/subjects/${subjectId}/tests/${testId}/enrich/status/${jid}`
      );
      const data = await response.json();
      
      setProgress({
        completed: data.progress.completed,
        total: data.progress.total,
        failed: data.progress.failed
      });
      
      if (data.status === "completed") {
        clearInterval(interval);
        setResults(data.results);
        setStep("results");
      }
    }, 2000);
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-lg">
        <DialogHeader>
          <DialogTitle>
            {step === "configure" && "Enrich Questions with Feedback"}
            {step === "progress" && "Enriching Questions..."}
            {step === "results" && "Enrichment Complete"}
          </DialogTitle>
        </DialogHeader>

        {step === "configure" && (
          <div className="space-y-4">
            <p className="text-sm text-muted-foreground">
              This will add educational feedback to questions:
            </p>
            <ul className="text-sm list-disc list-inside space-y-1">
              <li>Per-choice rationales (why each answer is right/wrong)</li>
              <li>Step-by-step worked solutions</li>
            </ul>

            <RadioGroup value={selection} onValueChange={(v) => setSelection(v as any)}>
              <div className="flex items-center space-x-2">
                <RadioGroupItem value="all" id="all" />
                <label htmlFor="all">All tagged questions ({stats.tagged_count})</label>
              </div>
              <div className="flex items-center space-x-2">
                <RadioGroupItem value="unenriched" id="unenriched" />
                <label htmlFor="unenriched">
                  Only questions without feedback ({stats.tagged_count - stats.enriched_count})
                </label>
              </div>
            </RadioGroup>

            <div className="bg-muted p-3 rounded-md">
              <p className="text-sm font-medium">Cost Estimate</p>
              <p className="text-sm">Questions: {questionsToProcess}</p>
              <p className="text-sm">Model: GPT 5.1 (medium reasoning)</p>
              <p className="text-sm font-medium">
                Estimated cost: ~${estimatedCost.toFixed(2)}
              </p>
            </div>

            <div className="flex justify-end gap-2">
              <Button variant="outline" onClick={() => onOpenChange(false)}>
                Cancel
              </Button>
              <Button onClick={startEnrichment}>
                Start Enrichment
              </Button>
            </div>
          </div>
        )}

        {step === "progress" && (
          <div className="space-y-4">
            <Progress value={(progress.completed / progress.total) * 100} />
            <p className="text-sm">
              Progress: {progress.completed}/{progress.total} questions
            </p>
            {progress.failed > 0 && (
              <p className="text-sm text-destructive">
                {progress.failed} questions failed XSD validation
              </p>
            )}
          </div>
        )}

        {step === "results" && (
          <div className="space-y-4">
            <div className="space-y-2">
              <p className="text-sm text-green-600">
                ✓ {results.filter(r => r.status === "success").length} questions enriched
              </p>
              {results.filter(r => r.status === "failed").length > 0 && (
                <p className="text-sm text-destructive">
                  ✗ {results.filter(r => r.status === "failed").length} questions failed
                </p>
              )}
            </div>

            <p className="text-sm text-muted-foreground">
              Next step: Run Validation to verify content quality
            </p>

            <div className="flex justify-end">
              <Button onClick={() => onOpenChange(false)}>Close</Button>
            </div>
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
}
```

---

## 5.5 ValidationModal Component

```tsx
// frontend/components/pipelines/ValidationModal.tsx
"use client";

import { useState } from "react";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group";
import { Progress } from "@/components/ui/progress";
import { CheckCircle, XCircle, Download } from "lucide-react";

interface ValidationModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  testId: string;
  subjectId: string;
  stats: {
    enriched_count: number;
    validated_count: number;
  };
}

type ValidationStep = "configure" | "progress" | "results";

export function ValidationModal({ 
  open, 
  onOpenChange, 
  testId, 
  subjectId,
  stats 
}: ValidationModalProps) {
  const [step, setStep] = useState<ValidationStep>("configure");
  const [selection, setSelection] = useState<"all" | "unvalidated" | "revalidate">("unvalidated");
  const [jobId, setJobId] = useState<string | null>(null);
  const [progress, setProgress] = useState({ completed: 0, total: 0, passed: 0, failed: 0 });
  const [results, setResults] = useState<any[]>([]);

  const questionsToValidate = selection === "revalidate" 
    ? stats.enriched_count 
    : stats.enriched_count - stats.validated_count;
  
  // $0.015 per question for validation (high reasoning)
  const estimatedCost = questionsToValidate * 0.015;

  const startValidation = async () => {
    const response = await fetch(
      `/api/subjects/${subjectId}/tests/${testId}/validate`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          all_enriched: selection === "all" || selection === "revalidate",
          revalidate_passed: selection === "revalidate"
        })
      }
    );
    const data = await response.json();
    setJobId(data.job_id);
    setStep("progress");
    pollProgress(data.job_id);
  };

  const pollProgress = async (jid: string) => {
    const interval = setInterval(async () => {
      const response = await fetch(
        `/api/subjects/${subjectId}/tests/${testId}/validate/status/${jid}`
      );
      const data = await response.json();
      
      setProgress({
        completed: data.progress.completed,
        total: data.progress.total,
        passed: data.progress.passed,
        failed: data.progress.failed
      });
      
      if (data.status === "completed") {
        clearInterval(interval);
        setResults(data.results);
        setStep("results");
      }
    }, 2000);
  };

  const exportReport = () => {
    const failedResults = results.filter(r => r.status === "fail");
    const report = {
      test_id: testId,
      timestamp: new Date().toISOString(),
      summary: { total: results.length, passed: progress.passed, failed: progress.failed },
      failed_questions: failedResults
    };
    
    const blob = new Blob([JSON.stringify(report, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `validation-report-${testId}.json`;
    a.click();
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-lg">
        <DialogHeader>
          <DialogTitle>
            {step === "configure" && "Validate Questions"}
            {step === "progress" && "Validating Questions..."}
            {step === "results" && "Validation Complete"}
          </DialogTitle>
        </DialogHeader>

        {step === "configure" && (
          <div className="space-y-4">
            <p className="text-sm text-muted-foreground">
              Final validation checks:
            </p>
            <ul className="text-sm list-disc list-inside space-y-1 text-muted-foreground">
              <li>Correct answer is mathematically correct</li>
              <li>Feedback accurately explains right/wrong</li>
              <li>No typos or character issues</li>
              <li>Images align with question stem</li>
            </ul>

            <RadioGroup value={selection} onValueChange={(v) => setSelection(v as any)}>
              <div className="flex items-center space-x-2">
                <RadioGroupItem value="unvalidated" id="unvalidated" />
                <label htmlFor="unvalidated">
                  Only unvalidated questions ({stats.enriched_count - stats.validated_count})
                </label>
              </div>
              <div className="flex items-center space-x-2">
                <RadioGroupItem value="all" id="all" />
                <label htmlFor="all">All enriched questions ({stats.enriched_count})</label>
              </div>
              <div className="flex items-center space-x-2">
                <RadioGroupItem value="revalidate" id="revalidate" />
                <label htmlFor="revalidate">Re-validate all (including passed)</label>
              </div>
            </RadioGroup>

            <div className="bg-muted p-3 rounded-md">
              <p className="text-sm font-medium">Cost Estimate</p>
              <p className="text-sm">Questions: {questionsToValidate}</p>
              <p className="text-sm">Model: GPT 5.1 (high reasoning)</p>
              <p className="text-sm font-medium">
                Estimated cost: ~${estimatedCost.toFixed(2)}
              </p>
            </div>

            <div className="flex justify-end gap-2">
              <Button variant="outline" onClick={() => onOpenChange(false)}>
                Cancel
              </Button>
              <Button onClick={startValidation} disabled={questionsToValidate === 0}>
                Start Validation
              </Button>
            </div>
          </div>
        )}

        {step === "progress" && (
          <div className="space-y-4">
            <Progress value={(progress.completed / progress.total) * 100} />
            <p className="text-sm">
              Progress: {progress.completed}/{progress.total} questions
            </p>
            <div className="flex gap-4 text-sm">
              <span className="text-green-600">✓ {progress.passed} passed</span>
              <span className="text-red-600">✗ {progress.failed} failed</span>
            </div>
          </div>
        )}

        {step === "results" && (
          <div className="space-y-4">
            <div className="flex gap-4">
              <div className="flex items-center gap-2 text-green-600">
                <CheckCircle className="w-5 h-5" />
                <span>{progress.passed} passed</span>
              </div>
              <div className="flex items-center gap-2 text-red-600">
                <XCircle className="w-5 h-5" />
                <span>{progress.failed} failed</span>
              </div>
            </div>

            {progress.failed > 0 && (
              <div className="max-h-48 overflow-y-auto border rounded-md">
                {results.filter(r => r.status === "fail").map((r, i) => (
                  <div key={i} className="p-2 border-b last:border-b-0">
                    <p className="font-medium text-sm">{r.question_id}</p>
                    <p className="text-xs text-muted-foreground">
                      Failed: {r.failed_checks?.join(", ")}
                    </p>
                    {r.issues?.[0] && (
                      <p className="text-xs text-red-600 mt-1">{r.issues[0]}</p>
                    )}
                  </div>
                ))}
              </div>
            )}

            <p className="text-sm text-muted-foreground">
              {progress.passed} questions ready to sync
            </p>

            <div className="flex justify-end gap-2">
              {progress.failed > 0 && (
                <Button variant="outline" size="sm" onClick={exportReport}>
                  <Download className="w-4 h-4 mr-2" />
                  Export Report
                </Button>
              )}
              <Button onClick={() => onOpenChange(false)}>Close</Button>
            </div>
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
}
```

---

## 5.6 TestSyncModal Component

```tsx
// frontend/components/pipelines/TestSyncModal.tsx
"use client";

import { useState, useEffect } from "react";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { AlertTriangle, Plus, Edit, Minus } from "lucide-react";

interface TestSyncModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  testId: string;
  subjectId: string;
  stats: {
    validated_count: number;
    total: number;
  };
}

type SyncStep = "loading" | "preview" | "syncing" | "complete";

interface SyncPreview {
  questions: {
    to_create: any[];
    to_update: any[];
    unchanged: any[];
    skipped: any[];
  };
  summary: {
    create: number;
    update: number;
    unchanged: number;
    skipped: number;
  };
}

export function TestSyncModal({ 
  open, 
  onOpenChange, 
  testId, 
  subjectId,
  stats 
}: TestSyncModalProps) {
  const [step, setStep] = useState<SyncStep>("loading");
  const [preview, setPreview] = useState<SyncPreview | null>(null);
  const [includeVariants, setIncludeVariants] = useState(true);
  const [uploadImages, setUploadImages] = useState(true);
  const [syncResult, setSyncResult] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);

  // Load preview when modal opens
  useEffect(() => {
    if (open) {
      loadPreview();
    }
  }, [open]);

  const loadPreview = async () => {
    setStep("loading");
    setError(null);
    
    try {
      const response = await fetch(
        `/api/subjects/${subjectId}/tests/${testId}/sync/preview`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ include_variants: includeVariants, upload_images: uploadImages })
        }
      );
      
      if (!response.ok) throw new Error("Failed to load preview");
      
      const data = await response.json();
      setPreview(data);
      setStep("preview");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load preview");
      setStep("preview");
    }
  };

  const executeSync = async () => {
    setStep("syncing");
    
    try {
      const response = await fetch(
        `/api/subjects/${subjectId}/tests/${testId}/sync/execute`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ include_variants: includeVariants, upload_images: uploadImages })
        }
      );
      
      if (!response.ok) throw new Error("Sync failed");
      
      const data = await response.json();
      setSyncResult(data);
      setStep("complete");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Sync failed");
      setStep("preview");
    }
  };

  const canSync = stats.validated_count > 0;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-lg">
        <DialogHeader>
          <DialogTitle>Sync Test to Database</DialogTitle>
        </DialogHeader>

        {!canSync ? (
          <div className="space-y-4">
            <Alert variant="destructive">
              <AlertTriangle className="h-4 w-4" />
              <AlertDescription>
                Cannot sync - no validated questions
              </AlertDescription>
            </Alert>
            <p className="text-sm text-muted-foreground">
              To sync questions, you must:
            </p>
            <ol className="text-sm list-decimal list-inside space-y-1 text-muted-foreground">
              <li>Tag questions with atoms</li>
              <li>Run "Enrich Feedback" to add educational content</li>
              <li>Run "Validate" to verify quality</li>
            </ol>
            <div className="flex justify-end">
              <Button onClick={() => onOpenChange(false)}>Close</Button>
            </div>
          </div>
        ) : step === "loading" ? (
          <div className="py-8 text-center text-muted-foreground">
            Loading sync preview...
          </div>
        ) : step === "preview" && preview ? (
          <div className="space-y-4">
            {error && (
              <Alert variant="destructive">
                <AlertDescription>{error}</AlertDescription>
              </Alert>
            )}
            
            <div className="grid grid-cols-2 gap-2 text-sm">
              <div className="flex items-center gap-2 p-2 bg-green-50 rounded">
                <Plus className="w-4 h-4 text-green-600" />
                <span>Create: {preview.summary.create}</span>
              </div>
              <div className="flex items-center gap-2 p-2 bg-blue-50 rounded">
                <Edit className="w-4 h-4 text-blue-600" />
                <span>Update: {preview.summary.update}</span>
              </div>
              <div className="flex items-center gap-2 p-2 bg-gray-50 rounded">
                <Minus className="w-4 h-4 text-gray-400" />
                <span>Unchanged: {preview.summary.unchanged}</span>
              </div>
              <div className="flex items-center gap-2 p-2 bg-yellow-50 rounded">
                <AlertTriangle className="w-4 h-4 text-yellow-600" />
                <span>Skipped: {preview.summary.skipped}</span>
              </div>
            </div>

            {preview.summary.skipped > 0 && (
              <Alert>
                <AlertTriangle className="h-4 w-4" />
                <AlertDescription>
                  {preview.summary.skipped} questions will be skipped (not validated)
                </AlertDescription>
              </Alert>
            )}

            {preview.summary.update > 0 && (
              <p className="text-sm text-muted-foreground">
                ⚠️ {preview.summary.update} questions will be overwritten in database.
              </p>
            )}

            <div className="space-y-2 border-t pt-4">
              <div className="flex items-center space-x-2">
                <Checkbox 
                  id="variants" 
                  checked={includeVariants}
                  onCheckedChange={(c) => setIncludeVariants(!!c)}
                />
                <label htmlFor="variants" className="text-sm">Include approved variants</label>
              </div>
              <div className="flex items-center space-x-2">
                <Checkbox 
                  id="images" 
                  checked={uploadImages}
                  onCheckedChange={(c) => setUploadImages(!!c)}
                />
                <label htmlFor="images" className="text-sm">Upload images to S3 first</label>
              </div>
            </div>

            <div className="flex justify-end gap-2">
              <Button variant="outline" onClick={() => onOpenChange(false)}>
                Cancel
              </Button>
              <Button onClick={executeSync}>
                Sync {preview.summary.create + preview.summary.update} Questions
              </Button>
            </div>
          </div>
        ) : step === "syncing" ? (
          <div className="py-8 text-center text-muted-foreground">
            Syncing to database...
          </div>
        ) : step === "complete" && syncResult ? (
          <div className="space-y-4">
            <div className="text-center py-4">
              <p className="text-lg font-medium text-green-600">Sync Complete!</p>
            </div>
            
            <div className="grid grid-cols-3 gap-2 text-sm text-center">
              <div className="p-2 bg-green-50 rounded">
                <p className="font-medium">{syncResult.created}</p>
                <p className="text-muted-foreground">Created</p>
              </div>
              <div className="p-2 bg-blue-50 rounded">
                <p className="font-medium">{syncResult.updated}</p>
                <p className="text-muted-foreground">Updated</p>
              </div>
              <div className="p-2 bg-yellow-50 rounded">
                <p className="font-medium">{syncResult.skipped}</p>
                <p className="text-muted-foreground">Skipped</p>
              </div>
            </div>

            <div className="flex justify-end">
              <Button onClick={() => onOpenChange(false)}>Close</Button>
            </div>
          </div>
        ) : null}
      </DialogContent>
    </Dialog>
  );
}
```

---

## Summary Checklist

```
[ ] 5.1 Add Enriched/Validated columns to questions table
[ ] 5.2 Update pipeline status bar with new stages
[ ] 5.3 Add new actions to Actions menu
[ ] 5.4 Create EnrichmentModal component
[ ] 5.5 Create ValidationModal component
[ ] 5.6 Create TestSyncModal component
[ ] Update types in frontend/lib/api-types.ts
[ ] Test all modals with real API calls
[ ] Add error handling and loading states
```
