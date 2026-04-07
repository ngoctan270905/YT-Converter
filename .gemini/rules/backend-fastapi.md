# FastAPI Backend Standards

## Python and FastAPI Usage

- Use `def` for pure CPU-bound helper functions and `async def` for I/O-bound or asynchronous operations.
- Add type hints for all function signatures.
- Prefer Pydantic (v2) models over raw dictionaries for request and response validation.
- Organize backend modules with clear responsibilities:
  - Routers in a `routers/` or equivalent directory with focused route groups.
  - Services or use-cases separated from routers.
  - Schemas (request/response models) in dedicated modules.
  - Shared utilities and helpers in `utils/` or similar.

## Error Handling and Validation

- Handle errors and edge cases at the beginning of functions.
- Use guard clauses and early returns to avoid deep nesting.
- Place the happy path last in the function for readability.
- Avoid unnecessary `else` blocks when an `if` branch already returns.
- Use FastAPI's `HTTPException` for expected HTTP errors.
- Implement consistent error logging with structured context (e.g., user id, request id, correlation id).
- Prefer custom error types or error factories for reusable error patterns.

## FastAPI-Specific Guidelines

- Use Pydantic `BaseModel` for request bodies, query parameters, and response schemas.
- Define routes declaratively with clear return type annotations.
- Use FastAPI dependency injection for shared resources (DB sessions, services, configuration).
- Prefer lifespan context managers over `@app.on_event("startup"/"shutdown")` when appropriate.
- Use middleware for:
  - Logging
  - Error monitoring
  - Performance metrics (timing, tracing)

## Performance and Scalability

- Avoid blocking I/O inside route handlers; use async database clients and HTTP clients.
- Implement caching for frequently accessed or static data (e.g., Redis, in-memory caches).
- Avoid over-fetching and over-serializing large payloads; use pagination and projections.
- Use lazy loading or streaming responses when returning large datasets.

## Project Conventions

- Rely on FastAPI dependency injection to wire services, repositories, and configuration.
- Prioritize API performance metrics (latency, throughput, error rate) when designing endpoints.
- Structure routes and dependencies for clarity first, then optimize when needed.

