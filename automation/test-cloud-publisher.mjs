import assert from 'node:assert/strict';
import { NightlyPublisher, centralTime, publishTime } from './cloud-publisher.mjs';

const day = '2026-11-24';
const key = `day:${day}`;
const start = new Date('2026-11-25T05:00:00Z');
assert.equal(centralTime(start).hour, 23);
assert.equal(publishTime(new Date('2026-11-25T04:30:12Z')), start.getTime());
assert.equal(publishTime(new Date('2026-07-02T03:30:12Z')), Date.parse('2026-07-02T04:00:00Z'));

function fixture() {
  const records = new Map([[key, { phase: 'ready', container_id: 'container', caption: 'fake demo' }]]);
  let alarm;
  const storage = {
    get: async key => structuredClone(records.get(key)),
    put: async (key, value) => records.set(key, structuredClone(value)),
    setAlarm: async value => { alarm = value; },
  };
  const object = new NightlyPublisher({ storage }, { IG_USER_ID: 'account' });
  object.media = async () => [];
  let publications = 0;
  object.api = async (path, data, post) => {
    if (post) {
      publications++;
      return { id: 'published' };
    }
    if (path === 'container') return { status_code: 'FINISHED' };
    return { permalink: 'https://www.instagram.com/reel/example/', timestamp: start.toISOString() };
  };
  return { object, records, getAlarm: () => alarm, publications: () => publications };
}

const early = fixture();
await early.object.run(new Date('2026-11-25T04:30:00Z'));
assert.equal(early.publications(), 0);
assert.equal(early.getAlarm(), start.getTime());
await early.object.run(start);
await early.object.run(new Date(start.getTime() + 60000));
assert.equal(early.publications(), 1);
assert.equal(early.records.get(key).phase, 'published');

const ambiguous = fixture();
ambiguous.object.api = async (path, data, post) => {
  if (post) throw new Error('Response lost');
  return { status_code: 'FINISHED' };
};
await assert.rejects(ambiguous.object.run(start));
assert.equal(ambiguous.records.get(key).phase, 'publishing');
await ambiguous.object.run(new Date(start.getTime() + 60000));
assert.equal(ambiguous.records.get(key).phase, 'publishing');

const manual = fixture();
manual.object.media = async () => [{ id: 'manual', timestamp: start.toISOString() }];
await manual.object.run(start);
assert.equal(manual.publications(), 0);
assert.equal(manual.records.get(key).phase, 'observed_post');
console.log('Passed Central winter/summer timing, exact-time alarm, one publish, lost-response protection and manual-post duplicate check.');
