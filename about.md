---
layout: default
title: 关于我们
permalink: /about/
---
<section id="about">
  <div class="wrap">
    {% include section-head.html key="about" %}
    {% assign about = site.data.about %}
    <div class="about">
      <img class="team-logo" src="{{ about.logo | relative_url }}" alt="{{ about.team_title | escape }}">
      <h2 id="qianli">{{ about.author | escape }} <span> / {{ about.role | escape }}</span></h2>
      {% for paragraph in about.paragraphs %}<p>{{ paragraph | escape }}</p>{% endfor %}
      <h2>{{ about.team_title | escape }}</h2>
      <p>{{ about.team_description | escape }}</p>
      <div class="story-links">{% for link in about.research_links %}<a class="text-link" href="{{ link.url | relative_url }}">{{ link.title | escape }} →</a>{% endfor %}</div>
    </div>
    <div class="contact-grid">{% for contact in about.contacts %}
      {% if contact.modal %}<button class="contact-card" type="button" data-modal="{{ contact.modal | escape }}">{% else %}<a class="contact-card" href="{{ contact.url | relative_url }}" target="_blank" rel="noopener">{% endif %}
      <span class="c-glyph g-{{ contact.tone | default: 'gold' | escape }}">{{ contact.glyph | escape }}</span><span class="c-title">{{ contact.title | escape }}</span><span class="c-desc">{{ contact.description | escape }}</span>
      {% if contact.modal %}</button>{% else %}</a>{% endif %}
    {% endfor %}</div>
  </div>
</section>
