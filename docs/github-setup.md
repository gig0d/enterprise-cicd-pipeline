# GitHub setup and owner-controlled settings

Repository: `gig0d/enterprise-cicd-pipeline`; origin: `https://github.com/gig0d/enterprise-cicd-pipeline.git`; branch: `main`.

## Local authorship

After cloning, configure the repository locally:

```powershell
git config --local user.name 'Giovanny Alvarado Barrantes'
git config --local user.email 'gioab0411@gmail.com'
git config --local core.hooksPath .githooks
git remote -v
git var GIT_AUTHOR_IDENT
git var GIT_COMMITTER_IDENT
```

Inspect conflicting `GIT_AUTHOR_*`/`GIT_COMMITTER_*` environment overrides before committing. The hook rejects incorrect identities. Use Conventional Commits, review the staged diff, run applicable checks and Gitleaks, inspect resulting author/committer metadata, push to the exact remote, and verify its SHA. Do not add AI attribution or automation coauthors.

## Observed settings

The initial API inspection on 2026-10-27 found a public empty repository, owner admin/push access, read-only default workflow tokens, no branch protection/rulesets, and no environments. The owner subsequently authorized GHCR publication and `ENABLE_GHCR_PUBLISH=true` was set and read back. After successful staging/release simulations created the environments, the owner explicitly approved main-only restrictions on both and production review by `gig0d`, with administrator bypass disabled and self-review allowed. Those settings were applied and verified through the API. `main` branch protection remains a recommendation, not an active control. See [verification](verification.md) and the [environment snapshot](evidence/environment-settings.json).

Repository protection and reviewer rules are not enabled merely by committing YAML. No important security setting is changed without the owner's explicit approval. Optional promotion/draft jobs request extra permission only when the owner deliberately selects those manual inputs; those operations are not needed for the default simulation.

## Recommended branch protection

In **Settings → Rules → Rulesets**, create an active branch ruleset targeting the default branch (or use **Settings → Branches → Add branch protection rule** for `main`):

1. Require a pull request before merging.
2. Require the observed **CI required checks** status and require the branch to be up to date.
3. Block force pushes and branch deletion.
4. Require conversation resolution and disallow bypass, including administrator bypass.
5. For a solo repository, choose the approval count deliberately; requiring a second person's review requires an additional collaborator. Do not claim peer review when only a PR is required.

Keep the status name exact and verify the rule through the API after saving. If a protected branch rejects a push, use a dedicated owner-authored feature branch and PR; never weaken the rule or force push. Inspect merge metadata too: the strict project identity policy applies to development commits and may require an owner-approved merge procedure.

## Environments and production approval

In **Settings → Environments**, inspect/create `staging` and `production`. For each, select **Deployment branches and tags → Selected branches and tags**, add a **branch** rule for `main`, and avoid unrestricted sources.

For `production`, add `gig0d` as a required reviewer and disable administrator bypass. In this solo-owner project, permitting self-review allows the owner to approve a manually initiated deployment. Enable **Prevent self-review** only after adding a different authorized reviewer; otherwise the sole owner cannot approve their own dispatch. These options depend on repository plan/visibility; verify availability and saved settings in the UI/API.

The workflow never approves its own pending deployment. Without a saved required-reviewer rule, the implemented fallback is owner-only manual dispatch on `main`. That fallback is not GitHub-enforced reviewer approval. The environments represent ephemeral container verification, not persistent hosted services.

## Actions and package settings

In **Settings → Actions → General → Workflow permissions**, keep **Read repository contents and packages permissions** and leave PR creation/approval disabled. Each job grants only its required extra permission. Keep checkout credentials unpersisted and do not expose secrets to PR code.

GHCR publication uses the run's `GITHUB_TOKEN`; no repository token secret is required. Keep the package linked to this repository and verify this repository has Actions access. The source OCI label establishes that link. Package visibility is separate from repository visibility; do not assume a public source repository makes its image public. No workflow changes package visibility.

Owner-approved activation uses **Settings → Secrets and variables → Actions → Variables → New repository variable**: name `ENABLE_GHCR_PUBLISH`, value `true`. Removing/disabling that variable prevents future automatic publication; local Docker validation still works. Do not change this switch to bypass a failed gate.

Enable dependency graph, vulnerability alerts, and supported supply-chain features under **Settings → Advanced Security** when available. Automatic dependency version-update commits are intentionally disabled to preserve required development authorship; weekly audits are read-only. Review and apply dependency, Action, scanner checksum, and base-image updates manually, then run the complete pipeline.

References: [GitHub environment protection](https://docs.github.com/en/actions/reference/workflows-and-actions/deployments-and-environments), [branch protection](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/about-protected-branches), [package access and visibility](https://docs.github.com/en/packages/learn-github-packages/configuring-a-packages-access-control-and-visibility).
