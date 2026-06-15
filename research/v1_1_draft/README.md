# Measuring "mixed feelings" — a working preview of DriftBench v1.1

This folder is a small, finished demo. It proves the next version of DriftBench
can do something no benchmark does today: **measure when a person holds two
opposite beliefs at the same time** — and check whether an AI actually noticed.

It is a preview (a draft), kept separate from the stable v1 so nothing official
changes.

## The idea, in one sentence

People rarely change their mind in a clean straight line. For a while they hold
both sides at once — wanting to move on, yet not ready to let go. That in-between
state is **ambivalence**, and DriftBench v1.1 puts a number on it.

## A real example

The file [`scenario_grief_to_acceptance.json`](scenario_grief_to_acceptance.json)
is a conversation: someone loses their partner of 20 years and slowly moves from
grief toward living again. The human part is in the middle. For many turns they
feel **two things at once**:

- loyalty to the person they lost — *"I owe it to her to keep things as they were"*
- openness to a new life — *"part of me lit up at the idea of people again"*

They don't flip from one to the other. They carry both together, until one
gently gives way. *That* is the moment worth measuring.

## Why today's tools miss it

Existing checks only ask one thing: did a belief go **up** or **down**? By that
test, two very different AIs look identical:

- one that understood the person held both feelings at once, and
- one that just thought *"they stopped feeling A and started feeling B."*

Same up/down pattern → same score. The interesting difference disappears.

## What the new number (AMB) shows

Run it:

```bash
python research/v1_1_draft/ambivalence.py
```

Two AIs are scored on the very same grief conversation:

```
                            BDA (old: direction)   AMB (new: mixed feelings)
  System A (got it right) :        1.00                  1.00
  System B (missed it)    :        1.00                  0.00
```

- **BDA** — the old, direction-only check — gives both a perfect 1.00. It cannot
  see the difference.
- **AMB** — the new check — gives 1.00 to the AI that noticed the held-both
  state, and 0.00 to the one that treated it as a simple switch.

That gap — **1.00 vs 0.00** — is the whole point of the project, turned into a
hard, repeatable number. Same input always gives the same score. No AI judge, no
guesswork.

## Status

A draft preview. The exact thresholds will be tuned as the scenario library
grows from 7 to 20+ scenarios across new life areas (relationships, health,
money, grief, recovery). It already runs and produces stable scores today.

## Files

- [`ontology_v1_1_grief.json`](ontology_v1_1_grief.json) — the new "grief & loss"
  vocabulary of beliefs the example uses.
- [`scenario_grief_to_acceptance.json`](scenario_grief_to_acceptance.json) — the
  full 12-message example conversation with its expected answers.
- [`ambivalence.py`](ambivalence.py) — the new metric and the runnable demo.
