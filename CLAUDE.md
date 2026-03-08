# CLAUDE.md — Cost Savings Repository

This file provides context and conventions for AI assistants (Claude, Copilot, etc.) working in this repository.

## Repository Overview

**Name:** Cost-savings-
**Owner:** tylerweinberg-ux
**Purpose:** This repository is in early initialization — no application code or tech stack has been committed yet. Use this file as a guide for development conventions as the project evolves.

## Repository Structure

```
Cost-savings-/
├── .gitkeep          # Placeholder to preserve the repo root
└── CLAUDE.md         # This file — AI assistant context and conventions
```

As files and directories are added, update this section to reflect the actual project layout.

## Branch Conventions

| Branch Pattern | Purpose |
|---|---|
| `master` / `main` | Stable, production-ready code |
| `claude/<description>-<session-id>` | AI-assisted development branches |
| `feature/<short-description>` | New features |
| `fix/<short-description>` | Bug fixes |

**Current active development branch:** `claude/add-claude-documentation-hiuUm`

## Git Workflow

1. **Never commit directly to `main` or `master`** without a review.
2. All changes should be made on a feature or AI-specific branch.
3. When work is complete, open a pull request targeting `main`.
4. AI assistant branches must be named `claude/<description>-<session-id>`.
5. Use clear, descriptive commit messages written in the imperative mood:
   - `Add cost calculation module`
   - `Fix rounding error in savings estimate`
   - `Update CLAUDE.md with tech stack details`

## Development Setup

> This section should be updated once a tech stack is chosen and dependencies are added.

Placeholder steps:
```bash
# Clone the repository
git clone <repo-url>
cd Cost-savings-

# Install dependencies (update once a package manager is configured)
# e.g., npm install  /  pip install -r requirements.txt

# Run the application (update once entry points are defined)
# e.g., npm start  /  python main.py

# Run tests (update once a test framework is configured)
# e.g., npm test  /  pytest
```

## Code Conventions

These conventions should be followed as the project grows:

- **Clarity over cleverness:** Prefer readable, self-documenting code.
- **Small, focused functions:** Each function should do one thing well.
- **No dead code:** Remove unused variables, imports, and functions.
- **Consistent naming:**
  - Use `camelCase` for JavaScript/TypeScript identifiers.
  - Use `snake_case` for Python identifiers.
  - Use `PascalCase` for classes and components.
- **Comments:** Only add comments where the logic is non-obvious. Avoid restating what the code already says.
- **Error handling:** Validate at system boundaries (user input, API calls). Do not over-engineer internal error handling.

## AI Assistant Guidelines

When working in this repository, AI assistants should:

1. **Read before modifying.** Always read existing files before editing them.
2. **Avoid over-engineering.** Make only the changes requested or clearly necessary.
3. **Keep solutions minimal.** Three clear lines are better than a premature abstraction.
4. **No backwards-compatibility hacks.** Delete unused code rather than wrapping it.
5. **Update this file.** When the tech stack, structure, or workflows change, update the relevant sections in `CLAUDE.md`.
6. **Commit and push to the correct branch.** Confirm the active branch before committing. Never push to `main`/`master` directly.
7. **No speculative features.** Do not add functionality that isn't requested.

## Environment Variables

> Update this section once the project requires configuration.

Expected `.env` variables (create a `.env.example` file when these are defined):
```
# Example — replace with actual variables
# API_KEY=
# DATABASE_URL=
```

Never commit secrets or credentials. Add `.env` to `.gitignore`.

## Testing

> Update this section once a test framework is configured.

- Tests should live in a `tests/` or `__tests__/` directory.
- Each module should have corresponding test coverage.
- All tests must pass before merging to `main`.

## Updating This File

This file should be updated whenever:
- A tech stack or framework is chosen and added.
- New directories or major modules are created.
- Development workflows change.
- New environment variables are required.
- Test or build commands change.
