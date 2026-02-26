# UP: The Missing Safety Net for AI-Assisted Development

*Why spec-driven development isn't enough, and what happens when you give AI coding a real engineering backbone.*

---

There's a term floating around the AI coding community: **vibe coding**. You describe what you want, the LLM generates code, you ship it. It feels productive — until the project grows, bugs compound silently, and nobody (including the AI) remembers why anything was built the way it was.

Tools like [OpenSpec](https://github.com/Fission-AI/OpenSpec) recognized this problem early. Their answer: write specs first, then let AI implement against them. It's a good instinct. But after months of building production software with AI assistants, I realized specs are just the beginning. The real question isn't *"what should the AI build?"* — it's *"what happens when it fails, and how do you know what it actually did?"*

That's why I built **UP**.

## What is UP?

UP is a CLI framework that wraps AI-assisted development in an engineering safety net. It works with Claude Code and Cursor — not replacing them, but adding the layers they're missing: resilient execution loops, persistent memory, provenance tracking, and a plugin system that lets you customize every step.

```bash
pip install up-cli

# Initialize a project
up init

# Analyze your codebase and generate a PRD
up learn auto

# Run the autonomous product loop
up start
```

That `up start` command kicks off something no other tool does: a fully autonomous development loop with built-in circuit breakers, verification gates, and automatic rollback.

## The Core Problem: AI Coding Without Guardrails

Let me paint a picture most AI-assisted developers know too well:

1. You ask Claude to implement a feature
2. It writes 200 lines across 5 files
3. Tests break. You ask it to fix them
4. It "fixes" them by changing the tests
5. Three iterations later, the original feature is subtly wrong
6. You have no idea which change introduced the regression

This is the **doom loop** — AI making confident changes that compound into silent failures. Spec-driven tools like OpenSpec address step 1 (clarity of intent), but steps 2-6 are where projects actually die.

UP addresses the entire lifecycle.

## Architecture: The SESRC Loop

At UP's core is the **SESRC product loop** — five principles that govern every autonomous AI operation:

- **Stable**: Graceful degradation when things go wrong
- **Efficient**: Token budget tracking, incremental testing
- **Safe**: Input validation, path whitelisting, dry-run previews
- **Reliable**: Circuit breakers, idempotency, verifiable rollback
- **Cost-effective**: Early termination, parallel execution

Every task runs through this cycle:

```
OBSERVE → CHECKPOINT → EXECUTE → VERIFY → COMMIT
```

**OBSERVE** reads the PRD, detects project state, checks system health. **CHECKPOINT** creates a git tag before AI touches anything — your rollback point. **EXECUTE** runs the AI task with full context injection. **VERIFY** runs your test suite, linter, and type checker. **COMMIT** only happens if verification passes.

If verification fails, UP rolls back to the checkpoint automatically. If the same task fails 3 times in a row, the **circuit breaker** trips and stops the loop — no more doom spirals.

```
┌─────────────────────────────────────────────┐
│              UP Product Loop                │
│                                             │
│  OBSERVE ──► CHECKPOINT ──► EXECUTE         │
│     ▲                          │            │
│     │                          ▼            │
│  COMMIT ◄──── VERIFY ◄────── AI            │
│     │            │                          │
│     │         FAIL? ──► ROLLBACK ──► RETRY  │
│     │                       │               │
│     │                  3x? ──► CIRCUIT BREAK│
│     ▼                                       │
│  NEXT TASK                                  │
└─────────────────────────────────────────────┘
```

This isn't theoretical. UP has run hundreds of autonomous task cycles across real projects, catching regressions that would have shipped silently with manual AI coding.

## Memory That Persists Across Sessions

Here's something that bothers me about every AI coding tool: they forget everything between sessions. You spend 30 minutes debugging a ChromaDB connection issue, solve it, and next week the AI hits the same error with zero recollection.

UP has a **persistent memory system** backed by ChromaDB (with a JSON fallback). It works through three auto-hooks:

**Auto-Record**: After 2+ consecutive failures on the same task, UP automatically saves the error signature, full context, and files involved. When you eventually fix it, it records the solution too.

**Auto-Recall**: When a task fails, UP extracts error keywords (exception class, test name, lint rule) and searches memory for past solutions. If it finds a match, it injects the solution directly into the AI's prompt:

```
Past solution found:
Previously, a similar error was solved by: adding the --no-cache flag
to the ChromaDB client initialization. Consider this approach.
```

**Auto-Index**: Every git commit gets indexed into semantic memory — commit message, files changed, diff summary. You can search your project history by meaning, not just by grep.

## Design Philosophy: Why "Safety Net" Beats "Spec First"

Most AI coding tools focus on one moment: the prompt. Write a better spec, get better code. That's true — but it's also incomplete. It's like saying "write better requirements and your software project will succeed." Requirements matter, but they're maybe 10% of why projects fail.

The other 90% is operational: regressions, lost context, silent failures, no rollback path, no audit trail, no way to know if the AI changed the tests instead of fixing the code.

UP's design philosophy starts from a different premise: **assume the AI will fail, and build the infrastructure to catch it.**

This isn't pessimism — it's engineering. Every serious production system has circuit breakers, health checks, rollback mechanisms, and audit logs. Why should AI-assisted development be any different?

The SESRC principles aren't abstract ideals. Each one maps to concrete failure modes I hit repeatedly while building real software with AI:

| Principle | Failure Mode It Prevents |
|-----------|--------------------------|
| **Stable** | AI crashes mid-task, leaving half-written files and broken state |
| **Efficient** | Burning $50 in API tokens on a doom loop that produces nothing |
| **Safe** | AI modifying files outside the project, or injecting untested code |
| **Reliable** | Same bug recurring across sessions because nobody remembers the fix |
| **Cost-effective** | Running full test suites on every single tool call instead of only on writes |

The key insight: these aren't features you bolt on later. They're architectural decisions that have to be baked into the execution model from day one.

## How It's Implemented: Atomic State and Merkle Chains

Under the hood, UP treats every AI operation like a database transaction. Here's what actually happens when `up start` processes a task:

### 1. Atomic State Management

All UP state lives in a single file: `.up/state.json`. Not scattered across five different JSON files (which is where I started — and quickly learned why that's a nightmare with concurrent AI agents).

The `StateManager` uses a pattern borrowed from databases:

```python
# Atomic write: temp file → fsync → os.replace()
fd, tmp_path = tempfile.mkstemp(dir=state_dir, suffix=".tmp")
with os.fdopen(fd, "w") as f:
    json.dump(state.to_dict(), f, indent=2)
    f.flush()
    os.fsync(f.fileno())
os.replace(tmp_path, state_file)
```

This guarantees the state file is never partially written. If the process crashes mid-write, you get either the old state or the new state — never a corrupted half-state. A rolling `.json.bak` backup adds another layer of safety. Cross-process access is synchronized with file locks.

Why does this matter? Because when you're running parallel AI agents in separate git worktrees, they're all updating shared state. One corrupted state file means the entire loop loses track of what's been done.

### 2. Provenance: A Merkle Chain for AI Operations

Here's a question nobody asks until it's too late: *which AI model wrote this code, what prompt produced it, and did it pass verification?*

UP tracks every AI operation in a **content-addressed Merkle chain**. Each operation gets a `ProvenanceEntry`:

```python
@dataclass
class ProvenanceEntry:
    id: str              # SHA256 content hash (first 16 chars)
    ai_model: str        # claude, cursor, gpt-4
    task_id: str         # Which user story
    prompt_hash: str     # SHA256 of the full prompt
    context_hash: str    # SHA256 of all context files
    files_modified: list # What the AI touched
    commit_sha: str      # Git commit
    parent_id: str       # Previous entry → Merkle chain link
    tests_passed: bool
    lint_passed: bool
    type_check_passed: bool
    status: str          # pending, accepted, rejected, reverted
```

The `id` is generated from the content fields — not timestamps. Identical operations produce the same ID, enabling deduplication. And because each entry includes `parent_id`, the chain is tamper-evident: change any historical entry and every subsequent ID breaks.

```python
def _generate_id(self) -> str:
    content = "|".join([
        self.task_id, self.prompt_hash, self.context_hash,
        self.ai_model, sorted_files, self.parent_id,
    ])
    return hashlib.sha256(content.encode()).hexdigest()[:16]
```

This isn't just for auditing. It answers practical questions: "Why did this file change?" "Did the AI's output pass tests before it was committed?" "Which model produced the most accepted code?" The provenance manager exposes stats — acceptance rates, test pass rates, models used — so you can make data-driven decisions about your AI workflow.

### 3. Circuit Breakers: Stopping the Doom Loop

The circuit breaker is borrowed directly from distributed systems (Netflix's Hystrix pattern). It has three states:

```
CLOSED ──(3 failures)──► OPEN ──(cooldown)──► HALF_OPEN ──(success)──► CLOSED
                                                    │
                                                 (failure)
                                                    │
                                                    ▼
                                                  OPEN
```

**CLOSED**: Normal operation. Failures are counted but execution continues.

**OPEN**: After 3 consecutive failures on the same task, the circuit opens. All further attempts are blocked immediately — no API calls, no token burn, no wasted time. The loop stops and tells you why.

**HALF_OPEN**: After a configurable cooldown (default 5 minutes), the circuit allows one test execution. If it succeeds, the circuit closes. If it fails, it reopens.

```python
def record_failure(self):
    self.failures += 1
    self.last_failure = datetime.now().isoformat()
    if self.failures >= self.failure_threshold:
        self.state = "OPEN"
        self.opened_at = datetime.now().isoformat()

def can_execute(self) -> bool:
    if self.state == "CLOSED":
        return True
    if self.state == "HALF_OPEN":
        return True
    self.try_reset()  # Check if cooldown expired
    return self.state != "OPEN"
```

This is the single most important feature for autonomous AI coding. Without it, you get the doom loop: AI fails, retries, fails differently, retries, burns through your token budget, and leaves the codebase worse than it started. With it, you get a clean stop and a clear signal that human intervention is needed.

## The Plugin System: Customize Every Step

UP ships with built-in plugins for memory, provenance, safety, and verification. But the real power is that every step of the pipeline is hookable.

A plugin is a directory with a `plugin.json` manifest and optional components:

```
.up/plugins/installed/code-review/
├── plugin.json          # Name, version, category
├── hooks/
│   ├── hooks.json       # Hook definitions
│   └── post_verify.py   # Runs after verification
├── rules/
│   └── review-standards.md
└── commands/
    └── review.md
```

Hooks are polyglot — write them in Python, Bash, JavaScript, whatever. UP executes them as subprocesses with a simple contract:

- **Input**: JSON on stdin (event type, workspace path, tool name, file paths)
- **Output**: Exit code semantics — `0` = allow, `1` = warn, `2+` = block

```json
{
  "hooks": [
    {
      "type": "command",
      "command": "python3 hooks/post_tool_use.py",
      "matcher": "post_tool_use",
      "tool_matcher": "Write|Edit",
      "timeout": 60
    }
  ]
}
```

The `tool_matcher` field is key. Without it, a verification hook would run on every single AI tool call — every file read, every grep, every glob. With `"Write|Edit"`, it only fires when the AI actually modifies files. This was a real bug I hit: the verify plugin was running the full test suite on every `Read` call, making Claude Code unusable.

### Config Sync: One Source of Truth

Here's a subtle problem with AI coding tools: each one has its own config format. Claude Code reads `.claude/settings.json` and `CLAUDE.md`. Cursor reads `.cursorrules`. If you have plugins with hooks and rules, you need to maintain all of these separately — and they drift.

UP solves this with `up sync`. One command reads your plugin configurations and generates all the tool-specific config files:

```bash
up sync
# Generates:
#   CLAUDE.md          ← AI rules, commands, safety rules, memory protocol
#   .cursorrules       ← Same rules in Cursor format
#   .claude/settings.json ← Hook definitions with matchers and resolved paths
```

The sync pipeline uses a renderer pattern — same `TemplateContext`, different output formats. Plugin hooks get mapped to each tool's native hook system. Relative script paths get resolved using `$CLAUDE_PROJECT_DIR` so hooks work regardless of where the AI tool runs from.

This means your plugins are portable. Write a hook once, and it works in Claude Code, Cursor, or whatever comes next.

## Diverge-Then-Converge: Parallel AI Agents

Single-threaded AI coding is slow. You have a PRD with 12 user stories — why implement them one at a time?

UP supports parallel execution through a **diverge-then-converge** pattern built on git worktrees:

```
                    ┌── Worktree A ── Agent 1 (US-001) ──┐
                    │                                     │
main branch ────────┼── Worktree B ── Agent 2 (US-002) ──┼── Merge ── main
                    │                                     │
                    └── Worktree C ── Agent 3 (US-003) ──┘
                   DIVERGE                            CONVERGE
```

Each agent gets its own git worktree — a full, isolated copy of the repository on its own branch. They run the complete SESRC loop independently: checkpoint, execute, verify, commit. No shared mutable state between agents during execution.

The `AgentState` tracks each agent's lifecycle:

```python
@dataclass
class AgentState:
    task_id: str
    branch: str
    worktree_path: str
    status: str    # created → executing → verifying → passed → failed → merged
    phase: str     # INIT → RESEARCH → PLAN → IMPLEMENT → VERIFY → MERGE
    commits: int
    verification: dict  # tests_passed, lint_passed, type_check_passed
```

After all agents complete, UP converges: successful branches get merged back to main, failed branches are discarded. Conflicts are detected and flagged for human resolution.

The default is 3 parallel workers — enough to get meaningful speedup without overwhelming your machine or API rate limits. It's configurable in `.up/config.json`.

## UP vs OpenSpec vs Raw AI Coding

OpenSpec is a good tool solving a real problem. But it solves a different problem than UP. Here's how they compare:

| Capability | Raw AI Coding | OpenSpec | UP |
|------------|:---:|:---:|:---:|
| Spec-driven prompts | ❌ | ✅ | ✅ |
| Automatic rollback | ❌ | ❌ | ✅ |
| Circuit breakers | ❌ | ❌ | ✅ |
| Persistent memory | ❌ | ❌ | ✅ |
| Provenance tracking | ❌ | ❌ | ✅ |
| Verification gates | ❌ | ❌ | ✅ |
| Plugin system | ❌ | ❌ | ✅ |
| Parallel agents | ❌ | ❌ | ✅ |
| Multi-tool sync | ❌ | ❌ | ✅ |
| Autonomous loop | ❌ | ❌ | ✅ |

OpenSpec focuses on the **input** side: better specs → better AI output. That's valuable, and UP actually incorporates spec-driven development through its `up learn` pipeline, which analyzes your codebase and generates a structured PRD with user stories, acceptance criteria, and priorities.

But UP goes further by addressing the **output** side: what happens after the AI generates code? Is it correct? Is it safe? Can you roll it back? Will you remember the fix next week? These are the questions that determine whether AI-assisted development actually works at scale.

## Why It's Efficient: Doing Less to Achieve More

Efficiency in AI-assisted development isn't about speed — it's about not wasting tokens, time, and human attention on things that shouldn't happen.

UP saves resources at every layer:

**1. Memory hints eliminate repeated debugging.** When a task fails, UP extracts error keywords and searches its semantic memory for past solutions. If it finds one, it injects the fix directly into the AI's next prompt. The AI doesn't waste a cycle rediscovering what you already solved last Tuesday.

```python
def _get_memory_hint(workspace, task):
    extractor = ErrorPatternExtractor()
    keywords = extractor.extract(last_error)
    results = manager.search(" ".join(keywords), limit=3, entry_type="error")
    if results:
        return f"Past solution found:\n{results[0].content}\nConsider this approach."
```

**2. Circuit breakers cap wasted spend.** Without a circuit breaker, a failing task can burn through 10+ API calls before a human notices. With UP's 3-strike limit, the maximum waste is 3 attempts — then it stops and waits for you.

**3. Tool-scoped hooks avoid unnecessary work.** The `tool_matcher` field means verification only runs when the AI writes or edits files — not when it reads, searches, or thinks. In practice, this cuts hook invocations by 80-90% during a typical coding session.

**4. Context budget tracking prevents token overflow.** UP monitors cumulative token usage across the session. At 40% budget, it warns. At 80%, it triggers an "Intentional Compaction" — summarizing progress to a handoff file and resetting context. This prevents the degraded output quality that happens when AI models hit their context ceiling.

**5. Checkpoints make rollback instant.** Instead of manually `git stash`-ing or hunting through reflog, UP's checkpoint system means rollback is a single operation: `git reset --hard` to the tagged SHA. The metadata in `.up/checkpoints/` tells you exactly what was attempted and why it was rolled back.

**6. Parallel execution multiplies throughput.** Three agents working on independent user stories in parallel worktrees can complete a 12-story PRD in roughly a third of the sequential time — with no coordination overhead during execution.

The compound effect matters most. Memory hints reduce retry cycles. Circuit breakers cap the cost of those retries. Tool-scoped hooks avoid wasting cycles between retries. Checkpoints make recovery from retries instant. Each layer reinforces the others.

## The Learning Pipeline: From Codebase to PRD

Before UP can run its product loop, it needs to know what to build. That's where `up learn` comes in — a three-phase pipeline that turns your existing codebase into a structured development plan:

```bash
# Full auto pipeline: research → analyze → plan
up learn auto
```

**Research**: Scans your codebase, documentation, and dependencies. Collects patterns, conventions, and architectural decisions into structured research files.

**Analyze**: Feeds research into the AI to extract insights — what patterns exist, what's missing, where the gaps are. Produces per-file analysis and a gap report.

**Plan**: Synthesizes insights into a PRD with prioritized user stories, acceptance criteria, and effort estimates. The output is a `prd.json` that the product loop consumes directly.

The JSON extraction uses a fallback chain — fenced code blocks first, then raw parsing, then bracket-depth parsing for when the AI wraps JSON in prose. This kind of defensive parsing is what makes the difference between a demo and a tool you can actually rely on.

## Getting Started

```bash
pip install up-cli

# Initialize in your project
cd your-project
up init

# Let UP learn your codebase and generate a PRD
up learn auto

# Sync plugin configs to your AI tools
up sync

# Run the autonomous product loop
up start
```

`up init` sets up the `.up/` directory, installs git hooks for memory indexing, and scaffolds the plugin structure. `up learn auto` analyzes your codebase and produces a `prd.json`. `up sync` generates tool-specific configs. `up start` runs the SESRC loop against your PRD.

You can also run individual phases:

```bash
# Just research
up learn research

# Preview what the loop would do without executing
up start --preview

# Run a specific user story
up start --task US-001

# Create a manual checkpoint
up save "before refactor"

# Roll back to last checkpoint
up reset
```

## The Real Argument: Software Engineering Enables Vibe Coding

Let me say something controversial: **vibe coding isn't the problem. Vibe coding without engineering is the problem.**

The instinct behind vibe coding is correct. Describing what you want in natural language and letting AI handle the implementation — that's not laziness, that's abstraction. It's the same progression that took us from assembly to C to Python. Each level lets you think at a higher level and produce more with less.

But every previous abstraction leap came with infrastructure. Compilers have type checkers. Package managers have dependency resolution. CI/CD pipelines have automated testing. Nobody ships C code without a build system. Why would you ship AI-generated code without a verification system?

The answer, right now, is that the infrastructure didn't exist. So vibe coding worked for weekend projects and broke for anything serious. People concluded vibe coding was the problem. It wasn't. The missing infrastructure was the problem.

UP is that infrastructure.

## What Vibe Coding Actually Needs at Scale

Think about what a vibe coder actually does:

1. Describes a feature in natural language
2. Lets the AI implement it
3. Checks if it works
4. Moves on to the next thing

That's a valid workflow. But at scale — 50 files, 10,000 lines, multiple modules with interdependencies — steps 2 and 3 collapse. The AI loses context. "Check if it works" becomes a manual nightmare. Moving on means forgetting what just happened.

Here's what each step actually needs to work in a large project:

**"Describe a feature"** → You need structured intent, not just a chat message. UP's `up learn auto` pipeline turns vague ideas into a PRD with user stories, acceptance criteria, and priorities. The vibe coder says "I want authentication." UP turns that into five atomic, testable stories the AI can execute independently.

**"Let the AI implement it"** → You need checkpoints before execution, context injection from past sessions, and memory hints from previous failures. UP's SESRC loop wraps every AI invocation in this infrastructure. The vibe coder doesn't think about any of it — they just run `up start`.

**"Check if it works"** → You need automated verification — tests, linting, type checking — that runs without human intervention. UP's verification gates do this after every AI operation. If it fails, rollback is automatic. The vibe coder never manually runs `pytest`.

**"Move on to the next thing"** → You need persistent memory so context carries forward, provenance so you can trace what happened, and a state machine that picks up the next task automatically. UP handles all of this. The vibe coder just watches the loop advance through the PRD.

The pattern is clear: vibe coding at scale is just vibe coding + software engineering automation. The human stays in the vibe. The tooling handles the engineering.

## Pure AI Vibe Coding: When No Human Writes a Single Line

Here's where it gets interesting. UP itself was built almost entirely through vibe coding — with UP.

The project has 534 passing tests, 6 phases of implementation, a plugin system, a Merkle chain provenance tracker, parallel agent execution, and a semantic memory system. I didn't write most of this code by hand. I described what I wanted, and the AI built it — inside UP's own safety net.

This is what pure AI vibe coding looks like on a real project. And it only works because of three things traditional vibe coding doesn't have:

### 1. A Verification Contract the AI Can't Cheat

The biggest risk in pure AI vibe coding is the AI "fixing" tests by weakening them. You describe a feature, the AI implements it, tests fail, and the AI rewrites the tests to pass. You never notice because you're vibing — you're not reading every line.

UP's verification gates are independent of the AI. The test suite, linter, and type checker run as separate processes after the AI finishes. The AI can't modify the verification step because it's not part of the AI's execution context — it's part of UP's loop. If the AI changes a test file, the verification still runs the *full* suite, including tests the AI didn't touch.

And if verification fails, the checkpoint rollback undoes *everything* the AI did — including any test modifications. The AI starts fresh from a known-good state.

### 2. Institutional Memory Without a Human Brain

In traditional development, the senior engineer is the institutional memory. They remember why the database schema looks that way, which approach was tried and failed last quarter, what the edge cases are.

In pure AI vibe coding, there is no senior engineer in the loop. The AI has no memory between sessions. Every new context window starts from zero.

UP's memory system fills this gap. Every error, every solution, every decision gets indexed into semantic memory. When the AI hits a problem, UP searches for past solutions and injects them into the prompt *before* the AI starts working. The AI doesn't need to remember — the system remembers for it.

This is what makes multi-session vibe coding possible. Session 1 discovers that ChromaDB needs `--no-cache` on initialization. Session 47 hits the same issue. Without memory, session 47 burns 30 minutes rediscovering the fix. With UP's auto-recall, it gets the answer in the first prompt.

### 3. Bounded Failure in an Unbounded Process

Pure AI vibe coding is, by definition, an unbounded process. You're not writing code — you're describing intent and letting an autonomous system run. If that system has no bounds, a single bad task can cascade into hours of wasted compute and a corrupted codebase.

UP bounds every dimension of failure:

- **Time**: Configurable timeouts per AI invocation (default 10 minutes)
- **Attempts**: Circuit breaker trips after 3 consecutive failures
- **Scope**: Checkpoints isolate each task's blast radius to one rollback
- **Cost**: Context budget tracking warns at 40%, compacts at 80%
- **State**: Atomic writes ensure you never end up with half-corrupted metadata

This is what lets you walk away from a vibe coding session and come back to a codebase that's either better than you left it or exactly the same — never worse. The bounded failure guarantee is what turns vibe coding from a gamble into a process.

### The Vibe Coding Maturity Model

Looking at it now, there's a clear progression:

| Level | What It Looks Like | Limit |
|-------|-------------------|-------|
| **Level 0: Raw vibe** | Chat with AI, copy-paste code, hope it works | ~500 lines before chaos |
| **Level 1: Spec-driven** | Write specs first, AI implements against them | ~2,000 lines before context loss |
| **Level 2: Loop-driven** | Automated verify/rollback cycle per task | ~10,000 lines with discipline |
| **Level 3: Full infrastructure** | Memory + provenance + circuit breakers + parallel agents | Production-scale, indefinitely |

Most vibe coders are stuck at Level 0 or 1. They hit the wall around 2,000 lines and conclude that AI coding doesn't scale. It does — but only if you add the engineering layers that make scaling possible.

UP operates at Level 3. That's not because it's magic. It's because it applies the same patterns that made traditional software engineering scale — CI/CD, rollback, audit trails, circuit breakers, persistent state — to the specific problem of autonomous AI code generation.

## What's Next

UP is already running in production across multiple projects — including itself. The plugin ecosystem is growing: code review, security scanning, documentation generation. The parallel agent system is being extended with smarter merge strategies and conflict resolution.

But the bigger picture is this: we're at the beginning of a shift in how software gets built. The question isn't whether AI will write most code — it will. The question is whether we'll have the engineering infrastructure to make that code trustworthy.

Vibe coding is the future. But like every paradigm shift before it, the future needs plumbing. UP is that plumbing.

---

*UP is open source. Check it out at [github.com/your-repo/up-cli](https://github.com/your-repo/up-cli).*

*If you're building with Claude Code or Cursor and tired of doom loops, give it a try. The circuit breaker alone might save your weekend.*
