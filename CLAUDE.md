# CLAUDE.md

## Commit Convention

All commits MUST follow [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>: <description>
```

**Types:**

| Type | When |
|------|------|
| `feat` | New feature |
| `fix` | Bug fix |
| `docs` | Documentation only |
| `style` | Formatting, no code change |
| `refactor` | Code restructuring, no feature/fix |
| `test` | Adding/updating tests |
| `chore` | Build, CI, tooling, dependencies |
| `ci` | CI/CD configuration |
| `perf` | Performance improvement |
| `revert` | Reverting a commit |

**Rules:**

- Description: imperative mood, lowercase, no period, max 72 chars
- No `Update`, `Add`, `Fix` as description starters — use imperative: `update` not `Updated`
- Scope optional: `feat(auth): add JWT refresh`
- Breaking changes: `feat!: drop Python 3.11 support`

**Examples:**

```
chore: initial cookiecutter scaffolding
feat: add users module with full auth flow
fix: Dockerfile for correct build and runtime
ci: add GitHub Actions workflow
docs: update READMEs and fix test imports
refactor: use fastapi[standard] and drop redundant uvicorn[standard]
test: add test suite with health and user flow tests
```
