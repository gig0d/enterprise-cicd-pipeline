# Repository instructions

Build a small Python 3.13 FastAPI service to demonstrate reliable CI/CD. Prioritize delivery, security, reproducibility, and honest evidence; do not add databases, authentication, Kubernetes, or paid infrastructure without a concrete approved need.

- Repository: `enterprise-cicd-pipeline`; only authorized remote: `https://github.com/gig0d/enterprise-cicd-pipeline.git`; default branch: `main`.
- Every development commit must have author **and** committer `Giovanny Alvarado Barrantes <gioab0411@gmail.com>`. Verify local configuration, environment overrides, and `git var` before committing; inspect commit metadata afterward. Never add AI coauthor trailers or attribution in Git metadata or project credits.
- Use professional English for code, comments, tests, docs, workflow names, and Conventional Commit messages.
- Before each commit run the applicable formatting, Ruff, MyPy, tests, build, and security checks. Review the staged diff and scan for secrets. Record unavailable checks accurately.
- Keep dependencies locked, external Actions pinned to verified full commit SHAs, workflow permissions minimal, timeouts bounded, and publishing limited to trusted `main` code. Never use `pull_request_target` to execute pull request code.
- Never commit secrets, environment files, tokens, scanner caches, or generated credentials. Use fake, clearly synthetic fixtures for failure demonstrations.
- Make cohesive incremental commits; push only to the authorized remote and verify the remote SHA. If protections reject a push, use a feature branch and PR. Never force push, discard unrelated work, or rewrite history without owner authorization.
- Maintain the README, architecture, operational runbooks, and verification evidence as behavior changes. Distinguish implemented controls from configured GitHub settings and observed workflow results.
- Never claim CI, security, publishing, staging, approval, release, or rollback success without inspecting the actual result. Runner containers are ephemeral validation, not persistent hosted environments.
- Production promotion is a manual, isolated simulation using an already validated digest. Ask before paid/public deployments, privileged permission grants, or important repository security setting changes.
