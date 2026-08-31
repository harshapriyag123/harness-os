import json
import os
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


DEFAULT_REPOSITORY = 'harshapriyag123/harness-os'
DEFAULT_PR_NUMBER = '7'


def _request_json(url: str):
    headers = {
        'Accept': 'application/vnd.github+json',
        'User-Agent': 'Harness-OS-Qodo-Evidence',
        'X-GitHub-Api-Version': '2022-11-28',
    }
    token = os.getenv('GITHUB_TOKEN', '').strip()
    if token:
        headers['Authorization'] = f'Bearer {token}'
    request = Request(url, headers=headers)
    with urlopen(request, timeout=4) as response:
        return json.loads(response.read().decode('utf-8'))


def snapshot():
    repository = os.getenv('QODO_REPOSITORY', DEFAULT_REPOSITORY).strip() or DEFAULT_REPOSITORY
    pr_number = os.getenv('QODO_PR_NUMBER', DEFAULT_PR_NUMBER).strip() or DEFAULT_PR_NUMBER
    evidence_url = f'https://github.com/{repository}/pull/{pr_number}'
    api_root = f'https://api.github.com/repos/{repository}'

    try:
        issue_comments = _request_json(f'{api_root}/issues/{pr_number}/comments?per_page=100')
        reviews = _request_json(f'{api_root}/pulls/{pr_number}/reviews?per_page=100')
        candidates = []

        for item in issue_comments:
            login = ((item.get('user') or {}).get('login') or '').lower()
            if 'qodo' in login:
                candidates.append({
                    'kind': 'comment',
                    'author': (item.get('user') or {}).get('login'),
                    'created_at': item.get('created_at'),
                    'url': item.get('html_url'),
                    'body': item.get('body') or '',
                })

        for item in reviews:
            login = ((item.get('user') or {}).get('login') or '').lower()
            if 'qodo' in login:
                candidates.append({
                    'kind': 'review',
                    'author': (item.get('user') or {}).get('login'),
                    'created_at': item.get('submitted_at') or item.get('created_at'),
                    'url': item.get('html_url'),
                    'body': item.get('body') or '',
                    'state': item.get('state'),
                })

        candidates.sort(key=lambda item: item.get('created_at') or '', reverse=True)
        latest = candidates[0] if candidates else None
        if not latest:
            return {
                'name': 'Qodo Review',
                'status': 'NO REVIEW FOUND',
                'detail': f'GitHub PR #{pr_number} is reachable, but no Qodo bot review/comment was found.',
                'href': evidence_url,
                'proof': {'repository': repository, 'pr_number': int(pr_number), 'qodo_events': 0},
            }

        body = ' '.join((latest.get('body') or '').split())
        summary = body[:220] + ('…' if len(body) > 220 else '')
        return {
            'name': 'Qodo Review',
            'status': 'EVIDENCE FOUND',
            'detail': summary or f'Qodo evidence found on PR #{pr_number}.',
            'href': latest.get('url') or evidence_url,
            'proof': {
                'repository': repository,
                'pr_number': int(pr_number),
                'qodo_events': len(candidates),
                'latest_kind': latest.get('kind'),
                'latest_at': latest.get('created_at'),
                'latest_author': latest.get('author'),
                'review_state': latest.get('state'),
            },
        }
    except (HTTPError, URLError, TimeoutError, ValueError, json.JSONDecodeError) as exc:
        return {
            'name': 'Qodo Review',
            'status': 'UNAVAILABLE',
            'detail': f'Could not retrieve Qodo evidence from GitHub: {exc}',
            'href': evidence_url,
            'proof': {'repository': repository, 'pr_number': int(pr_number)},
        }
