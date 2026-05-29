# AI Contract Analyzer Agent Guardrails

## File ownership and boundaries

- Backend/AI work must stay in `backend/**`, `docs/**`, `AGENTS.md`, `.env.example`.
- Do not modify `frontend/**` in backend-focused agent tasks.
- Do not rewrite large existing modules when a minimal extension is enough.

## API and schema stability

- Do not remove existing endpoints.
- Do not break `docs/report-schema.json` shape once published.
- Extend API in backward-compatible way when possible.

## Legal and compliance rules

- Never claim legal advice from the system.
- Always keep disclaimer in reports.
- Legal research must use only publicly accessible pages.
- Never bypass paywalls, authentication, or closed legal systems.
- Never claim full access to private consultant/garant knowledge bases.
