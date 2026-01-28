# BrokeDancer Project Instructions

## Project Overview

**BrokeDancer** is a multi-domain automation platform with a React dashboard for monitoring and controlling trading bots. Originally focused on Polymarket prediction markets, it now supports 8 exchange providers and 11 trading strategies.

## Architecture

```
Backend (Python)              Frontend (React)
─────────────────            ─────────────────
src/providers/    ←───────→  web/src/services/api.ts
src/strategies/              web/src/services/websocket.ts
src/infrastructure/          web/src/components/
src/workflow/                web/src/pages/
src/web/server.py (8080)     web/src/hooks/
src/web/websocket_server.py (8001)
```

**Ports**: API=8080, WebSocket=8001, Frontend=5173

## Domain Skills

Context-specific skills are available in `.claude/skills/`. Use them for focused work:

| Skill | Trigger |
|-------|---------|
| `brokedancer-provider` | Adding/modifying exchange integrations |
| `brokedancer-strategy` | Trading strategy logic |
| `brokedancer-infrastructure` | State, events, logging, resilience |
| `brokedancer-frontend` | React components, WebSocket, tests |
| `brokedancer-workflow` | Node-based DAG automation |

## Key Commands

```bash
# Frontend (from web/)
npm run dev           # Dev server (localhost:5173)
npm run build         # Production build
npm run lint          # ESLint check
npm run test:e2e      # Playwright tests (242 tests)

# Backend
python -m src.web.server --port 8080
python src/web/run_websocket_server.py --port 8001
python -m src.web.demo_mode --port 8080  # Demo mode

# Tests
pytest tests/infrastructure/ -v    # 109 infrastructure tests
pytest tests/ -k "provider" -v     # Provider tests
pytest tests/ -k "strategy" -v     # Strategy tests
```

## Development Patterns

### API Case Transformation
Frontend uses camelCase, backend uses snake_case. Transformation happens automatically in `web/src/services/api.ts`.

### TypeScript Constraints
- `erasableSyntaxOnly`: Use `const` objects for enums, not TypeScript enums
- Vite: Use `import.meta.env` not `process.env`
- TailwindCSS v4: Use `@import "tailwindcss"` not `@tailwind` directives
- ReactFlow v12: Node types extend `Record<string, unknown>`

### WebSocket Events
**From Backend**: `workflow_event`, `stats_update`, `trade_executed`, `bot_started`, `bot_stopped`, `bot_list_update`
**To Backend**: `subscribe_workflow`, `subscribe_bot`, `subscribe_all_bots`, `request_stats`

## Commit Conventions

Use gitmoji format:
- ✨ `:sparkles:` New feature
- 🐛 `:bug:` Bug fix
- 📚 `:books:` Documentation
- ♻️ `:recycle:` Refactor
- ✅ `:white_check_mark:` Tests
- 🔧 `:wrench:` Configuration

Include `Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>` in commits.

## Testing Requirements

Before commits, verify:
1. `npm run lint` passes (0 errors)
2. `npm run build` succeeds
3. `npm run test:e2e` passes (or relevant subset)
4. `pytest tests/infrastructure/` passes

## File Organization

**Prefer editing over creating**: Always look for existing files before creating new ones.

**Key locations**:
- New provider: `src/providers/<name>.py` + update `factory.py`
- New strategy: `src/strategies/<name>.py` + update `factory.py`
- New page: `web/src/pages/<Name>.tsx` + update `App.tsx` routes
- New component: `web/src/components/<Category>/<Name>.tsx`

## Current Technical Debt

| Area | Priority | Status |
|------|----------|--------|
| Provider tests | P1 | Needed |
| Strategy tests | P1 | Needed |
| Frontend unit tests | P2 | Hooks need tests |
| Accessibility | P2 | No ARIA attributes |

## Handoff Documents

For session context, read:
- `docs/HANDOFF_WEEK5.md` - Latest progress
- `ARCHITECTURE.md` - System design
- `web/COMPONENT_CATALOG.md` - UI components
