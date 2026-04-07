# Code Review and Todo Standards

## Code Review Principles

- Focus on correctness, security, and maintainability before style-only feedback.
- Prefer specific, actionable comments over vague feedback.
- When suggesting changes:
  - Explain why the change is needed.
  - Provide a concrete example fix when possible.
- Avoid over-refactoring in a single change; keep suggestions scoped and feasible.

## Review Style

- Use clear, concise language; avoid generic comments like "improve this" without details.
- Distinguish between:
  - Must fix: bugs, security issues, broken contracts, missing validation.
  - Should fix: performance issues, confusing logic, complex flows.
  - Nice to have: style cleanups, minor refactors.
- When reviewing AI-generated changes, verify:
  - Types and models are consistent across layers.
  - Error handling covers edge cases, not just the happy path.
  - No silent failures or swallowed exceptions.

## Todo and Task Management

- Use a todo list for any task that:
  - Touches multiple files, or
  - Has more than 3 meaningful steps, or
  - Involves refactoring or architectural changes.
- Todos must be:
  - Short and action-oriented (e.g., "Add validation for user input", not "validation").
  - Tracked with clear status: `pending`, `in_progress`, `completed`, `cancelled`.
- Only one todo should be `in_progress` at a time.
- Mark todos as `completed` immediately after finishing, and create follow-up todos if new work is discovered.

## Pull Requests and Testing

- Before finalizing a change, ensure:
  - All relevant tests are run (unit/integration where applicable).
  - Edge cases and error paths are considered, not just the happy path.
- For each change, be ready to summarize:
  - What was changed.
  - Why it was changed.
  - How it was tested (or why tests are not applicable).

