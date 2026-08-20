/* Publication filtering.
   136 items grouped into nine themes is more than anyone scans, so the page
   lets a reader narrow by member, language, and whether a free full text
   exists. Filtering is progressive enhancement: with JavaScript off the whole
   list is still there, and the controls simply never appear. */
(function () {
  var form = document.getElementById('pub-filter');
  if (!form) return;
  form.hidden = false;

  var member = document.getElementById('f-member');
  var lang = document.getElementById('f-lang');
  var oa = document.getElementById('f-oa');
  var counter = document.getElementById('f-count');
  var empty = document.getElementById('f-empty');
  var nav = document.querySelector('.pub-nav');

  var pubs = Array.prototype.slice.call(document.querySelectorAll('.pub'));
  var blocks = Array.prototype.slice.call(document.querySelectorAll('.theme-block'));
  var total = pubs.length;
  var showing = counter.dataset.showing || '';
  var unit = (document.querySelector('.count') || {}).dataset;
  unit = unit ? unit.unit : '';

  function matches(el) {
    if (member.value && (' ' + el.dataset.members + ' ').indexOf(' ' + member.value + ' ') === -1) return false;
    if (lang.value && el.dataset.lang !== lang.value) return false;
    if (oa.checked && el.dataset.oa !== '1') return false;
    return true;
  }

  function apply() {
    var visible = 0;
    pubs.forEach(function (el) {
      var ok = matches(el);
      el.hidden = !ok;
      if (ok) visible++;
    });

    // a theme with nothing left in it should not leave a stranded heading
    var liveIds = {};
    blocks.forEach(function (block) {
      var n = block.querySelectorAll('.pub:not([hidden])').length;
      block.hidden = n === 0;
      liveIds[block.id] = n > 0;
      var count = block.querySelector('.count');
      if (count) {
        count.textContent = (n === Number(count.dataset.total))
          ? count.dataset.total + ' ' + count.dataset.unit
          : n + ' / ' + count.dataset.total + ' ' + count.dataset.unit;
      }
    });

    if (nav) {
      Array.prototype.forEach.call(nav.querySelectorAll('a'), function (a) {
        var id = a.getAttribute('href').slice(1);
        a.hidden = liveIds[id] === false;
      });
    }

    var filtered = member.value || lang.value || oa.checked;
    counter.textContent = filtered ? showing + ' ' + visible + ' / ' + total : '';
    empty.hidden = visible !== 0;
  }

  form.addEventListener('change', apply);
  form.addEventListener('submit', function (e) { e.preventDefault(); });
  apply();
})();
