/* Editing tool for the Circle of the Fish site.
 *
 * There is no server. This page reads data/*.json out of the repository through
 * the GitHub API, edits it in the browser, and commits it straight back; a
 * GitHub Action then rebuilds the pages. The editor's token never leaves this
 * browser except to github.com.
 *
 * The forms encode the site's own rules rather than exposing raw JSON: a
 * publication's author, title, and journal stay in their original language and
 * are shown as single locked-language fields, while summaries are edited in all
 * four languages at once.
 */
(function () {
  'use strict';

  var REPO = 'circle-of-fish/circle-of-fish.github.io';
  var BRANCH = 'main';
  var LANGS = ['en', 'ko', 'zh', 'ja'];
  var TOKEN_KEY = 'cof-admin-token';
  var FILES = ['publications', 'seminars', 'members'];

  var token = null;
  var store = {};            // file -> {data, sha, dirty}
  var current = 'publications';
  var selected = null;       // the record being edited
  var els = {};

  // ── tiny helpers ─────────────────────────────────────────────────────────
  function $(id) { return document.getElementById(id); }
  function el(tag, cls, text) {
    var n = document.createElement(tag);
    if (cls) n.className = cls;
    if (text != null) n.textContent = text;
    return n;
  }
  function toast(msg, kind, html) {
    var t = $('toast');
    t.className = 'toast' + (kind ? ' ' + kind : '');
    if (html) t.innerHTML = msg; else t.textContent = msg;
    t.hidden = false;
    clearTimeout(t._timer);
    t._timer = setTimeout(function () { t.hidden = true; }, kind === 'bad' ? 9000 : 6000);
  }
  function b64encode(str) {
    var bytes = new TextEncoder().encode(str), bin = '', CHUNK = 0x8000;
    for (var i = 0; i < bytes.length; i += CHUNK) {
      bin += String.fromCharCode.apply(null, bytes.subarray(i, i + CHUNK));
    }
    return btoa(bin);
  }
  function b64decode(b64) {
    var bin = atob(String(b64).replace(/\s/g, ''));
    var bytes = new Uint8Array(bin.length);
    for (var i = 0; i < bin.length; i++) bytes[i] = bin.charCodeAt(i);
    return new TextDecoder().decode(bytes);
  }
  function bundle(v) {                       // always hand the form a full bundle
    var out = {};
    LANGS.forEach(function (l) { out[l] = (v && typeof v === 'object') ? (v[l] || '') : (l === 'en' ? (v || '') : ''); });
    return out;
  }
  function tidyBundle(b) {                   // drop empty languages; "" everywhere -> undefined
    var out = {}, any = false;
    LANGS.forEach(function (l) { if (b[l] && b[l].trim()) { out[l] = b[l].trim(); any = true; } });
    return any ? out : null;
  }
  function yearNum(rec) {
    var y = String(rec.year || '');
    if (/forth/i.test(y)) return 9999;
    var m = y.match(/\d{4}/);
    return m ? +m[0] : 0;
  }

  // ── GitHub ───────────────────────────────────────────────────────────────
  function gh(path, options) {
    options = options || {};
    return fetch('https://api.github.com/repos/' + REPO + '/' + path, {
      method: options.method || 'GET',
      headers: {
        'Authorization': 'Bearer ' + token,
        'Accept': 'application/vnd.github+json',
        'X-GitHub-Api-Version': '2022-11-28'
      },
      body: options.body ? JSON.stringify(options.body) : undefined
    }).then(function (r) {
      return r.json().catch(function () { return {}; }).then(function (body) {
        if (!r.ok) {
          var e = new Error(body.message || ('HTTP ' + r.status));
          e.status = r.status;
          throw e;
        }
        return body;
      });
    });
  }
  function loadFile(name) {
    return gh('contents/data/' + name + '.json?ref=' + BRANCH).then(function (res) {
      store[name] = { data: JSON.parse(b64decode(res.content)), sha: res.sha, dirty: false };
    });
  }
  // Keys the editor hangs on a record for its own use — which group a
  // publication sits in, whether a seminar is newly added — must never reach
  // the committed file. Stripping them here rather than before validation makes
  // it impossible for a later pass to put them back.
  function omitEditingKeys(key, value) {
    return key.charAt(0) === '_' ? undefined : value;
  }
  function saveFile(name, message) {
    var s = store[name];
    return gh('contents/data/' + name + '.json', {
      method: 'PUT',
      body: {
        message: message,
        content: b64encode(JSON.stringify(s.data, omitEditingKeys, 2) + '\n'),
        sha: s.sha,
        branch: BRANCH
      }
    }).then(function (res) {
      s.sha = res.content.sha;
      s.dirty = false;
    });
  }

  // ── field specs ──────────────────────────────────────────────────────────
  var PUB_TYPES = [
    ['journal_article', '학술지 논문'], ['book', '단행본'], ['book_chapter', '단행본 장'],
    ['edited_volume', '편저'], ['dissertation', '박사학위논문'],
    ['policy_report', '정책보고서·논평'], ['review', '서평'],
    ['translation', '번역'], ['other', '그 밖의 글']
  ];
  var TYPE_LABELS = {
    book: { en: 'Book', ko: '단행본', zh: '专著', ja: '単著' },
    book_chapter: { en: 'Chapter', ko: '단행본 장', zh: '论文集章节', ja: '所収論考' },
    edited_volume: { en: 'Edited volume', ko: '편저', zh: '编著', ja: '編著' },
    dissertation: { en: 'PhD dissertation', ko: '박사학위논문', zh: '博士论文', ja: '博士論文' }
  };
  var LANG_OPTS = [['en', '영문'], ['ko', '국문'], ['ja', '일문'], ['zh', '중문']];

  var SPECS = {
    publications: [
      { k: '_group', label: '묶음', type: 'group' },
      { k: 'type', label: '유형', type: 'select', options: PUB_TYPES, half: true },
      { k: 'year', label: '연도', type: 'text', half: true, note: '숫자 네 자리, 또는 forthcoming' },
      { k: 'authors', label: '저자', type: 'text', locked: true },
      { k: 'title', label: '제목', type: 'textarea', locked: true, note: '&lt;em&gt; 같은 표시는 그대로 쓸 수 있습니다' },
      { k: 'venue', label: '게재지·출판사', type: 'text', locked: true },
      { k: 'volume_issue_pages', label: '권·호·쪽', type: 'text', half: true, note: '예: 31(1): 28–52' },
      { k: 'language', label: '원문 언어', type: 'select', options: LANG_OPTS, half: true },
      { k: 'doi', label: 'DOI', type: 'text', half: true, note: '10.1093/… 형태' },
      { k: 'url_publisher', label: '출판사 링크', type: 'text', half: true },
      { k: 'url_fulltext', label: '무료 전문 링크', type: 'text', note: '실제로 열어 전문이 보이는 주소만 넣으십시오. 초록만 보이면 비워 둡니다.' },
      { k: 'summary', label: '요약', type: 'i18n', rows: 3, note: '두 문장 안팎으로, 무엇을 논증하는지 쓰십시오. 주제만 적지 않습니다.' },
      { k: 'members', label: '복어회 저자', type: 'tags' }
    ],
    seminars: [
      { k: 'iso', label: '날짜', type: 'date', half: true },
      { k: 'kind', label: '형식', type: 'select', options: [], half: true },
      { k: 'date_display', label: '표시할 날짜', type: 'i18n', short: true, note: '날짜를 고르면 자동으로 채워집니다. 기간이면 직접 고치십시오.' },
      { k: 'title', label: '내용', type: 'i18n', rows: 3, note: '서지는 원어 그대로 두고, 저자명과 설명만 각 언어로 옮깁니다.' },
      { k: 'meta', label: '부기', type: 'i18n', rows: 2, note: '초고·장소·판본 같은 짧은 덧말. 없으면 비워 둡니다.' }
    ],
    members: [
      { k: 'key', label: '식별자', type: 'text', readonly: true, half: true, note: '사진 파일 이름과 같아야 합니다' },
      { k: 'role', label: '역할', type: 'i18n', short: true, note: '간사 등. 없으면 비워 둡니다.' },
      { k: 'name', label: '이름', type: 'i18n', short: true, note: '한국어판은 한글, 나머지는 로마자' },
      { k: 'name_alt', label: '이름 (보조 표기)', type: 'i18n', short: true },
      { k: 'affiliation', label: '소속', type: 'i18n', rows: 2 },
      { k: 'interests', label: '연구 관심', type: 'i18n', rows: 2, note: '가운뎃점(·)으로 나열' },
      { k: 'email', label: '이메일', type: 'text', note: '링크는 걸지 않고 주소만 보여 줍니다' },
      { k: 'links', label: '링크', type: 'links' }
    ]
  };

  // ── flatten / rebuild ────────────────────────────────────────────────────
  function groupsOf(file) {
    if (file !== 'publications') return [];
    var d = store.publications.data;
    return d.themes.map(function (t) { return { id: t.id, label: t.title.ko || t.title.en, other: false }; })
      .concat(d.other_groups.map(function (g) { return { id: g.id, label: (g.title.ko || g.title.en) + ' (기타)', other: true }; }));
  }
  function records(file) {
    var d = store[file].data;
    if (file === 'publications') {
      var out = [];
      d.themes.concat(d.other_groups).forEach(function (g) {
        g.entries.forEach(function (e) { e._group = g.id; out.push(e); });
      });
      return out;
    }
    return file === 'seminars' ? d.entries : d.people;
  }
  function rebuild(file) {
    var d = store[file].data;
    if (file === 'publications') {
      var all = records(file);
      d.themes.concat(d.other_groups).forEach(function (g) {
        g.entries = all.filter(function (e) { return e._group === g.id; })
          .sort(function (a, b) { return yearNum(b) - yearNum(a); });
      });
      var titles = {};
      all.forEach(function (e) { titles[e.title] = 1; });
      d.featured = (d.featured || []).filter(function (f) { return titles[f.title]; });
    } else if (file === 'seminars') {
      d.entries.sort(function (a, b) { return a.iso < b.iso ? 1 : a.iso > b.iso ? -1 : 0; });
      d.entries.forEach(function (e) { e.year = String(e.iso).slice(0, 4); });
    }
  }
  function blank(file) {
    if (file === 'publications') {
      var g = groupsOf('publications')[0];
      return {
        _group: g ? g.id : '', type: 'journal_article', year: String(new Date().getFullYear()),
        authors: '', title: '', venue: '', volume_issue_pages: '', language: 'en',
        doi: '', url_publisher: '', url_fulltext: '', summary: bundle(''), members: []
      };
    }
    if (file === 'seminars') {
      return { iso: '', year: '', kind: 'reading', date_display: bundle(''), title: bundle(''), _new: true };
    }
    return { key: '', name: bundle(''), affiliation: bundle(''), interests: bundle(''), email: '', links: [] };
  }

  // ── list ─────────────────────────────────────────────────────────────────
  function rowText(file, r) {
    if (file === 'publications') return { title: strip(r.title) || '(제목 없음)', meta: [r.year, r.authors].filter(Boolean).join(' · ') };
    if (file === 'seminars') return { title: strip(r.title && r.title.ko || r.title && r.title.en) || '(내용 없음)', meta: r.iso };
    var nm = r.name && typeof r.name === 'object' ? (r.name.ko || r.name.en) : r.name;
    return { title: nm || '(이름 없음)', meta: strip(r.affiliation && (r.affiliation.ko || r.affiliation.en) || '') };
  }
  function strip(s) { return String(s == null ? '' : s).replace(/<[^>]*>/g, '').replace(/&[a-z]+;/g, ' ').trim(); }

  function renderList() {
    var file = current, list = $('list');
    list.innerHTML = '';
    var q = $('search').value.trim().toLowerCase();
    var gf = $('group-filter').value;
    var rows = records(file).filter(function (r) {
      if (file === 'publications' && gf && r._group !== gf) return false;
      if (!q) return true;
      var t = rowText(file, r);
      return (t.title + ' ' + t.meta).toLowerCase().indexOf(q) !== -1;
    });
    if (file === 'publications') {
      var order = {};
      groupsOf('publications').forEach(function (g, i) { order[g.id] = i; });
      rows.sort(function (a, b) {
        var d = (order[a._group] || 0) - (order[b._group] || 0);
        return d !== 0 ? d : yearNum(b) - yearNum(a);
      });
    }

    var lastGroup = null;
    rows.forEach(function (r) {
      if (file === 'publications' && r._group !== lastGroup) {
        lastGroup = r._group;
        var g = groupsOf('publications').filter(function (x) { return x.id === lastGroup; })[0];
        list.appendChild(el('li', 'group-head', g ? g.label : lastGroup));
      }
      var t = rowText(file, r);
      var li = el('li', selected === r ? 'on' : '');
      li.appendChild(el('div', 'row-title', t.title.slice(0, 110)));
      li.appendChild(el('div', 'row-meta', t.meta));
      li.addEventListener('click', function () { selected = r; renderList(); renderForm(); });
      list.appendChild(li);
    });
    $('count').textContent = rows.length + ' / ' + records(file).length + '건';
  }

  // ── form ─────────────────────────────────────────────────────────────────
  function labelFor(spec) {
    var lab = el('div', 'label');
    lab.textContent = spec.label;
    if (spec.locked) {
      var tag = el('span', 'locked', '원어 고정');
      lab.appendChild(tag);
    }
    return lab;
  }

  function renderForm() {
    var pane = $('pane');
    pane.innerHTML = '';
    if (!selected) {
      pane.appendChild(el('p', 'empty', '왼쪽에서 항목을 고르거나 새 항목을 누르십시오.'));
      return;
    }
    var file = current, rec = selected;
    var t = rowText(file, rec);
    pane.appendChild(el('h2', null, t.title.slice(0, 90) || '새 항목'));

    if (file === 'seminars') {
      SPECS.seminars[1].options = Object.keys(store.seminars.data.kinds).map(function (k) {
        return [k, store.seminars.data.kinds[k].ko || k];
      });
    }

    var grid = el('div', 'grid2'), plain = el('div');
    SPECS[file].forEach(function (spec) {
      var wrap = el('div', 'field');
      wrap.appendChild(labelFor(spec));
      wrap.appendChild(control(spec, rec));
      if (spec.note) { var n = el('div', 'note'); n.innerHTML = spec.note; wrap.appendChild(n); }
      (spec.half ? grid : plain).appendChild(wrap);
    });
    pane.appendChild(grid);
    pane.appendChild(plain);

    var actions = el('div', 'pane-actions');
    var del = el('button', 'btn danger', '삭제');
    del.addEventListener('click', function () {
      if (!confirm('이 항목을 목록에서 지웁니다. 계속할까요?')) return;
      var arr = file === 'publications'
        ? null
        : (file === 'seminars' ? store.seminars.data.entries : store.members.data.people);
      if (file === 'publications') {
        store.publications.data.themes.concat(store.publications.data.other_groups).forEach(function (g) {
          var i = g.entries.indexOf(rec);
          if (i >= 0) g.entries.splice(i, 1);
        });
      } else {
        var i = arr.indexOf(rec);
        if (i >= 0) arr.splice(i, 1);
      }
      selected = null;
      markDirty();
      renderList(); renderForm();
    });
    actions.appendChild(del);
    pane.appendChild(actions);
  }

  function control(spec, rec) {
    var v = rec[spec.k];

    if (spec.type === 'i18n') {
      var box = el('div', 'i18n');
      var b = bundle(v);
      LANGS.forEach(function (l) {
        box.appendChild(el('div', 'tag', l.toUpperCase()));
        var input = spec.short ? el('input') : el('textarea');
        if (!spec.short) input.rows = spec.rows || 3;
        input.value = b[l];
        input.addEventListener('input', function () {
          if (!rec[spec.k] || typeof rec[spec.k] !== 'object') rec[spec.k] = bundle(rec[spec.k]);
          rec[spec.k][l] = input.value;
          markDirty();
          if (l === 'ko' || l === 'en') renderListSoon();
        });
        box.appendChild(input);
      });
      return box;
    }

    if (spec.type === 'tags') {
      var tb = el('div', 'tagbox');
      (store.members.data.people || []).forEach(function (m) {
        var key = m.key.replace(/-/g, '_');
        var lab = el('label');
        var cb = el('input');
        cb.type = 'checkbox';
        cb.checked = (rec.members || []).indexOf(key) !== -1;
        cb.addEventListener('change', function () {
          rec.members = rec.members || [];
          var i = rec.members.indexOf(key);
          if (cb.checked && i === -1) rec.members.push(key);
          if (!cb.checked && i >= 0) rec.members.splice(i, 1);
          markDirty();
        });
        lab.appendChild(cb);
        lab.appendChild(document.createTextNode(
          m.name && typeof m.name === 'object' ? (m.name.ko || m.name.en) : m.name));
        tb.appendChild(lab);
      });
      return tb;
    }

    if (spec.type === 'links') {
      var wrap = el('div');
      function draw() {
        wrap.innerHTML = '';
        (rec.links || []).forEach(function (link, idx) {
          var row = el('div', 'linkrow');
          var a = el('input'); a.value = link.label || ''; a.placeholder = '이름';
          var b2 = el('input'); b2.value = link.url || ''; b2.placeholder = 'https://…';
          a.addEventListener('input', function () { link.label = a.value; markDirty(); });
          b2.addEventListener('input', function () { link.url = b2.value; markDirty(); });
          var x = el('button', 'btn danger', '×');
          x.addEventListener('click', function () { rec.links.splice(idx, 1); markDirty(); draw(); });
          row.appendChild(a); row.appendChild(b2); row.appendChild(x);
          wrap.appendChild(row);
        });
        var add = el('button', 'btn', '+ 링크');
        add.addEventListener('click', function () {
          rec.links = rec.links || [];
          rec.links.push({ label: '', url: '' });
          markDirty(); draw();
        });
        wrap.appendChild(add);
      }
      draw();
      return wrap;
    }

    if (spec.type === 'group' || spec.type === 'select') {
      var sel = el('select');
      var opts = spec.type === 'group'
        ? groupsOf('publications').map(function (g) { return [g.id, g.label]; })
        : spec.options;
      opts.forEach(function (o) {
        var op = el('option', null, o[1]);
        op.value = o[0];
        sel.appendChild(op);
      });
      sel.value = v || opts[0][0];
      rec[spec.k] = sel.value;
      sel.addEventListener('change', function () {
        rec[spec.k] = sel.value;
        if (spec.k === 'type') {
          if (TYPE_LABELS[sel.value]) rec.type_label = TYPE_LABELS[sel.value];
          else delete rec.type_label;
        }
        if (spec.k === '_group') moveGroup(rec, sel.value);
        markDirty(); renderListSoon();
      });
      return sel;
    }

    if (spec.type === 'date') {
      var d = el('input'); d.type = 'date'; d.value = v || '';
      d.addEventListener('change', function () {
        rec.iso = d.value;
        rec.year = d.value.slice(0, 4);
        var parts = d.value.split('-');
        if (parts.length === 3) {
          var MONTHS = ['January', 'February', 'March', 'April', 'May', 'June', 'July',
            'August', 'September', 'October', 'November', 'December'];
          var enForm = (+parts[2]) + ' ' + MONTHS[+parts[1] - 1] + ' ' + parts[0];
          var cjk = parts[0] + '.' + parts[1] + '.' + parts[2];
          rec.date_display = { en: enForm, ko: cjk, zh: cjk, ja: cjk };
        }
        markDirty(); renderForm(); renderList();
      });
      return d;
    }

    var input = spec.type === 'textarea' ? el('textarea') : el('input');
    if (spec.type === 'textarea') input.rows = 2;
    input.value = v == null ? '' : v;
    if (spec.readonly) input.readOnly = true;
    input.addEventListener('input', function () { rec[spec.k] = input.value; markDirty(); renderListSoon(); });
    return input;
  }

  function moveGroup(rec, groupId) {
    var d = store.publications.data;
    d.themes.concat(d.other_groups).forEach(function (g) {
      var i = g.entries.indexOf(rec);
      if (i >= 0) g.entries.splice(i, 1);
    });
    var target = d.themes.concat(d.other_groups).filter(function (g) { return g.id === groupId; })[0];
    if (target) target.entries.push(rec);
    rec._group = groupId;
  }

  var listTimer = null;
  function renderListSoon() {
    clearTimeout(listTimer);
    listTimer = setTimeout(renderList, 350);
  }
  function markDirty() {
    store[current].dirty = true;
    $('dirty').hidden = false;
    $('save').disabled = false;
  }

  // ── save ─────────────────────────────────────────────────────────────────
  function cleanForCommit() {
    FILES.forEach(function (f) { rebuild(f); });
    // editing-only keys are dropped at serialization; here we only tidy content
    records('publications').forEach(function (e) {
      var t = tidyBundle(bundle(e.summary));
      if (t) e.summary = t; else delete e.summary;
    });
    store.seminars.data.entries.forEach(function (e) {
      ['title', 'meta', 'date_display'].forEach(function (k) {
        if (e[k]) { var t = tidyBundle(bundle(e[k])); if (t) e[k] = t; else delete e[k]; }
      });
    });
    store.members.data.people.forEach(function (m) {
      ['name_alt', 'interests', 'role'].forEach(function (k) {
        if (m[k]) { var t = tidyBundle(bundle(m[k])); if (t) m[k] = t; else delete m[k]; }
      });
      if (m.links && !m.links.length) delete m.links;
      if (!m.email) delete m.email;
    });
  }
  function problems() {
    var out = [];
    function bad(file, rec, msg) { out.push({ file: file, rec: rec, msg: msg }); }
    records('publications').forEach(function (e) {
      var name = strip(e.title).slice(0, 40) || '(제목 없음)';
      if (!String(e.title || '').trim()) bad('publications', e, '제목이 비어 있습니다.');
      else if (!String(e.authors || '').trim()) bad('publications', e, '저자가 비어 있습니다 — ' + name);
      ['url_fulltext', 'url_publisher'].forEach(function (k) {
        if (e[k] && !/^https?:\/\//.test(e[k])) bad('publications', e, '주소가 http로 시작하지 않습니다 — ' + name);
      });
    });
    store.seminars.data.entries.forEach(function (e) {
      if (!/^\d{4}-\d{2}-\d{2}$/.test(e.iso || '')) bad('seminars', e, '날짜를 정해 주십시오.');
    });
    store.members.data.people.forEach(function (m) {
      if (!/^[a-z0-9-]+$/.test(m.key || '')) {
        bad('members', m, '식별자는 영소문자와 하이픈만 씁니다 — ' + (m.key || '(빈칸)'));
      }
    });
    return out;
  }

  function save() {
    cleanForCommit();
    var bad = problems();
    if (bad.length) {
      var first = bad[0];
      if (current !== first.file) switchTo(first.file);
      selected = first.rec;
      renderList(); renderForm();
      if ($('pane').scrollIntoView) $('pane').scrollIntoView({ block: 'nearest' });
      toast(first.msg + (bad.length > 1 ? ' (그 밖에 ' + (bad.length - 1) + '건)' : ''), 'bad');
      return;
    }

    var pending = FILES.filter(function (f) { return store[f].dirty; });
    if (!pending.length) { toast('바뀐 것이 없습니다.'); return; }

    $('save').disabled = true;
    toast('저장하는 중…');
    var labels = { publications: '출판 목록', seminars: '세미나', members: '구성원' };
    var chain = Promise.resolve();
    pending.forEach(function (f) {
      chain = chain.then(function () {
        return saveFile(f, 'Update the ' + f + ' data from the editor\n\nEdited through /admin/.');
      });
    });
    chain.then(function () {
      $('dirty').hidden = true;
      toast('저장했습니다 — ' + pending.map(function (f) { return labels[f]; }).join(', ') +
        '. 사이트 반영까지 1–2분 걸립니다. <a href="https://github.com/' + REPO +
        '/actions" target="_blank" rel="noopener">진행 상황</a>', 'good', true);
    }).catch(function (e) {
      $('save').disabled = false;
      if (e.status === 409) {
        toast('저장소가 그 사이에 바뀌었습니다. 새로고침해서 다시 편집해 주십시오.', 'bad');
      } else {
        toast('저장하지 못했습니다: ' + e.message, 'bad');
      }
    });
  }

  // ── boot ─────────────────────────────────────────────────────────────────
  function enterApp() {
    $('gate').hidden = true;
    $('app').hidden = false;
    $('tabs').hidden = false;
    $('signout').hidden = false;
    switchTo('publications');
  }
  function switchTo(file) {
    current = file;
    selected = null;
    Array.prototype.forEach.call($('tabs').children, function (b) {
      b.className = b.dataset.file === file ? 'on' : '';
    });
    var gf = $('group-filter');
    gf.innerHTML = '';
    if (file === 'publications') {
      gf.hidden = false;
      var all = el('option', null, '모든 묶음'); all.value = '';
      gf.appendChild(all);
      groupsOf('publications').forEach(function (g) {
        var o = el('option', null, g.label); o.value = g.id; gf.appendChild(o);
      });
    } else {
      gf.hidden = true;
    }
    $('search').value = '';
    renderList();
    renderForm();
  }

  function signIn(value, remember) {
    token = value.trim();
    return Promise.all(FILES.map(loadFile)).then(function () {
      if (remember) localStorage.setItem(TOKEN_KEY, token);
      else sessionStorage.setItem(TOKEN_KEY, token);
      enterApp();
    });
  }

  document.addEventListener('DOMContentLoaded', function () {
    els.gateErr = $('gate-err');

    $('gate-form').addEventListener('submit', function (e) {
      e.preventDefault();
      els.gateErr.hidden = true;
      signIn($('token').value, $('remember').checked).catch(function (err) {
        localStorage.removeItem(TOKEN_KEY);
        sessionStorage.removeItem(TOKEN_KEY);
        els.gateErr.textContent = err.status === 401 || err.status === 404
          ? '토큰이 맞지 않거나 이 저장소에 쓸 권한이 없습니다. Contents 권한이 Read and write인지 확인해 주십시오.'
          : ('불러오지 못했습니다: ' + err.message);
        els.gateErr.hidden = false;
      });
    });

    $('signout').addEventListener('click', function () {
      localStorage.removeItem(TOKEN_KEY);
      sessionStorage.removeItem(TOKEN_KEY);
      location.reload();
    });

    Array.prototype.forEach.call($('tabs').children, function (b) {
      b.addEventListener('click', function () { switchTo(b.dataset.file); });
    });
    $('search').addEventListener('input', renderListSoon);
    $('group-filter').addEventListener('change', renderList);
    $('save').addEventListener('click', save);
    $('add').addEventListener('click', function () {
      var rec = blank(current);
      if (current === 'publications') {
        var d = store.publications.data;
        var g = d.themes.concat(d.other_groups).filter(function (x) { return x.id === rec._group; })[0];
        if (g) g.entries.unshift(rec);
      } else if (current === 'seminars') {
        store.seminars.data.entries.unshift(rec);
      } else {
        store.members.data.people.push(rec);
      }
      selected = rec;
      markDirty();
      renderList(); renderForm();
    });

    window.addEventListener('beforeunload', function (e) {
      if (FILES.some(function (f) { return store[f] && store[f].dirty; })) {
        e.preventDefault();
        e.returnValue = '';
      }
    });

    var saved = sessionStorage.getItem(TOKEN_KEY) || localStorage.getItem(TOKEN_KEY);
    if (saved) {
      signIn(saved, !!localStorage.getItem(TOKEN_KEY)).catch(function () {
        localStorage.removeItem(TOKEN_KEY);
        sessionStorage.removeItem(TOKEN_KEY);
      });
    }
  });
})();
