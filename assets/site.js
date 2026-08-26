/* ==========================================================================
   Driving Test Simulator — site.js
   Consent-gated analytics, reveal motion, FAQ + CTA instrumentation.

   Nothing Google-owned loads until the visitor presses Accept. The inline
   <head> snippet on every page has already set Consent Mode v2 to denied,
   so even a mis-ordered load cannot write a cookie first.
   ========================================================================== */

(function () {
  'use strict';

  /* ---------------------------------------------------------------------
     Measurement IDs — the owner supplies the real values.
     While these still contain X placeholders NOTHING is injected, even on
     Accept, and a single console warning explains why.
     --------------------------------------------------------------------- */
  var GA4_ID = 'G-XXXXXXXXXX';
  var ADS_ID = 'AW-XXXXXXXXXX';
  var ADS_LABEL = 'XXXXXXXX';

  var STORAGE_KEY = 'dts-consent';
  var CONSENT_VERSION = 1;

  var warned = false;
  var loaded = false;

  function isPlaceholder(id) {
    return !id || /X{4,}/.test(id);
  }

  function idsAreReal() {
    return !isPlaceholder(GA4_ID) && !isPlaceholder(ADS_ID) && !isPlaceholder(ADS_LABEL);
  }

  function warnOnce() {
    if (warned) return;
    warned = true;
    // eslint-disable-next-line no-console
    console.warn(
      '[Driving Test Simulator] Analytics consent was granted, but the GA4 / ' +
      'Google Ads IDs in assets/site.js are still placeholders ' +
      '(GA4_ID="' + GA4_ID + '", ADS_ID="' + ADS_ID + '", ADS_LABEL="' + ADS_LABEL + '"). ' +
      'No Google tag has been loaded and no cookies have been set. Replace the ' +
      'three constants at the top of assets/site.js to switch measurement on.'
    );
  }

  /* gtag() is defined by the inline <head> snippet. Guard anyway so this
     file is safe if that snippet is ever missing. */
  function gtag() {
    window.dataLayer = window.dataLayer || [];
    window.dataLayer.push(arguments);
  }

  /* ---------------------------------------------------------------------
     Stored choice
     --------------------------------------------------------------------- */

  function readConsent() {
    try {
      var raw = window.localStorage.getItem(STORAGE_KEY);
      if (!raw) return null;
      var parsed = JSON.parse(raw);
      if (!parsed || parsed.v !== CONSENT_VERSION) return null;
      if (typeof parsed.analytics !== 'boolean' || typeof parsed.ads !== 'boolean') return null;
      return parsed;
    } catch (e) {
      return null;
    }
  }

  function writeConsent(analytics, ads) {
    var record = {
      v: CONSENT_VERSION,
      analytics: !!analytics,
      ads: !!ads,
      ts: new Date().toISOString()
    };
    try {
      window.localStorage.setItem(STORAGE_KEY, JSON.stringify(record));
    } catch (e) { /* private mode — the choice simply won't persist */ }
    return record;
  }

  function clearConsent() {
    try { window.localStorage.removeItem(STORAGE_KEY); } catch (e) {}
  }

  function hasConsent() {
    var c = readConsent();
    return !!(c && c.analytics);
  }

  /* ---------------------------------------------------------------------
     Tag loading
     --------------------------------------------------------------------- */

  function loadGoogleTags() {
    if (loaded) return;

    if (!idsAreReal()) {
      warnOnce();
      return;               // placeholder guard — nothing injected
    }

    loaded = true;

    var s = document.createElement('script');
    s.async = true;
    s.src = 'https://www.googletagmanager.com/gtag/js?id=' + encodeURIComponent(GA4_ID);
    document.head.appendChild(s);

    gtag('js', new Date());
    gtag('config', GA4_ID, { anonymize_ip: true });
    gtag('config', ADS_ID);
  }

  function grant() {
    gtag('consent', 'update', {
      ad_storage: 'granted',
      ad_user_data: 'granted',
      ad_personalization: 'granted',
      analytics_storage: 'granted',
      functionality_storage: 'granted',
      security_storage: 'granted'
    });
    loadGoogleTags();
  }

  /* Fire an event only when the visitor has opted in AND real IDs exist. */
  function track(name, params) {
    if (!hasConsent() || !idsAreReal()) return;
    gtag('event', name, params || {});
  }

  /* ---------------------------------------------------------------------
     Banner
     --------------------------------------------------------------------- */

  var banner = null;

  /* The banner is position:fixed across the bottom of the viewport, so at the
     end of the page it covers the footer — including the "Cookie settings"
     button that reopens it, which made that button impossible to click while
     the banner was open. Publish the banner's height so .footer can reserve
     matching space and the page can scroll clear of it. */
  var BANNER_INSET = 18;   /* must match #consent { bottom: } in site.css */
  var BANNER_GAP = 20;     /* breathing room between banner and footer text */

  function syncBannerSpace() {
    if (!banner) return;
    var space = banner.hidden ? 0 : banner.offsetHeight + BANNER_INSET + BANNER_GAP;
    document.documentElement.style.setProperty('--consent-space', space + 'px');
  }

  function showBanner() {
    if (!banner) return;
    banner.hidden = false;
    syncBannerSpace();
  }

  function hideBanner() {
    if (!banner) return;
    banner.hidden = true;
    syncBannerSpace();
  }

  function onAccept() {
    writeConsent(true, true);
    hideBanner();
    grant();
    track('consent_choice', { choice: 'accept' });
  }

  function onReject() {
    writeConsent(false, false);
    hideBanner();
    // Consent Mode stays denied; nothing is loaded and nothing is sent.
  }

  function openSettings() {
    clearConsent();
    gtag('consent', 'update', {
      ad_storage: 'denied',
      ad_user_data: 'denied',
      ad_personalization: 'denied',
      analytics_storage: 'denied',
      functionality_storage: 'denied'
    });
    showBanner();
    var accept = document.getElementById('consent-accept');
    if (accept && typeof accept.focus === 'function') accept.focus();
  }

  function initConsent() {
    banner = document.getElementById('consent');

    var stored = readConsent();
    if (stored) {
      if (stored.analytics) grant();
      hideBanner();
    } else {
      showBanner();
    }

    var accept = document.getElementById('consent-accept');
    var reject = document.getElementById('consent-reject');
    if (accept) accept.addEventListener('click', onAccept);
    if (reject) reject.addEventListener('click', onReject);

    var settings = document.querySelectorAll('[data-consent-settings]');
    for (var i = 0; i < settings.length; i++) {
      settings[i].addEventListener('click', function (ev) {
        ev.preventDefault();
        openSettings();
      });
    }

    /* The banner's height changes when the buttons rewrap, so re-measure
       rather than assuming the first reading holds. */
    if (banner && window.ResizeObserver) {
      new window.ResizeObserver(syncBannerSpace).observe(banner);
    } else {
      window.addEventListener('resize', syncBannerSpace);
    }
  }

  /* ---------------------------------------------------------------------
     CTA + FAQ instrumentation
     --------------------------------------------------------------------- */

  function initTracking() {
    var ctas = document.querySelectorAll('a[data-cta]');
    for (var i = 0; i < ctas.length; i++) {
      ctas[i].addEventListener('click', function () {
        var where = this.dataset.cta || 'unknown';
        track('conversion', {
          send_to: ADS_ID + '/' + ADS_LABEL,
          transport_type: 'beacon'
        });
        track('play_store_click', { link_location: where });
      });
    }

    var instructorCtas = document.querySelectorAll('[data-instructor-cta]');
    for (var j = 0; j < instructorCtas.length; j++) {
      instructorCtas[j].addEventListener('click', function () {
        track('instructor_cta_click', {
          link_location: this.dataset.instructorCta || 'instructors'
        });
      });
    }

    var faqs = document.querySelectorAll('.faq details');
    for (var k = 0; k < faqs.length; k++) {
      faqs[k].addEventListener('toggle', function () {
        if (!this.open) return;
        var q = this.querySelector('summary');
        track('faq_open', {
          question: q ? q.textContent.replace(/\s+/g, ' ').trim().slice(0, 90) : 'unknown'
        });
      });
    }
  }

  /* ---------------------------------------------------------------------
     Reveal motion — fade-up with a per-group stagger
     --------------------------------------------------------------------- */

  function initReveal() {
    var items = document.querySelectorAll('.reveal');
    if (!items.length) return;

    var reduce = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    if (reduce || !('IntersectionObserver' in window)) {
      for (var i = 0; i < items.length; i++) items[i].classList.add('is-in');
      return;
    }

    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        if (!entry.isIntersecting) return;
        var el = entry.target;

        // Stagger against siblings that share a parent, capped so a long
        // grid never leaves the last card waiting.
        var sibs = el.parentElement
          ? el.parentElement.querySelectorAll(':scope > .reveal')
          : [];
        var idx = Array.prototype.indexOf.call(sibs, el);
        var delay = Math.min(idx < 0 ? 0 : idx, 5) * 70;
        el.style.setProperty('--reveal-delay', delay + 'ms');

        el.classList.add('is-in');
        io.unobserve(el);
      });
    }, { rootMargin: '0px 0px -8% 0px', threshold: 0.08 });

    for (var j = 0; j < items.length; j++) io.observe(items[j]);
  }

  /* --------------------------------------------------------------------- */

  function init() {
    document.documentElement.classList.remove('no-js');
    initConsent();
    initTracking();
    initReveal();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
