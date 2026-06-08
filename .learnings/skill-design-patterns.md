# Skill Design Patterns — Learned from yueban-image-to-code analysis

## Date: 2026-06-08
## Context: Analyzing yueban-image-to-code skill for BubbleUniverseSkills enhancement

---

## Pattern 1: Manifest as Single Source of Truth

**Insight**: A structured JSON manifest (`layers.manifest.json`) acts as the contract between analysis, asset extraction, code generation, and QA phases.

**Why it works**:
- Prevents "guesstimation" during code generation
- Makes every layer traceable: code → manifest → source
- Enables script-based validation (audit, compare, preview)
- Creates a data bridge between different skills (image-to-code ↔ figma-page-replication)

**How to apply**:
- Any design-to-code workflow should define a manifest schema first
- The manifest must be created BEFORE writing any code
- All coordinates, dimensions, and asset paths must flow through the manifest

---

## Pattern 2: Toolchain Closure Loop

**Insight**: A complete QA loop requires 4 specialized tools in sequence:

```
preview → extract → audit → compare
   ↑_________________________________|
```

| Tool | Purpose | What it prevents |
|------|---------|-----------------|
| `preview_bboxes.py` | Visual bbox verification | Wrong crop regions |
| `extract_png_asset.py` | Exact-bbox extraction | Auto-trim, size drift |
| `audit_png_assets.py` | Edge/alpha/dimension check | Clipping, missing transparency |
| `compare_images.py` | Pixel-level diff metrics | Unnoticed visual regressions |

**Why it works**:
- Each tool has a single, focused responsibility
- Tools are composable (can be chained in scripts)
- Output is quantitative (not subjective "looks good")
- Failing fast at each stage prevents compound errors

---

## Pattern 3: Mandatory Wording Hierarchy

**Insight**: SKILL.md effectiveness correlates with wording strictness hierarchy.

| Level | Wording | Example | Usage |
|-------|---------|---------|-------|
| P0 (Critical) | "必须" / "禁止" / "高于所有" | "画板宽度必须精确为 750px" | Non-negotiable constraints |
| P1 (Sequential) | "先...再..." / "只有...才..." | "先创建 manifest，再导出切图" | Order enforcement |
| P2 (Validation) | "判定失败" / "视为未完成" | "没有 manifest 的交付视为未完成" | Pass/fail criteria |
| P3 (Guidance) | "优先" / "推荐" | "优先使用项目现有 Button 组件" | Best practices |

**yueban's strength**: Uses P0/P1 wording extensively (7 "禁止" rules, 10 "判定失败" conditions). This directly reduces AI hallucination by removing interpretive wiggle room.

---

## Pattern 4: Strategy Decision Table

**Insight**: When multiple implementation paths exist, use a condition → strategy table instead of prose.

```
| Condition | Strategy |
|-----------|----------|
| Complex decoration (SVG-heavy) | A: Export whole image |
| Photo-level detail | A: Export whole image |
| Pure text only | B: Native widget render |
| Simple button (solid/gradient) | B: Native widget render |
```

**Why it works**:
- Forces exhaustive condition enumeration
- Eliminates ambiguity in strategy assignment
- Enables systematic manifest population
- User can validate the table before execution

---

## Pattern 5: Cross-Skill Script Reuse with Specialization

**Insight**: Core scripts can be shared across skills if the manifest format is unified.

**Applied in this project**:
- `compare_images.py` — identical in both skills
- `preview_bboxes.py` → `preview_modules.py` — added strategy coloring and gap indicators
- `audit_png_assets.py` → `audit_assets.py` — added black-bg detection and filesize checks

**Principle**: Reuse the engine, specialize the interface.

---

## Anti-Pattern Discovered: "Write Code First, Assets Later"

**Problem**: yueban explicitly calls this out as a failure mode. When AI writes approximate code first, then tries to "fill in" assets:
- Layout drifts from source
- Crop regions become guesses
- Transparency handling is skipped
- Final result never matches source

**Solution**: Enforce manifest-first workflow. No code without manifest. No assets without bbox preview.

---

## Files Referenced

- `/Users/jiangxiaoqiang/Documents/workspace/yueban-image-to-code/SKILL.md`
- `/Users/jiangxiaoqiang/Documents/workspace/yueban-image-to-code/references/slicing.md`
- `/Users/jiangxiaoqiang/Documents/workspace/yueban-image-to-code/scripts/`
