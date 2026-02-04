# Task 06: Frontend - Question Detail Panel

> **Type**: Implementation Task
> **Prerequisites**: [05-frontend-test-detail.md](./05-frontend-test-detail.md) completed
> **Estimated Sessions**: 1-2

## Context

Update the question detail panel (shown when clicking a question row) to display
feedback and validation details in a tabbed interface.

## Acceptance Criteria

- [ ] Panel shows tabs: Question | Feedback | Validation | Variants
- [ ] Status badges show enriched/validated/sync status
- [ ] Feedback tab displays per-choice feedback and worked solution
- [ ] Validation tab shows all check results
- [ ] Re-enrich and Re-validate action buttons work
- [ ] Graceful handling when feedback/validation not available

---

## Files to Modify

- `frontend/components/questions/QuestionDetailPanel.tsx`

## Files to Create

- `frontend/components/questions/FeedbackTab.tsx`
- `frontend/components/questions/ValidationTab.tsx`

---

## 6.1 Panel Structure

```
┌─────────────────────────────────────────────────────────────────┐
│  Q6 - Juego de bolitas                                     [X] │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Status: ✓ Enriched  ✓ Validated  ✓ Ready to sync              │
│                                                                 │
│  ┌──────────┬──────────┬────────────┬──────────┐               │
│  │ Question │ Feedback │ Validation │ Variants │               │
│  └──────────┴──────────┴────────────┴──────────┘               │
│                                                                 │
│  [Tab content here]                                             │
│                                                                 │
│                        [Re-enrich]  [Re-validate]               │
└─────────────────────────────────────────────────────────────────┘
```

---

## 6.2 Status Badges Component

```tsx
interface QuestionStatusProps {
  isEnriched: boolean;
  isValidated: boolean;
  canSync: boolean;
  syncStatus: "not_in_db" | "in_sync" | "local_changed" | "not_validated";
}

function QuestionStatusBadges({ 
  isEnriched, 
  isValidated, 
  canSync, 
  syncStatus 
}: QuestionStatusProps) {
  return (
    <div className="flex gap-2 items-center">
      <Badge variant={isEnriched ? "success" : "secondary"}>
        {isEnriched ? "✓ Enriched" : "Not Enriched"}
      </Badge>
      <Badge variant={isValidated ? "success" : "secondary"}>
        {isValidated ? "✓ Validated" : "Not Validated"}
      </Badge>
      <Badge variant={canSync ? "success" : "outline"}>
        {canSync ? "✓ Ready to sync" : syncStatus === "in_sync" ? "In sync" : "Cannot sync"}
      </Badge>
    </div>
  );
}
```

---

## 6.3 Tabbed Interface

```tsx
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";

function QuestionDetailPanel({ question }: { question: QuestionDetail }) {
  return (
    <div className="space-y-4">
      <QuestionStatusBadges 
        isEnriched={question.is_enriched}
        isValidated={question.is_validated}
        canSync={question.can_sync}
        syncStatus={question.sync_status}
      />
      
      <Tabs defaultValue="question">
        <TabsList>
          <TabsTrigger value="question">Question</TabsTrigger>
          <TabsTrigger value="feedback" disabled={!question.is_enriched}>
            Feedback
          </TabsTrigger>
          <TabsTrigger value="validation" disabled={!question.validation_result}>
            Validation
          </TabsTrigger>
          <TabsTrigger value="variants">
            Variants ({question.variants_count})
          </TabsTrigger>
        </TabsList>
        
        <TabsContent value="question">
          <QuestionPreview qtiXml={question.qti_xml} />
        </TabsContent>
        
        <TabsContent value="feedback">
          <FeedbackTab qtiXml={question.qti_xml} />
        </TabsContent>
        
        <TabsContent value="validation">
          <ValidationTab result={question.validation_result} />
        </TabsContent>
        
        <TabsContent value="variants">
          <VariantsTab questionId={question.id} />
        </TabsContent>
      </Tabs>
      
      <div className="flex justify-end gap-2">
        <Button variant="outline" size="sm" onClick={handleReEnrich}>
          Re-enrich
        </Button>
        <Button variant="outline" size="sm" onClick={handleReValidate}>
          Re-validate
        </Button>
      </div>
    </div>
  );
}
```

---

## 6.4 FeedbackTab Component

```tsx
// frontend/components/questions/FeedbackTab.tsx
"use client";

import { useMemo } from "react";
import { parseFeedbackFromQti } from "@/lib/qti-parser";

interface FeedbackTabProps {
  qtiXml: string;
}

export function FeedbackTab({ qtiXml }: FeedbackTabProps) {
  const feedback = useMemo(() => parseFeedbackFromQti(qtiXml), [qtiXml]);
  
  if (!feedback) {
    return (
      <div className="text-sm text-muted-foreground p-4">
        No feedback available. Run "Enrich Feedback" to add educational content.
      </div>
    );
  }
  
  return (
    <div className="space-y-6 p-4">
      {/* Per-choice feedback */}
      <section>
        <h3 className="font-medium mb-3">Per-choice feedback</h3>
        <div className="space-y-3">
          {feedback.choices.map((choice) => (
            <div 
              key={choice.identifier}
              className={`p-3 rounded-md border ${
                choice.isCorrect 
                  ? "border-green-200 bg-green-50" 
                  : "border-gray-200"
              }`}
            >
              <div className="flex items-center gap-2 mb-1">
                <span className="font-mono text-sm">{choice.identifier}</span>
                {choice.isCorrect && (
                  <span className="text-xs text-green-600">✓ Correct</span>
                )}
              </div>
              <p className="text-sm">{choice.feedbackText}</p>
            </div>
          ))}
        </div>
      </section>
      
      {/* Worked solution */}
      {feedback.workedSolution && (
        <section>
          <h3 className="font-medium mb-3">Worked solution</h3>
          <div className="p-3 bg-blue-50 rounded-md border border-blue-200">
            <div 
              className="prose prose-sm"
              dangerouslySetInnerHTML={{ __html: feedback.workedSolution }}
            />
          </div>
        </section>
      )}
    </div>
  );
}
```

---

## 6.5 ValidationTab Component

```tsx
// frontend/components/questions/ValidationTab.tsx
"use client";

import { CheckCircle, XCircle, MinusCircle } from "lucide-react";

interface ValidationTabProps {
  result: ValidationResult | null;
}

const statusIcons = {
  pass: <CheckCircle className="w-4 h-4 text-green-500" />,
  fail: <XCircle className="w-4 h-4 text-red-500" />,
  not_applicable: <MinusCircle className="w-4 h-4 text-gray-400" />
};

export function ValidationTab({ result }: ValidationTabProps) {
  if (!result) {
    return (
      <div className="text-sm text-muted-foreground p-4">
        No validation results. Run "Validate" to check question quality.
      </div>
    );
  }
  
  const checks = [
    { name: "Correct Answer", result: result.correct_answer_check },
    { name: "Feedback Quality", result: result.feedback_check },
    { name: "Content Quality", result: result.content_quality_check },
    { name: "Image Alignment", result: result.image_check },
    { name: "Math Validity", result: result.math_validity_check }
  ];
  
  return (
    <div className="space-y-4 p-4">
      {/* Overall result */}
      <div className={`p-3 rounded-md ${
        result.validation_result === "pass" 
          ? "bg-green-50 border border-green-200" 
          : "bg-red-50 border border-red-200"
      }`}>
        <div className="flex items-center gap-2">
          {result.validation_result === "pass" 
            ? <CheckCircle className="w-5 h-5 text-green-500" />
            : <XCircle className="w-5 h-5 text-red-500" />
          }
          <span className="font-medium">
            {result.validation_result === "pass" 
              ? "All checks passed" 
              : "Validation failed"
            }
          </span>
        </div>
      </div>
      
      {/* Individual checks */}
      <div className="space-y-2">
        {checks.map((check) => (
          <div 
            key={check.name}
            className="flex items-start gap-3 p-2 rounded border"
          >
            {statusIcons[check.result.status]}
            <div className="flex-1">
              <div className="font-medium text-sm">{check.name}</div>
              {check.result.issues?.length > 0 && (
                <ul className="text-sm text-red-600 mt-1 list-disc list-inside">
                  {check.result.issues.map((issue, i) => (
                    <li key={i}>{issue}</li>
                  ))}
                </ul>
              )}
              {check.result.reasoning && (
                <p className="text-sm text-muted-foreground mt-1">
                  {check.result.reasoning}
                </p>
              )}
            </div>
          </div>
        ))}
      </div>
      
      {/* Overall reasoning */}
      {result.overall_reasoning && (
        <div className="p-3 bg-muted rounded-md">
          <p className="text-sm font-medium mb-1">Summary</p>
          <p className="text-sm">{result.overall_reasoning}</p>
        </div>
      )}
    </div>
  );
}
```

---

## 6.6 QTI Parser Utility

Add to `frontend/lib/qti-parser.ts`:

```typescript
interface ChoiceFeedback {
  identifier: string;
  isCorrect: boolean;
  feedbackText: string;
}

interface ParsedFeedback {
  choices: ChoiceFeedback[];
  workedSolution: string | null;
}

export function parseFeedbackFromQti(qtiXml: string): ParsedFeedback | null {
  // Parse QTI XML to extract feedback-inline and feedback-block elements
  // This is a simplified version - real implementation would use a proper XML parser
  
  const parser = new DOMParser();
  const doc = parser.parseFromString(qtiXml, "text/xml");
  
  // Check for parse errors
  if (doc.querySelector("parsererror")) {
    return null;
  }
  
  // Extract correct answer
  const correctValue = doc.querySelector("qti-correct-response qti-value")?.textContent;
  
  // Extract choice feedback
  const choices: ChoiceFeedback[] = [];
  const choiceElements = doc.querySelectorAll("qti-simple-choice");
  
  choiceElements.forEach((choice) => {
    const identifier = choice.getAttribute("identifier") || "";
    const feedbackEl = choice.querySelector("qti-feedback-inline");
    const feedbackText = feedbackEl?.textContent?.trim() || "";
    
    choices.push({
      identifier,
      isCorrect: identifier === correctValue,
      feedbackText
    });
  });
  
  // Extract worked solution
  const solutionBlock = doc.querySelector('qti-feedback-block[outcome-identifier="SOLUTION"]');
  const workedSolution = solutionBlock?.innerHTML || null;
  
  if (choices.length === 0 && !workedSolution) {
    return null;
  }
  
  return { choices, workedSolution };
}
```

---

## Summary Checklist

```
[ ] 6.1 Add status badges component
[ ] 6.2 Implement tabbed interface in QuestionDetailPanel
[ ] 6.3 Create FeedbackTab component
[ ] 6.4 Create ValidationTab component
[ ] 6.5 Add QTI parser utility for feedback extraction
[ ] 6.6 Add Re-enrich and Re-validate buttons
[ ] Handle loading states for each tab
[ ] Test with real question data
```
