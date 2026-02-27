# Project Learnings & Patterns

Documented patterns, anti-patterns, and general learnings.

---

### 2026-02-27

- When using FileLock, do not hold a second lock inside the context manager to avoid deadlocks.
