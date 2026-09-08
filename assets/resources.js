(function () {
  'use strict';
  var search = document.getElementById('resource-search');
  if (!search) return;
  var type = document.getElementById('resource-type');
  var topic = document.getElementById('resource-topic');
  var entries = Array.from(document.querySelectorAll('[data-resource]'));
  var params = new URLSearchParams(window.location.search);
  search.value = params.get('q') || '';
  type.value = params.get('type') || '';
  topic.value = params.get('topic') || '';
  function filter() {
    var terms = search.value.toLowerCase().trim().split(/\s+/).filter(Boolean);
    var count = 0;
    entries.forEach(function (entry) {
      var text = entry.dataset.search.toLowerCase();
      var match = terms.every(function (term) { return text.includes(term); }) &&
        (!type.value || entry.dataset.type === type.value) &&
        (!topic.value || entry.dataset.topics.split('|').includes(topic.value));
      entry.hidden = !match;
      if (match) count++;
    });
    document.getElementById('resource-count').textContent = count + ' 条资料';
    document.getElementById('resource-empty').hidden = count !== 0;
  }
  search.addEventListener('input', filter);
  type.addEventListener('change', filter);
  topic.addEventListener('change', filter);
  search.form.addEventListener('reset', function () { setTimeout(filter, 0); });
  filter();
})();
