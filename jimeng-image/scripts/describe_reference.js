// 即梦识图：上传参考图 → 调 Agent 模式让 agent 描述构图/光照/视角 → 提取文字
// 用法: ego-browser nodejs < describe_ref.js (参考图路径写死在 REF_PATH)
const sleep = (ms) => new Promise(r => setTimeout(r, ms));

const TASK_SPACE = __TASK_SPACE__;
await useOrCreateTaskSpace(TASK_SPACE);
const tabs = await listTabs();
if (!tabs.some(t => (t.url || '').includes('jimeng.jianying.com'))) {
  await openOrReuseTab('https://jimeng.jianying.com/ai-tool/generate?enter_from=ai_feature&from_page=explore&ai_feature_name=image', { wait: true, timeout: 30 });
  await sleep(5000);
}

const ctx = await js(`(() => ({
  webId: (document.cookie.match(/(?:^|; )_tea_web_id=([^;]*)/) || [])[1] || null,
  ws: (location.href.match(/workspace=(\\d+)/) || [])[1] || null
}))()`);
if (!ctx.webId) throw new Error('no_webid');

// 0) 清空残留参考图
const refCount = await js("document.querySelectorAll('.reference-item-V8Tkbi').length");
if (refCount > 1) {
  cliLog('CLEAR_REFS:' + refCount);
  await js('location.reload()');
  await sleep(8000);
}

// 1) 装 XHR 拦截
await js(`(() => {
  window.__auditUris = [];
  if (XMLHttpRequest.prototype.__jmPatched) return 'already';
  XMLHttpRequest.prototype.__jmPatched = true;
  const oo = XMLHttpRequest.prototype.open, os = XMLHttpRequest.prototype.send;
  XMLHttpRequest.prototype.open = function(m,u,...r){ this.__jmUrl=String(u); return oo.apply(this,[m,u,...r]); };
  XMLHttpRequest.prototype.send = function(b){ if(this.__jmUrl && this.__jmUrl.indexOf('submit_audit_job')!==-1){ try{const d=JSON.parse(String(b)); if(d&&Array.isArray(d.uri_list)) window.__auditUris.push(...d.uri_list);}catch(e){} } return os.apply(this, arguments); };
})()`);

// 2) 上传参考图
const REF_PATH = __REF_PATH__;
const { readFileSync } = await import('node:fs');
const b64 = readFileSync(REF_PATH).toString('base64');
const name = REF_PATH.split('/').pop();
const inject = await js(`(() => {
  try {
    const b64 = ${JSON.stringify(b64)};
    const bin = atob(b64); const bytes = new Uint8Array(bin.length);
    for (let i=0;i<bin.length;i++) bytes[i]=bin.charCodeAt(i);
    const file = new File([bytes], ${JSON.stringify(name)}, {type:'image/jpeg'});
    const dt = new DataTransfer(); dt.items.add(file);
    // 2026-09-16 修复：即梦已移除常驻 file input（改为点击加号→原生文件选择器），旧 input.files 注入必报 no input。
    // 与 agent_generate.js 同款通道：往 [class^="reference-upload-"] 容器派发 dragenter/dragover/drop，SDK 自行上传。
    const target = document.querySelector('[class^="reference-upload-"]') || document.body;
    const opts = { dataTransfer: dt, bubbles: true, cancelable: true };
    target.dispatchEvent(new DragEvent('dragenter', opts));
    target.dispatchEvent(new DragEvent('dragover', opts));
    target.dispatchEvent(new DragEvent('drop', opts));
    return {ok:true};
  } catch(e) { return {ok:false, err:String(e)}; }
})()`);
if (!inject.ok) throw new Error('inject fail: ' + JSON.stringify(inject));
let uri = null;
for (let i=0;i<30;i++) { await sleep(1000); const n = await js('window.__auditUris.length'); if (n>0) { uri = await js('window.__auditUris[0]'); break; } }
if (!uri) throw new Error('upload timeout');
cliLog('URI:' + uri);

// 3) 调 Agent 模式识图
const workspaceId = ctx.ws ? parseInt(ctx.ws) : 19374684610316;
const convId = crypto.randomUUID();
const msgId = crypto.randomUUID();
const babiInner = { feature_entrance:'to-generate', feature_entrance_detail:'to-generate-creation_agent',
  feature_key:'creation_agent', scenario:'image_video_generation', edit_type:'agent', tool_id:'agent',
  sub_tool_id:'agent', tab_name:'agent', enter_from:'agent', template_id:'', scene_lv1:'agent', scene_lv2:'agent' };
const babi = encodeURIComponent(encodeURIComponent(JSON.stringify(babiInner)));

const content_parts = [
  { file: { uri: uri, file_type: 5, file_name: name, url: 'blob:https://jimeng.jianying.com/' + crypto.randomUUID(), id: crypto.randomUUID() } },
  { text: '请详细描述这张参考图的视觉特征，分点输出：1主体内容（画面主体是什么、前景中景背景空间层次）2构图逻辑（主体位置、元素布局、留白、对称错落、分隔）3元素密度（简洁还是丰富、有无堆砌）4色彩配色（主色调、饱和度、冷暖、明度、配色搭配）5对比度（高对比/低对比/柔和）6材质笔触（油画/水彩/厚涂/扁平、颗粒感、肌理质感）7皮肤质感（若主体是人物：红润通透/哑光/白皙/光泽）8光照（光的方向、明暗、光线质感、色温）9镜头景深（焦段、前景背景虚化、清晰范围）10视角景别（平视俯视仰视、特写近景中景全景远景）11透视（一点/两点/三点透视、畸变）12线条风格（手绘柔线/硬边/无线条/轮廓线）13艺术风格（古典/现代/卡通/写实/印象派/厚涂油画）14文字排版（有无文字、字体类型、位置、颜色、手写/印刷）。只描述不要生成图片。', is_referenced: false }
];
const body = {
  conversation_id: convId,
  messages: [{ author: { role: 'user' },
    metadata: { is_visually_hidden_from_conversation:false, conversation_id: convId, parent_message_id:'',
      metrics_extra: JSON.stringify({ userMessageId: msgId, prompt:'描述参考图', isAddImage:1, conversationId:convId, hasRejectedAudit:0, enterFrom:'new_conversation', referenceCnt:1, position:'page_bottom_box' }) },
    id: msgId,
    content: { content_type:'', content_parts: content_parts },
    create_time: Date.now() }],
  version: '3.0.0',
  workspace_id: workspaceId
};

const url = '/mweb/v1/creation_agent/v2/conversation?aid=513695&device_platform=web&region=cn&webId=' + ctx.webId +
  '&da_version=3.1.3&os=mac&web_version=7.5.0&aigc_features=app_lip_sync&generate_id=gen-' + crypto.randomUUID() + '&babi_param=' + babi;

// 在页面里启动后台读流（不 await，避免 js() CDP evaluate 超时），累积到 window.__sseBuf
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
      while (true) {
        const {done, value} = await reader.read();
        if (done) break;
        window.__sseBuf += dec.decode(value, {stream:true});
      }
    } catch(e) { window.__sseBuf += 'ERR:' + String(e); }
    window.__sseDone = true;
  })();
  return 'started';
})()`);

// 轮询读流进度（最多 90 秒）
let sseText = '';
for (let i = 0; i < 90; i++) {
  await sleep(1000);
  const done = await js('window.__sseDone');
  if (done) { sseText = await js('window.__sseBuf'); break; }
}
if (!sseText) sseText = await js('window.__sseBuf');

cliLog('SSE_LEN:' + sseText.length);
cliLog('SSE_FULL:' + JSON.stringify(sseText));
process.exit(0);
