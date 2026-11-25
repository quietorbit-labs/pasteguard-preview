"""Render six verified fake-data demos and upload intended-public video assets."""
import datetime as dt
import json
import os
from pathlib import Path
import shutil
import subprocess
import urllib.request

import bot
import render


def main():
    tag = 'pasteguard-silent-library-v1'
    try:
        release = bot.github('releases/tags/' + tag)
    except RuntimeError as error:
        if '404' not in str(error):
            raise
        release = bot.github('releases', {
            'tag_name': tag, 'name': 'PasteGuard verified silent demos',
            'body': 'Six seven-second silent demos with invented data.',
            'prerelease': True,
        }, 'POST')

    def upload(filename, content_type):
        name = filename.name
        existing = next((asset for asset in release.get('assets', []) if asset['name'] == name), None)
        if existing:
            return existing['browser_download_url']
        url = release['upload_url'].split('{')[0] + '?name=' + name
        request = urllib.request.Request(url, data=filename.read_bytes(), method='POST', headers={
            'Authorization': 'Bearer ' + os.environ['GITHUB_TOKEN'],
            'Content-Type': content_type, 'Accept': 'application/vnd.github+json',
        })
        with urllib.request.urlopen(request, timeout=90) as response:
            return json.load(response)['browser_download_url']

    assets = Path('library-assets')
    assets.mkdir(exist_ok=True)
    videos = []
    for index, example in enumerate(bot.EXAMPLES):
        # plan chooses the matching fixture by ordinal modulo six.
        date = dt.date(2026, 12, 1)
        while date.toordinal() % len(bot.EXAMPLES) != index:
            date += dt.timedelta(days=1)
        plan = bot.plan({'decision': 'explore_no_winner'}, date)
        Path('run').mkdir(exist_ok=True)
        Path('run/plan.json').write_text(json.dumps(plan))
        subprocess.run(['node', 'automation/capture.mjs'], check=True)
        render.render()
        verified = json.loads(Path('run/verification.json').read_text())
        if verified.get('audio') != 'none' or verified.get('seconds') != 7 or not verified.get('decode_passed'):
            raise ValueError('Silent video verification failed')
        target = assets / (example['name'] + '.mp4')
        shutil.copyfile('run/video.mp4', target)
        videos.append({'example': example['name'], 'url': upload(target, 'video/mp4'),
                       'caption': plan['caption']})
    manifest = assets / 'library.json'
    manifest.write_text(json.dumps({'videos': videos}, indent=2))
    print('Verified video library:', upload(manifest, 'application/json'))


if __name__ == '__main__':
    main()
