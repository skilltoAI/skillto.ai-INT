/* Shared schema-driven controls for the SkillTo review page. */
(() => {
  const views = new Map();
  const mediaTypes = new Set(['image', 'video', 'short_video_info']);
  const present = value => value != null && (typeof value !== 'string' || value.trim() !== '') && (!Array.isArray(value) || value.some(item => item != null && item !== ''));
  const printable = value => Array.isArray(value) ? value.map(printable).join(' / ') : value && typeof value === 'object' ? JSON.stringify(value) : String(value ?? '');
  const fieldsFor = table => {
    const fields = [...(table.fields || [])];
    const known = new Set(fields.map(f => f.name));
    for (const row of table.rows || []) for (const [name, value] of Object.entries(row.fields || {})) {
      if (known.has(name)) continue;
      known.add(name);
      fields.push({name, label:name, type:typeof value === 'number' ? 'number' : typeof value === 'boolean' ? 'boolean' : 'text'});
    }
    return fields;
  };
  function viewFor(table) {
    if (!views.has(table.id)) {
      let saved = null;
      try { saved = JSON.parse(localStorage.getItem(`skillto-columns:${table.id}`)); } catch {}
      const fields = fieldsFor(table);
      const defaults = fields.filter(f => !/^(secUid|videoId|source.*Id|profileUrl|coverUrl)$/.test(f.name)).slice(0, 9).map(f => f.name);
      const media = fields.filter(f => f.type === 'short_video_info').map(f => f.name);
      views.set(table.id, {filters:{}, visible:new Set(Array.isArray(saved) ? saved : [...defaults, ...media]), schema:''});
    }
    return views.get(table.id);
  }
  function matches(value, field, rule) {
    if (!rule) return true;
    if (field.type === 'number' || field.type === 'date') {
      if (!rule.min && !rule.max) return true;
      const numeric = field.type === 'number';
      const min = rule.min ? (numeric ? Number(rule.min) : rule.min) : null;
      const max = rule.max ? (numeric ? Number(rule.max) : rule.max) : null;
      if (min != null && max != null && min > max) return false;
      if (!present(value) || (numeric && (typeof value === 'boolean' || !Number.isFinite(Number(value))))) return false;
      const current = numeric ? Number(value) : String(value).slice(0,10);
      return (!numeric || Number.isFinite(current)) && (min == null || current >= min) && (max == null || current <= max);
    }
    if (mediaTypes.has(field.type)) return !rule.value || (rule.value === 'yes' ? present(value) : !present(value));
    if (field.type === 'boolean') return !rule.value || value === (rule.value === 'yes');
    if (field.type === 'single_choice' || field.type === 'multiple_choice') {
      return !rule.value || (Array.isArray(value) ? value.map(String).includes(rule.value) : String(value ?? '') === rule.value);
    }
    return !rule.value || printable(value).toLocaleLowerCase().includes(rule.value.toLocaleLowerCase());
  }
  function fieldControl(field, index, rule) {
    const label = escapeHtml(field.label || field.name), name = escapeHtml(field.name);
    const value = escapeHtml(rule?.value || '');
    let input;
    if (['number','date'].includes(field.type)) {
      const type = field.type === 'date' ? 'date' : 'number';
      input = `<div class="schema-range"><input type="${type}" ${type === 'number' ? 'step="any"' : ''} data-bound="min" value="${escapeHtml(rule?.min || '')}" aria-label="${label}最小值"><span>至</span><input type="${type}" ${type === 'number' ? 'step="any"' : ''} data-bound="max" value="${escapeHtml(rule?.max || '')}" aria-label="${label}最大值"></div>`;
    } else if (mediaTypes.has(field.type) || field.type === 'boolean') {
      const labels = field.type === 'boolean' ? ['是','否'] : ['有','无'];
      input = `<select aria-label="${label}"><option value="">不限</option><option value="yes" ${rule?.value === 'yes' ? 'selected' : ''}>${labels[0]}</option><option value="no" ${rule?.value === 'no' ? 'selected' : ''}>${labels[1]}</option></select>`;
    } else if (['single_choice','multiple_choice'].includes(field.type)) {
      const options = [...new Set([...(field.options || []).map(String), ...state.table.rows.flatMap(row => {
        const v = row.fields[field.name]; return Array.isArray(v) ? v.map(String) : present(v) ? [String(v)] : [];
      })])];
      input = `<select aria-label="${label}"><option value="">不限</option>${options.map(v => `<option value="${escapeHtml(v)}" ${rule?.value === v ? 'selected' : ''}>${escapeHtml(v)}</option>`).join('')}</select>`;
    } else input = `<input type="search" value="${value}" aria-label="${label}" placeholder="包含文字">`;
    return `<div class="schema-field" data-field="${name}"><span id="schema-label-${index}">${label}</span>${input}</div>`;
  }
  function ensureControls() {
    if (!state.table) return;
    const view = viewFor(state.table), fields = fieldsFor(state.table);
    const signature = JSON.stringify(fields);
    let host = document.getElementById('schemaControls');
    if (!host) {
      host = document.createElement('section'); host.id = 'schemaControls';
      document.querySelector('.filters').after(host);
    }
    if (host.dataset.table !== state.table.id || view.schema !== signature) {
      host.dataset.table = state.table.id; view.schema = signature;
      host.innerHTML = `<details class="schema-filter-panel"><summary>字段筛选 <span id="schemaActiveCount"></span></summary><div class="schema-fields">${fields.map((f,i) => fieldControl(f,i,view.filters[f.name])).join('')}</div><p id="schemaFilterError" role="status"></p></details><details class="schema-column-panel"><summary>显示字段</summary><div class="schema-column-actions"><button type="button" data-columns="all">全选</button><button type="button" data-columns="reset">恢复默认</button></div><div class="schema-columns">${fields.map(f=>`<label><input type="checkbox" data-column="${escapeHtml(f.name)}" ${view.visible.has(f.name)?'checked':''}>${escapeHtml(f.label||f.name)}</label>`).join('')}</div></details>`;
      host.oninput = event => {
        const cell = event.target.closest('[data-field]');
        if (!cell) return;
        const current = viewFor(state.table);
        const rule = current.filters[cell.dataset.field] ||= {};
        rule[event.target.dataset.bound || 'value'] = event.target.value;
        renderRows();
      };
      host.onchange = event => {
        if (event.target.dataset.column) {
          const current = viewFor(state.table), name = event.target.dataset.column;
          if (event.target.checked) current.visible.add(name); else current.visible.delete(name);
          saveColumns(current); renderRows();
        } else if (event.target.matches('select')) host.oninput(event);
      };
      host.onclick = event => {
        const mode = event.target.dataset.columns;
        if (!mode) return;
        const current = viewFor(state.table);
        current.visible = new Set(mode === 'all' ? fieldsFor(state.table).map(f=>f.name) : fieldsFor(state.table).filter(f=>! /^(secUid|videoId|source.*Id|profileUrl|coverUrl)$/.test(f.name)).slice(0,9).map(f=>f.name));
        if (mode === 'reset') fieldsFor(state.table).filter(f=>f.type==='short_video_info').forEach(f=>current.visible.add(f.name));
        saveColumns(current);
        host.querySelectorAll('[data-column]').forEach(input=>input.checked=current.visible.has(input.dataset.column));
        renderRows();
      };
    }
    for (const id of ['minVideos','dateFrom','dateTo','llmCategoryFilter']) document.getElementById(id)?.closest('label')?.setAttribute('hidden','');
    for (const id of ['ratioRange','collectRange']) document.getElementById(id)?.setAttribute('hidden','');
    document.getElementById('schemaActiveCount').textContent = Object.values(view.filters).filter(r=>r.value || r.min || r.max).length || '';
    const inverted = fields.filter(f=>['number','date'].includes(f.type)).filter(f=>{
      const r=view.filters[f.name]; return r?.min && r?.max && (f.type==='number'?Number(r.min)>Number(r.max):r.min>r.max);
    });
    document.getElementById('schemaFilterError').textContent = inverted.length ? `${inverted.map(f=>f.label||f.name).join('、')}：最小值不能大于最大值` : '';
  }
  function saveColumns(view) {
    try { localStorage.setItem(`skillto-columns:${state.table.id}`, JSON.stringify([...view.visible])); }
    catch { notify('显示字段偏好未保存，仅本次有效',true); }
  }
  filteredRows = function() {
    if (!state.table) return [];
    const fields=fieldsFor(state.table), view=viewFor(state.table);
    const query=$('#searchInput').value.trim().toLocaleLowerCase(), tag=$('#tagFilter').value;
    return state.table.rows.filter(row => (!query || fields.some(f=>printable(row.fields[f.name]).toLocaleLowerCase().includes(query)))
      && (!tag || row.tagIds?.includes(tag)) && fields.every(f=>matches(row.fields[f.name],f,view.filters[f.name])))
      .sort((a,b)=>{
        const x=a.fields[state.sort.field],y=b.fields[state.sort.field];
        if (x==null) return y==null?0:1; if(y==null) return -1;
        return state.sort.direction*(typeof x==='number'?x-y:printable(x).localeCompare(printable(y),'zh-CN'));
      });
  };
  function mediaUrl(value) {
    if (typeof value !== 'string') return '';
    if (value.startsWith('/') && !value.startsWith('//')) return value;
    return safeUrl(value);
  }
  function cellHtml(row,field) {
    const value=row.fields[field.name];
    if (field.candidateGroup && field.type==='image') return renderCandidateCell(row,field).replace(/^<td[^>]*>|<\/td>$/g,'');
    if (field.type==='short_video_info') return videoPreview({...row,fields:{...row.fields,recentVideos:Array.isArray(value)?value:[]}});
    if (field.type==='image') {
      const src=mediaUrl(value); return src?`<img class="video-thumb" loading="lazy" src="${escapeHtml(src)}" alt="${escapeHtml(field.label||field.name)}">`:'<span class="muted">无</span>';
    }
    if (field.type==='video') {
      const src=mediaUrl(value); return src?`<video class="schema-video" controls preload="none" src="${escapeHtml(src)}"></video>`:'<span class="muted">无</span>';
    }
    if (!present(value)) return '<span class="muted">—</span>';
    if (field.type==='number') return formatNumber(value);
    if (field.type==='boolean') return value===true?'是':value===false?'否':'—';
    if (field.type==='date') return escapeHtml(formatDate(value));
    const text=printable(value), link=mediaUrl(value);
    if (link) return `<a href="${escapeHtml(link)}" target="_blank" rel="noopener noreferrer">${escapeHtml(text)}</a>`;
    return text.length>140?`<details class="schema-long-text"><summary>${escapeHtml(text.slice(0,100))}…</summary><p>${escapeHtml(text)}</p></details>`:escapeHtml(text);
  }
  renderRows = function() {
    if (!state.table) return;
    ensureControls();
    const fields=fieldsFor(state.table).filter(f=>viewFor(state.table).visible.has(f.name));
    const table=$('#dataTable');
    table.classList.remove('llm-table','benchmark-table','video-table','edit-table','fusion-table');
    table.classList.add('schema-table');
    $('#tableHead').innerHTML='<tr>'+fields.map(f=>`<th><button data-sort="${escapeHtml(f.name)}">${escapeHtml(f.label||f.name)} ↕</button></th>`).join('')+'<th>标签</th><th>评分</th><th>编辑</th></tr>';
    const rows=filteredRows();
    $('#resultCount').textContent=`${rows.length} / ${state.table.rows.length} 条记录`;
    $('#rows').innerHTML=rows.map(row=>`<tr data-id="${escapeHtml(row.id)}">`+fields.map(f=>`<td class="${f.type==='number'?'num':''}">${cellHtml(row,f)}</td>`).join('')+`<td><div class="tag-list">${(row.tagIds||[]).map(id=>state.table.tags.find(t=>t.id===id)).filter(Boolean).map(t=>`<span class="tag">${escapeHtml(t.name)}</span>`).join('')}</div><button class="tag-edit" data-action="assign">编辑标签</button></td><td><button class="score-button" data-action="review">${row.rating?.score==null?'未评分':row.rating.score+' / 5'}</button></td><td><button class="icon-button" data-action="edit" title="编辑记录">⋯</button></td></tr>`).join('')||`<tr><td colspan="${fields.length+3}" class="empty">没有符合条件的记录</td></tr>`;
  };
  const previousSelect=selectTable;
  selectTable=async function(entry) {
    await previousSelect(entry);
    if (!fieldsFor(state.table).some(f=>f.name===state.sort.field)) state.sort={field:fieldsFor(state.table)[0]?.name,direction:1};
    renderRows();
  };
  document.addEventListener('DOMContentLoaded',()=>{
    $('#clearFilters').addEventListener('click',()=>{
      if (!state.table) return;
      const view=viewFor(state.table); view.filters={}; view.schema=''; renderRows();
    });
    // The existing media dialog reads recentVideos; resolve other schema media lists here.
    $('#rows').addEventListener('click',event=>{
      const button=event.target.closest('[data-action="videos"]');
      if (!button) return;
      const row=state.table.rows.find(r=>r.id===button.closest('tr').dataset.id);
      const fields=fieldsFor(state.table).filter(f=>f.type==='short_video_info');
      if (fields.length===1 && fields[0].name!=='recentVideos') openVideos({...row,fields:{...row.fields,recentVideos:row.fields[fields[0].name]||[]}});
    });
  });
})();
