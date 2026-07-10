
(function(){
  const data = Array.isArray(window.DARUMA_PRICE_GROUPS) ? window.DARUMA_PRICE_GROUPS : [];
  const root = document.querySelector('[data-price-list]');
  if(!root) return;
  const list = root.querySelector('[data-pl-list]');
  const count = root.querySelector('[data-pl-count]');
  const search = root.querySelector('[data-pl-search]');
  const sort = root.querySelector('[data-pl-sort]');
  const type = root.querySelector('[data-pl-type]');
  const empty = root.querySelector('[data-pl-empty]');
  const tabs = Array.from(root.querySelectorAll('[data-pl-category]'));
  const views = Array.from(root.querySelectorAll('[data-pl-view]'));
  let category = 'All';
  let view = 'card';
  const yen = new Intl.NumberFormat('ja-JP');
  const isNum = v => typeof v === 'number' && isFinite(v);
  const priceText = v => isNum(v) ? `¥${yen.format(v)}` : (String(v || 'ASK').toUpperCase());
  const safe = s => String(s ?? '').replace(/[&<>'"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[c]));
  const lowest = g => Math.min(...g.variants.map(v => isNum(v.price) ? v.price : Infinity));
  const highest = g => Math.max(...g.variants.map(v => isNum(v.price) ? v.price : -1));
  const latest = g => g.variants.map(v => String(v.updateDate || '')).sort().pop() || '';
  function variantMatches(v, filter){
    const t = String(v.type || '').toUpperCase();
    const c = String(v.condition || '').toLowerCase();
    if(filter==='All') return true;
    if(filter==='CASE') return t === 'CASE';
    if(filter==='BOX') return t === 'BOX' && !c.includes('no shrink');
    if(filter==='No Shrink') return c.includes('no shrink');
    if(filter==='Bulk') return t === 'BULK';
    return true;
  }
  function filterGroups(){
    const q=(search.value||'').toLowerCase().trim();
    const t=type.value||'All';
    let groups=data
      .filter(g=> category==='All' || g.category===category)
      .map(g=> ({...g, variants:g.variants.filter(v=>variantMatches(v,t))}))
      .filter(g=>g.variants.length)
      .filter(g=> !q || [g.item,g.category,g.variants.map(v=>[v.type,v.condition,v.stock,v.price,v.updateDate,v.comment].join(' ')).join(' ')].join(' ').toLowerCase().includes(q));
    const mode=sort.value;
    groups.sort((a,b)=>{
      if(mode==='priceDesc') return highest(b)-highest(a);
      if(mode==='priceAsc') return lowest(a)-lowest(b);
      if(mode==='updated') return latest(b).localeCompare(latest(a));
      return String(a.item||'').localeCompare(String(b.item||''));
    });
    return groups;
  }
  function renderVariant(v){
    return `<div class="pl-variant">
      <div class="pl-v-main">${safe(v.type || '-')}<span class="pl-v-sub">${safe(v.condition || '-')}</span></div>
      <div class="pl-v-stock">Stock<br><strong>${safe(v.stock || '-')}</strong></div>
      <div class="pl-v-price ${isNum(v.price)?'':'is-ask'}">${safe(priceText(v.price))}</div>
      ${v.comment ? `<p class="pl-comment">${safe(v.comment)}</p>` : ''}
    </div>`;
  }
  function render(){
    const groups=filterGroups();
    count.textContent = `${groups.length} products`;
    empty.style.display = groups.length ? 'none':'block';
    list.classList.toggle('is-table', view==='table');
    list.innerHTML = groups.map(g=>`
      <article class="pl-card">
        <div class="pl-img-wrap">${g.image ? `<img class="pl-img" src="${safe(g.image)}" alt="${safe(g.item)}">` : `<span class="pl-img-placeholder">DARUMA</span>`}</div>
        <div class="pl-body">
          <div class="pl-card-top"><h3 class="pl-item">${safe(g.item)}</h3><span class="pl-category">${safe(g.category)}</span></div>
          <div class="pl-variants">${g.variants.map(renderVariant).join('')}</div>
        </div>
      </article>`).join('');
  }
  tabs.forEach(btn=>btn.addEventListener('click',()=>{category=btn.dataset.plCategory;tabs.forEach(b=>b.classList.toggle('is-active', b===btn));render();}));
  views.forEach(btn=>btn.addEventListener('click',()=>{view=btn.dataset.plView;views.forEach(b=>b.classList.toggle('is-active', b===btn));render();}));
  [search,sort,type].forEach(el=>el.addEventListener('input',render));
  render();
})();
