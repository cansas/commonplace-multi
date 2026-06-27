# Contributing

Thanks for your interest in Commonplace! Small fixes, typos, and improvements are always welcome.

## Bug Reports & Feature Requests

Open a [GitHub Issue](https://github.com/cansas/commonplace/issues). Include:

- What you expected vs what happened
- Steps to reproduce
- Screenshots if relevant
- Your environment (browser, OS, self-hosted version)

For bugs, include relevant logs or error messages if possible.

## Pull Requests

1. **Discuss first** — For anything beyond a one-line fix, open an issue first so we agree on the approach before you put work in.
2. **Keep it small** — One PR = one thing. No surprise scope creep.
3. **Test it** — Run `pytest tests/ -v` before opening. Add tests for new functionality.
4. **Commit messages** — Use [Conventional Commits](https://www.conventionalcommits.org/):
   ```
   feat: add email digest unsubscribe link
   fix: resolve crash when book has no highlights
   docs: update deploy instructions
   refactor: extract settings service from routes
   ```
5. **Target `main`** — PRs merge to `main`. CI runs automatically on push.

## AI-Generated Code

AI-assisted code (Copilot, LLMs, agents, etc.) is welcome — this project is itself maintained with AI assistance. Guidelines:

- **Review the output** before submitting. AI can produce code that looks plausible but has subtle bugs, security issues, or doesn't fit the project's style.
- **Test it** like any other contribution. AI code isn't exempt from CI.
- **Be honest** — no need to hide it. Just mark the PR description clearly.

## Code Standards

- Python: `ruff` for linting and formatting
- Templates: Jinja2, Tailwind CSS classes
- JS: vanilla, no framework — keep it consistent with `app/static/commonplace.js`
- Follow established patterns in the codebase (same error handling, same logging style, same function signatures)
- No `'unsafe-inline'` in CSP — use event delegation with `data-*` attributes instead of inline handlers

## Local Development

```bash
git clone https://github.com/cansas/commonplace
cd commonplace
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
COMMONPLACE_USERNAME=admin COMMONPLACE_PASSWORD=devpass \
  SESSION_SECRET=dev-secret SESSION_HTTPS_ONLY=false \
  python -m app.main
```

Opens at `http://localhost:8765`.

## Licensing

By contributing, you agree that your contributions will be licensed under the project's license.
