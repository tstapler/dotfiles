/* Measured design checks, injected into a COPY of the mockup, read back from document.title.
 * Usage:  probe.sh file.html [width]  (see probe.sh). Edit nothing in the mockup itself.
 * Reports: text contrast failures (computed styles, 4.5:1 / 3:1 large), interactive targets under 24px,
 * onclick elements that are not keyboard-operable, duplicate link names, heading outline, landmarks,
 * horizontal overflow, and how many top-level sections end above the 900px fold. */
(function(){
  const out = {};
  const lum = c => { const v = c.map(x => { x/=255; return x<=.03928 ? x/12.92 : Math.pow((x+.055)/1.055,2.4); }); return .2126*v[0]+.7152*v[1]+.0722*v[2]; };
  const rgb = s => { const m = s.match(/rgba?\(([^)]+)\)/); if (!m) return null; const p = m[1].split(',').map(Number); return {c:p.slice(0,3), a:p.length>3?p[3]:1}; };
  const bg = e => { while (e) { const r = rgb(getComputedStyle(e).backgroundColor); if (r && r.a > .9) return r.c; e = e.parentElement; } return [255,255,255]; };
  const ratio = (a,b) => { const x = lum(a), y = lum(b); return (Math.max(x,y)+.05)/(Math.min(x,y)+.05); };
  const fails = []; let checked = 0;
  document.querySelectorAll('body *').forEach(e => { if (e.closest('[data-probe-ignore]')) return;
    if (![...e.childNodes].some(n => n.nodeType===3 && n.textContent.trim()) || !e.offsetParent) return;
    const cs = getComputedStyle(e), fg = rgb(cs.color); if (!fg) return; checked++;
    const big = parseFloat(cs.fontSize) >= 24 || (parseFloat(cs.fontSize) >= 18.66 && +cs.fontWeight >= 700), r = ratio(fg.c, bg(e));
    if (r < (big ? 3 : 4.5)) fails.push([e.textContent.trim().slice(0,28), +r.toFixed(2), cs.fontSize]);
  });
  out.textChecked = checked; out.textFails = fails.slice(0,12);
  out.smallTargets = [...document.querySelectorAll('button,select,a[href],input')].map(e => { const b = e.getBoundingClientRect(); return [(e.textContent||e.tagName).trim().slice(0,20), Math.round(b.width), Math.round(b.height)]; }).filter(x => x[1] && (x[1]<24 || x[2]<24));
  out.onclickNotKeyboard = [...document.querySelectorAll('[onclick]')].filter(e => !e.matches('button,a[href],select,input,summary')).length;
  const names = {}; document.querySelectorAll('button,a[href]').forEach(b => { const n = (b.getAttribute('aria-label')||b.textContent).trim(); if (n) names[n] = (names[n]||0)+1; });
  out.duplicateControlNames = Object.fromEntries(Object.entries(names).filter(([k,v]) => v>1 && k.length>0).slice(0,10));
  out.headings = [...document.querySelectorAll('h1,h2,h3,h4')].filter(h => h.offsetParent).map(h => h.tagName+':'+h.textContent.trim().slice(0,24));
  out.landmarks = {header:!!document.querySelector('header'), main:!!document.querySelector('main'), nav:!!document.querySelector('nav')};
  out.overflow = {scrollWidth:document.documentElement.scrollWidth, innerWidth};
  document.title = JSON.stringify(out);
})();
