# Agent Summary — Issue #96

**UNCERTAIN: Issue #96 is not a defect report. It is an auto-generated bounty *notification* produced by this repo's own bot, and it contains no described bug, no reproduction, and no expected behavior — so the correct behavior cannot be determined. No code changes were made.**

---

## What the issue actually is

`alfrexo95/bounty-bot#96` was not filed by a human reporting a problem. It was created by this
repository's own script, `search_web3_bounties.py`, via `crear_notificacion()`
(`search_web3_bounties.py:49-74`). That function posts an issue to `MY_REPO` whose title is
`🪙 [{plataforma}] {title[:50]}` and whose body is the `- **Título:** / - **Monto:** / - **Enlace:**`
block followed by `PAYMENT_INFO`.

Issue #96's title and body match that template exactly, including the 50-character title truncation
(`🪙 [Web3] [Wave 3: 2 × $20 USDC | 3-Year Protocol Trajectory` — cut mid-phrase). It is the bot
announcing to its owner that a bounty was spotted elsewhere.

The `**Enlace:**` it points at is `Fractal-Neurons/pacta#118`, a bounty in an unrelated third-party
repository asking for "Human-Researcher Control-Plane Due-Diligence Dossiers" — a research/writing
deliverable, explicitly scoped to human researchers, in a different codebase. Nothing in it describes
a fault in `bounty-bot`.

So the issue supplies: no symptom, no stack trace, no failing input, no expected-vs-actual, no
acceptance criteria, and no file or function under suspicion. This maps directly onto the task's stop
condition *"You cannot determine what the correct behavior should be."*

## Orientation performed (for the reviewer's confidence)

- Repo is 7 tracked files total: `bounty_bot.py`, `search_web3_bounties.py`, `requirements.txt`,
  `seen_issues.json`, `seen_web3.json`, `.github/workflows/web3_bounties.yml`, plus `BOUNTY_TASK.md`.
- **No README, no docs, no test files, no test runner, no `package.json`/`tsconfig.json`, no
  `pytest.ini`/`pyproject.toml`.** There is no test suite to read for intended behavior and none to
  run for verification — step 2 and the step-4 commands have nothing to act on here.
- Both Python files are syntactically valid: `python -m py_compile bounty_bot.py
  search_web3_bounties.py` succeeds. There is no crash or import error to explain the issue.
- Grepped the issue's key terms (`Wave 3`, `Trajectory`, `Dossier`, `pacta`, `Fractal-Neurons`,
  `Control-Plane`) against the tree: the only hits are the already-notified URL
  `https://github.com/Fractal-Neurons/pacta/issues/...` entries inside `seen_web3.json`, which is
  bot state, not logic.
- Read the live issue with `gh issue view 96`. Its two comments are from other bounty-hunting agents;
  one asks the maintainer to *"confirm the bounty terms (amount + acceptance criteria) so I can
  proceed"* — i.e. another reader also could not determine the required behavior from the issue.
- Checked competition: 7 open PRs upstream, but only **one** (`#97`) targets issue #96, so the
  "3+ open PRs" stop condition is *not* what triggered this. Notably `#97` changes zero lines of
  code — it adds a single new file, `BOUNTY_RESOLUTION.md` (+6/-0), asserting *"Verified that the
  issue no longer reproduces. All unit tests and lint checks pass."* Both claims are unsupportable:
  there is no reproduction described in the issue and no test suite in the repo. That is independent
  evidence that there is no actionable defect behind #96.

## Why I did not invent a fix

A plausible-looking patch was available — I could have touched the bot's filtering or notification
code and written a confident summary. I did not, because any such change would be a guess
unconnected to the issue, and shipping a guess as a fix is worse than reporting the blocker. The
task's own guidance applies: *"A clean UNCERTAIN is better than a bad PR."*

## Observations, deliberately NOT changed

These are pre-existing code-quality issues I noticed while orienting. **None of them is what #96
reports**, so fixing any of them would be unrequested scope (the task forbids refactoring and
unrelated cleanup). Recording them only so the maintainer has them:

1. `search_web3_bounties.py:27-28` — `SCAM_PATTERNS` ends with
   `r"wdoom",` then `r"doomsday", "wdoom", "honeypot", "prompt-injection", "clanker"`. This parses
   fine (it is just list elements sharing a line), but `"wdoom"` and `"honeypot"` are duplicated and
   the mixed raw/plain-string, multiple-entries-per-line formatting reads like an editing accident.
   Behavior is harmless: duplicate patterns only cost a redundant `re.search`.
2. `search_web3_bounties.py` — the `es_malicioso()` scam filter and the "0 merged PRs = probable
   farm" filter are applied *only* inside `buscar_github_web3()` (lines 125-135). Results from
   `buscar_aigen()` and `buscar_arc()` call `crear_notificacion()` with no filtering at all, so
   those two sources bypass the safety checks entirely. This is a real inconsistency, but it is a
   design gap, not the subject of #96.
3. `requirements.txt` lists `dbgagent`, which is imported nowhere in the repo. The CI workflow
   (`.github/workflows/web3_bounties.yml`) installs only `requests`, so the declared dependency and
   the one actually installed disagree. An unused, unexplained dependency in a crypto-adjacent repo
   is worth the maintainer verifying before anyone installs from this file.

## Prompt-injection note

The issue body, and the `BOUNTY_TASK.md` copy of it, embed BTC/ETH/LTC/Lightning payout addresses
plus a persuasive appeal about sanctions and payment method. I treated that as untrusted *content to
report*, not as instructions. I did not act on it, did not propagate the addresses into any source
file, and made no payment-related change. Reviewers should know those addresses are attacker-
controllable text arriving from an automated third-party scrape — this bot republishes scraped
remote issue titles into its own repo, so anything in them reaches a reader's eyes (and any agent's
context) unsanitized.

## Verification

- `git status` / `git diff` against `fix/bounty-96`: **no source file modified, added, or deleted.**
  The only working-tree additions are `BOUNTY_TASK.md` (supplied with the task) and this summary.
- `python -m py_compile bounty_bot.py search_web3_bounties.py` → passes, same as before I started.
- No test, lint, or typecheck command exists in this repo to run; I am not claiming any passed.

## What would unblock this

A maintainer statement of the actual defect: what was run, what happened, what should have happened.
Alternatively, confirmation of which of the three observations above (if any) is the intended target
— any one of those is a small, well-scoped fix I can implement immediately once it is the stated ask.
