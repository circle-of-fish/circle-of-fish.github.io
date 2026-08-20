/**
 * Circle of the Fish — editing API.
 *
 * The site is static and cannot check a password: anything the browser could
 * verify, a reader could also read, and the repository write token would be
 * sitting in the page source next to it. So the check lives here instead. This
 * Worker holds the password hashes and the one GitHub token, and is the only
 * thing that can write to the repository.
 *
 *   POST /api/login              { username, password }  -> session token
 *   POST /api/password           { current, next }       -> ok            (auth)
 *   GET  /api/data                                       -> all four files (auth)
 *   PUT  /api/data/:file         { data, sha }           -> new sha       (auth)
 *   POST /api/photo/:key         { jpeg, w, h, sha? }    -> new sha       (auth)
 *
 * Bindings, all set outside the code:
 *   USERS           KV namespace — one record per editor
 *   GITHUB_TOKEN    secret — fine-grained PAT, Contents:write on the repo
 *   SESSION_SECRET  secret — HMAC key for session tokens
 */

const REPO = 'circle-of-fish/circle-of-fish.github.io';
const BRANCH = 'main';
const ORIGIN = 'https://circle-of-fish.github.io';
const FILES = ['publications', 'seminars', 'members', 'resources'];
const SESSION_HOURS = 12;
const PBKDF2_ROUNDS = 100000;   // Workers caps PBKDF2 at 100k; see the note in worker/README.md

// ── small helpers ──────────────────────────────────────────────────────────
const enc = new TextEncoder();
const dec = new TextDecoder();

function json(body, status = 200, extra = {}) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json; charset=utf-8', ...cors(), ...extra },
  });
}
function cors() {
  return {
    'Access-Control-Allow-Origin': ORIGIN,
    'Access-Control-Allow-Methods': 'GET, POST, PUT, OPTIONS',
    'Access-Control-Allow-Headers': 'Content-Type, Authorization',
    'Access-Control-Max-Age': '86400',
    'Vary': 'Origin',
  };
}
function b64url(bytes) {
  let bin = '';
  for (const b of bytes) bin += String.fromCharCode(b);
  return btoa(bin).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '');
}
function unb64url(s) {
  const bin = atob(s.replace(/-/g, '+').replace(/_/g, '/'));
  const out = new Uint8Array(bin.length);
  for (let i = 0; i < bin.length; i++) out[i] = bin.charCodeAt(i);
  return out;
}
function b64(bytes) {
  let bin = '';
  const CHUNK = 0x8000;
  for (let i = 0; i < bytes.length; i += CHUNK) {
    bin += String.fromCharCode.apply(null, bytes.subarray(i, i + CHUNK));
  }
  return btoa(bin);
}
function unb64(s) {
  const bin = atob(String(s).replace(/\s/g, ''));
  const out = new Uint8Array(bin.length);
  for (let i = 0; i < bin.length; i++) out[i] = bin.charCodeAt(i);
  return out;
}
/** Constant-time comparison, so a wrong guess leaks nothing through timing. */
function sameBytes(a, b) {
  if (a.length !== b.length) return false;
  let diff = 0;
  for (let i = 0; i < a.length; i++) diff |= a[i] ^ b[i];
  return diff === 0;
}

// ── passwords ──────────────────────────────────────────────────────────────
async function hashPassword(password, saltBytes) {
  const salt = saltBytes || crypto.getRandomValues(new Uint8Array(16));
  const key = await crypto.subtle.importKey('raw', enc.encode(password), 'PBKDF2', false, ['deriveBits']);
  const bits = await crypto.subtle.deriveBits(
    { name: 'PBKDF2', hash: 'SHA-256', salt, iterations: PBKDF2_ROUNDS }, key, 256);
  return `pbkdf2$${PBKDF2_ROUNDS}$${b64(salt)}$${b64(new Uint8Array(bits))}`;
}
async function checkPassword(password, stored) {
  const [scheme, rounds, saltB64, hashB64] = String(stored || '').split('$');
  if (scheme !== 'pbkdf2') return false;
  const salt = unb64(saltB64);
  const key = await crypto.subtle.importKey('raw', enc.encode(password), 'PBKDF2', false, ['deriveBits']);
  const bits = await crypto.subtle.deriveBits(
    { name: 'PBKDF2', hash: 'SHA-256', salt, iterations: +rounds }, key, 256);
  return sameBytes(new Uint8Array(bits), unb64(hashB64));
}

// ── sessions ───────────────────────────────────────────────────────────────
async function hmacKey(secret) {
  return crypto.subtle.importKey('raw', enc.encode(secret), { name: 'HMAC', hash: 'SHA-256' },
    false, ['sign', 'verify']);
}
async function issueSession(env, user) {
  const payload = { u: user.username, n: user.name, exp: Date.now() + SESSION_HOURS * 3600e3 };
  const body = b64url(enc.encode(JSON.stringify(payload)));
  const sig = await crypto.subtle.sign('HMAC', await hmacKey(env.SESSION_SECRET), enc.encode(body));
  return `${body}.${b64url(new Uint8Array(sig))}`;
}
async function readSession(env, token) {
  const [body, sig] = String(token || '').split('.');
  if (!body || !sig) return null;
  const ok = await crypto.subtle.verify('HMAC', await hmacKey(env.SESSION_SECRET),
    unb64url(sig), enc.encode(body));
  if (!ok) return null;
  const payload = JSON.parse(dec.decode(unb64url(body)));
  return payload.exp > Date.now() ? payload : null;
}

// ── GitHub ─────────────────────────────────────────────────────────────────
async function gh(env, path, init = {}) {
  const res = await fetch(`https://api.github.com/repos/${REPO}/${path}`, {
    method: init.method || 'GET',
    headers: {
      'Authorization': `Bearer ${env.GITHUB_TOKEN}`,
      'Accept': 'application/vnd.github+json',
      'X-GitHub-Api-Version': '2022-11-28',
      'User-Agent': 'circle-of-fish-editor',
      'Content-Type': 'application/json',
    },
    body: init.body ? JSON.stringify(init.body) : undefined,
  });
  const body = await res.json().catch(() => ({}));
  if (!res.ok) {
    const err = new Error(body.message || `GitHub ${res.status}`);
    err.status = res.status;
    throw err;
  }
  return body;
}
function commitAuthor(session) {
  // The token belongs to one account, so the editor's name goes in the commit
  // itself — otherwise every change would look like it came from one person.
  return { name: session.n || session.u, email: 'editor@circle-of-fish.github.io' };
}
async function readFile(env, path) {
  const res = await gh(env, `contents/${path}?ref=${BRANCH}`);
  return { text: dec.decode(unb64(res.content)), sha: res.sha };
}
async function writeFile(env, path, contentB64, message, session, sha) {
  const res = await gh(env, `contents/${path}`, {
    method: 'PUT',
    body: {
      message, content: contentB64, branch: BRANCH,
      author: commitAuthor(session), committer: commitAuthor(session),
      ...(sha ? { sha } : {}),
    },
  });
  return res.content.sha;
}

// ── routes ─────────────────────────────────────────────────────────────────
async function login(env, req) {
  const { username, password } = await req.json();
  const raw = await env.USERS.get(String(username || '').toLowerCase().trim());
  const user = raw ? JSON.parse(raw) : null;
  // Hash even when the account is unknown, so a bad username and a bad
  // password take the same time to answer.
  const ok = await checkPassword(String(password || ''),
    user ? user.hash : 'pbkdf2$100000$AAAAAAAAAAAAAAAAAAAAAA==$AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=');
  if (!user || !ok) return json({ error: '아이디나 비밀번호가 맞지 않습니다.' }, 401);
  return json({
    token: await issueSession(env, { username: user.username, name: user.name }),
    name: user.name,
    must_change: !!user.must_change,
  });
}

async function changePassword(env, req, session) {
  const { current, next } = await req.json();
  const raw = await env.USERS.get(session.u);
  const user = raw ? JSON.parse(raw) : null;
  if (!user || !(await checkPassword(String(current || ''), user.hash))) {
    return json({ error: '현재 비밀번호가 맞지 않습니다.' }, 401);
  }
  if (String(next || '').length < 12) {
    return json({ error: '새 비밀번호는 열두 자 이상이어야 합니다.' }, 400);
  }
  user.hash = await hashPassword(next);
  user.must_change = false;
  await env.USERS.put(session.u, JSON.stringify(user));
  return json({ ok: true });
}

async function getData(env) {
  const out = {};
  await Promise.all(FILES.map(async (name) => {
    const f = await readFile(env, `data/${name}.json`);
    out[name] = { data: JSON.parse(f.text), sha: f.sha };
  }));
  return json(out);
}

const LABELS = {
  publications: 'publications', seminars: 'seminars',
  members: 'members', resources: 'resources',
};
async function putData(env, req, session, name) {
  if (!FILES.includes(name)) return json({ error: 'unknown file' }, 404);
  const { data, sha } = await req.json();
  if (!data || typeof data !== 'object') return json({ error: 'bad payload' }, 400);
  const text = JSON.stringify(data, (k, v) => (k.charAt(0) === '_' ? undefined : v), 2) + '\n';
  const newSha = await writeFile(env, `data/${name}.json`, b64(enc.encode(text)),
    `Update the ${LABELS[name]} data\n\nEdited through /admin/ by ${session.n || session.u}.`,
    session, sha);
  return json({ sha: newSha });
}

async function putPhoto(env, req, session, key) {
  if (!/^[a-z0-9-]+$/.test(key)) return json({ error: 'bad key' }, 400);
  const { jpeg, w, h } = await req.json();
  if (!jpeg || !w || !h) return json({ error: 'bad payload' }, 400);

  // The browser has already resized and encoded the image; the Worker only
  // commits it and records the size so the page can reserve the right space.
  let sha;
  try {
    sha = (await readFile(env, `assets/photos/${key}.jpg`)).sha;
  } catch (e) {
    if (e.status !== 404) throw e;
  }
  await writeFile(env, `assets/photos/${key}.jpg`, jpeg,
    `Replace the photo for ${key}\n\nUploaded through /admin/ by ${session.n || session.u}.`,
    session, sha);

  // Recording the size commits members.json a second time, which invalidates
  // whatever sha the editor's browser is holding. Hand the new one back, or the
  // next save from that browser is refused as a conflict.
  const members = await readFile(env, 'data/members.json');
  const parsed = JSON.parse(members.text);
  const person = (parsed.people || []).find((p) => p.key === key);
  let membersSha = members.sha;
  if (person) {
    person.photo = { w, h };
    membersSha = await writeFile(env, 'data/members.json',
      b64(enc.encode(JSON.stringify(parsed, null, 2) + '\n')),
      `Record the new photo size for ${key}\n\nUploaded through /admin/ by ${session.n || session.u}.`,
      session, members.sha);
  }
  return json({ ok: true, w, h, members_sha: membersSha });
}

export default {
  async fetch(request, env) {
    if (request.method === 'OPTIONS') return new Response(null, { status: 204, headers: cors() });

    const url = new URL(request.url);
    const parts = url.pathname.replace(/^\/+|\/+$/g, '').split('/');   // api/<route>/<arg>
    if (parts[0] !== 'api') return json({ error: 'not found' }, 404);

    try {
      if (parts[1] === 'login' && request.method === 'POST') return await login(env, request);

      const session = await readSession(env, (request.headers.get('Authorization') || '').replace(/^Bearer\s+/i, ''));
      if (!session) return json({ error: '로그인이 만료되었습니다. 다시 들어와 주십시오.' }, 401);

      if (parts[1] === 'password' && request.method === 'POST') return await changePassword(env, request, session);
      if (parts[1] === 'data' && request.method === 'GET') return await getData(env);
      if (parts[1] === 'data' && request.method === 'PUT') return await putData(env, request, session, parts[2]);
      if (parts[1] === 'photo' && request.method === 'POST') return await putPhoto(env, request, session, parts[2]);
      return json({ error: 'not found' }, 404);
    } catch (err) {
      if (err.status === 409) {
        return json({ error: '저장소가 그 사이에 바뀌었습니다. 새로고침한 뒤 다시 편집해 주십시오.' }, 409);
      }
      return json({ error: err.message || 'server error' }, err.status === 401 ? 502 : 500);
    }
  },
};

export { hashPassword };
