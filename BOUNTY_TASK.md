# Bounty Fix

**Reward:** $20.00
**Issue:** https://github.com/alfrexo95/bounty-bot/issues/96
**Repo:** https://github.com/alfrexo95/bounty-bot

---

## Issue

🪙 [Web3] [Wave 3: 2 × $20 USDC | 3-Year Protocol Trajectory

🤖 **Bounty Encontrado en Web3**

- **Título:** [Wave 3: 2 × $20 USDC | 3-Year Protocol Trajectory & Integrity Dossiers] Human-Researcher Control-Plane Due-Diligence Pool
- **Monto:** $20
- **Plataforma:** Web3
- **Enlace:** [https://github.com/Fractal-Neurons/pacta/issues/118](https://github.com/Fractal-Neurons/pacta/issues/118)

---

### 💰 Payment Details
- BTC: bc1qt3rukpe7qp737zj5j5xpxxmcqv90cfefhg5e00
- ETH: 0xA5E6eB31868A85127B1ED82b8C760193356206ED
- LTC: ltc1qdyyg99l8ehp9aj4ehzvmefglmpl9750226k7ne
- Lightning: chieftrait089@walletofsatoshi.com

**Note:** I am a developer from Cuba. Due to the economic blockade, traditional payment methods are often blocked. Cryptocurrency is the most stable and free way for me to receive payments. I would appreciate it if the bounty could be paid in crypto. Thank you!



---

## Process

### 1. Orient yourself first
Before touching any code:
- Read the README and any relevant docs
- Run: find . -type f | grep -v node_modules | grep -v .git | grep -v dist | head -60
- Grep for the key terms from the issue title to find the relevant files
- Read the files around the bug — understand what's currently happening

### 2. Find and read the tests
- Look for test files near the relevant code (*.test.ts, *.spec.js, __tests__, etc.)
- Read them — they tell you what behavior is expected
- Understand what a passing fix looks like before writing a line

### 3. Implement the fix
- Make the MINIMAL change that fixes the issue — nothing more
- Do not refactor, rename, reorganize, or clean up unrelated code
- Do not add dependencies unless the issue explicitly requires it
- Do not modify config files (package.json, tsconfig.json, etc.) unless that IS the fix
- One logical change, one commit

### 4. Verify
- Run the test suite: check package.json scripts for "test", "lint", "typecheck"
  Common commands: npm test, yarn test, pnpm test, pytest, go test ./..., cargo test
- If TypeScript is present: npx tsc --noEmit
- Fix any test failures your change caused — if a test was wrong before, update it

### 5. Commit and document
- git add -A
- git commit -m "fix: 🪙 [Web3] [Wave 3: 2 × $20 USDC | 3-Year Protocol Trajectory"
- Write AGENT_SUMMARY.md with:
  - Root cause: what was wrong and why
  - Fix: what you changed and the reasoning
  - Verification: how to confirm it works
  - Concerns: anything a reviewer should know

---

## Stop conditions

If ANY of these are true, write "UNCERTAIN: [reason]" at the top of AGENT_SUMMARY.md, make NO code changes, and stop:
- The fix requires changing more than ~5 files
- You cannot determine what the correct behavior should be
- The issue requires a database migration, API key, or external service
- You find 3+ open PRs already attempting this fix (high competition)
- The repo is not in a language/framework you can reason about confidently

A clean UNCERTAIN is better than a bad PR.
