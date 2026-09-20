#!/usr/bin/env python3
"""即梦(jimeng) AI 生图：通过 ego-lite 浏览器（复用其登录态），页面内 XHR 自动带字节系签名。

用法:
  python3 jimeng_generate.py "提示词" [--count 1] [--model 5.0] [--out ./jimeng_output] [--timeout 240]
  python3 jimeng_generate.py "提示词" --ref 图1.png --ref 图2.jpg   # 一张或多张参考图 + 文案

参考图模式（2026-08-13 抓包实测）：
  - 上传：注入参考文件到页面参考输入框 → 页面 SDK 走 get_upload_token→ApplyImageUpload→TOS→CommitImageUpload→submit_audit_job；
    脚本拦截 submit_audit_job 请求体拿 store_uri（uri_list[0]），无需复制 TOS 签名。
  - 生成：image_base_component.generate_type="blend" + abilities.blend.ability_list（每参考图一个
    name="byte_edit" 条目，image_uri_list=[uri] / image_list=[{image_uri:uri,...}]）+ prompt 前加 "##"×N
    + babi_param feature_key="to_image_referenceimage" / extra_param.generate_type="i2i"。
  - 参考图默认模型 5.0 Pro（抓包时 UI 默认即此，pro 下 i2i 结构实测成功），分辨率 1296×1728 "1.5k"。

输出: stdout 逐行 JSON。成功: {"status":"ok","count":N,"images":[...]}
"""
import argparse
import base64
import io
import json
import re
import subprocess
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

# ---- 模型映射（来自页面 __image_generate_model_config__，2026-08-04 实测）----
MODEL_MAP = {
    "4.0": "high_aes_general_v40",
    "4.1": "high_aes_general_v41",
    "4.5": "high_aes_general_v40l",
    "4.6": "high_aes_general_v42",
    "4.7": "high_aes_general_v43",
    "5.0": "high_aes_general_v50",
    "5.0 Pro": "high_aes_general_v50p_large",
}
DEFAULT_MODEL = "5.0 Pro"  # 默认模型（文生图 + 参考图都默认 5.0 Pro）；额度不足自动 fallback 到 4.7
DEFAULT_REF_MODEL = "5.0 Pro"  # 参考图模式默认模型（与 DEFAULT_MODEL 一致）
FALLBACK_MODEL_KEY = MODEL_MAP["4.7"]

# ---- 固定参数（3:4）----
WIDTH, HEIGHT = 1728, 2304       # 文生图 3:4 @ 2K
RESOLUTION = "2k"
REF_WIDTH, REF_HEIGHT = 1296, 1728  # 参考图 3:4 @ 1.5K（5.0 Pro i2i 抓包实测参数）
REF_RESOLUTION = "1.5k"
IMAGE_RATIO = 2                  # 3:4 枚举值

EGO = str(Path.home() / ".local" / "bin" / "ego-browser")
JIMENG_HOME = "https://jimeng.jianying.com/ai-tool/home?type=image"

NODE_JS_TEMPLATE = r"""
const PROMPT = __PROMPT__;
const COUNT = __COUNT__;
const TIMEOUT_S = __TIMEOUT__;
const REF_IMAGES = __REF_IMAGES__;   // [{b64,name,mime}] 参考图
const REF_STRENGTH = __STRENGTH__;   // byte_edit 参考图强度（默认 0.5，越高越贴参考图）

let MODEL = __MODEL__;
const FALLBACK_MODEL = __FALLBACK_MODEL__;
const WIDTH = 1728, HEIGHT = 2304, RESOLUTION = '2k', IMAGE_RATIO = 2;
const REF_WIDTH = 1296, REF_HEIGHT = 1728, REF_RESOLUTION = '1.5k';

const withTimeout = (p, ms, label) => Promise.race([
  p,
  new Promise((_, rej) => setTimeout(() => rej(new Error((label || 'op') + ' timeout')), ms))
]);

// 注意：不能用 ego 的 wait() —— 它等页面空闲，即梦页持续有动画/网络活动，永远不空闲会挂死
const sleep = (ms) => new Promise(r => setTimeout(r, ms));

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

function babi(hasRef) {
  const isRef = !!hasRef;
  const inner = { feature_entrance: isRef ? 'to-generate' : 'makesame',
    feature_entrance_detail: isRef ? 'to-generate-referenceimage-byte_edit' : 'makesame-' + MODEL,
    feature_key: isRef ? 'to_image_referenceimage' : 'aigc_to_image',
    scenario: 'image_video_generation', edit_type: 'tool',
    tool_id: 'tool_image', sub_tool_id: 'tool_image', tab_name: 'tool', enter_from: 'tool',
    template_id: '', scene_lv1: 'tool', scene_lv2: 'tool_image',
    extra_param: { model_id: MODEL, generate_type: isRef ? 'i2i' : '1' } };
  return encodeURIComponent(encodeURIComponent(JSON.stringify(inner)));
}

function buildPayload(prompt, count, workspaceId, refUris) {
  const submitId = crypto.randomUUID();
  const compId = crypto.randomUUID();
  const isRef = Array.isArray(refUris) && refUris.length > 0;
  // 参考图模式：core_param 里的 prompt 前面加 "##"×N（抓包实测 UI 行为）
  const finalPrompt = isRef ? '##'.repeat(refUris.length) + prompt : prompt;
  // 参考图模式 core_param 精确对齐网页端（抓包实测）：无 negative_prompt、无 seed
  const coreParam = { type: '', id: crypto.randomUUID(), model: MODEL, prompt: finalPrompt,
    ...(isRef ? {} : { negative_prompt: '', seed: Math.floor(Math.random() * 2 ** 31) }),
    sample_strength: 0.5,
    image_ratio: IMAGE_RATIO,
    large_image_info: { type: '', id: crypto.randomUUID(),
      height: isRef ? REF_HEIGHT : HEIGHT, width: isRef ? REF_WIDTH : WIDTH,
      resolution_type: isRef ? REF_RESOLUTION : RESOLUTION },
    intelligent_ratio: false, generate_type: 0 };
  let abilities;
  if (isRef) {
    // 参考图模式：blend 能力，每个参考图一个 byte_edit 条目（抓包实测 2026-08-13）
    const abilityList = refUris.map(u => ({
      type: '', id: crypto.randomUUID(),
      name: 'byte_edit',
      image_uri_list: [u],
      image_list: [{ type: 'image', id: crypto.randomUUID(), source_from: 'upload', platform_type: 1,
        name: '', image_uri: u, width: 0, height: 0, format: '', title: '', uri: u }],
      strength: REF_STRENGTH
    }));
    abilities = { type: '', id: crypto.randomUUID(),
      blend: { type: '', id: crypto.randomUUID(), min_features: [],
        core_param: coreParam,
        ability_list: abilityList,
        prompt_placeholder_info_list: [{ type: '', id: crypto.randomUUID(), ability_index: 0 }],
        postedit_param: { type: '', id: crypto.randomUUID(), generate_type: 0 } },
      gen_option: { type: '', id: crypto.randomUUID(), gen_count: count, generate_all: false } };
  } else {
    // 文生图模式：generate 能力（原实现）
    abilities = { type: '', id: crypto.randomUUID(),
      generate: { type: '', id: crypto.randomUUID(), core_param: coreParam },
      gen_option: { type: '', id: crypto.randomUUID(), gen_count: count, generate_all: false } };
  }
  const draft = { type: 'draft', id: crypto.randomUUID(), min_version: '3.0.2', min_features: [],
    is_from_tsn: true, version: '3.3.26', main_component_id: compId,
    component_list: [{ type: 'image_base_component', id: compId, min_version: '3.0.2', aigc_mode: 'workbench',
      metadata: { type: '', id: crypto.randomUUID(), created_platform: 3, created_platform_version: '',
        created_time_in_ms: String(Date.now()), created_did: '' },
      generate_type: isRef ? 'blend' : 'generate',
      abilities: abilities }] };
  return { extend: { root_model: MODEL, workspace_id: workspaceId }, submit_id: submitId,
    metrics_extra: JSON.stringify({ promptSource: 'custom', generateCount: count, enterFrom: 'click',
      position: 'page_bottom_box', isBoxSelect: false, isCutout: false, hasRejectedAudit: 0,
      generateId: submitId, isRegenerate: false }),
    draft_content: JSON.stringify(draft), http_common_info: { aid: 513695 } };
}

// 参考图上传：在页面上下文装拦截器（nodejs 上下文没有 window/XMLHttpRequest，页面操作必须走 js()），
// 把文件注入页面参考输入框，页面 SDK 自动走 TOS 上传；
// 拦截 submit_audit_job 请求体拿 store_uri（uri_list[0]），避免复制 TOS 签名逻辑
async function uploadRefImages(refs) {
  if (!refs.length) return [];
  // 0) 仅当残留参考图累积(>1)才 reload 清空：复用 tab 会累积参考图（实测 12 个后注入失效，
  //    input.files 被 React 清空）。干净状态(<=1)直接上传——无条件 reload 反而把稳定页面破坏
  //    （reload 后 input 短暂消失，注入失败）
  const refCount = await js("document.querySelectorAll('.reference-item-V8Tkbi').length");
  if (refCount > 1) {
    cliLog('CLEAR_REFS:' + refCount);
    await js('location.reload()');
    await sleep(8000);
  }
  // 1) 页面里安装 XHR 拦截（幂等：只装一次；每次运行都重置 uri 收集，防止复用 tab 残留旧数据）
  await js(`(() => {
    window.__jmAuditUris = [];
    if (XMLHttpRequest.prototype.__jmPatched) return 'already';
    XMLHttpRequest.prototype.__jmPatched = true;
    const origOpen = XMLHttpRequest.prototype.open;
    const origSend = XMLHttpRequest.prototype.send;
    XMLHttpRequest.prototype.open = function (method, url, ...rest) {
      this.__jmUrl = String(url);
      return origOpen.apply(this, [method, url, ...rest]);
    };
    XMLHttpRequest.prototype.send = function (body) {
      const self = this;
      if (self.__jmUrl && self.__jmUrl.indexOf('submit_audit_job') !== -1) {
        try {
          const d = JSON.parse(String(body));
          if (d && Array.isArray(d.uri_list)) window.__jmAuditUris.push(...d.uri_list);
        } catch (e) {}
      }
      return origSend.apply(this, arguments);
    };
    return 'patched';
  })()`);
  const uris = [];
  for (let k = 0; k < refs.length; k++) {
    const ref = refs[k];
    const before = await js('window.__jmAuditUris.length');
    // 2) 页面里注入文件（base64 → File → DataTransfer → input.files → change）
    const inject = await js(`(() => {
      try {
        const b64 = ${JSON.stringify(ref.b64)};
        const bin = atob(b64);
        const bytes = new Uint8Array(bin.length);
        for (let i = 0; i < bin.length; i++) bytes[i] = bin.charCodeAt(i);
        const file = new File([bytes], ${JSON.stringify(ref.name)}, {type: ${JSON.stringify(ref.mime)}});
        const dt = new DataTransfer();
        dt.items.add(file);
        const input = document.querySelector('.reference-upload-eWIGta input[type=file]') || document.querySelector('input[type=file]');
        if (!input) return {ok: false, reason: 'no reference input'};
        input.files = dt.files;
        input.dispatchEvent(new Event('change', {bubbles: true}));
        return {ok: true};
      } catch (e) { return {ok: false, err: String(e)}; }
    })()`);
    if (!inject || inject.ok !== true) throw new Error('参考图注入失败: ' + JSON.stringify(inject));
    // 3) 等该张图上传完成（audit 请求发出，即新增了 uri）
    const deadline = Date.now() + 30000;
    while (Date.now() < deadline) {
      if ((await js('window.__jmAuditUris.length')) > before) break;
      await sleep(1000);
    }
    const n = await js('window.__jmAuditUris.length');
    if (n <= before) throw new Error('参考图 ' + (k + 1) + ' 上传超时（30s）');
    const uri = await js('window.__jmAuditUris[window.__jmAuditUris.length - 1]');
    uris.push(uri);
    cliLog('REF_UPLOADED:' + JSON.stringify({ index: k + 1, uri }));
  }
  return uris;
}

async function api(path, payload, webId, extraQuery) {
  const url = '/mweb/v1/' + path + '?aid=513695&device_platform=web&region=cn&webId=' + webId +
    '&da_version=3.3.22&os=mac&web_version=7.5.0&aigc_features=app_lip_sync' + (extraQuery || '');
  const raw = await withTimeout(js('(' + XHR_SRC + ')(' + JSON.stringify(url) + ', ' + JSON.stringify(JSON.stringify(payload)) + ')'), 30000, path);
  if (raw === null) throw new Error(path + ' network error');
  return JSON.parse(raw);
}

// ---- main ----
await useOrCreateTaskSpace('jimeng image generation');
const tabs = await listTabs();
if (!tabs.some(t => (t.url || '').includes('jimeng.jianying.com'))) {
  await openOrReuseTab('https://jimeng.jianying.com/ai-tool/home?type=image', { wait: true, timeout: 30 });
  await sleep(5000);
}

const ctx = await withTimeout(js(`(() => ({
  webId: (document.cookie.match(/(?:^|; )_tea_web_id=([^;]*)/) || [])[1] || null,
  ws: (location.href.match(/workspace=(\\d+)/) || [])[1] || null
}))()`), 10000, 'ctx');
if (!ctx.webId) throw new Error('no_webid: 浏览器未登录即梦，请先在 ego lite 里登录 jimeng.jianying.com');

let workspaceId = ctx.ws ? parseInt(ctx.ws) : null;
if (!workspaceId) {
  const list = await api('workspace/list', { offset: 0, limit: 30 }, ctx.webId);
  const ws = ((list.data || {}).workspaces || []).find(w => w.workspace_id > 0);
  if (ws) workspaceId = ws.workspace_id;
}
if (!workspaceId) {
  const created = await api('workspace/create', { name: '未命名对话' }, ctx.webId);
  workspaceId = (created.data || {}).workspace_id;
}
if (!workspaceId) throw new Error('no_workspace');

async function generateAndPoll(workspaceId, ctx, timeoutMs, refUris) {
  const payload = buildPayload(PROMPT, COUNT, workspaceId, refUris);
  const hasRef = Array.isArray(refUris) && refUris.length > 0;
  const genResp = await api('aigc_draft/generate', payload, ctx.webId,
    '&generate_id=gen-' + crypto.randomUUID() + '&babi_param=' + babi(hasRef) + '&commerce_with_input_video=1&web_component_open_flag=1');
  if (genResp.ret !== '0') return { error: { stage: 'generate', ret: genResp.ret, errmsg: genResp.errmsg } };
  const submitId = genResp.data.aigc_data.submit_id;
  const historyId = genResp.data.aigc_data.history_record_id;
  const deadline = Date.now() + timeoutMs;
  let urls = null, failMsg = null;
  while (Date.now() < deadline) {
    await sleep(5000);
    let poll;
    try { poll = await api('get_history_by_ids', { submit_ids: [submitId] }, ctx.webId); }
    catch (e) { continue; }
    const rec = (poll.data || {})[submitId];
    if (!rec) continue;
    if (rec.status === 50) {
      urls = [];
      for (const it of rec.item_list || [])
        for (const li of ((it.image || {}).large_images || []))
          if (li.image_url) urls.push(li.image_url);
      break;
    }
    if (rec.status === 30 || rec.status === 40) { failMsg = rec.fail_starling_message || ('status=' + rec.status); break; }
  }
  if (urls && urls.length) return { urls, submit_id: submitId, history_id: historyId };
  return { error: { stage: 'poll', errmsg: failMsg || 'timeout' } };
}

// 额度不足特征：错误详情含 积分/余额/额度/credit/quota 等（generate 与 poll 阶段均适用）
const IS_CREDIT_ERROR = (e) => !!e && /积分|余额|额度|credit|insufficient|quota|denied/i.test(
  (e.errmsg || '') + ' ' + JSON.stringify(e));

let REF_URIS = [];
if (REF_IMAGES.length) {
  REF_URIS = await uploadRefImages(REF_IMAGES);
  cliLog('REFS_READY:' + JSON.stringify({ uris: REF_URIS }));
}

let result = await generateAndPoll(workspaceId, ctx, TIMEOUT_S * 1000, REF_URIS);
if (result.error && MODEL !== FALLBACK_MODEL && IS_CREDIT_ERROR(result.error)) {
  cliLog('FALLBACK:' + JSON.stringify({ from: MODEL, to: FALLBACK_MODEL, reason: result.error }));
  MODEL = FALLBACK_MODEL;
  result = await generateAndPoll(workspaceId, ctx, TIMEOUT_S * 1000, REF_URIS);
}
if (result.error) {
  cliLog('RESULT_JSON:' + JSON.stringify({ status: 'error', stage: result.error.stage || 'generate',
    ret: result.error.ret, errmsg: result.error.errmsg }));
  process.exit(0);
}
cliLog('SUBMITTED:' + JSON.stringify({ submit_id: result.submit_id, history_id: result.history_id }));
cliLog('RESULT_JSON:' + JSON.stringify({ status: 'ok', urls: result.urls, submit_id: result.submit_id, history_id: result.history_id }));
process.exit(0);
"""


def load_ref_image(path: str):
    """读取参考图；过大(>2MB)则用 PIL 压缩到最长边 2048 再转 JPEG。返回 (b64, name, mime)。"""
    p = Path(path)
    if not p.exists():
        raise SystemExit(f"参考图不存在: {path}")
    data = p.read_bytes()
    name = p.name
    ext = p.suffix.lower()
    mime = {'.png': 'image/png', '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg',
            '.webp': 'image/webp', '.bmp': 'image/bmp'}.get(ext, 'application/octet-stream')
    if len(data) > 2 * 1024 * 1024:
        from PIL import Image
        im = Image.open(p)
        if max(im.size) > 2048:
            im = im.convert('RGB')
            im.thumbnail((2048, 2048))
            buf = io.BytesIO()
            im.save(buf, 'JPEG', quality=88)
            data = buf.getvalue()
            name = Path(name).stem + '.jpg'
            mime = 'image/jpeg'
    return base64.b64encode(data).decode(), name, mime


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("prompt")
    ap.add_argument("--count", type=int, default=1)
    ap.add_argument("--model", default=None,
                    help="图片模型：4.0/4.1/4.5/4.6/4.7/5.0(图片5.0 Lite)/5.0 Pro，或直接传 model_req_key。"
                         "默认文生图 5.0=图片5.0 Lite；带 --ref 时默认 5.0 Pro（i2i 参考图实测默认）。额度不足自动 fallback 4.7")
    ap.add_argument("--ref", action="append", default=[],
                    help="参考图路径（可多次传，一张或多张）。参考图 + 文案 → 保留参考图构图/配色生成新图")
    ap.add_argument("--strength", type=float, default=0.5,
                    help="参考图强度（byte_edit），默认 0.5（与网页端一致）。"
                         "要更贴参考图的风格/构图/配色调高到 0.7-0.8；要高自由创作调低到 0.3-0.4")
    ap.add_argument("--out", default="./jimeng_output")
    ap.add_argument("--timeout", type=int, default=240)
    args = ap.parse_args()

    has_ref = bool(args.ref)
    model_arg = args.model if args.model else (DEFAULT_REF_MODEL if has_ref else DEFAULT_MODEL)
    model_key = MODEL_MAP.get(model_arg, model_arg)  # 支持友好名或原始 req_key

    ref_images = [load_ref_image(p) for p in args.ref]

    js_code = (NODE_JS_TEMPLATE
               .replace("__PROMPT__", json.dumps(args.prompt, ensure_ascii=False))
               .replace("__COUNT__", str(args.count))
               .replace("__TIMEOUT__", str(args.timeout))
               .replace("__MODEL__", json.dumps(model_key))
               .replace("__FALLBACK_MODEL__", json.dumps(FALLBACK_MODEL_KEY))
               .replace("__STRENGTH__", str(args.strength))
               .replace("__REF_IMAGES__", json.dumps(
                   [{"b64": b, "name": n, "mime": m} for b, n, m in ref_images],
                   ensure_ascii=False)))

    proc = subprocess.run([EGO, "nodejs"], input=js_code, capture_output=True,
                          text=True, timeout=args.timeout + 120)
    # cliLog 输出到 stderr，stdout 基本为空；合并两流解析标记
    out = proc.stdout + proc.stderr

    for m in re.finditer(r"^REF_UPLOADED:(.*)$", out, re.M):
        print(json.dumps({"stage": "ref_uploaded", **json.loads(m.group(1))},
                         ensure_ascii=False), flush=True)
    submitted = re.search(r"^SUBMITTED:(.*)$", out, re.M)
    if submitted:
        print(json.dumps({"stage": "submitted", **json.loads(submitted.group(1))},
                         ensure_ascii=False), flush=True)
    m = re.search(r"^RESULT_JSON:(.*)$", out, re.M)
    if not m:
        print(json.dumps({"status": "error", "stage": "runtime",
                          "errmsg": (out + proc.stderr)[-500:]}, ensure_ascii=False))
        sys.exit(1)
    result = json.loads(m.group(1))
    if result.get("status") != "ok":
        print(json.dumps(result, ensure_ascii=False))
        sys.exit(1)

    # 下载图片
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    slug = re.sub(r"[^\w一-鿿]+", "_", args.prompt)[:30].strip("_")
    ts = time.strftime("%Y%m%d_%H%M%S")
    paths = []
    for i, u in enumerate(result["urls"]):
        fp = out_dir / f"{ts}_{slug}_{i+1}.png"
        urllib.request.urlretrieve(u, fp)
        paths.append(str(fp.resolve()))

    print(json.dumps({"status": "ok", "count": len(paths), "images": paths,
                      "submit_id": result["submit_id"], "history_id": result["history_id"]},
                     ensure_ascii=False))


if __name__ == "__main__":
    main()
