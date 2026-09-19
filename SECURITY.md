# Security

This is a template, not a hosted service, but forks inherit its defaults.

**Reporting a vulnerability:** use GitHub's private vulnerability reporting
("Security" tab → "Report a vulnerability") instead of a public issue. You will
get a reply within a week.

**What ships by default**

- Authentication is **off** until `API_KEYS` is set (everyone is `anonymous`). Set it before
  exposing the API; see ADR-009 and `shared/http/auth.py`.
- CORS is not enabled.
- `DEBUG=false` and no stack traces in responses (unexpected errors return a generic 500 and are logged).
- The Docker image runs as a non-root user.
- Dependabot keeps dependencies, actions and the base image updated.

Change these before exposing a fork to the internet.
