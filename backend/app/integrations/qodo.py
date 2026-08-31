import json
import os
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

DEFAULT_REPOSITORY = 'harshapriyag123/harness-os'
DEFAULT_PR_NUMBER = '7'

def _request_json(url):
    headers = {'Accept':'application/vnd.github+json','User-Agent':'Harness-OS-Qodo-Evidence','X-GitHub-Api-Version':'2022-11-28'}
    token = os.getenv('GITHUB_TOKEN','').strip()
    if token:
        headers['Authorization'] = f'Bearer {token}'
    with urlopen(Request(url, headers=headers), timeout=4) as response:
        return json.loads(response.read().decode('utf-8'))

def snapshot(repository=None, pr_number=None):
    repository = (repository or os.getenv('QODO_REPOSITORY', DEFAULT_REPOSITORY)).strip() or DEFAULT_REPOSITORY
    raw_pr = str(pr_number if pr_number is not None else os.getenv('QODO_PR_NUMBER', DEFAULT_PR_NUMBER)).strip()
    try:
        prn = int(raw_pr)
    except ValueError:
        return {'name':'Qodo Review','status':'UNAVAILABLE','detail':f'Invalid Qodo PR number: {raw_pr}.','href':f'https://github.com/{repository}','proof':{'repository':repository,'pr_number':raw_pr}}
    evidence_url = f'https://github.com/{repository}/pull/{prn}'
    api_root = f'https://api.github.com/repos/{repository}'
    try:
        issue_comments = _request_json(f'{api_root}/issues/{prn}/comments?per_page=100')
        reviews = _request_json(f'{api_root}/pulls/{prn}/reviews?per_page=100')
        candidates = []
        for item in issue_comments:
            login = ((item.get('user') or {}).get('login') or '').lower()
            if 'qodo' in login:
                candidates.append({'kind':'comment','author':(item.get('user') or {}).get('login'),'created_at':item.get('created_at'),'url':item.get('html_url'),'body':item.get('body') or ''})
        for item in reviews:
            login = ((item.get('user') or {}).get('login') or '').lower()
            if 'qodo' in login:
                candidates.append({'kind':'review','author':(item.get('user') or {}).get('login'),'created_at':item.get('submitted_at') or item.get('created_at'),'url':item.get('html_url'),'body':item.get('body') or '','state':item.get('state')})
        candidates.sort(key=lambda item:item.get('created_at') or '', reverse=True)
        latest = candidates[0] if candidates else None
        if not latest:
            return {'name':'Qodo Review','status':'WAITING_FOR_REVIEW','detail':f'PR #{prn} exists, but Qodo review evidence is not available yet. Replay remains locked.','href':evidence_url,'proof':{'repository':repository,'pr_number':prn,'qodo_events':0}}
        body = ' '.join((latest.get('body') or '').split())
        summary = body[:220] + ('…' if len(body) > 220 else '')
        return {'name':'Qodo Review','status':'EVIDENCE_FOUND','detail':summary or f'Qodo evidence found on PR #{prn}.','href':latest.get('url') or evidence_url,'proof':{'repository':repository,'pr_number':prn,'qodo_events':len(candidates),'latest_kind':latest.get('kind'),'latest_at':latest.get('created_at'),'latest_author':latest.get('author'),'review_state':latest.get('state')}}
    except (HTTPError, URLError, TimeoutError, ValueError, json.JSONDecodeError) as exc:
        return {'name':'Qodo Review','status':'UNAVAILABLE','detail':f'Could not retrieve Qodo evidence from GitHub: {exc}','href':evidence_url,'proof':{'repository':repository,'pr_number':prn}}

def is_reviewed(repository, pr_number):
    evidence = snapshot(repository, pr_number)
    return evidence.get('status') == 'EVIDENCE_FOUND', evidence
