import unittest
from unittest.mock import patch
import submit_reviewed as bot

VALID = (
    "fix(corpus): prevent invalid cross-paragraph matches\n\n"
    "Reject false-positive breakdowns.\n"
    "Tests-Run: python3 -m unittest ... (17 passed)\n"
    "Upstream-Ready: true\n"
    "Tests-Verified: true\n"
    "AI-Assistance: permitted\n"
    "Payment-Eligibility: verified\n"
)


def simulate(*, existing=False, blocked=False, message=VALID):
    calls = []

    def fake_api(path, payload=None):
        calls.append((path, payload))
        if path.endswith("branches?per_page=100&page=1"):
            return [
                {"name": "submit/valid-fix"},
                {"name": "fix/not-approved"},
            ]
        if "/pulls?" in path:
            return [{"number": 4379}] if existing else []
        if "/compare/" in path:
            return {"ahead_by": 2, "files": [
                {"filename": ".github/workflows/surprise.yml" if blocked else "tools/check.py", "changes": 15}
            ]}
        if "/commits/" in path:
            return {"commit": {"message": message}}
        if path.endswith("/pulls") and payload is not None:
            return {"html_url": "https://github.com/limitlessprojects/Go-Hybrid/pull/5000"}
        raise AssertionError("Unexpected call: " + path)

    with patch.object(bot, "TOKEN", "mock-not-real"), patch.object(bot, "api", side_effect=fake_api):
        status = bot.run()
    return status, calls


class SubmissionTests(unittest.TestCase):
    def test_no_token_does_not_make_network_call(self):
        with patch.object(bot, "TOKEN", ""), patch.object(bot, "api", side_effect=AssertionError("No network call allowed")):
            self.assertEqual(bot.run(), 0)

    def test_ready_markers_required(self):
        self.assertIsNone(bot.ready_message("fix: no verification"))
        self.assertIsNone(bot.ready_message(VALID.replace("AI-Assistance: permitted", "AI-Assistance: unknown")))
        self.assertIsNone(bot.ready_message(VALID.replace("Payment-Eligibility: verified", "Payment-Eligibility: unknown")))
        self.assertIsNotNone(bot.ready_message(VALID))

    def test_creates_one_pr_with_scoped_repository_and_head(self):
        status, calls = simulate()
        self.assertEqual(status, 0)
        posts = [(url, body) for url, body in calls if body is not None]
        self.assertEqual(len(posts), 1)
        self.assertEqual(posts[0][0], "/repos/limitlessprojects/Go-Hybrid/pulls")
        self.assertEqual(posts[0][1]["head"], "BriDigitalCo:submit/valid-fix")
        self.assertEqual(posts[0][1]["base"], "main")
        self.assertIn("17 passed", posts[0][1]["body"])

    def test_duplicate_is_not_resubmitted(self):
        _, calls = simulate(existing=True)
        self.assertFalse(any(body is not None for _, body in calls))

    def test_workflow_and_secrets_paths_are_skipped(self):
        _, calls = simulate(blocked=True)
        self.assertFalse(any(body is not None for _, body in calls))

    def test_missing_approval_is_skipped(self):
        _, calls = simulate(message="fix: no approval")
        self.assertFalse(any(body is not None for _, body in calls))

    def test_branch_names_are_strictly_allowlisted(self):
        self.assertIsNone(bot.BRANCH_RE.fullmatch("fix/valid-fix"))
        self.assertIsNone(bot.BRANCH_RE.fullmatch("submit/../oops"))
        self.assertTrue(bot.BRANCH_RE.fullmatch("submit/valid-fix"))


if __name__ == "__main__":
    unittest.main()
