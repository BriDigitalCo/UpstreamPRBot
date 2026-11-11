# UpstreamPRBot

Automated GitHub pull request submission system for BriDigitalCo.

## Status

**Prepared, but DISABLED by default.** This repository's workflow does not submit
to upstream projects unless both of these account-owner settings exist:

- GitHub Actions repository secret `BRI_UPSTREAM_PR_TOKEN` with an appropriate
  GitHub identity credential.
- GitHub Actions repository variable `AUTO_SUBMIT_ENABLED` set to `true`.

The automation is designed to submit one qualified pull request at most per
scheduled run, from an explicitly designated branch in
`BriDigitalCo/Go-Hybrid` to `limitlessprojects/Go-Hybrid`. It does **not**
approve code quality, guarantee a bounty, merge code, or receive money.

## Owner-only activation

1. In GitHub, create an expiring personal access token for the **BriDigitalCo
   identity**, or a separate low-privilege bot identity that has write access
   to the relevant source fork. For a classic PAT consider only `public_repo`
   for public repositories, not the broader `repo` scope. Verify GitHub's
   current requirements. Treat a classic PAT as a broad credential; where
   practical, prefer a separately authorized limited GitHub App.
2. In **this** repository's Settings → Secrets and variables → Actions →
   Secrets, create `BRI_UPSTREAM_PR_TOKEN` and paste the token **there only**.
   Never paste a token in a chat, file, commit, issue, or PR.
3. In the adjacent **Variables** tab create `AUTO_SUBMIT_ENABLED` with value
   `true`, after reviewing the committed Python code and workflow. Changing
   it to `false` disables the scheduled submission job.
4. Run the workflow once via **Actions** → **Submit reviewed upstream
   contributions** → **Run workflow**, then inspect the real outcome. A
   skipped job does not prove the credential works, and a run with no
   qualifying branches cannot prove upstream PR creation works.

The scheduled trigger requests every five minutes; GitHub may delay or drop
runs, and it is not an uninterrupted AI coding worker.

## Preconditions on each proposed contribution

The script only scans branches named `submit/<safe-slug>` in
`BriDigitalCo/Go-Hybrid`. It refuses sensitive/configuration files, large
diffs, and a branch with an existing upstream pull request. It requires the
latest commit message to contain:

    fix(scope): accurate, descriptive PR title

    Summary of the reviewed fix and why it is needed.
    Tests-Run: <real test command, outcome and count>
    Upstream-Ready: true
    Tests-Verified: true
    AI-Assistance: permitted
    Payment-Eligibility: verified

These markers are **assertions**, not an independent reviewer. Only add them
after verifying the actual issue, the reward/eligibility/AI policy, duplicate
PRs, relevant tests and diff safety. The automatic submitter **does not**
verify payment independently. Never falsely add markers to force a PR.

A branch containing GitHub workflows or sensitive files is skipped. For each
approved submission it sends the PR to `limitlessprojects/Go-Hybrid` with the
source branch in BriDigitalCo's fork. It creates **at most one new PR per
run** and does not merge or modify upstream settings. The previously created
PR [#4379](https://github.com/limitlessprojects/Go-Hybrid/pull/4379) is
already submitted and must not be duplicated.

## Tests

    python3 -m unittest discover -s .github/scripts -p 'test_*.py' -v

The tests mock GitHub calls; they do not prove the token is authorized to
create upstream pull requests. Do not enable this unattended workflow without
reviewing code and privileges. Keep secrets in this separate repository, not
in the contribution fork.
