// 即梦 Agent 模式生图：上传参考图 → 调 creation_agent 让 Agent 理解并生成 → 轮询拿图
const REF_PATHS = __REF_PATHS__;   // 参考图路径数组（按传入顺序 = prompt 里的「图1/图2/图3」；空数组 = 纯文生图）
const PROMPT = __PROMPT__;
const MODEL_REQ_KEY = __MODEL_REQ_KEY__;   // 可选：指定图片模型（localStorage 注入 + 请求体带 model_req_key）
const MODEL_NAME = __MODEL_NAME__;
// 分格图比例（空=沿用 intelligent_ratio 自动；非空则显式指定 image_ratio）
// image_ratio 枚举（2026-08-21 实测自页面 __image_generate_model_config__ 的 image_ratio_sizes.ratio_type，2k 分辨率下）：
//   1=1:1(2048×2048)  2=3:4(1728×2304)  3=16:9(2560×1440)  4=4:3(2304×1728)  5=9:16(1440×2560)
//   6=2:3  7=3:2  8=7:3；jimeng_generate.py 的 IMAGE_RATIO=2=3:4 与之一致（交叉验证）。
const RATIO = __RATIO__;
const RATIO_ENUM = { '1:1': 1, '3:4': 2, '16:9': 3, '4:3': 4, '9:16': 5 };

const sleep = (ms) => new Promise(r => setTimeout(r, ms));
const TASK_SPACE = __TASK_SPACE__;
await useOrCreateTaskSpace(TASK_SPACE);
const tabs = await listTabs();
// 2026-08-20 修复：导航到 generate/agentic 生成页（home 页参考上传区含 2 个 file input 且注入不触发
// submit_audit_job → upload timeout；generate?type=agentic 页只有 1 个干净 input，注入直达 submit_audit_job）
await openOrReuseTab('https://jimeng.jianying.com/ai-tool/generate?type=agentic', { wait: true, timeout: 40 });
// 轮询等待页面加载完成 + 参考上传区出现
for (let i = 0; i < 20; i++) {
  await sleep(1000);
  const ok = await js("document.readyState === 'complete' && !!document.body");
  if (ok) break;
}
const ctx = await js(`(() => ({
  webId: (document.cookie.match(/(?:^|; )_tea_web_id=([^;]*)/) || [])[1] || null,
  ws: (location.href.match(/workspace=(\\d+)/) || [])[1] || null
}))()`);
if (!ctx.webId) throw new Error('no_webid');

// 指定模型（2026-08-19 抓包实测）：模型在 content_parts 的 generate_args 条目里（见下）。
// 注意不是 localStorage / body.model_req_key / metrics_extra.modelReqKey —— 那些都被后端忽略。

// 0-2) 上传参考图（多图支持 + 自动重试，2026-08-20 / 2026-09-16）：上传链路间歇性抖动（注入后 submit_audit_job
//      偶发不返回），每轮 reload 拿干净上传区 → 逐张 drop 注入 → 等 audit，最多 3 轮（已成功的张数续传不重传）。
//      多图按 REF_PATHS 顺序逐张上传，uris[i] 对应 REF_PATHS[i]。
const REF_MIMES = { png: 'image/png', jpg: 'image/jpeg', jpeg: 'image/jpeg', webp: 'image/webp', gif: 'image/gif' };
const fileMetas = [];
const uris = [];
let name = '';
if (REF_PATHS.length) {
  const { readFileSync } = await import('node:fs');
  for (const p of REF_PATHS) {
    const fn = p.split('/').pop();
    const ext = (fn.split('.').pop() || '').toLowerCase();
    fileMetas.push({ b64: readFileSync(p).toString('base64'), name: fn, mime: REF_MIMES[ext] || 'image/jpeg' });
  }
  name = fileMetas[0].name;
  const waitReady = async () => { for (let i=0;i<20;i++){ await sleep(1000); const ok = await js("document.readyState==='complete' && !!document.body"); if(ok) return; } };
  // 2026-09-09 修复：即梦把参考图上传从「常驻 file input」改为「点击加号→原生文件选择器」，DOM 里不再有
  // input[type=file]（实测 fileInputCount=0）。改等上传容器 [class^="reference-upload-"] 出现即可，
  // 注入通道改为在容器上派发 drop 事件（DragEvent+DataTransfer 带 File）触发 SDK 上传（见下 inject）。
  const waitInput = async () => { for (let i=0;i<15;i++){ if (await js("!!document.querySelector('[class^=\"reference-upload-\"]')")) return true; await sleep(1000); } return false; };
  // 装 XHR 拦截（reload 后页面上下文重置，每次重装）
  const installHook = () => js(`(() => {
      window.__auditUris = [];
      const oo = XMLHttpRequest.prototype.open, os = XMLHttpRequest.prototype.send;
      XMLHttpRequest.prototype.open = function(m,u,...r){ this.__jmUrl=String(u); return oo.apply(this,[m,u,...r]); };
      XMLHttpRequest.prototype.send = function(b){ if(this.__jmUrl && this.__jmUrl.indexOf('submit_audit_job')!==-1){ try{const d=JSON.parse(String(b)); if(d&&Array.isArray(d.uri_list)) window.__auditUris.push(...d.uri_list);}catch(e){} } return os.apply(this, arguments); };
    })()`);
  for (let attempt = 0; attempt < 3 && uris.length < fileMetas.length; attempt++) {
    await js('location.reload()'); await sleep(8000); await waitReady();
    if (!await waitInput()) continue;
    await installHook();
    for (let k = uris.length; k < fileMetas.length; k++) {   // 从上次成功的张数续传
      const meta = fileMetas[k];
      const before = await js('window.__auditUris.length');
      const inject = await js(`(() => {
        try {
          const b64 = ${JSON.stringify(meta.b64)};
          const bin = atob(b64); const bytes = new Uint8Array(bin.length);
          for (let i=0;i<bin.length;i++) bytes[i]=bin.charCodeAt(i);
          const file = new File([bytes], ${JSON.stringify(meta.name)}, {type: ${JSON.stringify(meta.mime)}});
          const dt = new DataTransfer(); dt.items.add(file);
          // 2026-09-09 修复：即梦上传区现无 file input（fileInputCount=0），改用拖拽 drop 事件把 File 注入上传容器。
          // 实测 dispatch dragenter/dragover/drop 后 SDK 自行走 submit_audit_job 流程，成功拿到 store_uri。
          const target = document.querySelector('[class^="reference-upload-"]') || document.body;
          const opts = { dataTransfer: dt, bubbles: true, cancelable: true };
          target.dispatchEvent(new DragEvent('dragenter', opts));
          target.dispatchEvent(new DragEvent('dragover', opts));
          target.dispatchEvent(new DragEvent('drop', opts));
          return {ok:true};
        } catch(e) { return {ok:false, err:String(e)}; }
      })()`);
      if (!inject.ok) break;
      for (let i=0;i<40;i++) {
        await sleep(1000);
        const n = await js('window.__auditUris.length');
        if (n > before) { uris.push(await js(`window.__auditUris[${before}]`)); break; }
      }
      if (uris.length <= k) break;   // 这张没传上去 → 跳出，外层 reload 重试
    }
  }
  if (uris.length < fileMetas.length) throw new Error(`upload timeout: ${uris.length}/${fileMetas.length} after 3 attempts`);
  cliLog('URI:' + uris.join(','));
}

// 3) 调 Agent 模式生成（带自动重试：SSE 流瞬时失败 ret:"7057" 等 → 重新发起会话，最多 3 次）
const workspaceId = ctx.ws ? parseInt(ctx.ws) : 19374684610316;
const babiInner = { feature_entrance:'to-generate', feature_entrance_detail:'to-generate-creation_agent',
  feature_key:'creation_agent', scenario:'image_video_generation', edit_type:'agent', tool_id:'agent',
  sub_tool_id:'agent', tab_name:'agent', enter_from:'agent', template_id:'', scene_lv1:'agent', scene_lv2:'agent' };
const babi = encodeURIComponent(encodeURIComponent(JSON.stringify(babiInner)));

async function runAgentConversation() {
  const convId = crypto.randomUUID();
  const msgId = crypto.randomUUID();
  const content_parts = [];
  for (let i = 0; i < uris.length; i++) {
    content_parts.push({ file: { uri: uris[i], file_type: 5, file_name: fileMetas[i].name, url: 'blob:https://jimeng.jianying.com/' + crypto.randomUUID(), id: crypto.randomUUID() } });
  }
  content_parts.push({ text: PROMPT, is_referenced: false });
  // 模型选择 = content_parts 追加 generate_args 条目（抓包自网页端 Agent 模式 + 图片5.0 Lite）
  // RATIO 非空 → 显式 image_ratio + 关智能比例；空 → 保留 intelligent_ratio:true（默认行为不变）
  if (MODEL_REQ_KEY) {
    content_parts.push({ generate_args: { image_args: RATIO
      ? { image_resolution_type: '2k', model_key: MODEL_REQ_KEY, image_ratio: RATIO_ENUM[RATIO], intelligent_ratio: false }
      : { image_resolution_type: '2k', model_key: MODEL_REQ_KEY, intelligent_ratio: true } } });
  }
  const body = {
    conversation_id: convId,
    messages: [{ author: { role: 'user' },
      metadata: { is_visually_hidden_from_conversation:false, conversation_id: convId, parent_message_id:'',
        metrics_extra: JSON.stringify({ userMessageId: msgId, prompt: PROMPT, isAddImage: uris.length ? 1 : 0, conversationId:convId, hasRejectedAudit:0, enterFrom:'new_conversation', referenceCnt: uris.length, position:'page_bottom_box' }) },
      id: msgId, content: { content_type:'', content_parts: content_parts }, create_time: Date.now() }],
    version: '3.0.0', workspace_id: workspaceId
    // 注意：UI 请求里的 extra_info(cloud_agent_experiment) 不能带 —— 带上后 SSE 只回握手+结束、不处理消息（2026-08-19 实测）
  };
  const url = '/mweb/v1/creation_agent/v2/conversation?aid=513695&device_platform=web&region=cn&webId=' + ctx.webId +
    '&da_version=3.1.3&os=mac&web_version=7.5.0&aigc_features=app_lip_sync&generate_id=gen-' + crypto.randomUUID() + '&babi_param=' + babi;
  // 后台读 SSE 流
  await js(`(() => {
    window.__sseBuf = '';
    window.__sseDone = false;
    const url = ${JSON.stringify(url)};
    const bodyStr = ${JSON.stringify(JSON.stringify(body))};
    (async () => {
      try {
        const resp = await fetch(url, {method:'POST', headers:{'Content-Type':'application/json','pf':'7','x-secsdk-sign-config':'1_5000'}, body: bodyStr, credentials:'include'});
        const reader = resp.body.getReader();
        const dec = new TextDecoder('utf-8');
        while (true) { const {done, value} = await reader.read(); if (done) break; window.__sseBuf += dec.decode(value, {stream:true}); }
      } catch(e) { window.__sseBuf += 'ERR:' + String(e); }
      window.__sseDone = true;
    })();
    return 'started';
  })()`);
  let sseText = '';
  for (let i = 0; i < 150; i++) {
    await sleep(1000);
    const done = await js('window.__sseDone');
    if (done) { sseText = await js('window.__sseBuf'); break; }
  }
  if (!sseText) sseText = await js('window.__sseBuf');
  return sseText;
}

// 4) 解析 submit_id + 自动重试（2026-08-20：7057 err stream receive 等瞬时失败重跑会话）
// 2026-08-15 即梦 agent 协议改版：submit_id 嵌在多层转义 JSON（\"submit_id\\\":\\\"...），
// 旧正则 /submit_id["\:]+/ 匹配不到。改用宽松分隔符 [^0-9a-f]* 兼容单/双转义。
let submitIds = [];
let sseText = '';
for (let attempt = 0; attempt < 3 && !submitIds.length; attempt++) {
  sseText = await runAgentConversation();
  const allM = [...sseText.matchAll(/submit_id[^0-9a-f]*([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})/g)];
  submitIds = [...new Set(allM.map(x => x[1]))];
  if (!submitIds.length) {
    cliLog('AGENT_RETRY:' + (attempt + 1) + ' 未提取到 submit_id: ' + sseText.slice(-300));
    await sleep(3000);
  }
}
if (!submitIds.length) {
  cliLog('RESULT_JSON:' + JSON.stringify({ status: 'error', stage: 'agent', errmsg: '未从 SSE 提取到 submit_id（3 次重试后）: ' + sseText.slice(-2000) }));
  process.exit(0);
}
cliLog('SUBMIT_ID:' + submitIds.join(','));

// 6) 轮询拿图
const XHR_SRC = `(url, body) => new Promise((resolve) => {
  const xhr = new XMLHttpRequest();
  xhr.open('POST', url, true);
  xhr.setRequestHeader('Content-Type', 'application/json');
  xhr.setRequestHeader('pf', '7');
  xhr.setRequestHeader('device-time', String(Math.floor(Date.now() / 1000)));
  xhr.setRequestHeader('x-secsdk-sign-config', '1_5000');
  xhr.withCredentials = true;
  xhr.onreadystatechange = () => { if (xhr.readyState === 4) resolve(xhr.responseText); };
  xhr.onerror = () => resolve(null);
  xhr.send(body);
})`;
async function api(path, payload) {
  const u = '/mweb/v1/' + path + '?aid=513695&device_platform=web&region=cn&webId=' + ctx.webId + '&da_version=3.3.22&os=mac&web_version=7.5.0&aigc_features=app_lip_sync';
  const raw = await js('(' + XHR_SRC + ')(' + JSON.stringify(u) + ', ' + JSON.stringify(JSON.stringify(payload)) + ')');
  if (raw === null) throw new Error(path + ' network error');
  return JSON.parse(raw);
}
let urls = [];
let modelUsed = 'unknown';
// 2026-08-15 实测：agent 模式 status 45（生成中）会持续几分钟，需更久轮询（90×5s≈7.5min）
// 2026-08-19 多张支持：批量时 SSE 可能含多个 submit_id，全部轮询收集，直到全部完成或超时
const pending = [...submitIds];
let lastModel = 'unknown';
for (let i = 0; i < 120 && pending.length; i++) {
  await sleep(5000);
  let poll;
  try { poll = await api('get_history_by_ids', { submit_ids: pending }); } catch (e) { continue; }
  for (const sid of [...pending]) {
    const rec = (poll.data || {})[sid];
    if (!rec) continue;
    if (rec.status === 50) {
      const recStr = JSON.stringify(rec);
      const mk = recStr.match(/model_req_key\\?"?\s*[:=]\s*\\?"([a-z0-9_]+)/i);
      if (mk) lastModel = mk[1];
      for (const it of rec.item_list || []) for (const li of ((it.image || {}).large_images || [])) if (li.image_url) urls.push(li.image_url);
      pending.splice(pending.indexOf(sid), 1);
    } else if (rec.status === 30 || rec.status === 40) {
      pending.splice(pending.indexOf(sid), 1);
    }
  }
}
cliLog('MODEL_USED:' + lastModel);
cliLog('REC_STRUCT:' + JSON.stringify({ submit_ids: submitIds.length, got: urls.length }));
if (urls.length) {
  cliLog('RESULT_JSON:' + JSON.stringify({ status: 'ok', urls: urls, submit_id: submitIds[0] }));
} else {
  cliLog('RESULT_JSON:' + JSON.stringify({ status: 'error', stage: 'poll', errmsg: '生成超时或失败' }));
}
process.exit(0);
