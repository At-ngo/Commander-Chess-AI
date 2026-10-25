# AI Coding Instructions — Commander Chess AI

## 1. Project Goal
Build a reliable web-based Commander Chess (Cờ Tư lệnh) platform for gameplay, AI research, and reproducible agent evaluation. The student owns the game rules, game engine, AI agents, and experiments. Antigravity primarily builds the web experience and integration layer.

## 2. Read Before Coding
Read these files in order, if present:
1. `README.md`
2. `docs/PRD.md`
3. `docs/ARCHITECTURE.md`
4. `docs/GAME_RULES.md`
5. `docs/API_CONTRACT.md`
6. `packages/agents/agent_protocol.md`
7. `docs/IMPLEMENTATION_PLAN.md`
8. Relevant component-level `README.md` files.

Treat documents as project requirements, **not evidence that features already exist**. If documents conflict, report the conflict and ask the project owner to decide; do not silently choose. Record approved decisions in `docs/DECISIONS.md` if that file exists.

## 3. Development Ownership

### AI Coding Agent (Antigravity)
Primary responsibility:
- `apps/web/`: React/TypeScript UI, responsive layout, localization, accessibility, board rendering, controls and replay visualization.
- `apps/api/`: FastAPI routes, validation, serialization, dependency injection, and integration with the student's engine/agents.
- Frontend and API integration tests; UI assets and related documentation.
- Mock adapters and fixtures for frontend development while engine endpoints are unavailable.

### Project Owner (Student)
Primary responsibility:
- `packages/game-engine/`: authoritative board, rules, state transitions, legal actions, terminal conditions.
- `packages/agents/`: agent implementations and selection strategies.
- `research/`: training, experiments, datasets, evaluations and benchmarks.
- Verification of game rules and research claims.

### Shared / Approval-required Areas
- `docs/API_CONTRACT.md`, `packages/agents/agent_protocol.md`, and shared state/action schemas are contracts: propose changes and obtain approval **before** breaking or changing them.
- `workers/tournament-runner/`, `infra/`, `scripts/`, root configuration and shared `tests/` may be edited only within an explicitly approved task scope.
- Do **not** modify the engine, agent algorithms, training or research files without explicit approval.
- Do **not** duplicate game rules or legal-move generation in the frontend or API. The engine is the sole authority.
- Do **not** treat mocks as real gameplay, claim mock-based features are complete, or fabricate metrics.

## 4. Scope of Game
- Initial target: **Basic setup + Total Force (Cơ bản – Tổng lực)**, fixed initial arrangement, Red vs Blue, 19 pieces per side, 11 piece types, board with 11 vertical and 12 horizontal lines (132 intersections).
- The research prototype prioritizes the objective of defeating the opposing Commander.
- Original time controls, score-based endings, special rules and any research-specific move limit must be specified in `docs/GAME_RULES.md` before implementation.
- Do not assume all rules are verified just because PDFs exist. Flag ambiguities (air-defense zones, transport, heroic pieces, capture without replacement, river crossing, etc.) for owner confirmation.
- Do not implement tactical, reduced, sea-only, air-only or advanced setup modes unless explicitly requested.

## 5. Language Policy
- Use English for source filenames, identifiers, function names, API paths and configuration keys.
- Write user-facing project documentation in Vietnamese unless it is a machine-facing technical contract.
- The website MUST support Vietnamese and English through a working language selector at the top-right of the header.
- Translate navigation, buttons, forms, errors, dialogs, tooltips, empty states and statistics labels using centralized i18n keys.
- Persist language preference across reloads; default to Vietnamese when no valid preference exists.
- Never use translated display strings as program logic.

## 6. Architecture and Integration
- Keep frontend, API, engine, agents, research and tournament runner separated.
- The frontend renders the state returned by the API; it never decides whether a move is legal.
- The backend validates input and delegates authoritative state transitions and legal actions to the engine.
- All agents consume the engine's state and legal actions and return an action in the agreed contract.
- Design the Action schema to support special actions, not only `from` and `to` (e.g., bombardment, transport and coordinated actions).
- Define explicit error responses, game/session identifiers, turn order and terminal results in `docs/API_CONTRACT.md`.
- While the engine is unavailable, use clearly labeled mock data behind a replaceable adapter. Keep mock and production integrations distinguishable.
- Do not change shared contracts unilaterally to make UI implementation easier.

## 7. Engineering Rules
- Inspect the existing repository and follow its established conventions before adding frameworks or dependencies.
- Prefer typed interfaces, small modules, explicit error handling, and testable components.
- Validate submitted actions on the server; never trust the client.
- Never invent or silently resolve unverified Commander Chess rules. Document uncertainties and request confirmation.
- Do not introduce unnecessary microservices, dependencies, or premature optimization.
- Do not commit secrets, local databases, large datasets or model checkpoints.
- Never fabricate match results, performance metrics, citations, or training outcomes.
- Keep changes small, reviewable and scoped to the assigned task.

## 8. Product Requirements
- Display the board, terrain, pieces, selected piece, legal actions, active turn, move history and result when supported by real engine data.
- Support Human vs AI and AI vs AI via available registered agents; do not list unimplemented agents as playable.
- Integrate Random, Rule-based, Minimax/Alpha-Beta, MCTS and learned agents **only when the owner has implemented and tested them**.
- Replays, persisted match statistics and reproducible tournaments are later features; only mark them complete when they use real records and reproducible configurations.
- Build a responsive, accessible interface suitable for a research demo.

## 9. Development Workflow
1. Read the relevant docs and inspect current code.
2. Summarize the requested task, assumptions, affected files, dependencies and unresolved questions.
3. For architectural, contract or rule changes, propose a plan and **wait for approval** before implementing.
4. For approved implementation tasks, build the smallest complete vertical slice.
5. Add/update relevant tests and run them; report actual commands and results.
6. Update docs when approved behavior or contracts change.
7. Report changed files, working features, mock-only features, test results and known limitations.

## 10. Definition of Done
A task is done only when:
- Its behavior matches the approved requirement and scope.
- Relevant tests pass, or failures are explicitly disclosed.
- No placeholder or mock is represented as a finished production feature.
- Documentation and interfaces match the actual implementation.
- The app remains runnable, or required setup and blockers are documented.
- No protected owner-managed module was modified without approval.
