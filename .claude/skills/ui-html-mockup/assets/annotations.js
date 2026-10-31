/* Figma-style annotations + guided tour for a single-file HTML mockup.
 * Host page defines window.MOCKUP before loading this file:
 *   MOCKUP = {
 *     pages: { summary:'Summary', detail:'Detail' },   // key -> label
 *     getPage: () => PAGE,                              // current page key
 *     go: (page) => {...},                              // switch page WITHOUT stealing focus, then re-render
 *     annos: [{ id, page:'*'|key, sel:'#css', type:'New'|'Changed'|'Question', title, was, now, data, ask }],
 *     tour: ['id1','id2'],                              // ordered annotation ids
 *     before: { id: () => {...} },                      // optional per-step setup (select a row, open a drawer)
 *   }
 * Host calls MOCKUP.afterRender() after every render. Markup needed once:
 *   <div id="annoLayer"></div><div id="tourLayer"></div>
 *   <details id="annoPanel" style="display:none"><summary><b>Notes on this page</b> <span id="annoCount"></span></summary><ol id="annoList"></ol></details>   (collapsed so it never covers content)
 *   <button id="annoBtn" class="hbtn" aria-pressed="false" onclick="MOCKUP.toggle()">Annotations</button>
 *   <button id="tourBtn" class="hbtn" onclick="MOCKUP.start()">Start tour</button>
 * Share links: file.html#annotations, file.html#tour, file.html#<pageKey>.
 */
(function(){
  const M = window.MOCKUP; let on = false, pop = null, ti = -1;
  const byId = id => M.annos.find(a => a.id === id);
  const pageAnnos = () => M.annos.filter(a => a.page === '*' || a.page === M.getPage());
  const cls = a => a.type.toLowerCase();
  const html = a => `<div class="ahead"><span class="atag ${cls(a)}">${a.type}</span><b>${a.title}</b></div><dl><dt>Was</dt><dd>${a.was}</dd><dt>Now</dt><dd>${a.now}</dd><dt>Data</dt><dd>${a.data}</dd><dt>Ask</dt><dd>${a.ask}</dd></dl>`;
  function place(){
    const layer = document.getElementById('annoLayer'); layer.innerHTML = '';
    document.getElementById('annoPanel').style.display = on ? '' : 'none';
    document.getElementById('annoBtn').setAttribute('aria-pressed', on);
    if (!on) return;
    const list = pageAnnos();
    document.getElementById('annoCount').textContent = `(${list.length}, collapsed by default)`;
    document.getElementById('annoList').innerHTML = list.map((a,i)=>`<li><button class="lk" onclick="MOCKUP.open('${a.id}',true)"><b>${i+1}</b> ${a.title}</button> <span class="atag ${cls(a)}">${a.type}</span></li>`).join('');
    list.forEach((a,i) => { const el = document.querySelector(a.sel); if (!el || !el.offsetParent) return;
      const r = el.getBoundingClientRect(), b = document.createElement('button');
      b.className = 'pin ' + cls(a); b.textContent = i+1; b.dataset.id = a.id; b.setAttribute('aria-label', `Note ${i+1}, ${a.type}: ${a.title}`);
      b.style.left = (r.left + scrollX - 12) + 'px'; b.style.top = (r.top + scrollY - 12) + 'px'; b.onclick = () => open(a.id); layer.appendChild(b); });
  }
  // Place a floating card beside the highlighted element (right, left, below, above), choosing the spot with least overlap.
  function placeNear(card, r){
    const W = card.offsetWidth, H = card.offsetHeight, m = 12, vw = innerWidth, vh = innerHeight;
    const clamp = (x,y) => ({x:Math.min(vw-W-8, Math.max(8, x)), y:Math.min(vh-H-8, Math.max(8, y))});
    const overlap = p => Math.max(0, Math.min(p.x+W, r.right+6) - Math.max(p.x, r.left-6)) * Math.max(0, Math.min(p.y+H, r.bottom+6) - Math.max(p.y, r.top-6));
    const cands = [clamp(r.right+m, r.top), clamp(r.left-m-W, r.top), clamp(r.left, r.bottom+m), clamp(r.left, r.top-m-H)];
    let best = cands[0], bo = overlap(best); for (const c of cands) { const o = overlap(c); if (o < bo) { best = c; bo = o; } if (bo === 0) break; }
    Object.assign(card.style, {left:best.x+'px', top:best.y+'px', bottom:'auto', transform:'none'});
  }
  function popPlace(){ if (!pop) return; const a = byId(pop), el = document.querySelector(a.sel), p = document.getElementById('annopop'), s = document.getElementById('annoSpot'); if (!el || !p) return;
    const r = el.getBoundingClientRect(); s.style.cssText = `left:${r.left-4}px;top:${r.top-4}px;width:${r.width+8}px;height:${r.height+8}px`; placeNear(p, r); }
  function open(id, scroll){ close(); const a = byId(id), el = document.querySelector(a.sel); if (scroll && el) { el.scrollIntoView({block:'start'}); scrollBy(0,-70); }
    setTimeout(() => { const p = document.createElement('div'); p.className = 'annopop'; p.id = 'annopop'; p.setAttribute('role','dialog'); p.setAttribute('aria-label', a.title);
      p.innerHTML = html(a) + '<button class="lk" onclick="MOCKUP.close()">Close</button>'; document.body.appendChild(p);
      const s = document.createElement('div'); s.id = 'annoSpot'; s.className = 'annospot'; document.body.appendChild(s);
      pop = id; popPlace(); p.querySelector('button').focus(); }, 0); }
  function close(){ document.getElementById('annopop')?.remove(); document.getElementById('annoSpot')?.remove(); pop = null; }
  function toggle(v){ on = v ?? !on; close(); place(); }
  function step(i){ if (i < 0 || i >= M.tour.length) return end(); ti = i; const a = byId(M.tour[i]);
    if (a.page !== '*' && a.page !== M.getPage()) M.go(a.page);
    M.before?.[a.id]?.();
    setTimeout(() => { const el = document.querySelector(a.sel); if (el) { el.scrollIntoView({block:'start'}); scrollBy(0,-70); } setTimeout(() => draw(a, i), 30); }, 30); }
  function draw(a, i){ const el = document.querySelector(a.sel), r = el ? el.getBoundingClientRect() : {left:0,top:0,right:0,bottom:0,width:0,height:0};
    const had = document.getElementById('tourcard'), focusNext = !had || had.dataset.step !== String(i);
    document.getElementById('tourLayer').innerHTML = `<div class="spot" style="left:${r.left-6}px;top:${r.top-6}px;width:${r.width+12}px;height:${r.height+12}px"></div>
      <div class="tourcard" id="tourcard" data-step="${i}" role="dialog" aria-label="Guided tour, step ${i+1} of ${M.tour.length}">${html(a)}<div class="ahead" style="margin-top:8px"><span style="color:var(--mute,#586072)">${i+1} of ${M.tour.length}</span><span style="flex:1"></span>
      <button class="tbtn" onclick="MOCKUP.step(${i-1})" ${i===0?'disabled':''}>Back</button><button class="tbtn primary" id="tournext" onclick="MOCKUP.step(${i+1})">${i===M.tour.length-1?'Finish':'Next'}</button><button class="tbtn" onclick="MOCKUP.end()">Skip tour</button></div></div>`;
    placeNear(document.getElementById('tourcard'), r); if (focusNext) document.getElementById('tournext').focus(); }
  function start(){ close(); M.go(Object.keys(M.pages)[0]); step(0); }
  function end(){ ti = -1; document.getElementById('tourLayer').innerHTML = ''; document.getElementById('tourBtn').focus(); }
  document.addEventListener('keydown', e => { if (e.key==='Escape') { ti>=0 ? end() : pop && close(); } if (ti>=0 && e.key==='ArrowRight') step(ti+1); if (ti>=0 && e.key==='ArrowLeft') step(ti-1); });
  let raf = 0; const reflow = () => { cancelAnimationFrame(raf); raf = requestAnimationFrame(() => { if (ti>=0) draw(byId(M.tour[ti]), ti); popPlace(); }); };
  addEventListener('scroll', reflow, {passive:true}); addEventListener('resize', () => { place(); reflow(); });
  Object.assign(M, { afterRender: () => setTimeout(place, 0), toggle, open, close, start, step, end });
  const h = location.hash.replace('#','').split(/[&,]/); if (h.includes('annotations')) on = true;
  const pg = h.find(x => M.pages[x]); if (pg) M.go(pg);
  if (h.includes('tour')) setTimeout(start, 50);
})();
