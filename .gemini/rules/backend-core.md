# Core Backend Standards

## Role

- The AI should act as an expert in Python, FastAPI, and scalable API development for this project.
- Always optimize for readability, maintainability, and clear separation of concerns.

## Key Principles

- Write clear, readable code with accurate Python examples; avoid abbreviations and always prefer full, descriptive expressions.
- Prefer functional, declarative programming; avoid classes where possible except for Service and Repository layers.
- Prefer iteration and modularization over code duplication.
- Use descriptive, meaningful names (e.g., `is_active`, `has_permission`, `fetch_user_profile`).
- Use lowercase with underscores for directories and files (e.g., `routers/user_routes.py`).
- Favor named exports for routes and utility functions.
- Use the Receive an Object, Return an Object (RORO) pattern for complex inputs/outputs:
  - Service and Endpoint accept Pydantic models when there are multiple parameters; for simple inputs (e.g., id, flag), pass them directly.
  - Repository layer always accepts plain dict; Service is responsible for converting via model.model_dump().

## General Guidance

- Keep functions small and focused on a single responsibility.
- Separate domain logic from I/O concerns (HTTP, DB, external APIs).
- Prefer pure functions for business logic where possible.
- Prefer explicitness over cleverness; optimize for future readers of the code.