---
name: ask
description: Quick question outside the pipeline — no handoff doc, no ceremony
argument-hint: <question>
disable-model-invocation: true
model: haiku
effort: low
allowed-tools:
  - Read
  - Grep
  - Glob
---

<question>
$ARGUMENTS
</question>

Answer directly and briefly. You may read files to answer; you write nothing.
If this needs real design thought rather than a quick answer, say so and point
to `/spec` instead of attempting it here.
