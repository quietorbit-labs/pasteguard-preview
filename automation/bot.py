"""Cloud assessment and publishing. Never logs credentials or private insight values."""
import argparse,base64,datetime as dt,json,os,time,urllib.request,urllib.parse,urllib.error
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT=Path('run'); TZ=ZoneInfo('America/Chicago'); USERNAME='pasteguard.local'
EXAMPLES=[
 {'name':'error_log','text':'Explain this log:\npassword="DemoOnly_4829"\nerror=HTTP_500','secret':'DemoOnly_4829','context':'error=HTTP_500','subtitle':'Check logs before sharing.'},
 {'name':'support_email','text':'Summarize this ticket:\nEmail: demo@example.com\nissue=login_timeout','secret':'demo@example.com','context':'issue=login_timeout','subtitle':'Check customer details.'},
 {'name':'config_key','text':'Explain this config:\nAKIA0000000000000000\nregion=us-east-1','secret':'AKIA0000000000000000','context':'region=us-east-1','subtitle':'Check config before sharing.'},
]
HOOKS=['Spot it','Before AI','Keep context','Check first']
class SetupRequired(RuntimeError):pass
def request(url,token=None,data=None,method=None):
 headers={'User-Agent':'PasteGuardCloud/1.0','Accept':'application/json'}
 if token:headers['Authorization']='Bearer '+token
 body=None
 if data is not None:body=json.dumps(data).encode();headers['Content-Type']='application/json'
 req=urllib.request.Request(url,data=body,headers=headers,method=method)
 try:
  with urllib.request.urlopen(req,timeout=45) as r:return json.load(r)
 except urllib.error.HTTPError as e:
  # Do not print API URLs, bodies or tokens; permissions errors must stay explicit.
  raise RuntimeError('Remote API returned HTTP '+str(e.code)) from None
def ig(path,params=None,post=False):
 host=os.getenv('IG_API_HOST','https://graph.instagram.com')
 if host not in ('https://graph.instagram.com','https://graph.facebook.com'):raise SetupRequired('IG_API_HOST must be a supported Meta host')
 version=os.getenv('IG_API_VERSION','')
 if not version.startswith('v') or not version[1:].replace('.','').isdigit():raise SetupRequired('Set IG_API_VERSION to the version enabled in your Meta app')
 url=host+'/'+version+'/'+path
 return request(url,os.environ['IG_ACCESS_TOKEN'],params if post else None,'POST' if post else None) if post else request(url+('?'+urllib.parse.urlencode(params) if params else ''),os.environ['IG_ACCESS_TOKEN'])
def number(item):
 values=item.get('values',[])
 value=values[-1].get('value') if values else item.get('total_value',{}).get('value')
 return value if isinstance(value,(int,float)) else None
def media_metrics(media_id):
 result={};unavailable=[]
 for metric in ('views','reach','saved','shares','total_interactions','ig_reels_avg_watch_time','ig_reels_video_view_total_time'):
  try:
   response=ig(media_id+'/insights',{'metric':metric})
   if response.get('data'):result[metric]=number(response['data'][0])
  except RuntimeError:unavailable.append(metric)
 return result,unavailable
def assessment():
 data={'instagram_connected':False,'website_analytics_connected':False,'decision':'explore_no_winner','retention_available':False,'sample_sufficient':False}
 token=os.getenv('IG_ACCESS_TOKEN'); uid=os.getenv('IG_USER_ID')
 if token and uid:
  identity=ig(uid,{'fields':'id,username'})
  if identity.get('username')!=USERNAME:raise SetupRequired('Instagram token belongs to the wrong account; publishing blocked')
  data['instagram_connected']=True
  media=ig(uid+'/media',{'fields':'id,caption,timestamp,media_type,permalink','limit':30}).get('data',[])
  recent=[]
  for item in media[:20]:
   if item.get('media_type')!='VIDEO':continue
   metrics,missing=media_metrics(item['id'])
   age=(dt.datetime.now(dt.timezone.utc)-dt.datetime.fromisoformat(item['timestamp'].replace('Z','+00:00'))).total_seconds()/3600
   recent.append({'media':item,'metrics':metrics,'missing':missing,'age_hours':age})
  mature=[r for r in recent if r['age_hours']>=24 and (r['metrics'].get('views') or 0)>=300]
  data['retention_available']=any(r['metrics'].get('ig_reels_avg_watch_time') is not None for r in mature)
  data['sample_sufficient']=len(mature)>=3
  # Compare only this bot's equally long demos. Three mature observations per
  # hook is a conservative exploration gate, not a scientific significance test.
  groups={}
  for item in mature:
   caption=item['media'].get('caption',''); watch=item['metrics'].get('ig_reels_avg_watch_time')
   hook=next((h for h in HOOKS if caption.startswith(h+'. Check before sharing.')),None)
   if hook and watch is not None:groups.setdefault(hook,[]).append(watch)
  eligible={h:sum(values)/len(values) for h,values in groups.items() if len(values)>=3}
  if len(eligible)>=2:
   data['decision']='repeat_observed_watch_time_leader'
   data['suggested_hook']=max(eligible,key=eligible.get)
  data['_recent']=recent
 cf_token=os.getenv('CF_ANALYTICS_TOKEN'); account=os.getenv('CF_ACCOUNT_ID'); site=os.getenv('CF_SITE_TAG')
 if cf_token and account and site:
  now=dt.datetime.now(dt.timezone.utc); start=now-dt.timedelta(days=7)
  query='query($account: String!, $start: Time!, $end: Time!, $site: String!){viewer{accounts(filter:{accountTag:$account}){rumPageloadEventsAdaptiveGroups(limit:100,filter:{datetime_geq:$start,datetime_leq:$end,siteTag:$site}){count dimensions{requestPath refererHost} sum{visits}}}}}'
  response=request('https://api.cloudflare.com/client/v4/graphql',cf_token,{'query':query,'variables':{'account':account,'start':start.isoformat(),'end':now.isoformat(),'site':site}})
  if response.get('errors'):data['website_analytics_status']='query_failed_check_permissions_or_schema'
  else:data['website_analytics_connected']=True; data['_website']=response.get('data')
 return data
def public_assessment(data):return {k:v for k,v in data.items() if not k.startswith('_')}
def plan(data,date):
 index=date.toordinal(); example=EXAMPLES[index%len(EXAMPLES)]; hook=HOOKS[(index//len(EXAMPLES))%len(HOOKS)]
 if data.get('suggested_hook') in HOOKS and index%3!=0:hook=data['suggested_hook']
 caption=f"{hook}. Check before sharing.\n\nRecorded website demo with fake data: PasteGuard hides a detected sensitive pattern and keeps the surrounding text. Edited before/after comparison.\n\nTry the free demo — link in bio.\npasteguard.pages.dev\n\nCan miss secrets. Review before sharing.\n#DeveloperTools #DataPrivacy #AITools"
 return {'date':date.isoformat(),'example':example,'hook':hook,'caption':caption,'decision':data['decision']}
def github(path,data=None,method=None):return request('https://api.github.com/repos/'+os.environ['GITHUB_REPOSITORY']+'/'+path,os.environ['GITHUB_TOKEN'],data,method)
def load_ledger():
 try:
  item=github('contents/automation/public-state.json?ref=main')
  return json.loads(base64.b64decode(item['content'])),item['sha']
 except RuntimeError as e:
  if '404' in str(e):return {'days':{}},None
  raise
def save_ledger(state,sha):
 body={'message':'Record daily publishing state [skip ci]','branch':'main','content':base64.b64encode(json.dumps(state,indent=2).encode()).decode()}
 if sha:body['sha']=sha
 result=github('contents/automation/public-state.json',body,'PUT')
 return result['content']['sha']
def publish(plan_data,assessment_data):
 if not assessment_data.get('instagram_connected'):raise SetupRequired('Instagram publishing/insights connection is missing')
 if os.getenv('IG_PUBLISH_ENABLED')!='true':raise SetupRequired('Publishing is not enabled; authorize Meta and set IG_PUBLISH_ENABLED=true')
 if os.getenv('GITHUB_REF_NAME')!='main':raise SetupRequired('Publishing is restricted to the default main branch')
 uid=os.environ['IG_USER_ID']; day=plan_data['date'];state,sha=load_ledger();entry=state['days'].get(day,{})
 # The API account and durable ledger both guard against manual posts and retries.
 if entry.get('phase') in ('published','observed_manual_post'):return 'already_handled_no_duplicate'
 if entry.get('phase')=='publishing':
  if entry.get('container_id') and ig(entry['container_id'],{'fields':'status_code'}).get('status_code')=='PUBLISHED':
   entry['phase']='published';save_ledger(state,sha);return 'published_confirmed_by_container'
  raise SetupRequired('Previous publish result is unconfirmed. Inspect the account/container; automatic retry is blocked to prevent duplicates')
 for item in assessment_data.get('_recent',[]):
  stamp=dt.datetime.fromisoformat(item['media']['timestamp'].replace('Z','+00:00')).astimezone(TZ).date().isoformat()
  if stamp==day:
   state['days'][day]={'phase':'observed_manual_post','media_id':item['media']['id']};save_ledger(state,sha);return 'already_posted_today'
 caption=entry.get('caption',plan_data['caption'])
 if not entry:
  entry={'phase':'prepared','caption':caption,'example':plan_data['example']['name'],'hook':plan_data['hook']};state['days'][day]=entry;sha=save_ledger(state,sha)
 # Hosted release contains only intended-public fake-data video, never insight reports or secrets.
 tag='pasteguard-demo-'+day
 try:release=github('releases/tags/'+tag)
 except RuntimeError as e:
  if '404' not in str(e):raise
  release=github('releases',{'tag_name':tag,'target_commitish':'main','name':'PasteGuard demo '+day,'body':'Recorded fake-data demo prepared by the authorized daily publisher.','draft':False,'prerelease':True},'POST')
 asset=next((a for a in release.get('assets',[]) if a['name']=='video.mp4'),None)
 if not asset:
  url=release['upload_url'].split('{')[0]+'?name=video.mp4'; req=urllib.request.Request(url,data=(ROOT/'video.mp4').read_bytes(),method='POST',headers={'Authorization':'Bearer '+os.environ['GITHUB_TOKEN'],'Content-Type':'video/mp4','Accept':'application/vnd.github+json'})
  with urllib.request.urlopen(req,timeout=90) as r:asset=json.load(r)
 if not entry.get('container_id'):
  container=ig(uid+'/media',{'media_type':'REELS','video_url':asset['browser_download_url'],'caption':caption,'share_to_feed':True},post=True)
  entry.update(phase='processing',container_id=container['id']);sha=save_ledger(state,sha)
 for _ in range(36):
  status=ig(entry['container_id'],{'fields':'status_code'})['status_code']
  if status=='PUBLISHED':entry['phase']='published';save_ledger(state,sha);return 'published_confirmed_by_container'
  if status=='FINISHED':break
  if status in ('ERROR','EXPIRED'):raise RuntimeError('Meta rejected or expired the media container; no automatic replacement posted')
  time.sleep(10)
 else:raise RuntimeError('Container still processing; retry must reuse the saved container')
 # Persist intent before the consequential request. An ambiguous result fails closed on retry.
 entry['phase']='publishing';sha=save_ledger(state,sha)
 result=ig(uid+'/media_publish',{'creation_id':entry['container_id']},post=True)
 entry.update(phase='published',media_id=result['id']);save_ledger(state,sha)
 try:
  media=ig(result['id'],{'fields':'id,permalink'});entry['permalink']=media.get('permalink');save_ledger(state,load_ledger()[1])
 except RuntimeError:pass  # Publication ID is already saved; URL lookup must not trigger a repost.
 return 'published'
def main():
 parser=argparse.ArgumentParser();parser.add_argument('task',choices=['prepare','assess','publish','auto','verify']);parser.add_argument('--date');args=parser.parse_args()
 ROOT.mkdir(exist_ok=True)
 if args.task=='verify':
  if not (ROOT/'verification.json').exists():raise RuntimeError('Video has not been rendered')
  print('Cloud rendering and full video decode passed. This does not prove publishing is connected.');return
 now=dt.datetime.now(TZ); date=dt.date.fromisoformat(args.date) if args.date else now.date();data=assessment()
 public=public_assessment(data);(ROOT/'assessment-status.json').write_text(json.dumps(public,indent=2))
 if args.task in ('prepare','auto'):
  (ROOT/'plan.json').write_text(json.dumps(plan(data,date),indent=2))
 if args.task=='publish':
  prepared=json.loads((ROOT/'plan.json').read_text())
  if prepared['date']!=now.date().isoformat():raise SetupRequired('Prepared video date is stale; refusing a mismatched daily post')
  if not (ROOT/'verification.json').exists():raise SetupRequired('Rendered video verification is missing')
  print(publish(prepared,data))
 elif args.task=='auto':
  if now.hour!=23:print('Assessment completed; no publishing outside the daily slot.')
  else:raise SetupRequired('Use the workflow publishing phase after capture/render; do not publish an unrendered plan')
 else:print(json.dumps(public))
if __name__=='__main__':
 try:main()
 except (SetupRequired,RuntimeError) as e:print('ACTION REQUIRED: '+str(e));raise SystemExit(2)
