"""One read-only cloud test: wait for tonight, then require a confirmed post."""
import datetime as dt
import json
import os
import time
import urllib.request
from zoneinfo import ZoneInfo

ZONE = ZoneInfo('America/Chicago')
BASE = 'https://pasteguard-nightly-publisher.edric-yan2022.workers.dev'


def get(path):
    with urllib.request.urlopen(BASE + path, timeout=30) as response:
        return json.load(response)


def main():
    now = dt.datetime.now(ZONE)
    day = now.date()
    target = dt.datetime.combine(day, dt.time(23), ZONE)
    deadline = target + dt.timedelta(minutes=15)
    if now > deadline:
        raise SystemExit('Tonight\'s test window has passed; no publication was requested.')
    health = get('/health')
    assert health['connected'] and health['username'] == 'pasteguard.local'
    print('Connected cloud timer. This test never sends a publishing request.', flush=True)
    while dt.datetime.now(ZONE) < target:
        time.sleep(min(60, (target - dt.datetime.now(ZONE)).total_seconds()))
    result = None
    while dt.datetime.now(ZONE) <= deadline:
        try:
            record = get('/status')['days'].get(f'day:{day}', {})
            if record.get('phase') == 'published' and record.get('permalink') and record.get('media_id'):
                published = dt.datetime.fromisoformat(record['published_at'].replace('Z', '+00:00')).astimezone(ZONE)
                if published.date() != day or published < target or published > deadline:
                    raise SystemExit('Post exists but its time is outside the requested test window.')
                result = {'verified': True, 'date': str(day), 'published_central': published.isoformat(),
                          'media_id': record['media_id'], 'permalink': record['permalink']}
                break
            if record.get('phase') in ('blocked', 'observed_post'):
                raise SystemExit(f'Independent timer did not publish: {record["phase"]}. No retry requested.')
        except (OSError, ValueError, KeyError) as error:
            print(f'Read-only check temporarily unavailable: {type(error).__name__}', flush=True)
        time.sleep(30)
    os.makedirs('run', exist_ok=True)
    if result is None:
        result = {'verified': False, 'date': str(day), 'reason': 'No confirmed publication by 11:15 PM Central'}
    with open('run/cloud-timer-test.json', 'w') as output:
        json.dump(result, output, indent=2)
    with open(os.environ['GITHUB_STEP_SUMMARY'], 'a') as output:
        output.write('### Actual nightly publishing test\n\n' + json.dumps(result, indent=2) + '\n')
    print(json.dumps(result), flush=True)
    if not result['verified']:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
