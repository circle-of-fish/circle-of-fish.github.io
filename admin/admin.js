/* Editing tool for the Circle of the Fish site.
 *
 * Members sign in with a username and password. The check cannot happen here —
 * anything this page could verify, a reader could also read — so it happens in
 * a small Worker that holds the password hashes and the one repository token.
 * This page only ever sees a short-lived session token.
 *
 * The forms encode the site's own conventions rather than exposing raw JSON:
 * an author, a title, and a journal name stay in their original language and
 * appear as single locked fields, while summaries are edited in all four
 * languages at once.
 */
(function () {
  'use strict';

  var API = 'https://cof-editor.circle-of-fish.workers.dev';
  var LANGS = ['en', 'ko', 'zh', 'ja'];
  var TOKEN_KEY = 'cof-session';
  var FILES = ['publications', 'seminars', 'members', 'resources'];
  var PHOTO_SHORT_SIDE = 320;

  var session = null;        // {token, name}
  var store = {};            // file -> {data, sha, dirty}
  var current = 'publications';
  var selected = null;

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
  function bundle(v) {
    var out = {};
    LANGS.forEach(function (l) {
      out[l] = (v && typeof v === 'object') ? (v[l] || '') : (l === 'en' ? (v || '') : '');
    });
    return out;
  }
  function tidyBundle(b) {
    var out = {}, any = false;
    LANGS.forEach(function (l) { if (b[l] && b[l].trim()) { out[l] = b[l].trim(); any = true; } });
    return any ? out : null;
  }
  function strip(s) { return String(s == null ? '' : s).replace(/<[^>]*>/g, '').replace(/&[a-z]+;/g, ' ').trim(); }
  function yearNum(rec) {
    var y = String(rec.year || '');
    if (/forth/i.test(y)) return 9999;
    var m = y.match(/\d{4}/);
    return m ? +m[0] : 0;
  }
  function pick(b) { return (b && typeof b === 'object') ? (b.ko || b.en || '') : (b || ''); }

  // ── API ──────────────────────────────────────────────────────────────────
  function api(path, options) {
    options = options || {};
    var headers = { 'Content-Type': 'application/json' };
    if (session) headers.Authorization = 'Bearer ' + session.token;
    return fetch(API + path, {
      method: options.method || (options.body ? 'POST' : 'GET'),
      headers: headers,
      body: options.body ? JSON.stringify(options.body) : undefined,
    }).then(function (r) {
      return r.json().catch(function () { return {}; }).then(function (body) {
        if (!r.ok) {
          var e = new Error(body.error || ('HTTP ' + r.status));
          e.status = r.status;
          throw e;
        }
        return body;
      });
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
      { k: 'key', label: '식별자', type: 'text', half: true, lockExisting: true,
        note: '영소문자와 하이픈. 사진 파일 이름이 됩니다.' },
      { k: 'photo', label: '사진', type: 'photo' },
      { k: 'name', label: '이름', type: 'i18n', short: true, note: '한국어판은 한글, 나머지는 로마자' },
      { k: 'name_alt', label: '이름 (보조 표기)', type: 'i18n', short: true },
      { k: 'role', label: '역할', type: 'i18n', short: true, note: '간사 등. 없으면 비워 둡니다.' },
      { k: 'affiliation', label: '소속', type: 'i18n', rows: 2 },
      { k: 'interests', label: '연구 관심', type: 'i18n', rows: 2, note: '가운뎃점(·)으로 나열' },
      { k: 'email', label: '이메일', type: 'text', note: '링크는 걸지 않고 주소만 보여 줍니다' },
      { k: 'links', label: '링크', type: 'links' }
    ],
    resources: [
      { k: '_group', label: '묶음', type: 'group' },
      { k: 'name', label: '이름', type: 'text', kind: 'link' },
      { k: 'url', label: '주소', type: 'text' },
      { k: 'affiliation', label: '소속·기관', type: 'text', kind: 'link', note: '없으면 비워 둡니다' },
      { k: 'desc', label: '설명', type: 'i18n', rows: 2, kind: 'link', note: '한 문장으로 무엇인지' },
      { k: 'authors', label: '저자', type: 'text', kind: 'book', locked: true },
      { k: 'year', label: '연도', type: 'text', kind: 'book', half: true, locked: true },
      { k: 'title', label: '제목', type: 'text', kind: 'book', locked: true },
      { k: 'publisher', label: '출판사', type: 'text', kind: 'book', locked: true }
    ]
  };

  // ── records: flatten the nested files into one editable list ─────────────
  function groupsOf(file) {
    var d = store[file] && store[file].data;
    if (!d) return [];
    if (file === 'publications') {
      return d.themes.map(function (t) { return { id: t.id, label: pick(t.title), kind: 'pub' }; })
        .concat(d.other_groups.map(function (g) { return { id: g.id, label: pick(g.title) + ' (기타)', kind: 'pub' }; }));
    }
    if (file === 'resources') {
      var out = d.reading.map(function (g, i) { return { id: 'reading:' + i, label: '독서 목록 — ' + pick(g.title), kind: 'book' }; });
      d.link_blocks.forEach(function (b, bi) {
        b.groups.forEach(function (g, gi) {
          out.push({ id: 'link:' + bi + ':' + gi, label: pick(b.title) + ' — ' + pick(g.title), kind: 'link' });
        });
      });
      return out;
    }
    return [];
  }
  function containerFor(file, groupId) {
    var d = store[file].data;
    if (file === 'publications') {
      return d.themes.concat(d.other_groups).filter(function (g) { return g.id === groupId; })[0];
    }
    var p = String(groupId).split(':');
    if (p[0] === 'reading') return d.reading[+p[1]];
    if (p[0] === 'link') return d.link_blocks[+p[1]].groups[+p[2]];
    return null;
  }
  function records(file) {
    var d = store[file].data;
    if (file === 'seminars') return d.entries;
    if (file === 'members') return d.people;
    var out = [];
    groupsOf(file).forEach(function (g) {
      var c = containerFor(file, g.id);
      if (!c) return;
      c.entries.forEach(function (e) { e._group = g.id; e._kind = g.kind; out.push(e); });
    });
    return out;
  }
  function rebuild(file) {
    var d = store[file].data;
    if (file === 'publications') {
      var all = records(file);
      groupsOf(file).forEach(function (g) {
        containerFor(file, g.id).entries = all
          .filter(function (e) { return e._group === g.id; })
          .sort(function (a, b) { return yearNum(b) - yearNum(a); });
      });
      var titles = {};
      all.forEach(function (e) { titles[e.title] = 1; });
      d.featured = (d.featured || []).filter(function (f) { return titles[f.title]; });
    } else if (file === 'resources') {
      var every = records(file);
      groupsOf(file).forEach(function (g) {
        containerFor(file, g.id).entries = every.filter(function (e) { return e._group === g.id; });
      });
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
      return { iso: '', year: '', kind: 'reading', date_display: bundle(''), title: bundle('') };
    }
    if (file === 'members') {
      return { _new: true, key: '', name: bundle(''), affiliation: bundle(''),
               interests: bundle(''), email: '', links: [] };
    }
    var lg = groupsOf('resources').filter(function (x) { return x.kind === 'link'; })[0];
    return { _group: lg ? lg.id : '', _kind: 'link', name: '', url: '', desc: bundle('') };
  }

  // ── list ─────────────────────────────────────────────────────────────────
  function rowText(file, r) {
    if (file === 'publications') {
      return { title: strip(r.title) || '(제목 없음)', meta: [r.year, r.authors].filter(Boolean).join(' · ') };
    }
    if (file === 'seminars') {
      return { title: strip(pick(r.title)) || '(내용 없음)', meta: r.iso || '(날짜 없음)' };
    }
    if (file === 'members') {
      return { title: pick(r.name) || '(이름 없음)', meta: strip(pick(r.affiliation)) };
    }
    return r._kind === 'book'
      ? { title: strip(r.title) || '(제목 없음)', meta: [r.authors, r.year].filter(Boolean).join(' ') }
      : { title: r.name || '(이름 없음)', meta: (r.url || '').replace(/^https?:\/\//, '').slice(0, 60) };
  }

  function renderList() {
    var file = current, list = $('list');
    list.innerHTML = '';
    var q = $('search').value.trim().toLowerCase();
    var gf = $('group-filter').value;
    var mf = $('member-filter').value;
    var grouped = file === 'publications' || file === 'resources';

    var rows = records(file).filter(function (r) {
      if (grouped && gf && r._group !== gf) return false;
      if (mf && file === 'publications' && (r.members || []).indexOf(mf) === -1) return false;
      if (!q) return true;
      var t = rowText(file, r);
      return (t.title + ' ' + t.meta).toLowerCase().indexOf(q) !== -1;
    });
    if (grouped) {
      var order = {};
      groupsOf(file).forEach(function (g, i) { order[g.id] = i; });
      rows.sort(function (a, b) {
        var d = (order[a._group] || 0) - (order[b._group] || 0);
        if (d !== 0) return d;
        return file === 'publications' ? yearNum(b) - yearNum(a) : 0;
      });
    }

    var lastGroup = null;
    rows.forEach(function (r) {
      if (grouped && r._group !== lastGroup) {
        lastGroup = r._group;
        var g = groupsOf(file).filter(function (x) { return x.id === lastGroup; })[0];
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
  function renderForm() {
    var pane = $('pane');
    pane.innerHTML = '';
    if (!selected) {
      pane.appendChild(el('p', 'empty', '왼쪽에서 항목을 고르거나 새 항목을 누르십시오.'));
      return;
    }
    var file = current, rec = selected;
    pane.appendChild(el('h2', null, rowText(file, rec).title.slice(0, 90) || '새 항목'));

    if (file === 'seminars') {
      SPECS.seminars[1].options = Object.keys(store.seminars.data.kinds).map(function (k) {
        return [k, pick(store.seminars.data.kinds[k])];
      });
    }

    var grid = el('div', 'grid2'), plain = el('div');
    SPECS[file].forEach(function (spec) {
      if (spec.kind && spec.kind !== rec._kind) return;      // resources: link vs book
      var wrap = el('div', 'field');
      var lab = el('div', 'label');
      lab.textContent = spec.label;
      if (spec.locked) lab.appendChild(el('span', 'locked', '원어 고정'));
      wrap.appendChild(lab);
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
      removeRecord(file, rec);
      selected = null;
      markDirty();
      renderList(); renderForm();
    });
    actions.appendChild(del);
    pane.appendChild(actions);
  }

  function removeRecord(file, rec) {
    if (file === 'seminars' || file === 'members') {
      var arr = file === 'seminars' ? store.seminars.data.entries : store.members.data.people;
      var i = arr.indexOf(rec);
      if (i >= 0) arr.splice(i, 1);
      return;
    }
    groupsOf(file).forEach(function (g) {
      var c = containerFor(file, g.id);
      var i = c.entries.indexOf(rec);
      if (i >= 0) c.entries.splice(i, 1);
    });
  }
  function moveGroup(file, rec, groupId) {
    removeRecord(file, rec);
    var target = containerFor(file, groupId);
    if (target) target.entries.push(rec);
    rec._group = groupId;
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

    if (spec.type === 'photo') return photoControl(rec);

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
        lab.appendChild(document.createTextNode(pick(m.name)));
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
          x.type = 'button';
          x.addEventListener('click', function () { rec.links.splice(idx, 1); markDirty(); draw(); });
          row.appendChild(a); row.appendChild(b2); row.appendChild(x);
          wrap.appendChild(row);
        });
        var add = el('button', 'btn', '+ 링크');
        add.type = 'button';
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
      var opts;
      if (spec.type === 'group') {
        opts = groupsOf(current)
          .filter(function (g) { return !rec._kind || g.kind === rec._kind; })
          .map(function (g) { return [g.id, g.label]; });
      } else {
        opts = spec.options;
      }
      opts.forEach(function (o) {
        var op = el('option', null, o[1]);
        op.value = o[0];
        sel.appendChild(op);
      });
      sel.value = v || (opts[0] && opts[0][0]) || '';
      sel.addEventListener('change', function () {
        if (spec.k === '_group') {
          moveGroup(current, rec, sel.value);
        } else {
          rec[spec.k] = sel.value;
          if (spec.k === 'type') {
            if (TYPE_LABELS[sel.value]) rec.type_label = TYPE_LABELS[sel.value];
            else delete rec.type_label;
          }
        }
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
          var cjk = parts[0] + '.' + parts[1] + '.' + parts[2];
          rec.date_display = { en: (+parts[2]) + ' ' + MONTHS[+parts[1] - 1] + ' ' + parts[0], ko: cjk, zh: cjk, ja: cjk };
        }
        markDirty(); renderForm(); renderList();
      });
      return d;
    }

    var input = spec.type === 'textarea' ? el('textarea') : el('input');
    if (spec.type === 'textarea') input.rows = 2;
    input.value = v == null ? '' : v;
    // the identifier names the photo file, so it is fixed once a member exists
    if (spec.lockExisting && !rec._new) input.readOnly = true;
    input.addEventListener('input', function () { rec[spec.k] = input.value; markDirty(); renderListSoon(); });
    return input;
  }

  // ── photo ────────────────────────────────────────────────────────────────
  function photoControl(rec) {
    var wrap = el('div', 'photo-row');
    var frame = el('span', 'photo-frame');
    var img = el('img');
    img.alt = '';
    if (rec._pendingPhoto) {
      img.src = rec._pendingPhoto.dataUrl;
    } else if (rec.photo && rec.key) {
      img.src = '../photos/' + rec.key + '.jpg?t=' + Date.now();
    } else {
      frame.classList.add('empty');
    }
    frame.appendChild(img);
    wrap.appendChild(frame);

    var side = el('div', 'photo-side');
    var file = el('input');
    file.type = 'file';
    file.accept = 'image/*';
    var hint = el('div', 'note');
    function idle() {
      hint.textContent = rec._pendingPhoto
        ? '고른 사진이 미리보기에 있습니다. 저장을 누르면 올라갑니다.'
        : (rec.key ? '고르면 미리보기가 바뀌고, 저장을 누를 때 함께 올라갑니다. 자르지 않고 원본 비율 그대로 씁니다.'
                   : '식별자를 정하고 한 번 저장한 뒤에 사진을 올릴 수 있습니다.');
    }
    idle();
    if (!rec.key) file.disabled = true;

    file.addEventListener('change', function () {
      var f = file.files && file.files[0];
      if (!f) return;
      hint.textContent = '줄이는 중…';
      shrink(f).then(function (out) {
        // held until Save, so that everything on this page commits the same way
        rec._pendingPhoto = out;
        img.src = out.dataUrl;
        frame.classList.remove('empty');
        markDirty();
        idle();
      }).catch(function (e) {
        idle();
        toast('사진을 읽지 못했습니다: ' + e.message, 'bad');
      });
    });

    side.appendChild(file);
    side.appendChild(hint);
    wrap.appendChild(side);
    return wrap;
  }

  /** Resize in the browser: the Worker has no image library, and this keeps the
      upload small. Short side to 320px, original proportions kept. */
  function shrink(fileObj) {
    return new Promise(function (resolve, reject) {
      var reader = new FileReader();
      reader.onerror = function () { reject(new Error('파일을 읽지 못했습니다.')); };
      reader.onload = function () {
        var img = new Image();
        img.onerror = function () { reject(new Error('이미지가 아닙니다.')); };
        img.onload = function () {
          var scale = Math.min(1, PHOTO_SHORT_SIDE / Math.min(img.width, img.height));
          var w = Math.round(img.width * scale), h = Math.round(img.height * scale);
          var canvas = document.createElement('canvas');
          canvas.width = w; canvas.height = h;
          canvas.getContext('2d').drawImage(img, 0, 0, w, h);
          var dataUrl = canvas.toDataURL('image/jpeg', 0.84);
          resolve({ b64: dataUrl.split(',')[1], w: w, h: h, dataUrl: dataUrl });
        };
        img.src = reader.result;
      };
      reader.readAsDataURL(fileObj);
    });
  }

  // ── dirty / save ─────────────────────────────────────────────────────────
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

  function tidyAll() {
    FILES.forEach(rebuild);
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
    records('resources').forEach(function (e) {
      if (e._kind !== 'link') return;
      var t = tidyBundle(bundle(e.desc));
      if (t) e.desc = t; else delete e.desc;
      if (!e.affiliation) delete e.affiliation;
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
      if (!/^[a-z0-9-]+$/.test(m.key || '')) bad('members', m, '식별자는 영소문자와 하이픈만 씁니다 — ' + (m.key || '(빈칸)'));
    });
    records('resources').forEach(function (e) {
      if (e.url && !/^https?:\/\//.test(e.url)) bad('resources', e, '주소가 http로 시작하지 않습니다 — ' + (e.name || e.title || ''));
      if (e._kind === 'link' && !String(e.name || '').trim()) bad('resources', e, '이름이 비어 있습니다.');
    });
    return out;
  }

  function save() {
    tidyAll();
    var bad = problems();
    if (bad.length) {
      var first = bad[0];
      if (current !== first.file) switchTo(first.file);
      selected = first.rec;
      renderList(); renderForm();
      toast(first.msg + (bad.length > 1 ? ' (그 밖에 ' + (bad.length - 1) + '건)' : ''), 'bad');
      return;
    }

    var pending = FILES.filter(function (f) { return store[f].dirty; });
    if (!pending.length) { toast('바뀐 것이 없습니다.'); return; }

    $('save').disabled = true;
    toast('저장하는 중…');
    var LABEL = { publications: '출판', seminars: '세미나', members: '구성원', resources: '자료·링크' };
    var chain = Promise.resolve();

    // Images are separate files, so they go up first; that write also touches
    // members.json, and the sha it returns is the one the save below needs.
    (store.members.data.people || []).filter(function (m) { return m._pendingPhoto; })
      .forEach(function (m) {
        chain = chain.then(function () {
          toast('사진을 올리는 중…');
          return api('/api/photo/' + m.key, {
            body: { jpeg: m._pendingPhoto.b64, w: m._pendingPhoto.w, h: m._pendingPhoto.h }
          }).then(function (res) {
            if (res.members_sha) store.members.sha = res.members_sha;
            m.photo = { w: m._pendingPhoto.w, h: m._pendingPhoto.h };
            delete m._pendingPhoto;
          });
        });
      });

    pending.forEach(function (f) {
      chain = chain.then(function () {
        return api('/api/data/' + f, { method: 'PUT', body: { data: store[f].data, sha: store[f].sha } })
          .then(function (res) { store[f].sha = res.sha; store[f].dirty = false; });
      });
    });
    chain.then(function () {
      $('dirty').hidden = true;
      toast('저장했습니다 — ' + pending.map(function (f) { return LABEL[f]; }).join(', ') +
        '. 사이트 반영까지 1–2분 걸립니다.', 'good');
    }).catch(function (e) {
      $('save').disabled = false;
      toast(e.message || '저장하지 못했습니다.', 'bad');
    });
  }

  // ── screens ──────────────────────────────────────────────────────────────
  function show(which) {
    $('gate').hidden = which !== 'gate';
    $('pwgate').hidden = which !== 'pw';
    $('app').hidden = which !== 'app';
    $('tabs').hidden = which !== 'app';
    $('save').hidden = which !== 'app';
    $('pw').hidden = which !== 'app';
    $('signout').hidden = which === 'gate';
    $('who').hidden = which === 'gate';
  }
  function switchTo(file) {
    current = file;
    selected = null;
    Array.prototype.forEach.call($('tabs').children, function (b) {
      b.className = b.dataset.file === file ? 'on' : '';
    });
    var gf = $('group-filter');
    gf.innerHTML = '';
    var groups = groupsOf(file);
    if (groups.length) {
      gf.hidden = false;
      var all = el('option', null, '모든 묶음'); all.value = '';
      gf.appendChild(all);
      groups.forEach(function (g) {
        var o = el('option', null, g.label); o.value = g.id; gf.appendChild(o);
      });
    } else {
      gf.hidden = true;
    }
    var mf = $('member-filter');
    mf.innerHTML = '';
    if (file === 'publications') {
      mf.hidden = false;
      var everyone = el('option', null, '구성원 전체'); everyone.value = '';
      mf.appendChild(everyone);
      (store.members.data.people || []).forEach(function (m) {
        var o = el('option', null, pick(m.name));
        o.value = m.key.replace(/-/g, '_');
        mf.appendChild(o);
      });
    } else {
      mf.hidden = true;
    }
    $('search').value = '';
    renderList();
    renderForm();
  }

  function loadAll() {
    return api('/api/data').then(function (res) {
      FILES.forEach(function (f) { store[f] = { data: res[f].data, sha: res[f].sha, dirty: false }; });
    });
  }
  function enterApp() {
    $('who').textContent = session.name;
    show('app');
    switchTo('publications');
  }

  function signIn(username, password, remember) {
    return api('/api/login', { body: { username: username, password: password } }).then(function (res) {
      session = { token: res.token, name: res.name };
      (remember ? localStorage : sessionStorage).setItem(TOKEN_KEY, JSON.stringify(session));
      if (res.must_change) { show('pw'); return; }
      return loadAll().then(enterApp);
    });
  }
  function signOut() {
    localStorage.removeItem(TOKEN_KEY);
    sessionStorage.removeItem(TOKEN_KEY);
    location.reload();
  }

  // ── boot ─────────────────────────────────────────────────────────────────
  document.addEventListener('DOMContentLoaded', function () {
    $('gate-form').addEventListener('submit', function (e) {
      e.preventDefault();
      var err = $('gate-err');
      err.hidden = true;
      $('gate-go').disabled = true;
      signIn($('username').value, $('password').value, $('remember').checked)
        .catch(function (ex) { err.textContent = ex.message; err.hidden = false; })
        .then(function () { $('gate-go').disabled = false; $('password').value = ''; });
    });

    $('pw-form').addEventListener('submit', function (e) {
      e.preventDefault();
      var err = $('pw-err');
      err.hidden = true;
      if ($('pw-next').value !== $('pw-again').value) {
        err.textContent = '새 비밀번호 두 칸이 서로 다릅니다.';
        err.hidden = false;
        return;
      }
      api('/api/password', { body: { current: $('pw-current').value, next: $('pw-next').value } })
        .then(function () {
          $('pw-form').reset();
          toast('비밀번호를 바꿨습니다.', 'good');
          if (store.publications) { show('app'); return; }
          return loadAll().then(enterApp);
        })
        .catch(function (ex) { err.textContent = ex.message; err.hidden = false; });
    });

    $('pw').addEventListener('click', function () {
      $('pw-title').textContent = '비밀번호 바꾸기';
      $('pw-lead').textContent = '';
      $('pw-cancel').hidden = false;
      show('pw');
    });
    $('pw-cancel').addEventListener('click', function () { show('app'); });
    $('signout').addEventListener('click', signOut);

    Array.prototype.forEach.call($('tabs').children, function (b) {
      b.addEventListener('click', function () { switchTo(b.dataset.file); });
    });
    $('search').addEventListener('input', renderListSoon);
    $('group-filter').addEventListener('change', renderList);
    $('member-filter').addEventListener('change', renderList);
    $('save').addEventListener('click', save);
    $('add').addEventListener('click', function () {
      var rec = blank(current);
      if (current === 'seminars') store.seminars.data.entries.unshift(rec);
      else if (current === 'members') store.members.data.people.push(rec);
      else {
        var c = containerFor(current, rec._group);
        if (c) c.entries.unshift(rec);
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
      try { session = JSON.parse(saved); } catch (e) { session = null; }
    }
    if (session) {
      loadAll().then(enterApp).catch(function () { signOut(); });
    } else {
      show('gate');
    }
  });
})();
