---
description: Quick status summary from the handoff record — outside the pipeline
agent: ask
---

<summary>
You MUST answer from the actual handoff files, not from memory or guesswork.
You MUST distinguish complete / partial / stopped / blocked, and call out
anything planned or specced but not yet reported as built.
You MUST cross-check against the work item tracker whenever it exists, not
only when the scope names a ticket ID, and flag any place the two disagree.
You MUST NOT write anything — this is a read and summarize, not a new record.
If the human wants this to persist, tell them to use /handoff instead.
</summary>

<scope>
$ARGUMENTS
</scope>

Recent reports:
!`ls -t .handoff/3-report/*.md 2>/dev/null | head -10`

Recent specs (planned, maybe not yet built):
!`ls -t .handoff/2-spec/*.md 2>/dev/null | head -10`

Recent plans (earliest stage — may not have gone further):
!`ls -t .handoff/1-plan/*.md 2>/dev/null | head -10`

Tracking status:
!`head -8 .workitems/TRACKING.md 2>/dev/null || echo "no .workitems/TRACKING.md"`

Work item index, if the tracker is set up:
!`cat .workitems/WORKITEMS.md 2>/dev/null || echo "no workitems index"`

Answer the scope above against these files — a ticket ID, an epic, "this
week", "the last few slices", whatever was asked. If no scope was given,
summarize the most recent handful across all three stages.

For each stem, work out where it actually got to:

- Report exists, `Status: complete` → done, built, verified — say what was
  verified and what wasn't (check the report's own verification section
  rather than assuming green).
- Report exists, `Status: partial` or `stopped` → say what's built and what
  isn't. Don't round this up to "done".
- Spec exists, no report → planned and specced, not yet built.
- Plan exists, no spec → still in planning, not yet verified against the
  codebase.
- Spec `Status: replan` → kicked back, waiting on the human to reconsider it.

**Cross-check against the tracker whenever `.workitems/TRACKING.md` says
`Tracking: yes`.** (If it says `none`, there is no tracker to cross-check —
say that in one line instead of listing missing tickets.)
Match each stem's ticket ID prefix against the work item index above —
active items and, if relevant to the scope, `items/done/`. Two systems
recording status independently will drift; surface it rather than picking
one silently:

- Tracker shows the ticket done (or filed under `items/done/`) but no
  report exists → say so plainly. Either the build hasn't happened, or the
  report was never written — don't assume which, name the gap.
- A report says `complete` but the tracker still shows the ticket active →
  say so. The build may genuinely be done with the tracker just stale, but
  that's the human's call to close, not this command's to assume.
- Ticket isn't in the tracker at all (removed, renamed, wrong ID) → note it
  rather than silently dropping it from the summary.

Do not attempt to resolve a divergence yourself — this command has no write
access to either side. Naming the mismatch is the whole job.

End with a short list, one line per stem, stage reached, tracker status if
known, and any divergence flagged. This is a summary of the record for this
conversation — it is not itself a record.
