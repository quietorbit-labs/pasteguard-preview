"""Read-only cloud checks. Never print tokens or private metric values."""
import json, os
import bot

data = bot.assessment()
print(json.dumps(bot.public_assessment(data), indent=2))
if os.getenv('CF_ANALYTICS_TOKEN') and not data['website_analytics_connected']:
    # Schema names are public API structure, not account traffic values.
    query = '{__schema{types{name fields{name type{kind name ofType{kind name}}}}}}'
    result = bot.request('https://api.cloudflare.com/client/v4/graphql',
                         os.environ['CF_ANALYTICS_TOKEN'], {'query': query})
    if result.get('errors'):
        print('Cloudflare schema discovery unavailable; inspect permissions.')
    else:
        for item in (result.get('data') or {}).get('__schema', {}).get('types', []):
            if 'rumpageloadevents' in item['name'].lower():
                print('Schema:', json.dumps(item))
if not data['website_analytics_connected']:
    raise SystemExit('Website analytics connection has not passed.')
print('Website analytics authenticated and queried successfully; private counts withheld.')
if not data['instagram_connected']:
    print('Instagram connection is still missing. No publishing request was made.')
