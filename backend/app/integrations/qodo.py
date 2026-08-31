from __future__ import annotations

import json
import os
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

DEFAULT_REPOSITORY = "harshapriyag123/harness-os"
DEFAULT_PR_NUMBER = "7"
DEFAULT_BOT_LOGINS = {"qodo-code-review[bot]"}
MAX_PAGES = 10
PER_PAGE = 100


def _bot_logins() -> set[str]:
    configured = {
        x.strip().lower()
        for x in os.getenv("QODO_BOT_LOGINS", "qodo-code-review[bot]").split(",")
        if x.strip()
    }
    return configured or set(DEFAULT_BOT_LOGINS)


def _request_json(url: str):
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "Harness-OS-Qodo-Evidence",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    token = os.getenv("GITHUB_TOKEN", "").strip()
    if token:
        headers["Authorization"] = f"Bearer {token}"
    with urlopen(Request(url, headers=headers), timeout=4) as response:
        return json.loads(response.read().decode("utf-8"))


def _paged(api_url: str) -> list[dict]:
    items: list[dict] = []
    for page in range(1, MAX_PAGES + 1):
        sep = "&" if "?" in api_url else "?"
        payload = _request_json(f"{api_url}{sep}{urlencode({'per_page': PER_PAGE, 'page': page})}")
        if not isinstance(payload, list):
            raise TypeError("GitHub collection response must be a list")
        page_items = [item for item in payload if isinstance(item, dict)]
        items.extend(page_items)
        if len(payload) < PER_PAGE:
            break
    return items


def _resolve_target(repository, pr_number):
    explicit_repository = repository is not None
    explicit_pr = pr_number is not None
    raw_repository = repository if explicit_repository else os.getenv("QODO_REPOSITORY", DEFAULT_REPOSITORY)
    raw_pr = pr_number if explicit_pr else os.getenv("QODO_PR_NUMBER", DEFAULT_PR_NUMBER)
    if not isinstance(raw_repository, str) or not raw_repository.strip():
        raise ValueError("Qodo repository must be a non-blank owner/repository value")
    repository = raw_repository.strip()
    if repository.count("/") != 1 or any(ch.isspace() for ch in repository):
        raise ValueError("Qodo repository must use owner/repository format")
    raw_pr_text = str(raw_pr).strip()
    if not raw_pr_text:
        raise ValueError("Qodo PR number must be non-blank")
    prn = int(raw_pr_text)
    if prn <= 0:
        raise ValueError("Qodo PR number must be positive")
    return repository, prn


def _unavailable(detail: str, repository=None, pr_number=None):
    repo = repository if isinstance(repository, str) and repository.strip() else None
    href = f"https://github.com/{repo}" if repo else None
    return {
        "name": "Qodo Review",
        "status": "UNAVAILABLE",
        "detail": detail,
        "href": href,
        "proof": {"repository": repo, "pr_number": pr_number},
    }


def snapshot(repository=None, pr_number=None, commit_sha: str | None = None, *, require_commit: bool = False):
    try:
        repository, prn = _resolve_target(repository, pr_number)
    except (TypeError, ValueError) as exc:
        return _unavailable(str(exc), repository, pr_number)

    expected_sha = (commit_sha or "").strip()
    if require_commit and not expected_sha:
        return _unavailable("A commit SHA is required for certification-grade Qodo evidence.", repository, prn)

    evidence_url = f"https://github.com/{repository}/pull/{prn}"
    api_root = f"https://api.github.com/repos/{repository}"
    official = _bot_logins()
    try:
        issue_comments = _paged(f"{api_root}/issues/{prn}/comments")
        reviews = _paged(f"{api_root}/pulls/{prn}/reviews")
        informational: list[dict] = []
        commit_reviews: list[dict] = []

        for item in issue_comments:
            user = item.get("user") if isinstance(item.get("user"), dict) else {}
            login = str(user.get("login") or "").lower()
            if login in official:
                informational.append({
                    "kind": "comment",
                    "author": user.get("login"),
                    "created_at": item.get("created_at"),
                    "url": item.get("html_url"),
                    "body": item.get("body") or "",
                    "commit_id": None,
                })

        for item in reviews:
            user = item.get("user") if isinstance(item.get("user"), dict) else {}
            login = str(user.get("login") or "").lower()
            if login in official:
                record = {
                    "kind": "review",
                    "author": user.get("login"),
                    "created_at": item.get("submitted_at") or item.get("created_at"),
                    "url": item.get("html_url"),
                    "body": item.get("body") or "",
                    "state": item.get("state"),
                    "commit_id": item.get("commit_id"),
                }
                informational.append(record)
                if expected_sha and item.get("commit_id") == expected_sha:
                    commit_reviews.append(record)

        informational.sort(key=lambda x: x.get("created_at") or "", reverse=True)
        commit_reviews.sort(key=lambda x: x.get("created_at") or "", reverse=True)
        latest = commit_reviews[0] if require_commit and commit_reviews else informational[0] if informational else None

        if require_commit and not commit_reviews:
            return {
                "name": "Qodo Review",
                "status": "WAITING_FOR_REVIEW",
                "detail": f"PR #{prn} has no official Qodo review bound to commit {expected_sha[:12]}. Replay remains locked.",
                "href": evidence_url,
                "proof": {
                    "repository": repository,
                    "pr_number": prn,
                    "expected_commit_sha": expected_sha,
                    "reviewed_commit_sha": None,
                    "qodo_events": len(informational),
                    "commit_bound_reviews": 0,
                },
            }

        if not latest:
            return {
                "name": "Qodo Review",
                "status": "WAITING_FOR_REVIEW",
                "detail": f"PR #{prn} exists, but official Qodo review evidence is not available yet.",
                "href": evidence_url,
                "proof": {"repository": repository, "pr_number": prn, "qodo_events": 0},
            }

        body = " ".join(str(latest.get("body") or "").split())
        summary = body[:220] + ("…" if len(body) > 220 else "")
        return {
            "name": "Qodo Review",
            "status": "EVIDENCE_FOUND",
            "detail": summary or f"Official Qodo evidence found on PR #{prn}.",
            "href": latest.get("url") or evidence_url,
            "proof": {
                "repository": repository,
                "pr_number": prn,
                "qodo_events": len(informational),
                "latest_kind": latest.get("kind"),
                "latest_at": latest.get("created_at"),
                "latest_author": latest.get("author"),
                "review_state": latest.get("state"),
                "expected_commit_sha": expected_sha or None,
                "reviewed_commit_sha": latest.get("commit_id"),
                "commit_bound_reviews": len(commit_reviews) if expected_sha else None,
            },
        }
    except (HTTPError, URLError, TimeoutError, OSError, TypeError, ValueError, AttributeError, json.JSONDecodeError) as exc:
        return _unavailable(f"Could not retrieve Qodo evidence from GitHub: {exc}", repository, prn)


def is_reviewed(repository, pr_number, commit_sha: str | None = None):
    evidence = snapshot(repository, pr_number, commit_sha, require_commit=bool(commit_sha))
    proof = evidence.get("proof") if isinstance(evidence.get("proof"), dict) else {}
    reviewed = evidence.get("status") == "EVIDENCE_FOUND"
    if commit_sha:
        reviewed = reviewed and proof.get("reviewed_commit_sha") == commit_sha
    return reviewed, evidence
