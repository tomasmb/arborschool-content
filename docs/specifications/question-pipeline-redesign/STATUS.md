# Question Pipeline Redesign - Status Tracker

> **Purpose**: This is the main tracking document for the question pipeline redesign.
> Update this file as tasks are completed.

## Quick Links

| Document | Description | Status |
|----------|-------------|--------|
| [00-overview.md](./00-overview.md) | Architecture, data model, pipeline flow | Reference |
| [01-cleanup-tasks.md](./01-cleanup-tasks.md) | Remove old feedback, clean modules | Complete |
| [02-backend-core.md](./02-backend-core.md) | `app/question_feedback/` module | Complete |
| [03-variant-integration.md](./03-variant-integration.md) | Integrate feedback into variants | Complete |
| [04-api-endpoints.md](./04-api-endpoints.md) | Enrichment, validation, sync endpoints | Complete |
| [05-frontend-test-detail.md](./05-frontend-test-detail.md) | Test detail page enhancements | Not Started |
| [06-frontend-question-panel.md](./06-frontend-question-panel.md) | Question panel tabs | Not Started |
| [07-migration.md](./07-migration.md) | Database migration | Not Started |
| [frontend-types.md](./frontend-types.md) | TypeScript types for frontend | Reference |
| [Appendix-A-example-qti.xml](./Appendix-A-example-qti.xml) | Example QTI with feedback | Reference |

---

## Overall Progress

```
Phase 0: Cleanup           [x] Complete
Phase 1: Backend Core      [x] Complete
Phase 2: Variant Integration [x] Complete
Phase 3: API Endpoints     [x] Complete
Phase 4: Frontend - Test   [ ] Not Started
Phase 5: Frontend - Panel  [ ] Not Started
Phase 6: Migration         [ ] Not Started
```

---

## Session Log

| Date | Session | Tasks Completed | Notes |
|------|---------|-----------------|-------|
| 2026-02-04 | 1 | Task 1.1: Removed feedback from 261 metadata_tags.json files | One-shot script, deleted after use |
| 2026-02-04 | 2 | Tasks 1.2-1.7: Full cleanup of sync, API, and frontend | Removed feedback/correct_answer/title fields from all layers |
| 2026-02-04 | 3 | Tasks 2.1-2.7: Created app/question_feedback/ module | FeedbackEnhancer, FinalValidator, QuestionPipeline, utils |
| 2026-02-04 | 4 | Task 3: Variant Integration | Integrated QuestionPipeline into VariantPipeline, added VariantResult model |
| 2026-02-04 | 5 | Phase 3: API Endpoints | Created enrichment/validation/sync services, tests router, updated question detail |

---

## Design Decisions Log

Track key decisions made during implementation:

| Date | Decision | Rationale | Documented In |
|------|----------|-----------|---------------|
| 2026-02-04 | GPT 5.1 for all LLM tasks | Best balance of cost/quality, reasoning_effort control | 00-overview.md |
| 2026-02-04 | QTI XML is single source of truth | Eliminates redundancy, feedback embedded in XML | 00-overview.md |
| 2026-02-04 | XSD validation after every XML change | Catch structural issues early | 00-overview.md |

---

## Open Questions

1. **Retry strategy for final validation**: If final validation fails, should we retry enhancement?
2. **Human review queue**: Should failed questions go to a human review queue?
3. **Cost monitoring**: Add cost tracking per question/test/day?

---

## Final Cleanup (After All Phases Complete)

**Do this AFTER everything is working in production:**

- [ ] Delete `examples/` folder (contains old feedback_system prototype)
- [ ] Remove any dead code from cleanup that was missed
- [ ] Verify no unused imports/functions remain
- [ ] Archive or delete this spec folder if no longer needed

---

## How to Use These Specs with Cursor

### Recommended Session Workflow

1. **Start session**: Read the relevant task document (e.g., `01-cleanup-tasks.md`)
2. **Generate plan**: Use Cursor's Plan Mode to create implementation plan
3. **Review**: Edit the plan if needed before executing
4. **Execute**: Work through tasks incrementally
5. **Verify**: Check acceptance criteria are met
6. **Update STATUS.md**: Mark task complete, log session

### Context Loading

For each session, provide Cursor with:
- This STATUS.md (for context)
- The specific task document you're working on
- The 00-overview.md (if architectural context is needed)
