"""Free event attribution and all-model-job controls; never contact a provider."""
import importlib.util
import io
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest import mock
import urllib.error
import yaml

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("paid_policy", ROOT / "ci/paid_policy.py")
policy = importlib.util.module_from_spec(spec)
spec.loader.exec_module(policy)
SHA = "a" * 40
BEFORE = "b" * 40
EARLIER = "c" * 40
PUSH = {"before": BEFORE, "after": SHA}
REPO = "example/plugins"


def merged(author, sha=SHA):
    return {"merged_at": "2026-11-01T00:00:00Z", "merge_commit_sha": sha,
            "user": {"login": author}, "base": {"repo": {"full_name": REPO}}}


def context(prs):
    return {**PUSH, "commits": [SHA], "pulls": {SHA: prs}}


class SpendPolicy(unittest.TestCase):
    def test_real_aggregates_distinguish_no_paid_from_failure(self):
        host_spec = importlib.util.spec_from_file_location("policy_host", ROOT / "ci/host_tools.py")
        host = importlib.util.module_from_spec(host_spec)
        host_spec.loader.exec_module(host)
        jobs = yaml.load((ROOT / ".github/workflows/evals.yml").read_text(encoding="utf-8"), Loader=yaml.BaseLoader)["jobs"]
        with tempfile.TemporaryDirectory() as folder:
            environment = {**os.environ, "CHEAP": "success", "POLICY": "success", "ALLOWED": "false",
                           "REASON": "Dependabot merge: free checks only", "DETECT": "success", "RUN": "skipped",
                           "GRADER": "skipped", "PLUGINS": '["fixture"]', "CHANGED": "true", "ENABLED": "true",
                           "GITHUB_STEP_SUMMARY": str(Path(folder) / "summary")}
            for name in ("behavioral", "deep"):
                for changes, expected in (({}, 0), ({"POLICY": "failure"}, 1), ({"CHEAP": "failure"}, 1), ({"RUN": "success"}, 1)):
                    with self.subTest(job=name, changes=changes):
                        result = subprocess.run([host.select_bash(), "-c", jobs[name]["steps"][0]["run"]],
                                                env={**environment, **changes}, capture_output=True)
                        self.assertEqual(result.returncode, expected, result.stdout + result.stderr)
                        if expected == 0:
                            self.assertIn(b"SKIPPED", result.stdout)
                            self.assertNotIn(b"legs passed", result.stdout)

    def test_prerequisite_can_opt_out_from_first_event_through_merge(self):
        pr = {**merged("human"), "head": {"ref": "no-paid/dependency-policy"}}
        self.assertFalse(policy.decide("pull_request", {"pull_request": pr}, REPO)[0])
        self.assertFalse(policy.decide("push", PUSH, REPO, context([pr]))[0])

    def test_bot_pr_never_eligible_even_with_paid_label(self):
        event = {"pull_request": {"user": {"login": "dependabot[bot]"}, "labels": [{"name": "paid-evals"}]}}
        self.assertFalse(policy.decide("pull_request", event, REPO)[0])

    def test_bot_merge_with_human_actor_never_eligible(self):
        self.assertFalse(policy.decide("push", {**PUSH, "sender": {"login": "human"}}, REPO, context([merged("dependabot[bot]")]))[0])

    def test_ordinary_policy_retained(self):
        self.assertTrue(policy.decide("pull_request", {"pull_request": {"user": {"login": "human"}}}, REPO)[0])
        self.assertTrue(policy.decide("workflow_dispatch", {}, REPO, {"ref": "refs/heads/main", "sha": SHA, "pulls": [merged("human")]})[0])
        self.assertTrue(policy.decide("push", PUSH, REPO, context([merged("human")]))[0])

    def test_unresolved_or_wrong_attribution_fails_closed(self):
        for evidence in (None, {}, context([]), context([merged("human", BEFORE)]), context([{**merged("human"), "merged_at": None}]),
                         context([{**merged("human"), "base": {"repo": {"full_name": "other/repo"}}}]), context([merged("")])):
            with self.subTest(evidence=evidence), self.assertRaises(ValueError):
                policy.decide("push", PUSH, REPO, evidence)

    def test_bot_in_exact_shared_merge_blocks_spending(self):
        self.assertFalse(policy.decide("push", PUSH, REPO, context([merged("human"), merged("dependabot[bot]")]))[0])

    def test_earlier_bot_merge_and_human_tip_never_spend(self):
        evidence = {**PUSH, "commits": [EARLIER, SHA], "pulls": {
            EARLIER: [merged("dependabot[bot]", EARLIER)], SHA: [merged("human")]}}
        self.assertFalse(policy.decide("push", PUSH, REPO, evidence)[0])
        evidence["pulls"][EARLIER] = []
        with self.assertRaises(ValueError):
            policy.decide("push", PUSH, REPO, evidence)

    def test_feature_commits_can_bind_to_their_introduced_merge(self):
        evidence = {**PUSH, "commits": [EARLIER, SHA], "pulls": {sha: [merged("human")] for sha in (EARLIER, SHA)}}
        self.assertTrue(policy.decide("push", PUSH, REPO, evidence)[0])

    def test_manual_dispatch_has_no_bot_or_unknown_exception(self):
        for ref in ("refs/heads/no-paid/prerequisite", "refs/heads/dependabot/npm/pkg"):
            self.assertFalse(policy.decide("workflow_dispatch", {}, REPO, {"ref": ref})[0])
        self.assertFalse(policy.decide("workflow_dispatch", {}, REPO, {"ref": "refs/heads/main", "sha": SHA, "pulls": [merged("dependabot[bot]")]})[0])
        with self.assertRaises(ValueError):
            policy.decide("workflow_dispatch", {}, REPO, {"ref": "refs/heads/main", "sha": SHA, "pulls": []})

    def test_api_paginates_full_range_and_each_commits_associations(self):
        class Reader:
            def read(self, path, page):
                if path.startswith("compare/"):
                    return {"status": "ahead", "base_commit": {"sha": BEFORE}, "total_commits": 2,
                            "commits": [{"sha": EARLIER if page == 1 else SHA}]}, page == 1
                if path == f"commits/{EARLIER}/pulls":
                    return [merged("human") if page == 1 else merged("dependabot[bot]", EARLIER)], page == 1
                return [merged("human")], False
        evidence = policy.inspect_push(Reader(), BEFORE, SHA)
        self.assertEqual(evidence["commits"], [EARLIER, SHA])
        self.assertFalse(policy.decide("push", PUSH, REPO, evidence)[0])

    def test_api_errors_truncation_and_bounds_do_not_authorize(self):
        class Broken:
            def read(self, path, page):
                raise OSError("synthetic API failure")
        with self.assertRaises(OSError):
            policy.inspect_push(Broken(), BEFORE, SHA)
        class Partial:
            def read(self, path, page):
                return {"status": "ahead", "base_commit": {"sha": BEFORE}, "total_commits": 2, "commits": [{"sha": SHA}]}, False
        with self.assertRaises(ValueError):
            policy.inspect_push(Partial(), BEFORE, SHA)
        class Unending:
            def read(self, path, page):
                return [], True
        with self.assertRaises(ValueError):
            policy.associated_prs(Unending(), SHA)

    def test_http_reader_paginates_without_following_link_urls(self):
        requested = []
        class Response(io.StringIO):
            def __init__(self, more):
                super().__init__(json.dumps([merged("human")]))
                self.headers = {"Link": '<https://untrusted.invalid/next>; rel="next"'} if more else {}
        class Opener:
            def open(self, request, timeout):
                requested.append(request.full_url)
                return Response(len(requested) == 1)
        with mock.patch.object(policy.urllib.request, "build_opener", return_value=Opener()):
            rows = policy.associated_prs(policy.GitHubReader(REPO, "synthetic-token"), SHA)
        self.assertEqual(len(rows), 2)
        self.assertEqual(requested, [f"https://api.github.com/repos/{REPO}/commits/{SHA}/pulls?per_page=50&page={page}" for page in (1, 2)])

    def test_http_failure_and_request_deadline_fail_closed(self):
        reader = policy.GitHubReader(REPO, "synthetic-token")
        with mock.patch.object(policy.urllib.request, "build_opener", side_effect=urllib.error.URLError("fixture only")):
            with self.assertRaises(urllib.error.URLError):
                policy.associated_prs(reader, SHA)
        for attribute, value in (("requests", policy.MAX_REQUESTS), ("deadline", 0)):
            reader = policy.GitHubReader(REPO, "synthetic-token")
            setattr(reader, attribute, value)
            with self.subTest(attribute=attribute), mock.patch.object(policy.urllib.request, "build_opener") as opener:
                with self.assertRaises(ValueError):
                    policy.associated_prs(reader, SHA)
                opener.assert_not_called()

    def test_every_model_job_requires_successful_policy(self):
        jobs = yaml.load((ROOT / ".github/workflows/evals.yml").read_text(encoding="utf-8"), Loader=yaml.BaseLoader)["jobs"]
        paid = {"grader-model", "subject-model", "behavioral-run", "routing-eval", "deep-run"}
        for name in paid:
            self.assertIn("paid-policy", jobs[name]["needs"])
            self.assertIn("needs.paid-policy.result == 'success'", jobs[name]["if"])
            self.assertIn("needs.paid-policy.outputs.allowed == 'true'", jobs[name]["if"])
        self.assertNotIn("paid-policy", jobs["cheap"].get("needs", []))
        for name in ("behavioral", "deep"):
            job = jobs[name]
            self.assertIn("paid-policy", job["needs"])
            script = job["steps"][0]["run"]
            self.assertIn('test "$POLICY" = success', script)
            self.assertIn('test "$RUN" = skipped', script)
            self.assertIn("not a model pass", script)


if __name__ == "__main__":
    unittest.main()
