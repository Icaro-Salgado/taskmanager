# GenAI development journal

Evidence log of the AI-assisted work (tool: Claude Code). `GENAI.md` is the summary and cites these entries by
number, so entries are never renumbered. Rules: `CLAUDE.md`.

Everything here is **observed** (it happened in a recorded session) unless marked reconstructed. Owner quotes are
verbatim, typos included. Part 1 was condensed on the owner's request; the longer versions are kept outside the
repository.

Models: the design (entries 1 to 9) was done with Claude Opus; the two reviews before the build (entries 10 and
11) with Claude Fable 5.2. Each build entry names the model that did the work.

## Part 1: Design (closed)

Each entry: type, who decided, and the `GENAI.md` section it feeds.

1. **prompt** | owner | section 2. The opening prompt asked only for an analysis of the requirements, with no code
   or files, set Claude as a critical engineering partner, and forbade fabricating development history.
2. **decision** | owner | section 4. No TDD; tests are written alongside the code. "No TDD", reason: "I'm not used
   to TDD (personal coding style)".
3. **correction** | owner | section 5. Claude bundled a data model, endpoints, layout and six questions in one
   message. Owner: "you are rushing it [...] lets start with the journal and claude instructions, so we start
   discussing the arch and project per part". Result: one topic per step.
4. **decision** | owner | section 6. "Be careful with OWASP Top 10 security problems."
5. **decision** | both | section 2. The implementation prompt is a living file, built up as decisions are agreed
   and given to a fresh session when ready. It is distilled from the design conversation, not written before it.
6. **correction** | owner | section 5. Claude read the owner's questions as scope requests; they were probing
   whether the base design survives future needs. Result: if a question does not change the foundation, it goes to
   `docs/backlog.md`.
7. **correction** | owner | section 5. The owner noticed the design drifting into "an internal tool for
   companies", which is not in the requirements. Claude agreed and recommended stopping design and starting the
   build.
8. **correction** | both | section 5. After a model switch, the owner asked for a review of the earlier decisions.
   Claude found 18 gaps; the main one: the Django admin site would bypass the service layer. Others: access for
   ex-members, undefined delete and reassign permissions. The owner asked to "simplify everything"; Claude proposed
   a simple default for each gap; owner: "Agreed with all". (One default, a single overdue notification per task,
   was replaced by grouped notifications in entry 9.)
9. **decision** | owner | section 2. Final owner review of the prompt. Added by the owner: git steps with separate
   commits, README content, restorable deletes ("exclude a team but I want to restore, for now no from UI but from
   a DB query"), common timestamp columns, grouped overdue notifications, a run command that works on Windows, a
   final rewrite of `CLAUDE.md`, and "archived is not a status but a query result". Claude proposed soft delete
   and Docker Compose with thin `run.sh` and `run.ps1` wrappers; owner agreed.
10. **validation** | both | sections 2 and 5. Before the build, the owner had a different model review the prompt:
    "see if there is any flaws or if its ok". No flaw in the foundation, 21 gaps; the owner decided each one.
    - Fixed: endpoints missing from every phase, auth planned after the tasks that need it, missing permission
      rules, no error contract, undefined app boundaries, admin site paths that skip the services, overdue job
      edge cases, deactivated users, a token refresh race, tokens surviving a password change.
    - Owner's choices: an explicit call over a signal between the teams and tasks apps ("a"); a task board instead
      of a list ("make it like a can ban"), with drag and drop in the backlog; `run.ps1` written but not tested
      ("dont test just do it").
    - Claude's own correction: the assignment notification it proposed created a second circular dependency,
      resolved by making `notifications` a delivery-only app.
11. **validation** | both | section 4. The owner asked the same model to review the GenAI process: "I'm not sure
    we are being efficient here". Finding: only the prompt was covered; no
    step in the plan produced evidence about generated code. Agreed ("I agree with all"): validation entries are
    logged as facts without waiting; two review checkpoints where the owner reads the code and a fresh session
    reviews it; planned performance evidence; `GENAI.md` created early and filled per phase; this journal
    shortened and given a fixed format for the build.

### Design decisions

| Decision | Decided by | Notes |
|---|---|---|
| Global admin is `is_superuser`; `is_staff` only for Django admin login | owner | "for a first version is fine and IF the project needs a custom one we do" |
| Team roles in our own `Membership` table, not Django groups | both | Groups are global; we need "leader of A, member of B" |
| Custom user, email login; no self-registration | both | Admins create users |
| `Team.name` unique, max 30 | owner | Identifies teams for users in several teams |
| `Team.archive_after_days` real column, default 15 | both | Owner asked about a JSON column; Claude recommended a real column |
| Removing a member unassigns their tasks synchronously | both | Owner asked about a background job; Claude: the invariant must never be false |
| Statuses: todo, in progress, blocked, done, canceled | both | `ready to deploy` left out ("Got it, you are right") |
| Terminal statuses are final; reopen moves to in progress | both | Owner first chose free movement, then reversed it: "Lets make the simples rules" |
| `due_date` is a nullable `DateField` | both | "Yes, DataField make it simple." |
| Layering: services, selectors, `policies.py` per app, thin API | both | Claude compared three options; owner: "option 2" |
| Leaderless teams allowed; admins use an orphan teams filter | both | Owner's design; Claude challenged adding an admin `Membership` row |
| Admin UI is the Django admin site | both | "lets keep the admin management simples (django)" |
| Soft delete for teams and tasks, restored by a database query | both | Entry 9 |
| Explicit call from teams to tasks, not a signal | owner | Entry 10 |
| `notifications` is delivery-only; task rules stay in `tasks` | Claude, owner informed | Entry 10 |
| Task board with one column per status | owner | Entry 10 |
| Typed Python, checked by mypy in strict mode | owner | "lets use typed python"; added after the reviews, before the build. Claude proposed mypy with the Django stubs |
| Quotas, custom statuses, status history, drag and drop | owner | Backlog |

## Part 2: Build log

Numbering continues from 12. Six lines at most per entry:

```
N. <type> | phase <P> | <model> | section <S of GENAI.md> | commit <hash>
   Command: <what was run>
   Output: <real output, trimmed>
   Note: <one line; for a correction: the finding and the fix>
```

No entries yet.
