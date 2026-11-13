/* live-sync: keeps a page of the platform up to date without reloading it.
   One static file, the same bytes for everybody. It asks this site (GET, same origin) every 2 seconds whether the page changed; when it did, it fetches the
   regions that differ and replaces only those. A region that holds a form control the person touched is left alone. It never sends anything but a GET, never
   presses a button, and holds no data of its own: the version of every region is in the page (the data-live attribute of body). */
(function () {
  'use strict';
  var body = document.body;
  var raw = body ? body.getAttribute('data-live') : null;
  if (!raw) { return; }
  var base;
  try { base = JSON.parse(raw); } catch (e) { return; }
  if (!base || !base.c) { return; }

  var INTERVAL = 2000;
  var CAP = 30000;
  var goUrl = body.getAttribute('data-live-u') || '';
  var here = location.pathname + location.search;
  var firstPick = new WeakMap();      // the option each drop-down showed when the page (or the region) came
  var mismatches = 0;
  var failures = 0;
  var timer = null;
  var busy = false;
  var stopped = false;
  var boxes = [];
  var boxEls = [];

  function locate(path) {
    var el = document.body;
    for (var i = 0; i < path.length; i++) {
      el = el.children[path[i]];
      if (!el) { return null; }
    }
    return el;
  }

  function isBox(el) { return boxEls.indexOf(el) !== -1; }

  function itemsOf(el) {
    var out = [];
    for (var i = 0; i < el.children.length; i++) {
      if (!isBox(el.children[i]) && el.children[i].tagName !== 'SCRIPT') { out.push(el.children[i]); }
    }
    return out;
  }

  (function build() {
    var i;
    for (i = 0; i < base.c.length; i++) {
      var el = locate(base.c[i].p);
      boxEls.push(el);
    }
    for (i = 0; i < base.c.length; i++) {
      var spec = base.c[i];
      var box = { n: spec.n, el: boxEls[i], ok: false, items: [] };
      if (box.el) {
        var kids = itemsOf(box.el);
        if (kids.length === spec.v.length) {
          box.ok = true;
          for (var k = 0; k < kids.length; k++) { box.items.push({ el: kids[k], v: spec.v[k] }); }
        }
      }
      boxes.push(box);
    }
  })();

  function isControl(el) {
    return /^(INPUT|TEXTAREA|SELECT)$/.test(el.tagName) && el.type !== 'hidden';
  }

  /* A control is "touched" while it differs from what the server gave: a box ticked and then unticked, or text typed and then deleted, is not touched any more.
     A drop-down shows its first option when none is marked, so it is compared with the option it showed when it came. */
  function remember(root) {
    var list = Array.prototype.slice.call(root.querySelectorAll('select'));
    if (root.tagName === 'SELECT') { list.push(root); }
    list.forEach(function (sel) { firstPick.set(sel, sel.selectedIndex); });
  }

  function changed(c) {
    if (c.tagName === 'SELECT') { return firstPick.has(c) && c.selectedIndex !== firstPick.get(c); }
    if (c.type === 'checkbox' || c.type === 'radio') { return c.checked !== c.defaultChecked; }
    return c.value !== c.defaultValue;
  }

  function touched(el) {
    var a = document.activeElement;
    if (a && a !== document.body && el.contains(a)) { return true; }
    var list = Array.prototype.slice.call(el.querySelectorAll('input, textarea, select'));
    if (isControl(el)) { list.push(el); }
    for (var i = 0; i < list.length; i++) {
      if (list[i].type === 'hidden') { continue; }
      if (changed(list[i])) { return true; }
    }
    return false;
  }

  function anyTouched() {
    return touched(document.body);
  }

  remember(document.body);

  function go() {
    if (stopped) { return; }
    stopped = true;
    if (timer) { clearTimeout(timer); }
    if (goUrl) { location.assign(goUrl); } else { location.reload(); }
  }

  function parse(text) {
    var t = document.createElement('template');
    t.innerHTML = text;
    var el = t.content.firstElementChild;
    if (el) { remember(el); }
    return el;
  }

  /* The longest common run of versions keeps its elements; between two such runs the old and the new regions are paired in order (replace), the rest is
     removed or inserted. A region of the page whose version did not change is never touched, whatever its place is now. */
  function plan(old, nv) {
    var n = old.length;
    var m = nv.length;
    var L = [];
    var i;
    var j;
    for (i = 0; i <= n; i++) { L.push(new Array(m + 1).fill(0)); }
    for (i = n - 1; i >= 0; i--) {
      for (j = m - 1; j >= 0; j--) {
        L[i][j] = old[i].v === nv[j] ? L[i + 1][j + 1] + 1 : Math.max(L[i + 1][j], L[i][j + 1]);
      }
    }
    var ops = [];
    var gapO = [];
    var gapN = [];
    function flush() {
      var both = Math.min(gapO.length, gapN.length);
      var k;
      for (k = 0; k < both; k++) { ops.push({ t: 'swap', i: gapO[k], j: gapN[k] }); }
      for (k = both; k < gapO.length; k++) { ops.push({ t: 'drop', i: gapO[k] }); }
      for (k = both; k < gapN.length; k++) { ops.push({ t: 'add', j: gapN[k] }); }
      gapO = [];
      gapN = [];
    }
    i = 0;
    j = 0;
    while (i < n || j < m) {
      if (i < n && j < m && old[i].v === nv[j] && L[i][j] === L[i + 1][j + 1] + 1) {
        flush();
        ops.push({ t: 'keep', i: i, j: j });
        i++;
        j++;
      } else if (i < n && (j >= m || L[i + 1][j] >= L[i][j + 1])) {
        gapO.push(i);
        i++;
      } else {
        gapN.push(j);
        j++;
      }
    }
    flush();
    return ops;
  }

  function apply(box, nv, ops, got) {
    var result = [];
    var prev = null;
    var first = box.items.length ? box.items[0].el : null;
    ops.forEach(function (op) {
      var item = op.i !== undefined ? box.items[op.i] : null;
      var name = box.n + '-' + op.j;
      var fresh;
      if (op.t === 'keep') {
        result.push({ el: item.el, v: nv[op.j] });
        prev = item.el;
      } else if (op.t === 'swap') {
        fresh = typeof got[name] === 'string' && !touched(item.el) ? parse(got[name]) : null;
        if (fresh) {
          item.el.replaceWith(fresh);
          result.push({ el: fresh, v: nv[op.j] });
          prev = fresh;
        } else {
          result.push(item);
          prev = item.el;
        }
      } else if (op.t === 'drop') {
        if (touched(item.el)) {
          result.push(item);
          prev = item.el;
        } else {
          item.el.remove();
        }
      } else if (op.t === 'add') {
        fresh = typeof got[name] === 'string' ? parse(got[name]) : null;
        if (!fresh) { return; }
        if (prev) {
          prev.after(fresh);
        } else if (first && first.parentNode === box.el) {
          first.before(fresh);
        } else {
          box.el.appendChild(fresh);
        }
        result.push({ el: fresh, v: nv[op.j] });
        prev = fresh;
      }
    });
    box.items = result;
  }

  function get(url, then) {
    var ctrl = typeof AbortController === 'function' ? new AbortController() : null;
    var cut = ctrl ? setTimeout(function () { ctrl.abort(); }, 15000) : null;
    var options = { method: 'GET', credentials: 'same-origin', cache: 'no-store', redirect: 'manual' };
    if (ctrl) { options.signal = ctrl.signal; }
    fetch(url, options).then(function (r) {
      if (cut) { clearTimeout(cut); }
      if (r.type === 'opaqueredirect' || r.status === 401) { return { lost: true }; }
      if (r.status === 429) { return { slow: true }; }      // asked too soon: not a failure, ask again at the usual time
      if (!r.ok) { throw new Error('status'); }
      return r.json();
    }).then(function (j) { then(null, j); }, function (e) { if (cut) { clearTimeout(cut); } then(e || new Error('failed'), null); });
  }

  function names(list) {
    return list.map(function (x) { return x; }).join(',');
  }

  function step(j, done) {
    if (!j || j.lost || j.slow) { done(j); return; }
    if (j.s === 'wait') { done(j); return; }
    if (j.s === 'reload') { go(); done(j); return; }
    if (j.s !== 'ok' || j.h !== base.h || j.c.length !== boxes.length) { go(); done(j); return; }
    var work = [];
    var wanted = [];
    var i;
    for (i = 0; i < boxes.length; i++) {
      var box = boxes[i];
      var spec = j.c[i];
      if (spec.n !== box.n) { go(); done(j); return; }
      var same = box.ok && box.items.length === spec.v.length && box.items.every(function (it, k) { return it.v === spec.v[k]; });
      if (same) { continue; }
      if (!box.ok) {
        if (!anyTouched()) { go(); done(j); return; }
        continue;
      }
      var ops = plan(box.items, spec.v);
      ops.forEach(function (op) {
        if (op.t === 'swap' && !touched(box.items[op.i].el)) { wanted.push(box.n + '-' + op.j); }
        if (op.t === 'add') { wanted.push(box.n + '-' + op.j); }
      });
      work.push({ box: box, nv: spec.v, ops: ops });
    }
    var expect = {};
    work.forEach(function (w) {
      w.ops.forEach(function (op) { if (op.j !== undefined) { expect[w.box.n + '-' + op.j] = w.nv[op.j]; } });
    });
    if (!work.length) { done(j); return; }
    var finish = function (got) {
      work.forEach(function (w) { apply(w.box, w.nv, w.ops, got); });
      done(j);
    };
    if (!wanted.length) { finish({}); return; }
    get('/live/content?u=' + encodeURIComponent(here) + '&n=' + encodeURIComponent(names(wanted)), function (err, c) {
      if (err || !c || c.lost || c.slow || c.s !== 'ok') {
        if (c && (c.lost || c.slow)) { done(c); return; }
        if (c && c.s === 'reload') { go(); }
        done(err ? { fail: true } : c);
        return;
      }
      /* The page may have changed between the question and the answer: every region must come with the version that was planned for, else nothing is put in. */
      var got = c.r || {};
      var ver = c.v || {};
      var bad = wanted.some(function (n) { return ver[n] !== expect[n]; });
      if (bad) {
        mismatches++;
        if (mismatches >= 2) { go(); }
        done({ retry: true });
        return;
      }
      mismatches = 0;
      finish(got);
    });
  }

  function later(delay) {
    if (stopped) { return; }
    if (timer) { clearTimeout(timer); }
    timer = setTimeout(poll, delay);
  }

  function poll() {
    if (stopped || busy) { return; }
    if (document.hidden) { return; }
    busy = true;
    get('/live/version?u=' + encodeURIComponent(here), function (err, j) {
      if (err) {
        failures++;
        busy = false;
        later(Math.min(CAP, INTERVAL * Math.pow(2, failures)));
        return;
      }
      step(j, function (seen) {
        busy = false;
        if (seen && seen.lost) {
          stopped = true;
          location.reload();
          return;
        }
        if (seen && seen.slow) {
          later(INTERVAL);
          return;
        }
        if (seen && seen.fail) {
          failures++;
          later(Math.min(CAP, INTERVAL * Math.pow(2, failures)));
          return;
        }
        failures = 0;
        if (seen && seen.x) {      // the page has everything it waited for: this was its last update
          stopped = true;
          return;
        }
        later(INTERVAL);
      });
    });
  }

  document.addEventListener('visibilitychange', function () {
    if (stopped) { return; }
    if (timer) { clearTimeout(timer); timer = null; }
    if (!document.hidden) { poll(); }
  });

  later(INTERVAL);
}());
