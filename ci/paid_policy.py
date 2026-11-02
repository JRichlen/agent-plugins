#!/usr/bin/env python3
"""Attribute CI events before allowing model calls; never call model providers."""
import argparse
import json
import os
from pathlib import Path
import re
import time
import urllib.error
import urllib.request

MAX_COMMITS = 100
MAX_PAGES = 4
PAGE_SIZE = 50
MAX_REQUESTS = 120


class AttributionError(ValueError):
    """A fixed, non-sensitive attribution diagnostic safe to show in CI."""



def explicit_no_paid(pr):
    # Ref is present in the initial opened event; adding a label afterward can
    # race the first run. PR head refs are also available in merge attribution.
    ref = (pr.get("head") or {}).get("ref")
    return isinstance(ref, str) and ref.startswith("no-paid/")


def _identity(value):
    return isinstance(value, str) and re.fullmatch(r"[0-9a-f]{40}", value) is not None


def _authors(prs, repository):
    if not prs:
        raise AttributionError("PR attribution unavailable")
    for pr in prs:
        if ((pr.get("base") or {}).get("repo") or {}).get("full_name") != repository:
            raise AttributionError("PR repository attribution differs")
        login = (pr.get("user") or {}).get("login")
        if not isinstance(login, str) or not login:
            raise AttributionError("PR author attribution unavailable")
    return any((pr["user"]["login"] == "dependabot[bot]") or explicit_no_paid(pr) for pr in prs)


def decide(event_name, event, repository, context=None):
    if event_name == "pull_request":
        pr = event.get("pull_request") or {}
        login = (pr.get("user") or {}).get("login")
        if not isinstance(login, str) or not login:
            raise AttributionError("PR author attribution unavailable")
        if explicit_no_paid(pr):
            return False, "explicit no-paid branch: free checks only"
        bot = login == "dependabot[bot]"
        return not bot, "Dependabot PR: free checks only" if bot else "ordinary PR policy retained"
    if event_name == "workflow_dispatch":
        if not isinstance(context, dict):
            raise AttributionError("manual ref attribution unavailable")
        ref = context.get("ref", "")
        if ref.startswith(("refs/heads/no-paid/", "refs/heads/dependabot/")):
            return False, "manual bot/no-paid ref: free checks only"
        sha = context.get("sha")
        if not _identity(sha):
            raise AttributionError("manual commit identity unavailable")
        prs = [pr for pr in context.get("pulls", []) if pr.get("merge_commit_sha") == sha
               or (pr.get("head") or {}).get("sha") == sha]
        blocked = _authors(prs, repository)
        return not blocked, "manual bot/no-paid attribution: free checks only" if blocked else "attributed manual ref; existing gates retained"
    if event_name != "push":
        raise AttributionError("unsupported event: " + event_name)
    before, after = event.get("before"), event.get("after")
    if not _identity(before) or not _identity(after) or before == after:
        raise AttributionError("push range identity unavailable")
    if not isinstance(context, dict) or (context.get("before"), context.get("after")) != (before, after):
        raise AttributionError("push range attribution unavailable")
    commits = context.get("commits")
    if not isinstance(commits, list) or not 0 < len(commits) <= MAX_COMMITS or len(set(commits)) != len(commits):
        raise AttributionError("introduced commit inventory unavailable or exceeds bound")
    if after not in commits or before in commits or not all(_identity(sha) for sha in commits):
        raise AttributionError("introduced commit inventory differs from push")
    blocked = False
    for sha in commits:
        associated = context.get("pulls", {}).get(sha)
        if not isinstance(associated, list):
            raise AttributionError("introduced commit lacks PR attribution")
        merged = [pr for pr in associated if pr.get("merged_at") and pr.get("merge_commit_sha") in commits
                  and ((pr.get("base") or {}).get("repo") or {}).get("full_name") == repository]
        blocked = _authors(merged, repository) or blocked
    return not blocked, "push includes bot/no-paid work: free checks only" if blocked else "entire push attributed to ordinary merged PRs; existing policy retained"


class GitHubReader:
    def __init__(self, repository, token):
        if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repository) or not token:
            raise AttributionError("authenticated repository attribution unavailable")
        self.repository, self.token = repository, token
        self.requests, self.deadline = 0, time.monotonic() + 90

    def read(self, path, page):
        self.requests += 1
        remaining = self.deadline - time.monotonic()
        if self.requests > MAX_REQUESTS or remaining <= 0:
            raise AttributionError("attribution request/time bound exceeded")
        url = f"https://api.github.com/repos/{self.repository}/{path}?per_page={PAGE_SIZE}&page={page}"
        request = urllib.request.Request(url, headers={"Authorization": "Bearer " + self.token,
                                                     "Accept": "application/vnd.github+json",
                                                     "X-GitHub-Api-Version": "2022-11-28"})
        class NoRedirect(urllib.request.HTTPRedirectHandler):
            def redirect_request(self, *args):
                return None
        with urllib.request.build_opener(NoRedirect()).open(request, timeout=min(30, remaining)) as response:
            return json.load(response), 'rel="next"' in response.headers.get("Link", "")


def pages(reader, path):
    for page in range(1, MAX_PAGES + 1):
        document, more = reader.read(path, page)
        yield document
        if not more:
            return
    raise AttributionError("attribution pagination bound exceeded")


def associated_prs(reader, sha):
    if not _identity(sha):
        raise AttributionError("invalid commit identity")
    result = []
    for document in pages(reader, f"commits/{sha}/pulls"):
        if not isinstance(document, list):
            raise AttributionError("invalid associated PR response")
        result.extend(document)
    return result


def inspect_push(reader, before, after):
    if not _identity(before) or not _identity(after) or before == after:
        raise AttributionError("invalid push range")
    commits, expected = [], None
    for document in pages(reader, f"compare/{before}...{after}"):
        count = document.get("total_commits")
        if (document.get("status") != "ahead" or (document.get("base_commit") or {}).get("sha") != before
                or type(count) is not int or not 0 < count <= MAX_COMMITS or (expected is not None and count != expected)):
            raise AttributionError("unresolved or oversized push range")
        expected = count
        commits.extend(item["sha"] for item in document["commits"])
    if len(commits) != expected or len(set(commits)) != expected or after not in commits or not all(_identity(sha) for sha in commits):
        raise AttributionError("truncated or inconsistent push range")
    return {"before": before, "after": after, "commits": commits,
            "pulls": {sha: associated_prs(reader, sha) for sha in commits}}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--event", default=os.environ.get("GITHUB_EVENT_NAME"))
    args = parser.parse_args()
    event = json.loads(Path(os.environ["GITHUB_EVENT_PATH"]).read_text(encoding="utf-8"))
    repository = os.environ["GITHUB_REPOSITORY"]
    try:
        context = None
        if args.event == "push":
            context = inspect_push(GitHubReader(repository, os.environ.get("GH_TOKEN")), event.get("before"), event.get("after"))
        elif args.event == "workflow_dispatch":
            context = {"ref": os.environ.get("GITHUB_REF", ""), "sha": os.environ.get("GITHUB_SHA", "")}
            if not context["ref"].startswith(("refs/heads/no-paid/", "refs/heads/dependabot/")):
                context["pulls"] = associated_prs(GitHubReader(repository, os.environ.get("GH_TOKEN")), context["sha"])
        allowed, reason = decide(args.event, event, repository, context)
    except Exception as error:
        # Never print HTTP request headers, credentials or server response bodies.
        detail = str(error) if isinstance(error, AttributionError) else ("HTTP " + str(error.code) if isinstance(error, urllib.error.HTTPError) else type(error).__name__)
        print("::error::paid policy could not establish attribution: " + detail + "; model calls blocked")
        return 1
    with open(os.environ["GITHUB_OUTPUT"], "a", encoding="utf-8", newline="\n") as output:
        output.write(f"allowed={str(allowed).lower()}\nreason={reason}\n")
    with open(os.environ["GITHUB_STEP_SUMMARY"], "a", encoding="utf-8", newline="\n") as summary:
        summary.write(f"Model-call policy: **{'eligible' if allowed else 'SKIPPED'}** — {reason}. Eligibility does not override labels, free checks or other gates.\n")
    print(reason)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
