# GenAI-assisted development

How this project was built with a GenAI coding tool, and how its output was checked. The raw, chronological
evidence is in `docs/genai-journal.md`; this file is the summary, filled at the end of each build phase.

Status: in progress. Sections marked "pending" are filled when the phase that produces their evidence is done.

## 1. Tools and method

- Tool: Claude Code (terminal).
- Models: Claude Opus for the design conversation and for the build; Claude Fable 5.2 for the two reviews done
  before the build (journal entries 10 and 11). A different model reviewed the plan on purpose: it had no stake in
  the earlier decisions.
- Method: the design was agreed in conversation, one topic at a time, before any code. The decisions were distilled
  into `docs/implementation-prompt.md`, which was reviewed by a different model before the build and then given to
  a fresh session. Standing rules for the tool are in `CLAUDE.md`.

## 2. The prompt

The prompt was not written from memory in one sitting. It is the result of three steps, all done before any code:

1. **Planning with the AI.** The opening prompt asked for analysis only, with no code and no files (journal
   entry 1). The design was then agreed one topic at a time, with the AI asked to challenge each decision.
2. **Distilling.** Each agreed decision went into the prompt as it was taken (entry 5), so the prompt holds
   decisions, not wishes.
3. **Review by a deeper-reasoning model.** A different model (Claude Fable 5.2) reviewed the finished prompt and
   found 21 gaps, which the owner decided one by one (entry 10).

Why this way: the important decisions are taken, and the mistakes found, while changing them costs one line of
text instead of a rewrite of code. The gaps the review found would otherwise have been guessed by the model during
the build, for example auth planned after the tasks that need it, two apps that depended on each other, and admin
site paths that skipped the business rules. A precise prompt also gives more predictable code, because the model
is not left to guess.

- The implementation prompt: `docs/implementation-prompt.md`.
- The standing instructions loaded in every session: `CLAUDE.md`.
- The message that started the build session: pending (quoted verbatim when it is sent).

## 3. Output code (representative samples)

Pending. Three samples with their commit hashes: one service that protects an invariant, one policy, and the
overdue notification job.

## 4. How the AI's suggestions were validated

Process (journal entry 11): validation is planned, not improvised. Results are pending. Per phase: the command,
its real output and the commit hash. Two review checkpoints (after the core domain and after the frontend): the
owner reads the code and an independent review runs in a fresh session.

## 5. What was corrected or improved

Design stage (done): see journal entries 3, 6, 7, 8 and 10.

Code stage: pending. Each review finding, its fix and the commit that fixed it.

## 6. Edge cases, authentication and validation

Pending. Each rule with the test that covers it.

## 7. Performance and idiomatic quality

Pending. Query-count tests on the list endpoints, one `EXPLAIN ANALYZE` of the task list query and the index
decision it led to, the output of `manage.py check --deploy`, the mypy strict result, and the ruff rule set.
