# Requirements

## Functional

A RESTful API for a task management system. Users can:

- Create, read, update and delete tasks.
- Assign tasks to users.
- Mark tasks as completed.
- Filter tasks by status and due date.

## Backend

- Django with Django REST Framework.
- CRUD endpoints for tasks.
- JWT authentication.
- Pagination when listing tasks.
- Filtering by status and due date.
- PostgreSQL, with a simple schema for tasks and users.
- Unit tests for critical endpoints with pytest, at least 80% coverage.
- Dockerfile and docker-compose.yml to run the app and the database locally.
- README.md with setup instructions and key implementation decisions.
- API documentation with Swagger/OpenAPI.
- Project configuration with pyproject.toml (uv), pre-commit and other good practices.
- Rate limiting to prevent API abuse.
- Background task processing (Celery and Redis).

## Frontend

- A React frontend integrated with the backend.
- Responsive and user-friendly.
- CRUD operations for the implemented use case.
- Components and state organised cleanly.
- No warnings in the browser console.

## Delivery

- README with setup instructions and any other relevant documentation.
- Seeded data and demo credentials.
- `GENAI.md` documenting the AI-assisted development:
  - the prompt used to generate the scaffold or implementation,
  - the output code, or a representative sample,
  - how the AI suggestions were validated,
  - what was corrected or improved,
  - how edge cases, authentication and validation were handled,
  - how performance and idiomatic quality were assessed.
