const TIMEZONE = 'America/Chicago';
const USERNAME = 'pasteguard.local';

export function centralTime(date) {
  const parts = new Intl.DateTimeFormat('en-CA', {
    timeZone: TIMEZONE, year: 'numeric', month: '2-digit', day: '2-digit',
    hour: '2-digit', minute: '2-digit', hourCycle: 'h23',
  }).formatToParts(date);
  const values = Object.fromEntries(parts.map(part => [part.type, part.value]));
  return { day: `${values.year}-${values.month}-${values.day}`,
    hour: Number(values.hour), minute: Number(values.minute) };
}

export function publishTime(now) {
  const local = centralTime(now);
  // Offset changes occur in the morning, before this evening preparation window.
  return now.getTime() + ((23 - local.hour) * 60 - local.minute) * 60000
    - now.getUTCSeconds() * 1000 - now.getUTCMilliseconds();
}

export default {
  async scheduled(controller, env, context) {
    const publisher = env.PUBLISHER.get(env.PUBLISHER.idFromName('pasteguard'));
    context.waitUntil(publisher.fetch('https://publisher.internal/tick'));
  },
  async fetch(request, env) {
    const path = new URL(request.url).pathname;
    if (request.method !== 'GET' || !['/status', '/health'].includes(path)) {
      return new Response('Not found', { status: 404 });
    }
    const publisher = env.PUBLISHER.get(env.PUBLISHER.idFromName('pasteguard'));
    return publisher.fetch(`https://publisher.internal${path}`);
  },
};

export class NightlyPublisher {
  constructor(context, env) {
    this.context = context;
    this.env = env;
    this.pending = Promise.resolve();
  }

  async fetch(request) {
    if (new URL(request.url).pathname === '/health') {
      try {
        await this.media();
        const response = await fetch('https://github.com/quietorbit-labs/pasteguard-preview/releases/download/pasteguard-silent-library-v1/library.json');
        if (!response.ok) throw new Error('Video library unavailable');
        const library = await response.json();
        if (library.videos?.length !== 6) throw new Error('Video library incomplete');
        return Response.json({ connected: true, username: USERNAME, videos: 6, timezone: TIMEZONE, publish_time: '23:00' });
      } catch (error) {
        return Response.json({ connected: false, error: error.message }, { status: 503 });
      }
    }
    if (new URL(request.url).pathname === '/status') {
      const records = await this.context.storage.list({ prefix: 'day:', reverse: true, limit: 8 });
      return Response.json({ days: Object.fromEntries(records) });
    }
    // Serialize cron and alarm executions within this Durable Object.
    const work = this.pending.catch(() => {}).then(() => this.run());
    this.pending = work;
    await work;
    return new Response('Checked');
  }

  async alarm() {
    const work = this.pending.catch(() => {}).then(() => this.run());
    this.pending = work;
    await work;
  }

  async api(path, parameters = {}, post = false) {
    const url = new URL(`https://graph.facebook.com/${this.env.IG_API_VERSION}/${path}`);
    const options = { headers: { Authorization: `Bearer ${this.env.IG_ACCESS_TOKEN}` } };
    if (post) {
      options.method = 'POST';
      options.headers['Content-Type'] = 'application/json';
      options.body = JSON.stringify(parameters);
    } else {
      url.search = new URLSearchParams(parameters).toString();
    }
    const response = await fetch(url, options);
    const body = await response.json();
    if (!response.ok) {
      const code = Number.isInteger(body.error?.code) ? body.error.code : 'unknown';
      throw new Error(`Instagram HTTP ${response.status}, code ${code}`);
    }
    return body;
  }

  async media() {
    const identity = await this.api(this.env.IG_USER_ID, { fields: 'id,username' });
    if (identity.username !== USERNAME) throw new Error('Wrong Instagram identity');
    const response = await this.api(`${this.env.IG_USER_ID}/media`, {
      fields: 'id,timestamp,caption,permalink', limit: '50',
    });
    if (!Array.isArray(response.data)) throw new Error('Instagram media list unavailable');
    return response.data;
  }

  async run(now = new Date()) {
    const { day, hour, minute } = centralTime(now);
    if (hour < 22 || (hour === 22 && minute < 30)) return;
    const key = `day:${day}`;
    let record = await this.context.storage.get(key);
    if (['published', 'observed_post', 'blocked'].includes(record?.phase)) return;
    const save = async () => {
      await this.context.storage.put(key, record);
    };
    const media = await this.media();
    const posted = media.find(item => centralTime(new Date(item.timestamp)).day === day);
    if (posted) {
      record = { phase: record?.phase === 'publishing' ? 'published' : 'observed_post',
        media_id: posted.id, permalink: posted.permalink, published_at: posted.timestamp };
      await save();
      return;
    }
    if (record?.phase === 'publishing') {
      const container = await this.api(record.container_id, { fields: 'status_code' });
      if (container.status_code === 'PUBLISHED') {
        record.phase = 'published';
        await save();
      }
      // A response lost after media_publish must never cause a second publish request.
      return;
    }
    if (!record) {
      const url = 'https://github.com/quietorbit-labs/pasteguard-preview/releases/download/pasteguard-silent-library-v1/library.json';
      const response = await fetch(url);
      if (!response.ok) throw new Error('Verified video library unavailable');
      const library = await response.json();
      if (!Array.isArray(library.videos) || library.videos.length !== 6) {
        throw new Error('Video library is incomplete');
      }
      const index = Math.floor(Date.parse(`${day}T12:00:00Z`) / 86400000) % library.videos.length;
      const video = library.videos[index];
      const mediaUrl = new URL(video.url);
      if (mediaUrl.origin !== 'https://github.com' || !mediaUrl.pathname.startsWith(
        '/quietorbit-labs/pasteguard-preview/releases/download/pasteguard-silent-library-v1/')) {
        throw new Error('Unexpected video source');
      }
      record = { phase: 'prepared', caption: video.caption, video_url: video.url };
      await save();
    }
    if (!record.container_id) {
      const container = await this.api(`${this.env.IG_USER_ID}/media`, {
        media_type: 'REELS', video_url: record.video_url,
        caption: record.caption, share_to_feed: true,
      }, true);
      record.container_id = container.id;
      record.phase = 'processing';
      await save();
    }
    const container = await this.api(record.container_id, { fields: 'status_code' });
    if (container.status_code === 'PUBLISHED') {
      record.phase = 'published';
      await save();
      return;
    }
    if (['ERROR', 'EXPIRED'].includes(container.status_code)) {
      record.phase = 'blocked';
      record.error = `Container ${container.status_code}`;
      await save();
      return;
    }
    if (container.status_code !== 'FINISHED') {
      await this.context.storage.setAlarm(now.getTime() + 60000);
      return;
    }
    if (hour < 23) {
      record.phase = 'ready';
      await save();
      await this.context.storage.setAlarm(publishTime(now));
      return;
    }
    // Recheck after preparation before making the single consequential request.
    const freshMedia = await this.media();
    if (freshMedia.some(item => centralTime(new Date(item.timestamp)).day === day)) {
      record.phase = 'observed_post';
      await save();
      return;
    }
    record.phase = 'publishing';
    await save();
    const result = await this.api(`${this.env.IG_USER_ID}/media_publish`, {
      creation_id: record.container_id,
    }, true);
    record.phase = 'published';
    record.media_id = result.id;
    record.published_at = now.toISOString();
    await save();
    const published = await this.api(result.id, { fields: 'id,permalink,timestamp' });
    record.permalink = published.permalink;
    record.published_at = published.timestamp;
    await save();
  }
}
