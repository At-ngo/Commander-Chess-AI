
# API Contract

Status: Draft. Finalize schemas alongside implementation.

Base path: `/api/v1`

## General
- JSON request and response bodies.
- Use consistent HTTP status codes.
- Return structured errors with a stable machine-readable code and a human-readable message.
- Never trust client-provided game state or legal actions.
- Document every endpoint and schema change.

## Endpoints

### GET `/health`
Return API health status.

### GET `/api/v1/agents`
List available agents and their supported configuration options.

### POST `/api/v1/games`
Create a game session.

Draft request:
- `agent_id`
- `initial_config` (optional)

Return:
- `game_id`
- `state`
- `legal_actions`
- `status`

### GET `/api/v1/games/{game_id}`
Return the current state and status of a game.

### POST `/api/v1/games/{game_id}/actions`
Submit a player action.

Draft request:
- `action`

The server must validate the action against the authoritative game engine.

### GET `/api/v1/replays`
List persisted replays. Support pagination when needed.

### GET `/api/v1/replays/{replay_id}`
Return replay metadata and ordered action history.

### GET `/api/v1/statistics/summary`
Return aggregate statistics computed from persisted records.

### GET `/api/v1/statistics/matchups`
Return statistics grouped by agent matchup and configuration.

## Error Model

Draft response:
- `error.code`
- `error.message`
- `error.details` (optional)

Use suitable status codes, including 400 for malformed requests, 404 for missing resources, and 409 for invalid state transitions.

## Data Integrity
- Record agent identifiers and versions.
- Record rules/engine version for research matches.
- Do not report incomplete games as wins.
- Distinguish unavailable metrics from zero-valued metrics.
- Do not fabricate results.

## Compatibility
The contract is provisional. Update this document when schemas or behavior change.
