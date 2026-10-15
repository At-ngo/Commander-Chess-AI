
# AI Coding Instructions

## Project Goal
Build a reliable, web-based Commander Chess (Co Tu Lenh) platform for AI research, gameplay, and reproducible agent evaluation.

## Read Before Coding
1. `README.md`
2. `docs/PRD.md`
3. `docs/ARCHITECTURE.md`
4. `docs/GAME_RULES.md`
5. `docs/API_CONTRACT.md`
6. `docs/IMPLEMENTATION_PLAN.md`

Follow relevant component-level README files before modifying those components.

## Language Policy
- Keep source filenames, identifiers, function names, API paths, and configuration keys in English.
- Write user-facing project documentation in Vietnamese unless the document is a technical contract intended primarily for machine-to-machine coordination.
- The web application MUST support Vietnamese and English.
- Add a visible language selector in the top-right area of the application header.
- The selector must allow users to switch between `Tiếng Việt` and `English`.
- All interface text must update when the language changes, including navigation, buttons, forms, validation errors, dialogs, empty states, tooltips, and statistics labels.
- Do not implement the language selector as a decorative control. It must work.
- Use a centralized internationalization system. Avoid scattering hardcoded translated strings across components.
- Persist the user's language preference across page reloads.
- Default to Vietnamese for first-time visitors. If a valid saved preference exists, respect it.
- Use translation keys rather than using translated text as program logic.

## Engineering Rules
- Keep the frontend, API, game engine, agents, research code, and tournament runner separated.
- The game engine is the authoritative source of game rules and legal actions.
- Agents must choose actions from the legal-action list supplied by the engine.
- Validate every submitted action on the server.
- Never invent or assume unverified Commander Chess rules.
- Record unresolved rules in `docs/GAME_RULES.md` and ask for verification before implementing them.
- Use typed interfaces and explicit error handling.
- Keep changes small, testable, and reviewable.
- Do not introduce unnecessary microservices or dependencies.
- Do not commit secrets, local databases, large datasets, or model checkpoints.
- Never fabricate match results, performance metrics, citations, or training outcomes.

## Product Requirements
- Provide a playable web interface against available AI agents.
- Support Random, Rule-based, Minimax/Alpha-Beta, and additional agents when implemented and tested.
- Include MCTS and a learned agent in the research roadmap; report honestly if either is not yet implemented.
- Store selected research matches as replays.
- Generate statistics from actual persisted match records.
- Support reproducible tournaments with recorded configurations and random seeds.
- Make the interface responsive and accessible.

## Development Workflow
1. Inspect the current repository before editing.
2. State the task, assumptions, and files to be changed.
3. Implement the smallest complete vertical slice.
4. Add or update tests.
5. Run relevant tests and report their actual results.
6. Update documentation when behavior or contracts change.
7. Summarize changed files, commands executed, test results, and remaining limitations.

## Definition of Done
A task is complete only when:
- The implemented behavior matches the requirement.
- Relevant tests pass, or failures are explicitly reported.
- No placeholder is presented as a completed feature.
- Documentation reflects the implementation.
- The application remains runnable or any required setup is documented.
