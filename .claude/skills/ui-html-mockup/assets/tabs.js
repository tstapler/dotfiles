/* Arrow-key navigation for any role=tablist (ARIA tabs pattern, automatic activation).
 * Markup: <div role="tablist" id="x"><button role="tab" aria-selected="true" tabindex="0">..</button><button role="tab" tabindex="-1">..</button></div>
 * Give each tablist an id so focus can be restored after a re-render. Page switching between top-level pages is NOT a tablist: use
 * <nav aria-label="Pages"> with buttons carrying aria-current="page". */
document.addEventListener('keydown', e => {
  const tab = e.target.closest?.('[role=tab]'); if (!tab) return;
  const list = tab.closest('[role=tablist]'); if (!list) return;
  const tabs = [...list.querySelectorAll('[role=tab]')]; let i = tabs.indexOf(tab);
  if (e.key==='ArrowRight') i = (i+1)%tabs.length; else if (e.key==='ArrowLeft') i = (i-1+tabs.length)%tabs.length; else if (e.key==='Home') i = 0; else if (e.key==='End') i = tabs.length-1; else return;
  e.preventDefault(); const id = list.id; tabs[i].click();
  setTimeout(() => { const l = id && document.getElementById(id); (l && (l.querySelector('[aria-selected=true]') || l.querySelector('[role=tab]')))?.focus(); }, 0);
});
