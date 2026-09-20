# 即梦生图 · 写真人像示例库（学习沉淀）

> 与 `prompt-presets.md` 配套：**预设库 = 怎么写（心法+模板），本库 = 好的长什么样（示例 + 可抄通用件）**。
> 来源：用户提供的多语写真提示词，逐条学习沉淀，含跨示例共性规律。写人像 prompt 前先翻这里找同款场景/光线抄骨架。
> 注：示例里的画幅参数（4:5 / 2:3 / 9:16 等）是来源原始值；即梦管线固定 3:4，用 3:4 时按预设库硬约束块处理。

---

## 一、写真人像六块通用件（跨场景直接复制拼装）

### 块1 · 35mm 胶片质感帧（二选一，禁止混搭）

```
胶片写实款：35毫米胶片摄影，真实的胶片颗粒和色彩偏移，高对比度，轻微偏色，
电影感编辑风格，真实胶片外观，无数码感，{胶片调色：暖调/冷调}。
```
```
日系负片款：日系负片风格，柔和过曝，低对比，褪色中性色，细微颗粒，
不经意的抓拍构图，安静私下氛围。
```
```
胶片模拟点名款（最强风格帧，专名词锁死风格）：{富士经典负片 Fujifilm Classic Negative /
柯达 Portra 400 / 电影卷 Cinestill 800T} 胶片模拟，低对比暗部，柔和高光，
真实胶片颗粒，复古{暖/冷}调。
```
> ⚠️ 选对口味：`Classic Negative`=低对比怀旧（人像/胶片感）；`Velvia`=高饱和高对比（旅行/风光鲜艳片，例20）；`Portra 400`=中性柔和（万能人像）。别把 Velvia 的"高饱和"配到低对比款上。
> 需要"锐利高光/眼神光"时换闪光灯款：`机顶直射闪光灯，皮肤和衣物上有锐利镜面高光，
> 眼睛里有强烈眼神光，高对比度闪光灯照明`。

### 块2 · 东方女性主角配方（跨图一致用，逐字复用，只改发型/服装/场景）

```
二十出头的中国女性偶像，超写实精致细腻的东方五官，
诱人的杏眼狐眼配自然双眼皮，高鼻梁，小巧尖锐的V型下颌线，
无瑕瓷白肌肤带冷象牙底调，{发型}，
自然清透妆容带脸颊柔和红晕，水润自然粉唇微张，
鼻和脸颊上有微妙的自然雀斑，真实细腻的皮肤纹理和微小毛孔。
```
> 跨图一致性 = 这块逐字复制，只换 `{发型}` 和后续服装/姿态/场景，一字不改其他。
> ⚠️ **AI感高危**：本块的「无瑕瓷白」「精致细腻」「清透」是偶像审美词，直接喂 AI 感。若目标是真实人像/去AI感，用**块7反AI纪实块**覆盖本块美颜词，只保留五官基础结构。

### 块3 · 肤质块（反塑料核心，几乎每条必带）

```
真实细腻的皮肤纹理和微小毛孔，自然水光感，
{光线下}镜面高光落在皮肤上，肤色过渡真实，带{底调}色调，
保留自然瑕疵和轻微雀斑，不做过度磨皮，无塑料感皮肤，
无美颜滤镜感，无假滑皮肤，无过度锐化。
```
> ⚠️ **2026-08-20 修正（用户反馈磨皮过头）**：原块写「无瑕疵，无痣」与共性规律10「可信小瑕疵增强纪实感」自相矛盾——模型会按"无瑕疵"方向磨皮到塑料感。已改为「保留自然瑕疵和轻微雀斑，不做过度磨皮」。

### 块4 · 发丝块

```
自然发丝，根根分明，{发型}，许多松散的发丝垂在脸庞和颈部周围，
逼真的发丝细节，{被风/光}拂动，{光线}给发丝边缘勾上{高光色}光。
```

### 块5 · 织物块

```
逼真的织物纹理、褶皱和垂坠感，{面料：薄纱/真丝/棉/针织}材质，
{衣物}自然{贴合/滑落/垂挂}，布料与肌肤之间有高级过渡，{接触点}细节真实。
```

### 块6 · 通用负向块（写真人像，直接抄）

```
无水印，无文字，无Logo，无签名，无AI标签，
AI感，CG感，渲染感，网红脸，整容脸，完美对称五官，呆滞眼神，空洞眼神，
多余的手指，变形的手，扭曲的脸，错误身份，重复人物，模糊的脸，
低分辨率，过度磨皮，磨皮感，美颜滤镜感，假滑皮肤，瓷娃娃脸，
塑料感皮肤，不自然的肢体结构，错误透视，
杂乱背景，生硬伪影，过曝，欠曝，死鱼眼，僵硬表情，假发感。
```

### 块7 · 反AI纪实块（去AI感核心，真人像必带，可与块3/块6叠加）

```
纪实抓拍感，非摆拍，自然随意，不做模特姿势；
表情自然有生活感，眼神平和有内容、不空洞，不做完美微笑，视线可自然偏移不直视镜头；
五官真实不完美，避免过度精致对称的"AI脸"，保留面部自然不对称和轻微瑕疵；
皮肤可见毛孔、汗毛、纹理和自然瑕疵，不做美颜磨皮；
自然环境光为主，有真实明暗层次和投影，不做均匀平光；
背景有生活细节和纵深失焦，不做干净棚拍背景，前景可有自然遮挡；
轻微不完美的构图/对焦，真实胶片颗粒或环境噪点，保留环境色温差异。
```

> **反AI感原理（AI感 = 过度完美）**：皮肤/五官/表情/构图/光线/背景全部"太对"就出 AI 感。去 AI 感 = 每个维度主动留"不完美"——这是规律10「可信小瑕疵」的全面化。
> **AI 感高危词（写真人像提示词时警惕）**：`无瑕 / 完美 / 精致 / 清透 / 柔和 / 对称 / 光滑 / 瓷白 / 水润` —— 这些词直接喂 AI 感，除非刻意要偶像/广告审美，否则用块7 覆盖。
> ⚠️ **真人感来自自然的生活动作，不是把动作规范化**（2026-08-20 用户实测：捧热饮的 v3 真人感 > 交叠手放膝的 v4）。为了规避乱加道具而把姿势改成"端正交叠手/端坐"= 摆拍感 = AI感。**反 AI 约束加在质感/细节层面，动作保持自然**；规避手持道具靠"锁道具"（`手中只有X，无照片/卡片`）而非改姿势。

---

## 二、示例目录

| # | 标题 | 光的主角 | 主打学点 |
|---|---|---|---|
| 1 | 红跑道低角度夏日人像 | 正午强太阳光+硬影 | POV手臂前景、环境对称、三色干净构图 |
| 2 | 深夜便利店霓虹少女 | 冷荧光+暖霓虹混光 | 双光源混光、玻璃反射、超写实全细节 |
| 3 | 夏日牵手回眸电影肖像 | 侧逆光勾发丝边缘光 | 第一人称POV、手局部入画安全构图、边缘光=主高光 |
| 4 | 唱片公司楼梯间写真人像 | 楼道平光+柔和光晕 | 日系负片调色、道具细节锚定瞬间、克制氛围 |
| 5 | 春日花田三联写真拼贴 | 黄金时刻+光晕光斑 | 三联景别递进叙事、白色涂鸦叠加、Instagram审美 |
| 6 | 日式温泉旅馆人像 | 暖木灯笼光+自然窗光 | 和风场景定调、露肩=克制性感、浴衣垂坠 |
| 7 | 逆光美背情绪写真 | 逆光勾肩胛/背中线 | 主视觉单一化（背）、结构性线条清单、避免直白性感 |
| 8 | 胶片闪光灯球场少女 | 机顶直射闪光灯 | 闪光灯高对比+眼神光配方、黄昏球场、臀部曲线可见语言 |
| 9 | 韩系极简氛围感少女写真 | 柔和侧光+软雾泛光 | 软黑迷雾滤镜、姿态不对称破摆拍、疏离表情、留白极简 |
| 10 | 春日蔷薇花墙抓拍 | 逆光(contre-jour)+彩虹光斑 | 胶片模拟点名(Classic Negative)、三语社媒模板、氧气感 |
| 11 | 深夜冰箱光 | 冰箱LED单光源+明暗对比 | 叙事性布光(diegetic)、背景隐入黑暗、身体线条 |
| 12 | 都市街头静像 | 自然柔光+长曝光人群模糊 | 静止vs运动模糊对比、35mm f/1.8点名 |
| 13 | 年轻女性梦幻肖像 | 左后强逆光轮廓+正面极弱柔光 | 分段编号式结构、眼神微证据、光的三段式、冷暖对比 |
| 14 | 细节中的优雅·1970s魅力 | 暖琥珀光+柔自然光 | 年代感=时代符号清单、JSON包装、道具细节锚定、三色服装系统 |
| 15 | 冬日乡村肖像（JSON表单式） | 阴天扁平光 | JSON完整表单结构、冷红脸颊、雪花落发 |
| 16 | 复古湿版摄影年轻女性 | 阴天自然光 | 湿版/达盖尔工艺点名+做旧、水平涂抹模糊、侧影 |
| 17 | 风中的美丽中国少女 | 强金色逆光直射镜头 | 红色高饱和色彩锚点、强光晕+灰尘粒子、三分构图 |
| 18 | 自然美vs工业质感全身像 | 柔和自然光+浅景深 | 完整相机参数点名、质感对比构图、身份锁定约束 |
| 19 | 金色黄昏木制阳台 | 暖黄昏光/冷阴影 | JSON多级嵌套、场景叙事道具(自行车+睡猫)、色温对比 |
| 20 | 追逐地平线的永恒阳光 | 金色时刻+逆光轮廓 | Velvia高饱和胶片模拟、24mm广角低角度强制透视 |
| 21 | 慵懒性感东方面孔 | 柔和室内自然光 | 叠穿暗示法(cozy but sexy)、focus_point明确、cast日志结构 |
| 22 | 韩国K-pop偶像肖像 | 城市灯光bokeh+重柔焦 | prompt_analysis+full双轨、Boyfriend POV、halation泛光 |
| 23 | 成人世界的未知体验 | 千禧年相机强直闪 | Y2K数码相机点名、镜前自拍构图、编辑式细节修正 |
| 24 | KR_Idol 无缝生活拼贴 | 四格四光（晨光/练舞/夕照/直闪） | 宫格=四象限时间线叙事、identity lock、每格视角刻意不同、无缝隙版式 |
| 25 | Winter Forest 故事板 | 阴天漫射冷光+暖灯微光 | 多帧故事板、一次定义角色+每帧只写变化、色彩系统、共享道具锚定一致 |
| 26 | Scribbly 涂鸦插画迁移 | 无写实光照（扁平明快） | 风格分维度穷举定义、identity lock、插画负向清单、参考图身份锁定 |
| 27 | Concept Art 一句话生成器 | 纸感铅笔+水彩 | 250字符单句约束、风格四要素(medium/linework/palette/vibe)、exclusion分类禁制、质量自检 |
| 28 | 炭笔+粉笔时尚编辑 | 戏剧性方向光(靠对比) | 画种点名+技法描述、媒介特性适配、i2i画种迁移、identity lock |
| 29 | Dune 环境塑造 | 蜡烛动态光 | 环境=隐喻塑造(文字变地形)、base→transformation→scale、超现实写实+渲染点名 |
| 30 | 雪板夏装少女 | 明亮自然阳光 | 反季节反差=视觉钩子、三色高对比、动作×环境交互 |

---

## 三、示例原文（逐条保留 + 学点）

### 示例1 · 红跑道低角度夏日人像（en）

```
红跑道低角度夏日人像
Use the uploaded portrait photo as the appearance reference for the person. Create a bright
photorealistic outdoor portrait of a young woman lying on a red running track on a modern white
arch pedestrian bridge. Ultra-wide low-angle selfie perspective, her arm reaching toward the
camera in the foreground, relaxed pose, wired headphones around her neck, white sleeveless top,
loose gray pants, black hair spread on the ground. Clean blue sky with soft white clouds, strong
midday sunlight, crisp shadows, high clarity, fresh youthful mood, architectural symmetry,
realistic skin texture, cinematic composition, 3:4 vertical image

Negative: watermark, logo, text, caption, signature, AI label, extra fingers, deformed hands,
distorted face, wrong identity, duplicate person, blurry face, low resolution, over-smoothed skin,
plastic skin, unnatural anatomy, bad perspective, messy background, harsh artifacts, overexposure,
underexposure
```

**学点**：
- 超广角低角度自拍 POV + 手臂伸向镜头 = 身临其境的前景纵深，替代"手持道具"这个高危构图。
- 环境三色块干净到可以点名：红跑道 / 白桥 / 蓝天 = 强符号环境，色彩关系本身就是构图。
- 负向块是英文写真通用版，和我们块6中文版一一对应，可互译。

---

### 示例2 · 深夜便利店里的性感霓虹少女（zh）

```
35毫米胶片摄影，带有刺眼的便利店荧光灯照明，混合着外面色彩斑斓的霓虹灯牌，
真实的胶片颗粒，高对比度，轻微的偏色，电影感街头编辑风格，亲密的中景镜头，
20岁出头性感的华人女性偶像，拥有超逼真精致细腻的东方五官，诱人的杏眼狐眼搭配天然双眼皮，
高鼻梁，小巧尖锐的V型下颌线，无瑕的瓷白肌肤带有冷象牙底色以及来自荧光灯的可见高光，
细腻的皮肤纹理和微小毛孔，自然清透妆容带有脸颊上的柔和红晕，水润自然的粉唇微张，
鼻子和脸颊上散布着微妙的自然雀斑，深棕色的长发扎成凌乱的高马尾，许多松散的发丝垂在脸庞和颈部周围，
穿着一件超大号的白衬衫作为唯一的上衣，顶部敞开露出深邃乳沟并在腰部宽松打结，
搭配一条极小的黑色百褶迷你裙，赤脚穿着简约的白色拖鞋，
在深夜24小时便利店的玻璃门上呈现出诱人随性的倚靠姿势，身体微微拱起，
一条腿弯曲，脚搭在门框上，另一条腿伸直，一只手拿着一瓶冰饮，另一只手轻轻拉扯迷你裙的裙摆，
极其诱人俏皮却又略显脆弱的目光直视观看者，柔和的鹿眼中充满安静的诱惑与挑逗的微笑，
来自店内明亮冷调的荧光灯光混合着来自外面招牌的粉色和蓝色霓虹光芒，玻璃门上真实的反射，
模糊的便利店内部，背景中有货架和零食，真实的35毫米胶片调色，带有刺眼的光照和霓虹点缀，
极其锐利却又柔和的皮肤渲染，自然的发丝，超大号衬衫和迷你裙上逼真的织物褶皱和垂坠感，
无塑料感皮肤，无数字过度锐化，无磨皮，无瑕疵，无痣，无油性皮肤，无水印，无文字，
真实的深夜便利店氛围
```

**学点**：
- **双光源混光是夜间霓虹感的配方**：店内冷荧光（主光） + 店外粉/蓝霓虹（点缀光），且明确写"玻璃门上真实反射"——光的两段写法（照在哪+反射去哪）。
- 主角配方块（块2）在此首次完整出现，后两条复用。
- 姿态细节给到关节级：`一条腿弯曲脚搭门框，另一条腿伸直`——位置三件套的身体版本。
- 性感表达靠"目光 + 姿态"而不是裸露：`诱人俏皮却略显脆弱的凝视直视观看者`。

---

### 示例3 · 夏日牵手回眸电影肖像（en）

```
Cinematic portrait photography, ultra-photorealistic, 2160x3840 vertical composition,
50mm or 85mm portrait lens rendering, shallow depth of field, clean translucent summer
natural-light color grading — not overly yellow, not over-filtered.

Subject: a young beautiful adult East Asian woman, [describe face shape and features,
e.g. soft heart-shaped face, refined classical features, bright almond/fox eyes, petite nose
bridge, naturally full lips], overall vibe sweet, sunny, energetic, cute with a touch of allure.
Gaze highly engaging — bright, clear, natural catchlights, as if it speaks; corners of mouth
slightly lifted, expression gentle, vivid, natural.

She walks along a [scene, e.g. garden stone path / tree-lined lane / European street / courtyard],
right hand reaching back to hold the hand of someone behind her; only their hand appears in the
lower-left corner — like a first-person couple's POV snapshot. She glances back at the camera
while her body stays in a forward walking motion, posture elegant and natural, clearly a candid
captured moment with a faint in-love feeling.

Long [hair color] hair, [style, e.g. naturally wavy / relaxed big waves / airy bangs / half-up],
many strands tousled and flying in the wind, richly layered and dynamic. Strong natural
side-backlight rims the hair edges — clean, crisp rim light and semi-translucent glow, hair edges
lit as if by sunlight, light and luminous. This is the core highlight of the image.

She wears [outfit, e.g. white lace slip dress / beige slip dress / light-blue short-sleeve top
with white skirt / light-pink fitted dress], fabric texture natural, material light and soft.
Bright natural summer sunlight realistically warms her skin, shoulders, collarbone, and clothing
with soft, clean highlight transitions.

Skin texture: extremely realistic — visible fine pores, natural skin texture, faint imperfections,
subtle tone variation, soft sheen. Cheeks, nose tip, shoulders show natural delicate gradations in
sunlight. Translucent, healthy, real and refined — no plastic look, no waxwork, no over-smoothing.

Background: soft atmospheric blur, never distracting.

Avoid: over-smoothing, plastic skin, CG look, anime look, wig look, stiff expression, dead eyes,
stiff poses, overall yellow cast, overexposed face, distorted features, wrong fingers, deformed
hands, cluttered background, heavy influencer retouching.
```

**学点**：
- **第一人称 POV 安全构图**：第二人的手只出现在左下角局部入画——既保"情侣"关系，又规避双手互握的高危构图（印证预设D"局部入画"）。
- **明确点明主高光**：`侧逆光勾发丝边缘，这是画面核心高光`——把"这张图的光要秀在哪"直接写给模型。
- 结构完整到可直接当模板抄：subject（外貌+气质）→ gaze → 场景+动作 → 发型 → 服装 → 肤质 → 背景。
- 调色写了"不黄、不过滤镜"的反向约束（`not overly yellow`），防止夏日调色溢出。

---

### 示例4 · 唱片公司楼梯间写真人像（en，--2:3）

```
photorealistic-natural. Cinematic portrait image. Create a photorealistic image of a fictional
adult Korean female idol in her mid-20s, not resembling any real celebrity. Maintain a Japanese
negative film look: soft overexposure, faded neutrals, low contrast, subtle grain, and imperfect
snapshot framing.

Scene/backdrop: the back stairwell of a small record label building, with moving boxes, scuffed
concrete steps, a gray metal handrail, and a pale security light. The atmosphere should feel quiet,
slightly intimate, and workaday, as if caught in a private in-between moment after practice and
during moving day.

Subject: a Korean female idol with a naturally attractive, understated sensuality rather than overt
glamour. She should feel quietly magnetic, relaxed, and a little teasing without being provocative.

Wardrobe/props: a slightly cropped black blazer worn casually and slightly open, over a fitted
heather-gray ribbed tee that softly outlines the figure without revealing cleavage, loose khaki
cargo pants sitting naturally on the waist, a thin silver chain necklace, a roll of black gaffer
tape placed beside her, and one sneaker lace still half-tied. The styling should feel subtly sexier
and more feminine than purely casual, but still fully modest and non-revealing.

Composition/framing: tall portrait. The subject is seated on the stairs with one knee slightly
raised and one leg relaxed lower on the step, leaning back lightly with one hand braced behind her
on the stair for support. The other hand is near her half-tied sneaker, as if she has just paused
while tying it. Her blazer falls naturally along the body, her posture creating a soft, elegant
silhouette. Her head is tilted up toward the camera with a calm, slightly sultry, self-possessed
expression. The pose should feel candid yet subtly alluring, natural rather than staged.

Lighting/mood: flat stairwell light, understated backstage realism, soft grain, muted tones,
gentle highlight bloom, and a quiet intimate mood. Keep the image photorealistic, restrained, and
cinematic, with no excessive glamour and no nudity.

Add small white handwriting signature text "BubbleBrain" on the bottom right corner.
```

**学点**：
- **日系负片调色是独立风格帧**（柔和过曝/褪色/低对比/颗粒/不完美取景）——需要安静私下氛围时用它，替代标准 35mm。
- **道具细节锚定"瞬间"**：半系鞋带 + 胶带卷 = 把画面钉在"练习后搬家间隙的某一刻"，比摆拍姿势真实。
- 克制性感表达：`subtle / modest / non-revealing` 反复出现，用姿态剪影而非裸露。
- 反面示范价值：这条自带签名文字指令（`Add "BubbleBrain" bottom right`）——即梦管线如果没文字需求，照预设库硬约束块删掉并禁文字。

---

### 示例5 · 春日花田三联竖版写真拼贴（en，4:5）

```
A high-quality 3-panel vertical photo collage of a stunning uploaded woman with soft, voluminous
wavy hair glowing in golden sunlight. She is styled in a cream-colored lace-up vintage blouse with
delicate textures, olive green high-waisted flowy trousers, and a wide-brimmed straw hat slightly
tilted for a fashionable editorial look. Light golden jewelry (thin chains, rings) adds a subtle
luxury touch.

The setting is a dreamy, vibrant yellow mustard flower field under a bright blue sky with soft
clouds, enhanced by golden hour lighting for a magical glow.

Top panel: Back view of the woman standing in the field with arms wide open, sunlight creating a
glowing halo around her hair, slight motion blur in flowers for a cinematic feel.
Middle panel: Close-up portrait, she smiles naturally at the camera, wind softly moving her hair,
her hand reaching toward the lens creating depth and a slightly blurred foreground for a DSLR effect.
Bottom panel: Playful pose, she leans sideways in the flowers, making a double peace sign, laughing
candidly, capturing an authentic joyful moment.

Add cute, trendy white doodle overlays (smiley faces, sparkles, stars, tiny hearts) with a subtle
animated/sketchy feel. Include light leaks, sun flares, and soft film grain for a premium Instagram
aesthetic. Ultra-realistic, 4K, cinematic lighting, shallow depth of field, high dynamic range,
natural skin tones, editorial fashion photography, soft pastel color grading. Aspect ratio: 4:5.
Style tags: viral Instagram aesthetic, Pinterest style, dreamy spring vibe, candid luxury
```

**学点**：
- **三联 = 景别递进叙事**：上-背影大全景 → 中-特写 → 下-互动近景，每格一个景别，逐格推近。
- **每格一个主姿态+一个辅助动作**（张臂 / 伸手向镜头 / 比耶大笑），严格遵循"每格 1 主体"减法。
- 白色涂鸦叠加 + 光斑 + 漏光 = Instagram/Pinterest 审美配方；金色时刻统一全片。
- 人物一致性靠"同一套服装+发型逐字复用"，跨格只换动作景别。

---

### 示例6 · 日式温泉旅馆人像（en）

```
35mm film photography, warm vintage Japanese onsen ryokan aesthetic, soft ambient wooden lantern
lighting mixed with gentle natural window light, subtle film grain, gentle color shift, high
atmosphere editorial style, intimate medium shot, early 20s beautiful Chinese female idol with
ultra-realistic delicate refined Chinese features, seductive almond-shaped fox eyes with natural
double eyelids, high nose bridge, small sharp V-shaped jawline, flawless porcelain skin with warm
ivory undertone, visible subtle skin texture and micro pores, soft natural makeup with dewy glow,
subtle rosy flush on cheeks, natural soft pink lips slightly parted, long dark brown hair tied in a
loose low bun with some messy strands falling around face and neck, wearing a loose white yukata
(traditional Japanese bathrobe) deliberately slipped off one shoulder and loosely tied at the waist,
the fabric slightly open revealing smooth skin and subtle cleavage, barefoot, seductive relaxed
sitting pose on the edge of a traditional wooden engawa veranda at a vintage onsen ryokan, body
slightly turned toward the camera, one leg bent with foot resting on the wooden floor, the other leg
gently dangling, one hand lightly holding the yukata collar, the other hand resting on the wooden
floor behind her for support, softly arched back to gently accentuate curves, intensely seductive
yet gentle and inviting gaze straight at the viewer with soft doe eyes full of quiet temptation and
warmth, warm wooden interior with paper sliding doors and distant steaming hot spring in soft focus,
gentle rim lighting highlighting skin and fabric texture, authentic vintage film color grading with
warm tones, extremely sharp yet soft skin rendering, natural hair strands, realistic fabric
wrinkles and drape on the yukata, no plastic skin, no digital over-sharpening, no airbrushing, no
blemishes, no moles, no oily skin, no watermark, no text, authentic 35mm film Japanese onsen ryokan
atmosphere
```

**学点**：
- **场景词定调全片**：`warm vintage Japanese onsen ryokan aesthetic` 放开头 = 氛围帧，模型按场景联想整体调性。
- 露肩 = 克制的性感表达：`yukata deliberately slipped off one shoulder`，配"手轻拉领口/手撑地面"两个支撑手动作，规避裸胸风险。
- 双光：暖木灯笼光（主）+ 自然窗光（补），`gentle rim lighting` 勾皮肤与织物边缘。
- 主角配方块（块2）第二次复用，只改了发型（低发髻）和底调（冷象牙→暖象牙）。

---

### 示例7 · 逆光美背女性情绪写真（zh）

```
逆光美背女性情绪写真提示词：

请生成一张竖版高质感女性情绪写真，主题为「逆光美背·女性情绪写真」。

核心要求：画面的绝对重点是"美背"，通过露背结构、肩颈线条、肩胛骨、脊柱中线、腰背曲线和逆光
轮廓来呈现女性美。请避免普通女性写真或普通穿搭图的处理方式，背部必须是主视觉核心，脸只作为辅助。

人物设定：成年女性，真实自然，气质可为温柔、清冷、慵懒、文艺、轻熟或安静。人物不要网红脸，
不要塑料感，不要夸张妆容。可侧脸、回眸、低头或闭眼，但正脸不是重点。

姿态要求：姿态必须服务于背部展示，例如背对镜头微微回头、侧身站立、侧坐、抬手整理头发、低头
蜷身、斜倚窗边、半躺回眸、披衣下滑等。动作自然，不要僵硬摆拍，不要正面直视镜头。

露背结构：必须有明确的露背设计，可为低背长裙、吊带裙、露背礼服、针织外套滑落、薄纱披肩、浴袍
半披、宽松衬衫滑肩、丝质罩衫半落等。重点表现肩线、肩胛骨、背中线、腰背收束和布料与肌肤之间的
高级过渡。

服装与材质：服装选择轻柔、垂坠、带有透光感和褶皱感的材质，如薄纱、真丝、针织、棉麻、细闪纱、
浴袍质地、软垂感长裙。布料要参与构图，形成半遮半露、滑落、包裹、垂挂的层次，但不能厚重。

场景：场景为卧室、窗边、床上、白墙房间、民宿、酒店房间、木质空间或复古公寓。背景简洁克制，
少量床品、窗帘、木椅、花束、地板等元素即可，不能喧宾夺主。

光线要求：采用自然光或柔和暖光，以逆光、侧逆光、窗边光为主。重点是让光打到背部，勾出肩颈边缘、
肩胛骨轮廓、腰线和发丝高光。可使用晨光、黄昏金光、柔雾散射光或冷白窗光，但背部受光状态必须成立。

构图：竖版构图，画幅可为 9:16、3:4 或 4:5。人物是绝对主角，视觉重心放在背部、肩颈和腰背曲线上。
可采用半身、七分身、近景或全身，但不要让场景抢走主体。

氛围：整体氛围安静、柔软、私密、克制、高级，像真实摄影师拍摄的电影感情绪写真。重点避免直白性感，
改用"美背 + 逆光 + 柔软布料 + 自然姿态"表达女性美。

画质要求：真实摄影感、电影感、柔雾胶片感、细腻肤色、真实皮肤质感、浅景深、轻微颗粒感、画面通透
自然。不要 AI 塑料感，不要 CG 感，不要错误手指，不要肢体畸形，不要低俗色情化表达，不要文字、
水印、Logo、边框。

最终效果：一张以"美背"为主视觉核心的高完成度女性情绪写真，通过露背结构、肩颈背部线条、柔光逆光
和柔软布料来呈现克制而高级的女性美。
```

**学点**：
- **主视觉单一化**：`背部必须是主视觉核心，脸只作为辅助` —— 明确"图的主角是谁"，直接写进 prompt。
- **结构性线条清单**：露背 = `肩线 + 肩胛骨 + 背中线 + 腰背收束`，把"美背"拆成镜头能拍到的骨骼/线条，这是块式描述的最佳范例。
- **姿态服务主题**：每个姿态（回眸/侧坐/披衣下滑）都写"为了露背"，不是摆拍。
- **避免直白性感的明确表态**：`不要低俗色情化表达，用美背+逆光+柔软布料表达女性美`——审美克制条款写死。

---

### 示例8 · 胶片闪光灯下的球场少女（zh，9:16）

```
35毫米彩色胶片摄影，带有强烈的机顶直射闪光灯，皮肤和衣物上有镜面高光，眼睛里有强烈的眼神光，
高对比度闪光灯照明，真实的胶片颗粒和色彩偏移，高级时尚清新纯真篮球场编辑风格，
亲密的第一人称低角度仰视POV镜头，二十出头的性感中国女性偶像，具有超写实的精致细腻的中国特征，
诱人的杏仁形狐狸眼，带有自然双眼皮，高鼻梁，小巧锋利的V型下颌线，无瑕逼真的瓷白肌肤，带有冷象牙
色底调和可见的闪光镜面高光，细腻精致的皮肤纹理，带有微妙的毛孔微距细节和闪光灯下的自然水光感，
清新自然的运动妆容，带有柔和的水光感，脸颊上有微妙的自然红晕，自然粉唇微张，鼻子和脸颊上有微妙的
自然雀斑，深棕色长发扎成高高的俏皮马尾辫，有一些散落的发丝修饰脸型，以及逼真的散落发丝，穿着宽松
的白色背心和白色高腰篮球短裤，白色及膝运动袜，在黄昏的户外球场上靠在篮球架杆上的诱人自然倾斜姿势，
身体侧成角度，背部自然弓起，臀部轻轻向后推，以凸显挺拔圆润的臀部和性感的臀部曲线，一条腿自然向前
伸向镜头，另一条腿微微弯曲以强调修长性感的双腿，双手轻轻放在肩膀高度的篮球杆上，极其诱人俏皮又
惹人怜爱的鹿眼凝视直视观看者，带着柔软脆弱渴望的眼睛和温柔挑逗的微笑，充满安静的诱惑和欲望，
强烈的机顶直射闪光灯产生锐利的镜面高光和强烈的眼神光，背景是黄昏天空下模糊的篮球场和篮筐，高对比度
胶片调色，带有自然闪光灯外观，极其锐利却又柔和的皮肤渲染，具有真实的35毫米直射闪光美学，自然发丝，
背心和短裤上逼真的织物纹理以及袜子细节，没有塑料感皮肤，没有数码过度锐化，没有磨皮，没有瑕疵，
没有痣，没有油性皮肤，没有水印，没有文字，真实的35毫米直射闪光胶片篮球场外观
```

**学点**：
- **闪光灯美学 = 高对比 + 锐利镜面高光 + 强烈眼神光**，写在开头定调，结尾再强调一次（`35毫米直射闪光胶片外观`），首尾呼应锁死风格。
- 低角度仰视 POV + 腿伸向镜头，人物动态用可见几何（侧身/弓背/推胯/伸腿）而不是情绪词。
- `臀部轻轻向后推，以凸显挺拔圆润的臀部`——把身体曲线翻译成动作描述，是可复制的"曲线写法"。
- 主角配方块第三次复用（冷象牙底调、雀斑、水润粉唇全部一致）。

---

### 示例9 · 韩系极简氛围感少女写真（zh，9:16）

```
韩系极简氛围感少女写真
9:16 竖版 — 杂志人像，单一主体
柔和的黑色迷雾滤镜，微妙的薄雾，柔和的高光泛光，柔和的色调
极简的室内空间，干净的背景，轻微的纹理
年轻韩国女性，淡妆，自然的皮肤纹理
服装：贴身的罗纹针织上衣或柔软的吊带背心叠穿在宽松衬衫下，搭配高腰短裤或裙子；
面料轻微贴合身体曲线，柔软自然，无暴露元素
头发：略显凌乱，自然的蓬松度
姿势：坐在地板上，一条腿弯曲，另一条腿放松，身体微微倾斜，肩膀不对称，头部倾斜
构图：主体略微偏离中心，存在留白
表情：平静，略显疏离，自然的嘴唇
光线：柔和的侧光，温和的阴影衰减
氛围：低调，安静，通过自然的身体线条展现微妙的性感，放松且非摆拍
画质：细腻颗粒，轻微的柔和感，写实外观
```

**学点**：
- **软黑迷雾滤镜是独立风格帧**：柔和黑色迷雾 + 微妙薄雾 + 柔和高光泛光 = 韩系极简的影调签名，比胶片颗粒更柔更灰，和示例4日系负片/示例8直射闪光区分开。
- **姿态不对称破摆拍感**：`一条腿弯曲另一条放松 + 身体微倾 + 肩膀不对称 + 头倾斜`——四条不对称写满。对称=摆拍，不对称=抓拍（共性规律第9条）。
- **表情给"疏离"不用甜词**：`平静、略显疏离、自然的嘴唇`——情绪克制化。
- **性感靠身体线条不靠暴露**：`通过自然的身体线条展现微妙性感` + 明确`无暴露元素`。
- **留白构图**：`主体略微偏离中心，存在留白`——极简场景+留白=高级感，和封面留白需求同源。

---

### 示例10 · 春日蔷薇花墙抓拍（zh，Fujifilm 经典负片 + 逆光）

```
春日蔷薇花墙抓拍
把春天穿在身上。在这面盛开的蔷薇花墙前，一切都显得那么温柔。
逆光下的彩虹光斑（Lens flare）和空气感，完美复刻了胶片摄影的怀旧美学。
这是一张充满"氧气感"的春日抓拍。

创作灵感 主要思路：
核心在于模拟 Fujifilm Classic Negative（富士经典负片）的色调。
低对比度的暗部和柔和的高光，让画面看起来既有电影感，又不失真实的胶片颗粒质感。

提示词：
注意：括号内的 [角色] 和 [服装/动作] 可以随意替换为你想要的设定！
```

**学点**：
- **胶片模拟点名 = 最强风格帧**：`Fujifilm Classic Negative（富士经典负片）` 一个专名词就锁死"低对比暗部 + 柔和高光 + 复古胶片颗粒"，比堆一串质感词更准更省（共性规律11）。
- **contre-jour 逆光 + 彩虹 lens flare**：逆光制造"氧气感/空气感"，彩虹光斑是高质社媒抓拍的签名元素。
- **三语社媒模板结构**（中/英/日 + 灵感思路 + 提示词 + CTA）：`[角色]/[服装/动作]` 是占位符——这类 prompt 本质是"可换人换装的模板"，和我们主角配方块同思路。

---

### 示例11 · 深夜的冰箱光：孤独与治愈的都市瞬间（zh，diegetic lighting）

```
深夜的冰箱光，是孤独也是治愈。在万籁俱寂的时刻，捕捉一份随性与真实。
这一刻的光影，勾勒出的不仅是身形，更是都市深夜的独特氛围。

创作灵感源于叙事性布光（Diegetic Lighting）的概念。
完全摒弃外部光源，仅依靠冰箱内部的冷白光来照亮主体。
通过模仿 Fujifilm Classic Negative (NC) 的胶片色彩，
增强了明暗对比（Chiaroscuro），在保留皮肤质感细节的同时，
让背景隐入深邃的黑暗中，营造出电影般的抓拍感。
```

**学点**：
- **叙事性布光（diegetic lighting）= 光源来自画面内的物体**：冰箱 LED 作为唯一光源，暗部全黑、明暗对比（chiaroscuro）强烈——这是"电影感抓拍"的高性价比配方（共性规律12）。
- **单一光源 + 背景自动隐黑**：`让背景隐入深邃的黑暗中`——不用写"虚化背景"，黑暗自己把杂乱环境清掉，还突出身形。
- 与示例2便利店荧光灯的区别：示例2是双光源混光（冷荧光+霓虹），这里是**纯单光源 + 明暗对比**。
- 胶片模拟点名第二次出现（NC），印证共性规律11。

---

### 示例12 · 都市街头静像（en，Nano Banana Pro on Gemini）

```
A cinematic street portrait of a young woman standing still in a busy urban crowd,
captured with motion blur all around her. She has short, slightly messy hair and a calm,
introspective expression, looking directly at the camera. She wears a soft beige sweater
and a textured brown skirt, minimal accessories. The background is a city street filled
with people in motion, creating a dreamy long-exposure effect. Shallow depth of field,
subject in sharp focus, crowd blurred, natural soft daylight, muted color palette,
film photography style, emotional and artistic mood, high detail, realistic, 35mm lens, f/1.8.
```

**学点**：
- **静止 vs 运动模糊对比**：主体锐利 + 周围人群长曝光模糊 = "在城市中静止的孤独感"，视觉反差即情绪。
- **35mm f/1.8 镜头参数点名**：焦距 + 光圈直接给，浅景深 + 背景虚化一次搞定——镜头语言比"浅景深"三个字更具体。
- 情绪克制：`introspective expression + emotional mood`，用"内向的表情"不用堆情绪词。

---

### 示例13 · 年轻女性梦幻肖像（zh，Nano Banana Pro 分段编号式）

```
年轻女性梦幻肖像
一、主体与动作
1 人物：年轻女性，清冷气质，半身近景，身体侧向右侧，回眸直视镜头
2 表情：眼神锐利克制，略带疏离与忧郁，嘴唇微抿
3 头发：乌黑长发，蓬松凌乱，强风吹拂，发丝大幅飘起并掠过脸颊
4 妆容：暖棕眼影与微红眼周，睫毛清晰，哑光红唇，肤质通透
5 服饰：深色细肩带衣裙或上衣，肩颈与锁骨露出，外侧有深色薄纱或外搭下滑形成暗部包裹

二、构图与镜头
1 画幅：竖幅
2 景别：胸口以上的半身近景，三分之二侧脸
3 位置：人物偏画面中右，头顶留少量空间，左侧留出光源与雾化区域
4 视角：平视或略微仰视，镜头距离较近但不夸张变形
5 对焦：焦点落在眼睛与面部，背景强虚化，整体带轻微柔化与朦胧感

三、光线与氛围
1 主光：左后方强逆光，形成发丝与肩部的明亮轮廓光
2 补光：正面极弱柔光，仅提亮面部细节，阴影保留
3 光质：散射柔光，明显雾化光晕，带空气感与轻微眩光
4 氛围：梦幻、神秘、安静、电影感、带一点冷感与孤独感

四、色彩与质感
1 色调：背景冷灰偏蓝，肤色偏暖，形成冷暖对比
2 饱和度：整体低饱和
3 明暗：对比偏高，暗部压低，高光柔亮不过曝
4 质感：皮肤细腻自然，轻微颗粒与雾面感，边缘高光带光晕

五、背景与环境元素
1 背景：暗灰到黑的渐变空间，无明确场景信息
2 光点：背景与发梢周围有零散点状光斑与闪烁颗粒，类似尘埃反光或微小光粒
3 动态：风带动发丝飞舞，光点呈漂浮散落的层次感

六、风格与后期
1 风格：唯美写实，梦幻柔雾，电影海报质感
2 后期：增强轮廓光与发丝高光，提升雾化与空气透光感，轻微褪色，暗角收束画面
3 清晰度：眼部与唇部相对清晰，其余区域柔化过渡，整体通透但不锐利

七、反向提示
1 人物错误：不要脸部畸变，不要五官错位，不要双脸，不要多余肢体，不要手指异常，不要不自然的皮肤塑料感
2 光影错误：不要正面硬光，不要强烈死白高光，不要背景过亮抢主体
3 风格偏差：不要卡通化，不要漫画厚涂感，不要夸张霓虹色，不要过度锐化与过度磨皮
```

**学点**：
- **分段编号结构 = 复杂肖像骨架**：一~七节全编号（主体动作/构图镜头/光线氛围/色彩质感/背景环境/风格后期/反向提示），比七层结构更细，每节独立、注意力分配更稳（共性规律14）。
- **眼神微证据写情绪**：`眼周微红、眼中略带血丝`——用生理微细节表达"克制忧伤"，这是"情绪用证据"的新层级，比"忧伤的表情"高级得多（共性规律13）。
- **光的三段式**：主光（左后强逆光→发丝肩部轮廓光）+ 补光（正面极弱柔光）+ 光质（散射柔光+雾化光晕）——光拆成来源/方向/质感三维，比"氛围光"精确。
- **冷暖对比调色**：背景冷灰偏蓝 + 肤色偏暖——统一色调之外的另一种做法：冷暖对撞出高级感。
- **尘埃光点漂浮**：`背景与发梢周围有零散点状光斑与闪烁颗粒，类似尘埃反光`——梦幻氛围关键小元素，与技法五"前景失焦光斑"同族。
- **负向三段分类**：人物错误/光影错误/风格偏差三组，比单条负向清单更好排查。

---

### 示例14 · 细节中的优雅，1970年代魅力（en，JSON 包装式）

```
Elegance in every detail, 1970s charm, warm tones, and a coffee pause that feels timeless.

{
  "image_generation_prompt": "Aesthetic 1970s-inspired fashion portrait of a stylish young woman
  sitting on outdoor cafe steps, holding a premium ornate green coffee cup with gold rim detailing,
  gazing softly at the camera. Her hair is styled in soft loose strands framing her face with vintage
  makeup, matte red lips, and subtle eyeliner. She is wearing a cozy forest green premium knit sweater
  paired with a long flowing black tutu skirt. A warm vintage plaid scarf in earthy brown, burnt
  orange, and muted red tones is wrapped loosely around her neck. A premium dark green leather
  crossbody bag with a gold filigree clasp and chain strap is placed beside her. Autumn street café
  setting with scattered fallen leaves and warm amber café lights glowing behind glass windows.
  1970s film tone, warm grainy texture, muted earthy color palette, cinematic atmosphere, shallow
  depth of field, soft natural lighting, analog film look, fashion editorial photography,
  ultra-realistic, high detail, 85mm lens, f/1.8, vintage aesthetic, dreamy mood."
}
```

**学点**：
- **年代感 = 时代符号清单**：1970s 靠具体元素点名——复古妆容+哑光红唇+细眼线 / 森林绿针织+黑纱裙 / 格纹披肩（土棕+焦橙+暗红）/ 琥珀色咖啡馆灯光 / 胶片调。不抽象写"复古"（共性规律15）。
- **JSON 包装结构**：`{"image_generation_prompt": "..."}` 是 Nano Banana Pro 的调用格式——提示词作为字段值传给模型。跨模型调用时注意这种包装差异（GPT 用字段模板，Gemini 用 JSON 字段）。
- **道具细节锚定**：绿咖啡杯带金边（`premium ornate green coffee cup with gold rim`）——道具给到材质+细节，比"拿着杯子"具体。
- **三色服装系统**：森林绿上衣+黑纱裙+土棕/焦橙格纹 = 70s 暖调统一色系，人物亮但不跳（呼应技法五第2招"服装融入环境综合色"）。
- 85mm f/1.8 再点名，印证共性规律11（镜头参数点名）。

---

### 示例15 · 年轻女子冬日乡村肖像（en，JSON 完整表单式）

```
{
  "subject": {
    "description": "Young woman, approximately late teens or early 20s",
    "pose": "Looking back over her shoulder at the viewer, body turned slightly away",
    "expression": "Calm, neutral, slightly melancholic, direct eye contact"
  },
  "face": {
    "skin": "Fair complexion, natural texture, distinct rosy cheeks and nose (cold flush)",
    "eyes": "Large, clear hazel-green eyes, sharp focus, long lashes",
    "lips": "Soft natural pink, closed mouth",
    "makeup": "Minimal to no visible makeup, natural look"
  },
  "hair": {
    "color": "Dark brown",
    "style": "Loosely pulled back into a messy bun or updo",
    "details": "Loose wisps framing the face, covered in varying sizes of white snowflakes"
  },
  "clothing": {
    "main_piece": "Thick, textured woven shawl or blanket wrapped around shoulders",
    "pattern": "Faded paisley or floral motif",
    "colors": "Beige base with muted rust-orange and faded denim blue accents",
    "texture": "Woolen, coarse weave, dusted with fresh snow"
  },
  "accessories": [],
  "environment": {
    "setting": "Outdoor winter scene, rural village",
    "background_elements": [
      "Blurred wooden log cabin or structure on the left",
      "Indistinct group of people in period-style clothing in the distance",
      "Bare tree branches",
      "White snowy ground"
    ],
    "atmosphere": "Cold, snowy, quiet"
  },
  "lighting": {
    "type": "Soft, diffuse natural light",
    "quality": "Overcast sky (flat lighting)",
    "shadows": "Very soft, minimal shadows on face"
  },
  "camera": {
    "perspective": "Eye-level",
    "shot_type": "Medium close-up portrait",
    "focus": "Shallow depth of field (bokeh), sharp focus on eyes and face, blurred background",
    "lens_effect": "Portrait focal length (approx 85mm)"
  },
  "style": {
    "aesthetic": "Cinematic realism with a vintage or painterly quality",
    "mood": "Nostalgic, serene, wintery",
    "visual_treatment": "Soft colors, slight film grain texture, naturalistic"
  }
}
```

**学点**：
- **JSON 完整表单式结构**：subject/face/hair/clothing/accessories/environment/lighting/camera/style 九个字段 = 一张结构化表单，比示例14单字段更细。适合"全面覆盖无遗漏"的场景（共性规律14的分段编号的 JSON 版）。
- **冷红脸颊（cold flush）= 环境温度写在皮肤上**：`distinct rosy cheeks and nose (cold flush)`——把"冷"翻译成脸部的可见证据，和例13眼神微证据同一思路。
- **雪花落发 = 环境×人物交互**：`hair covered in varying sizes of white snowflakes` + 服装上 `dusted with fresh snow`——环境不只背景，要"写到人身上"（共性规律16）。
- **阴天扁平光（overcast flat lighting）**：`very soft, minimal shadows on face`——阴天漫射光是一种独立光质，柔和平静氛围用。
- 时代感靠服装+背景人群：paisley 编织披肩 + 远景穿时代服装的人群 = 年代锚点（呼应共性规律15）。
- 85mm 再点名。

---

### 示例16 · 复古湿版摄影中的年轻女性（en）

```
A vintage wet-plate photograph of a young woman standing in a windy, indistinct outdoor landscape.
She wears a textured, ribbed V-neck wrap dress with a cinched waist and three-quarter sleeves.
Her hair is styled in a messy low bun with windswept strands framing a face with sharp cheekbones
and dark lipstick. She looks away to the right in profile with a serene, contemplative expression.
The image style mimics a damaged daguerreotype with a monochromatic sepia palette, heavy film
grain, surface scratches, and dust. A horizontal motion blur or smear effect runs across the image,
creating a ghostly, ethereal, and worn aesthetic.
```

**学点**：
- **复古工艺点名 = 比胶片模拟更早的帧**：`wet-plate（湿版）/ damaged daguerreotype（达盖尔银版）`——点名更早的摄影工艺，配 monochromatic sepia + heavy grain，年代感直接拉到摄影史早期（共性规律17）。
- **刻意做旧**：`damaged + surface scratches + dust`——主动加瑕疵做旧成"文物"，是共性规律10"可信小瑕疵"的极端版。
- **水平涂抹模糊贯穿画面**：`horizontal motion blur or smear effect runs across the image`——制造鬼影/飘渺/磨损美学，一种特殊运动模糊（区别于例12人群模糊）。
- 侧影 profile + 看向画面外 = 氛围感构图，避开正脸对视。

---

### 示例17 · 风中的美丽中国少女（en，ar 2:3）

```
A cinematic, film-style portrait of a beautiful Chinese young woman. Her messy black hair is blown
by the wind, partially covering her face, while her expressive eyes look directly into the camera.
She is positioned in the left third of the frame. She wears a thick, bright red knitted scarf and a
worn beige shearling jacket. The background shows a cold, dry wilderness and distant mountains at
sunset. Intense golden backlight shines directly into the lens, creating strong lens flare and a
hazy glow, with dust particles visible in the air. Film grain texture, shallow depth of field, and
a raw, natural aesthetic. ar 2:3
```

**学点**：
- **红色高饱和色彩锚点**：`bright red knitted scarf`——灰黄荒野里唯一的高饱和红，人物立刻跳出来。色彩表达不只"冷暖对比"（例13），还有"饱和度锚点"这一招。
- **强逆光直射镜头 = 风格元素不避讳**：`intense golden backlight shines directly into the lens, strong lens flare, hazy glow`——把镜头光晕/眩光当风格，不写"避免眩光"，反而强调。
- **灰尘粒子在空气中可见**：`dust particles visible in the air`——空气可见=氛围，和例13尘埃光点、示例10彩虹光斑同族。
- 三分构图：`positioned in the left third of the frame`。
- 2:3 画幅——即梦固定 3:4，构图按 3:4 重写。

---

### 示例18 · 自然美与工业质感对比的年轻女性全身像（en，完整相机参数）

```
12K hyper-realistic cinematic full-body portrait of a young woman, using the uploaded image
strictly for 100% natural face and identity match (do not alter facial features or proportions).
She is leaning effortlessly against a weathered gray concrete wall partially covered with climbing
red and soft pink roses, creating a poetic contrast between raw texture and natural beauty.

She wears an oversized deep umber button-down shirt styled loosely over crisp white tailored
trousers, exuding understated elegance. Accessories include a minimal silver chain necklace and a
refined black-dial wristwatch that subtly catches the light. Her hair appears voluminous and
naturally flowing, enhancing the cinematic presence.

The mood is moody yet softly lit, with gentle natural light shaping her features and creating a
shallow depth of field that softly blurs the background. Shot on a Canon EOS R5 with an 85mm lens
at f/1.8, ISO 400, 1/160 shutter speed. Ultra-detailed skin texture, realistic fabric folds,
cinematic color grading, editorial fashion photography aesthetic, premium realism, flawless clarity
```

**学点**：
- **完整相机参数点名 = 锁死电影感**：`Canon EOS R5 + 85mm f/1.8 + ISO 400 + 1/160`——机身+镜头+光圈+ISO+快门全给，比单写"85mm f/1.8"更彻底（共性规律18）。
- **质感对比 = 构图主题**：`weathered gray concrete wall + climbing red and soft pink roses`——粗糙工业质感 vs 自然柔美，用环境材质本身做诗性对比，不用道具堆情绪。
- **参考图身份锁定写法**：`use the uploaded image strictly for 100% natural face and identity match (do not alter facial features)`——换装不换脸的模式，写清"不要改五官"。

---

### 示例19 · 金色黄昏下的木制阳台（en，JSON 多级嵌套）

```
{
  "image_generation": {
    "style": "cinematic, realistic photography",
    "scene": {
      "location": "wooden viewpoint balcony overlooking a city",
      "time": "golden hour at sunset",
      "background": ["city below", "soft focus hills", "tall communication tower"],
      "sky": "pastel tones with gentle clouds",
      "mood": "calm, dreamy, peaceful"
    },
    "subject": {
      "type": "young woman",
      "pose": "standing and leaning casually against the wooden railing",
      "expression": "relaxed and thoughtful",
      "gaze": "looking outward over the city",
      "interaction": "standing beside a resting bicycle and a sleeping cat"
    },
    "outfit": {
      "top": "oversized grey knitted sweater",
      "bottom": "long brown skirt",
      "shoes": "brown ankle boots",
      "accessory": "small leather crossbody bag"
    },
    "props": ["white folding bicycle resting beside her", "orange cat sleeping on the wooden railing"],
    "lighting": { "type": "warm sunset light", "highlights": "soft and warm", "shadows": "gentle and cool" },
    "camera": { "lens": "35mm", "depth_of_field": "shallow", "bokeh": "soft", "focus": "sharp on subject, blurred background" },
    "color": { "palette": "natural pastel tones", "saturation": "balanced and soft" },
    "quality": { "detail": "high", "texture": "natural skin, fabric and wood detail", "finish": "editorial cinematic look" }
  }
}
```

**学点**：
- **JSON 多级嵌套**：style/scene/subject/outfit/props/lighting/camera/color/quality 多级嵌套，比示例15更深——适合"每个维度都有多个子项"的复杂场景。
- **场景叙事道具**：`white folding bicycle + orange cat sleeping on railing`——两件道具就立住"日常慵懒黄昏"氛围，比列十个元素有效。
- **暖高光/冷阴影**：`highlights soft and warm, shadows gentle and cool`——光的三段式里加**色温对比**维度（呼应例13冷暖对比）。

---

### 示例20 · 追逐地平线的永恒阳光（zh，Velvia 高饱和胶片模拟）

```
追逐地平线，定格永恒的阳光。🌻🚙 没有比开着复古敞篷车，手捧向日葵，行驶在无尽的公路上更让人
感到自由的了。这画面充满了夏日旅行 Vlog 的鲜活感，色彩浓郁，仿佛能感受到加州的阳光洒在肩头。

创作灵感: 这幅作品采用了 Fujifilm Velvia 胶片模拟风格，通过高饱和度和高对比度，
让车身的湛蓝与花朵的金黄形成强烈视觉冲击。构图上使用了 24mm 广角镜头配合低角度仰拍
（Worm's-eye view），利用强烈的透视关系突出了前景的花束，同时保留了远处山脉的景深，
营造出极具张力的空间感。
```

**学点**：
- **Velvia 胶片模拟 = 高饱和高对比**：与 Classic Negative（低对比怀旧）正相反——鲜艳的旅行/风光片用 Velvia，怀旧人像用 Classic Negative，选对口味（补充块1）。
- **24mm 广角 + 低角度仰拍（worm's-eye view）→ 强制透视**：广角+低机位放大前景花束、突出天空山脉纵深，制造张力构图（区别于 85mm 压缩感）。
- **逆光勾轮廓**：Backlighting 让被摄体轮廓清晰 + 戏剧感（呼应例17）。

---

### 示例21 · 慵懒性感东方面孔女性（en，Grok / cast 日志结构）

```
{ "casting_log": {
    "subject_archetype": "Sweet, cozy, but undeniably sexy.",
    "apparel_strategy": "Layering lingerie under cozy knitwear creates a powerful 'at home'
      contrast that is highly suggestive."
  },
  "execution_params": { "aspect_ratio": "4:3", "focus_point": "Eyes and exposed shoulder/lingerie strap" },
  "google_prompt": "A candid photograph of a sweet-faced East Asian woman lounging on a plush sofa,
    curled up under a blanket. She is wearing a delicate black lace bralette under a chunky, open
    cream-colored knit cardigan. The cardigan sits off one shoulder, revealing the lingerie strap
    and her sharp collarbone. She is holding a book but looking up at the camera with a gentle,
    relaxed smile. The pose is cozy but revealing. Soft, natural indoor light. The focus is soft
    and intimate, emphasizing the textures of the knit and lace. It feels like a lazy Sunday
    morning snapshot." }
```

**学点**：
- **叠穿暗示法（cozy but sexy）**：`black lace bralette under chunky cream knit cardigan`——内衣叠穿在舒适针织下 = 高暗示低暴露，是克制性感的结构性手法，比"露肩"更隐晦（共性规律19）。
- **focus_point 明确**：`Eyes and exposed shoulder/lingerie strap`——明确焦点落点，肩带/锁骨是暗示锚点，镜头知道看哪。
- **cast 日志结构**：casting_log（策略层：人物原型+服装策略）+ execution_params（执行参数）+ 实际 prompt——三层分工，策略写在日志里、成句给模型。

---

### 示例22 · 韩国K-pop偶像肖像（en，prompt_analysis + full 双轨）

```
{ "prompt_analysis": {
    "subject": ["1girl", "Korean K-pop idol", "cute and sexy (pure sexy vibe)", "playful expression",
      "flirty smile", "looking at viewer (eye contact)", "blushing cheeks"],
    "angle/composition": ["Boyfriend POV (girlfriend scenario)", "close-up shot", "slightly looking up",
      "intimate distance"],
    "clothing": ["white fluffy sweater (off-shoulder)", "winter date outfit", "soft texture"],
    "lighting/atmosphere": ["heavy soft focus", "dreamy haze", "halation (bloom effect)",
      "romantic night lighting", "city lights bokeh", "glowing skin"],
    "style": ["90s retro idol aesthetic", "film photography", "vintage lens style", "misty filter", "aesthetic"]
  },
  "full_prompt_string": "Boyfriend POV, close-up shot of a cute and sexy Korean K-pop idol with a
    flirty sweet smile, looking directly into the camera with alluring eyes. She is wearing a soft
    fluffy white sweater, winter night date scenario. Heavy soft focus, diffusion filter effect,
    dreamy hazy atmosphere, halation, glowing skin, city lights bokeh in background. Retro 90s
    aesthetic, film photography, romantic vibe, high quality, 8k." }
```

**学点**：
- **prompt_analysis 数组 + full_prompt_string 双轨**：先给模型结构化分析（subject/角度/服装/光/风格各成数组），再给成句 prompt——既喂结构又喂句子，两个都能吸收。
- **Boyfriend POV（女友/男友视角）**：亲密距离 + 近景 + 微微仰视 + 对视，一种可复用的 POV 类型（呼应例1自拍POV/例3情侣POV）。
- **halation（泛光）+ diffusion filter（柔焦扩散）**：柔焦滤镜效果 + 90s 复古偶像审美 + city lights bokeh——柔美梦幻向的风格配方。

---

### 示例23 · 成人世界的未知体验（en，Y2K 千禧年数码相机帧）

```
#prompt: Nighttime photograph of a young woman taken with an early-2000s digital camera,
Canon IXUS, strong flash, compact camera style (keep the face and features identical to the
original 100%, do not modify).

A young woman stands taking a photo of herself in a mirror inside a bedroom with a white–gray
color tone, clean and minimal atmosphere. She stands turned slightly to the right, her left hand
holding a digital camera up at face level while calmly looking at the camera screen. She has long,
straight dark hair flowing down her back. She wears a white strapless top with a cute cartoon print
on the front and puffed short pants with a gray checkered pattern, clearly revealing a slim figure
with naturally large breasts.

Behind her is a bed covered with light-colored bedding, with several brown and cream teddy bears
neatly arranged. Beside the bed is a white shelf; on it is a framed photo of the same woman, with a
cream-colored teddy bear placed in front. Next to it are books, a small box, and small minimalist
accessories. The room lighting is soft with a cool tone, making the image look clean, calm, orderly.

Same hairstyle, with small strands of hair partially covering the face, remove the flower from the
ear. Hair slightly blowing, chic, cool, and sexy, with lightly messy layers. Pink blush on the
cheeks, with a soft rosy tone on the cheeks and nose. Lips in a pink-orange shade.

Looking directly at the camera, cute expression, dreamy, innocent, and playful.
Pose: running fingers through the hair in a sexy way.

Canon IXUS flash hitting the face directly.
```

**学点**：
- **Y2K 千禧年数码相机点名 = 独立风格帧**：`early-2000s digital camera / Canon IXUS / strong flash / compact camera`——千禧年数码相机质感（强直闪、死白高光、冷调、略低清）是摄影史的另一端，和 35mm 胶片、湿版做旧（例16）方向相反（共性规律20）。
- **镜前自拍构图**：`taking a photo of herself in a mirror`——镜头拍镜子里的她 + 她手里的相机 + 屏幕亮光，镜像构图自带叙事层次。
- **编辑式细节修正**：`remove the flower from the ear`——直接写"删掉 X"，是编辑式约束；`keep the face 100% identical, do not modify` 锁身份。
- **房间细节一致性锚点**：`a framed photo of the same woman`——房间里摆着"同一个女人的相框"，场景内一致性锚点。

---

### 示例24 · KR_Idol 无缝生活拼贴（en，宫格/跨格一致性）

```
{
  "system_architecture": {
    "version": "KR_Idol_PureDesire_v2",
    "project_id": "Seamless_Life_Collage",
    "framework": {
      "format": "2x2 Seamless Grid (Zero Gap)",
      "aspect_ratio": "3:4",
      "composite_mode": "Perfectly fused edges / No white borders / No gutters",
      "engine_mode": "Analog Film Emulation / K-Pop Visual Aesthetic"
    }
  },
  "biometric_anchor": {
    "subject_desc": "Korean K-pop idol, visual member, pure and sexy aura",
    "identity_logic": {
      "consistency_lock": "100% facial feature match across quadrants",
      "vibe_blend": "Innocent face + Alluring vibe (Pure Desire style)",
      "surface_parameters": ["Pale glass skin", "Soft peach blush", "Slight sweat/glow for realism", "Film grain texture"]
    }
  },
  "quadrant_temporal_logic": {
    "quadrant_01": { "id": "MORNING_BED", "perspective": "POV Boyfriend / High angle looking down",
      "state_logic": { "facial": "Messy hair, rubbing one eye, lips slightly parted, defenseless look",
        "pose": "Lying on stomach, propped up on elbows, looking up lazily",
        "apparel": "Oversized white boyfriend shirt (one shoulder slipping off)" },
      "environmental_logic": { "location": "White bed sheets", "lighting": "Hazy overexposed morning sunlight", "style": "Dreamy, soft focus, intimate" } },
    "quadrant_02": { "id": "PRACTICE_SWEAT", "perspective": "Mirror Selfie (Floor level)",
      "state_logic": { "facial": "Biting lower lip playfully, wink, flushed cheeks from exercise",
        "pose": "Sitting with legs stretched out towards mirror, phone covering half face",
        "apparel": "Tight crop top + Grey sweatpants (waistband folded)", "accessory": "Cute stickers on phone case" },
      "environmental_logic": { "location": "Dance Studio", "lighting": "Mixed fluorescent and window light", "style": "Authentic grit, slight motion blur" } },
    "quadrant_03": { "id": "STREET_SUMMER_VIBE", "perspective": "High-Angle Candid (The 'Puppy' Angle)",
      "state_logic": { "facial": "Looking up at camera with wide innocent eyes, cooling cheek with a cold glass bottle",
        "pose": "Squatting/Crouching next to a retro vending machine, knees together (cute but alluring silhouette)",
        "apparel": "Short pleated skirt + fitted camisole" },
      "environmental_logic": { "location": "Street corner / Vending Machine", "lighting": "Golden hour sunlight hitting the face, lens flare", "style": "Vibrant colors, nostalgic summer film vibe, visually distinct" } },
    "quadrant_04": { "id": "NIGHT_FLASH_FUN", "perspective": "Direct Flash Close-up",
      "state_logic": { "facial": "Scrunching nose, messy eating (cream/sauce on lip), playful eye contact",
        "pose": "Leaning in very close to the lens, holding a snack/pizza slice",
        "apparel": "Silk pajamas or comfy homewear" },
      "environmental_logic": { "location": "Dimly lit living room", "lighting": "Harsh direct camera flash", "style": "Retro disposable camera aesthetic, high contrast" } }
  },
  "technical_pipeline": {
    "optical_simulation": { "film_stock": "Kodak Portra 400 (Warm & Grainy)", "lens": "35mm Prime", "effects": "Halation, Film Grain, Light Leaks" },
    "prohibition_matrix": {
      "elements": "NO TEXT, NO WATERMARKS, NO BORDERS, NO FRAMES, NO SPLIT LINES",
      "quality": "No bad anatomy, no blurry face",
      "vibe": "No western makeup style, no overly sexualized poses (keep it subtle/suggestive)"
    }
  }
}
```

**学点**：
- **宫格 = 四象限时间线叙事**：MORNING_BED→PRACTICE_SWEAT→STREET_SUMMER→NIGHT_FLASH = 一条"晨→夜"生活时间线，每格一个生活时刻，**不是四张无关图**（共性规律21）。
- **identity lock（跨格一致性锁）**：`biometric_anchor + 100% facial feature match across quadrants` + 统一 surface_parameters（玻璃肌/腮红/胶片颗粒）——显式锁脸，是预设A"配方块逐字复用"的显式版。
- **每格三要素自包含单元**：perspective（视角）+ state_logic（表情/姿态/服装）+ environmental_logic（地点/光/风格）——每格一个完整描述单元，且**四格视角刻意不同**（POV/镜前/高角/直闪）防雷同。
- **无缝隙拼贴硬约束**：`zero gap / fused edges / no borders / no gutters / NO SPLIT LINES`——宫格版式复刻的硬约束，与 SKILL.md"严格保持 N 宫格版式"互补。
- **每格光不同、风格帧统一**：四格四光（晨光/练舞混光/夕照/直闪），但统一 Kodak Portra 400 + halation + grain + light leaks——"每格内容变、整体帧不变"。
- **prohibition matrix 三层禁制**：elements（文字/水印/边框/分割线）+ quality（解剖/模糊）+ vibe（妆容/性感度）——负向按维度分组。

---

### 示例25 · Winter Forest 故事板系列（en，多帧故事板）

```
{
  "meta": { "title": "Winter Forest Storyboard Series", "theme": "Ethereal Winter Portraiture",
    "mood": "Serene, cold, nostalgic, festive, quiet" },
  "subject": { "demographics": "Young woman, approximately early 20s, Caucasian", "body_type": "Slim build",
    "pose_variations": ["Standing profile holding bouquet", "Sitting cross-legged in snow",
      "Leaning against tree trunk", "Lying supine on snowy ground", "Close-up embracing foliage"] },
  "hair": { "color": "Dark brown / Chestnut", "style": "Long, loose, natural waves",
    "texture": "Soft, sometimes messy or spread out on snow", "details": "Light dusting of snowflakes caught in strands" },
  "face": { "expression": "Peaceful, contemplative, soft, eyes often closed or looking away",
    "makeup": "Minimal/Natural, rosy cheeks (cold flush), nude lip", "features": "Soft jawline, natural brows" },
  "clothing": { "outerwear": "Long, oversized black wool coat or trench coat",
    "footwear": "Black heavy-duty winter boots with chunky tread",
    "accessories": "Black gloves (visible in some frames), dark leggings or trousers",
    "styling": "Coat often unbuttoned slightly or wrapped loosely" },
  "accessories": { "primary_prop": "Large bouquet of fresh fir/pine branches",
    "prop_details": "Wrapped in plain brown craft paper",
    "illumination": "Warm white fairy/string lights intertwining the branches", "secondary_prop": "Loose snow" },
  "environment": { "location": "Dense coniferous forest", "ground": "Deep, pristine white snow cover",
    "vegetation": "Tall pine/spruce trees with snow-laden branches", "atmosphere": "Cold, wintery, overcast" },
  "lighting": { "type": "Natural daylight, soft and diffused", "quality": "Overcast sky (cloudy day)",
    "contrast": "Low to medium contrast", "accents": "Subtle warm glow from fairy lights contrasting with cool daylight" },
  "camera": { "shot_types": ["Wide angle environmental shot", "Medium shot", "Close-up portrait",
      "Detail macro shot", "High-angle (looking down)"],
    "depth_of_field": "Shallow DOF (bokeh) for portraits, sharper focus for wide shots",
    "focus": "Sharp focus on subject/eyes, blurred forest background" },
  "style": { "aesthetic": "Cinematic storyboard, lifestyle photography",
    "color_palette": { "primary": ["Snow White", "Forest Green", "Black"],
      "accents": ["Brown (paper)", "Warm Gold (lights)", "Skin tone"] },
    "tone": "Muted saturation, cool temperature with warm highlights" },
  "frame_breakdown": [
    { "id": 1, "description": "Medium shot, standing, holding bouquet in brown paper, looking over shoulder." },
    { "id": 2, "description": "Sitting in snow, hugging bouquet to chest, head resting on greenery." },
    { "id": 3, "description": "Wide shot, sitting at base of trees, forest landscape dominant." },
    { "id": 4, "description": "Sitting near tree trunk, looking down introspectively." },
    { "id": 5, "description": "Close-up, face pressed into fir branches, eyes closed, fairy lights glowing." },
    { "id": 6, "description": "Macro detail shot of fir needles and glowing copper wire lights." },
    { "id": 7, "description": "Profile shot, walking through snow, holding bouquet." },
    { "id": 8, "description": "Leaning back against a large snowy tree trunk, holding bouquet low." },
    { "id": 9, "description": "Portrait, snowy hair, adjusting gloves or brushing snow." },
    { "id": 10, "description": "Lying on back in snow, hair fanned out halo-like, looking up at sky." }
  ]
}
```

**学点**：
- **故事板 = 一次定义角色 + 每帧只写变化**：人物/发型/脸/服装/道具/环境/光/色彩全在顶层定义**一次**，`frame_breakdown` 每帧只写"景别+动作+表情"一句，不重复外貌——一稿多帧的高效结构（共性规律22）。
- **跨帧一致性靠共享锚点**：十帧共用同一件大衣 + 同一个花束道具 + 同一色板（雪白/森林绿/黑 + 暖金点缀）——一致性不是靠重复描写，是靠"共享元素"。
- **每帧景别递进叙事**：medium→sitting→wide→close→macro→profile→portrait→lying，景别节奏本身就是叙事。
- **色彩系统 = primary + accents**：主色 + 点缀色分层定义，比一句话调色可控。

---

### 示例26 · Scribbly 涂鸦插画迁移（en，风格分维度穷举 + identity lock）

```
"prompt": "Use the uploaded image strictly as the identity reference. Preserve the same person,
exact facial structure, hairstyle, age, gender, body proportions, and overall likeness. Do not add
or remove any person. Do not change identity. Transform the subject into a messy, fun, scribbly
doodle-style illustration.

Doodle Illustration Style:
- Line art: hand-drawn doodle, uneven/rough/exaggerated line art, loose wobbly erratic lines,
  thick broken inconsistent outlines, rushed spontaneous energetic, visible pencil or crayon strokes.
- Color & Texture: bright pastel vivid colors, flat playful fill without careful detail,
  uneven imperfect scribbled-on colors, watercolor textures kept playful and imperfect.
- Facial Features: simple exaggerated childish, dot eyes, tiny squiggly smiles, tiny noses,
  rough uneven, lively fun expressions.
- Proportions & Form: slightly exaggerated, large head, simplified limbs, soft rounded shapes,
  stylized unrealistic anatomy, extra randomness (some parts bigger/smaller).
- Shading & Lighting: no realistic shading, rough pencil strokes or simple color blobs,
  minimal lighting, bright and flat without depth.
- Mood: fun quirky full of energy, carefree spontaneous, storybook or school notebook vibe.
- Background: mix of simple scribbly shapes, soft doodle marks, abstract forms
  (squiggles, hearts, stars, random lines), as loose as the subject.
Rendering Rules: no photorealism, no photo texture, no cinematic lighting, no digital painting,
no sharp clean edges, no detailed realism, rough spontaneous lines and colors.

Final Output: lively fun messy scribbly doodle illustration using crayon or colored pencil,
rough energetic lines, flat pastel colors, preserving the exact identity from the uploaded image
in a playful carefree doodle style.",
"negative_prompt": "photorealism, realistic skin texture, photo texture, cinematic lighting,
dramatic shadows, hyper-detail, anime, manga, 3D render, vector art, oil painting, digital painting,
glossy skin, sharp clean lines, realism, face change, identity change, extra people",
"quality": "high", "style_strength": "very strong scribbly doodle illustration",
"reference_usage": "exact face and identity preservation required"
```

**学点**：
- **风格迁移 = 分维度穷举 + identity lock**：把"涂鸦风"拆成 line art / color / facial / proportions / shading / mood / background / rendering rules **八个维度**逐条写死，同时 `use uploaded image strictly as identity reference, do not change identity` 锁脸（共性规律23）。
- **每个维度都是"不要写实"的具体化**：`no realistic shading / no digital painting / no sharp clean edges`——风格禁制写在每个维度里，不是一条负向清单。
- **插画负向清单可抄**：photorealism / photo texture / cinematic lighting / anime / 3D render / vector art / oil painting / digital painting / glossy skin / face change / identity change / extra people。
- **对照**：这是"风格从零描述"的详尽版，示例27 是一句话版——同一件事两种粒度。

---

### 示例27 · Concept Art 一句话生成器（en，系统提示词 / 250 字符约束）

```
role: "Concept Art Prompt Generator"
Objective: "Turn the user's concept into one image prompt in natural language, maximum 250
  characters, matching the specified hand drawn RPG aesthetic."
core_rules:
- "Output exactly one prompt, no extra commentary, no quotes, no markdown."
- "Maximum length: 250 characters total (including spaces and punctuation)."
- "Write a single sentence or a single sentence with commas; no line breaks."
- "Keep the user's concept as the subject; add only a few clarifying visual details."
- "If the user provides no setting, default to a simple neutral backdrop on paper."
style_guidelines:
- medium: "Production pencil sketch with soft watercolour and gouache washes on textured paper."
- linework: "Delicate, sketchy sepia or warm brown outlines, visible pencil construction."
- palette: "Muted, desaturated earth tones (cream, sage, rust), restrained highlights."
- vibe: "Nostalgic, elegant, high fantasy RPG character concept design, readable silhouette."
exclusions_and_safety:
- disallowed: "Photorealistic, photography, iPhone, camera, lens, cinematic HDR"
- "3D, CGI, Unreal Engine, Octane, Blender, render, ray tracing"
- "Vector art, logo, infographic, UI"
Formatting: "Subject + key attire/props + pose/mood + medium/style cues", max 250 chars.
quality_checks: "≤250 chars? one sentence no line breaks? medium + paper texture cue included?
  no disallowed mentions? no too many new details?"
example: input "A knight with a red cape" → Output "High fantasy knight with a rust-red cape,
  pencil production sketch with soft watercolour and gouache washes on textured cream paper,
  delicate sepia linework, muted earth tones."
```

**学点**：
- **250 字符一句话约束 = 极简 prompt 纪律**：`Subject + 道具 + 姿态情绪 + 媒介风格` 四段一句成型，无换行无多余——和 JSON 详尽式相反的另一端（共性规律24）。
- **风格四要素 = medium + linework + palette + vibe**：一句话里风格靠这四个锚点锁定，可抄进任何一句话 prompt。
- **exclusion 按媒介家族分类禁制**：photorealistic / 3D render / vector / UI——不是一条杂烩负向，是分类。
- **质量自检清单可借鉴**：字符数 / 单句 / 媒介+纸感 / 禁词 / 不添细节——出 prompt 前 5 项自查，可补进我们的生成前流程。
- 例子的成品直接示范了"一句话风格"长什么样。

---

### 示例28 · 炭笔+粉笔时尚编辑（en，i2i 画种迁移）

```
"input_type": "image_to_image", "target_image": "UPLOAD_IMAGE_HERE",
"prompt": "Use the uploaded reference image to preserve the subject's exact facial identity,
proportions, hair, and skin tone with zero alteration. Reimagine the portrait as a high-end
charcoal and chalk fashion editorial artwork. The subject may be a man or a woman; adapt styling
and pose accordingly while maintaining strength, confidence, and elegance. Render the face with
highly realistic charcoal detailing — rich blacks, soft greys, and precise facial structure —
while highlights on cheekbones, jawline, collarbones, and hair are created using subtle white or
warm chalk accents. Clothing is suggested through expressive charcoal strokes and tonal contrast,
implying Western luxury silhouettes without detailed textures. Pose is strong and editorial, calm
yet commanding. Background is minimal and atmospheric, composed of smudged charcoal gradients or
textured paper grain. Lighting is dramatic and directional, sculpting the subject through contrast
rather than color. Overall mood is bold, raw, timeless, and powerful — fashion editorial meets
fine-art charcoal portrait.",
"style": "charcoal and chalk fashion editorial", "preserve_identity": true, "preserve_face": true,
"style_strength": 0.9, "quality": "16K",
"negative_prompt": "color painting, watercolor wash, ink illustration, digital art look, cartoon,
anime, photorealism, smooth airbrush, explicit content, cluttered background"
```

**学点**：
- **画种点名 + 技法描述**：不只说"炭笔画"，还写怎么画——`rich blacks, soft greys, precise facial structure` + 高光用 `white or warm chalk accents`（共性规律25）。
- **媒介特性适配（知道炭笔能干什么）**：`clothing suggested through expressive charcoal strokes, implying silhouettes without detailed textures`——不要求炭笔画细腻纹理，反而写"暗示轮廓"。
- **光照靠对比不靠色彩**：`sculpting through contrast rather than color`——单色画种的正确光写法。
- identity lock 与示例26/18 一致：`preserve exact facial identity, zero alteration` + `preserve_identity/face: true`。
- 画种迁移家族至此凑齐：铅笔速写（例27）/ 涂鸦蜡笔（例26）/ 炭笔粉笔（例28）。

---

### 示例29 · Dune 环境塑造（en，超现实环境隐喻）

```
Concept: A storybook where the text creates the environment. [Input: Dune]

Analysis: Extract key settings, protagonists, sensory details, and dominant color palette.

Goal: An open book where the typography collapses into the physical world.

Rules:
- Base: An antique leather-bound book lying open on a dark mahogany desk.
- Transformation: The ink text creates the terrain — words pile up to form mountains,
  sentences flow like rivers, letters twist into trees or creatures.
- Scale: Isometric miniature world emerging from the page.
- Details: Paper texture, embossed letters, ink splatter turning into birds or debris.
- Lighting: Candlelight flickering, casting dynamic shadows that seem alive.

Output: Hyper-realistic fantasy realism, Octane render style.
```

**学点**：
- **环境 = 隐喻塑造，不是"在哪"**：`words pile up to form mountains / sentences flow like rivers / letters twist into trees`——环境由什么构成，而不是在什么地点。超现实主义世界观构建的写法（共性规律26）。
- **三步塑造法（base→transformation→scale）**：先给基准场景（书在桌面），再写变形规则（墨变地形），最后定尺度（等距微型世界）——环境塑造的可复用骨架。
- **细节参与世界构建**：`ink splatter turning into birds or debris`——连飞溅墨点都交代变成什么。
- **光写"活的"**：`candlelight flickering, dynamic shadows that seem alive`——动态光让静态环境有生命力。
- **风格点名收尾**：`Hyper-realistic fantasy realism, Octane render style`——超现实写实 + 渲染引擎点名。

---

### 示例30 · 雪板夏装少女（en，反季节反差）

```
"image_description": {
  "subject": { "type": "Human", "gender": "Female",
    "expression": "Laughing joyfully, eyes closed, mouth open in a wide smile",
    "pose": "Kneeling on a snowboard in the snow, leaning slightly forward, hands resting on the snowboard",
    "clothing": { "swimwear": "Bright pink bikini set (triangle top and tie-side bottoms)",
      "accessories": "Large, white padded winter gloves/mittens",
      "footwear": "White snowboard boots attached to bindings" },
    "hair": "Dark brown, shoulder-length, loose and slightly messy", "skin_tone": "Tan" },
  "action": "Snow is being thrown or falling around her, creating a dynamic, playful effect",
  "environment": { "setting": "Snowy mountain slope (ski resort or backcountry)",
    "ground": "Covered in white snow",
    "background": "Evergreen trees (pine or fir) and blurred mountains under a clear sky",
    "lighting": "Bright, natural sunlight, casting soft shadows" },
  "mood": "Playful, energetic, happy, adventurous, contrasting (summer swimwear in winter setting)",
  "technical_details": { "camera_angle": "Eye-level or slightly low angle",
    "focus": "Sharp focus on the subject, slightly blurred background (shallow depth of field)",
    "color_palette": "High contrast between the bright pink bikini, white snow, and dark green trees" }
}
```

**学点**：
- **反季节反差 = 视觉钩子**：`summer swimwear in winter setting`——服装与环境反差本身就是画面卖点，连 mood 里都写出来，是"刻意制造的反差"（共性规律27）。
- **高对比三色系统**：`bright pink bikini vs white snow vs dark green trees`——粉色/雪白/松绿三色高对比锚定，不用堆色。
- **动作×环境交互**：`snow is being thrown or falling around her`——环境参与动作（呼应共性规律16），比"站在雪地里"生动。
- 结构简洁：subject/action/environment/mood/technical_details——另一套 JSON 骨架，可用于动作场景。

---

## 四、跨示例共性规律（27 条共识）

1. **一张图只秀一种光**，光必须三件套：光源（机顶闪光/窗光/逆光）+ 照在哪（脸颊/背部/发丝）+ 什么效果（镜面高光/边缘光/眼神光）。
2. **主角配方块（块2）逐字复用 = 跨图一致性**，实例3/6/8 已示范；改动只在发型/底调/服装/场景。
3. **手部风险四级规避**：第一人称POV局部入画（例3）> 手臂做前景（例1）> 手做支撑动作（例6）> 道具/手远离镜头（例7）。正面持物永远最后考虑。
4. **克制的性感 > 直白性感**：`诱人却略显脆弱的目光`、`露肩而非裸露`、`美背+柔光+布料`——用可见姿态和光线表达，不堆裸露词。
5. **风格帧二选一不混搭**：胶片写实 / 日系负片 / 直射闪光是三种独立帧，混用必串味。
6. **调色反向约束要写**：`不黄、不过滤镜`（例3）、`不是普通穿搭图`（例7），防止模型自由发挥溢出。
7. **场景定调词放开头**：`warm vintage Japanese onsen ryokan aesthetic`（例6）——场景联想直接决定全片调性。
8. **氛围也写"不要什么"**：`not resembling any real celebrity`（例4）防撞脸、`no excessive glamour`（例4）防过度华丽。
9. **姿态不对称破摆拍感**：对称=摆拍，不对称=抓拍。`一条腿弯曲另一条放松 + 身体微倾 + 肩膀不对称 + 头倾斜`（例9）——四条不对称写满。非直视镜头（侧看/低头/微转）同理（技法五第3招）。
10. **主动加入可信小瑕疵增强纪实感**（GPT模板 + 例3肤质"faint imperfections"）：过度完美=塑料感，留一点"拍出来的真实"反而不假。可翻译成 `保留自然瑕疵和轻微不完美，不做过度润色` 加进肤质块。
11. **胶片模拟点名 = 最强风格帧**：`Fujifilm Classic Negative（富士经典负片）`、`35mm f/1.8` 这类专名词，一个词锁死一套风格，比堆质感词更准更省（例10/11）。块1可扩：`{富士经典负片 / 柯达 Portra 400 / Cinestill 800T} 胶片模拟，低对比暗部，柔和高光，真实胶片颗粒`。
12. **叙事性布光（diegetic lighting）= 光源来自画面内物体**：冰箱 LED / 手机屏 / 霓虹牌当唯一光源，天然自洽、明暗对比强、背景自动隐黑（例11）。比泛写"氛围光"更能出电影感。
13. **眼神微证据写情绪**：`眼周微红、眼中略带血丝`（例13）表达克制忧伤——用生理微细节，不用情绪词。可写 `眼周微红、睫毛微湿、眼中略带血丝`。
14. **分段编号结构 = 复杂肖像骨架**：一~七节编号（主体/构图/光/色彩/背景/后期/负向），每节独立、注意力分配更稳（例13）。复杂图用这个，简单图用七层就够。
15. **年代感 = 时代符号清单**：写"1970s/复古"不抽象，用服装/妆容/道具/色调/场景的具体时代元素点名（例14）。
16. **环境×人物交互细节**：雪花落发、冷红脸颊（cold flush）、风里碎发——环境不只在背景，要"写到人身上"（例15/17）。这是环境真实感的关键，比"氛围冷"具体得多。
17. **复古工艺点名 + 刻意做旧**：`湿版/达盖尔银版 + 划痕 + 灰尘 + 水平涂抹模糊`（例16）——比胶片模拟更早的工艺帧，且主动做旧成"文物"，是可信小瑕疵（规律10）的极端版。
18. **完整相机参数点名 = 锁死电影感**：`Canon EOS R5 + 85mm f/1.8 + ISO 400 + 1/160`（例18）——机身+镜头+光圈+ISO+快门全给，比单写镜头更彻底。胶片模拟同理要选对口味（Velvia=高饱和鲜艳 / Classic Negative=低对比怀旧）。
19. **叠穿暗示法（cozy but sexy）**：内衣叠穿在舒适针织/家居服下 = 高暗示低暴露（例21），是克制性感的结构性手法，比"露肩"更隐晦。配 `focus_point：眼睛和露出的肩带/锁骨`，让镜头知道看哪。
20. **早期数码相机点名 = Y2K 千禧风帧**：`Canon IXUS + strong flash + compact camera`（例23）——千禧年数码相机质感（强直闪、死白高光、冷调、略低清）是独立风格帧，与 35mm 胶片（规律1）、湿版做旧（规律17）是摄影史的三个不同方向。拍"怀旧但不胶片"就用它。
21. **宫格 = 四象限时间线叙事 + identity lock**：每格一个生活时刻（晨→夜），`biometric_anchor` 显式锁跨格人脸一致，每格视角刻意不同防雷同，无缝隙拼贴硬约束（例24）。对应即梦 `严格保持 N 宫格版式不变，不要变多不要变少，每格换新画面`（SKILL.md 宫格版式复刻）。
22. **故事板 = 一次定义角色 + 每帧只写变化**：人物/服装/道具/环境/光在顶层定义一次，`frame_breakdown` 每帧只写"景别+动作+表情"一句，不重复外貌（例25）。跨帧一致性靠"共享服装+道具+色板"锚点，不是重复描写。
23. **风格迁移 = 分维度穷举 + identity lock**：把目标风格拆成 line art / color / facial / proportions / shading / mood / background / rendering rules 八维度逐条写死，同时 `use uploaded image strictly as identity reference, do not change identity` 锁脸（例26）。
24. **一句话 prompt 纪律 = 250 字符单句 + 风格四要素**：`Subject + 道具 + 姿态情绪 + 媒介风格` 四段一句成型，风格靠 medium/linework/palette/vibe 四锚点锁死（例27）。和 JSON 详尽式是同一件事的两种粒度。
25. **画种点名 + 技法描述 + 媒介特性适配**：不只说"炭笔画"，还写怎么画（rich blacks/soft greys/white chalk highlights），且知道媒介能干什么（衣物用笔触暗示轮廓，不要求细纹理）（例28）。
26. **环境 = 隐喻塑造，不是"在哪"**：文字变地形、飞溅墨点变鸟——环境由什么构成而不是什么地点；base→transformation→scale 三步塑造法 + 动态光（例29）。
27. **反季节反差 = 视觉钩子**：服装与环境反差（夏装冬景）本身就是卖点，配三色高对比系统（粉/白/绿）+ 动作×环境交互（例30）。

---

## 五、技法笔记 · 前景失焦光斑遮挡法（室内人像私密感）

**来源**：一组成功室内写真的复盘（用户提供）。无完整 prompt，但技法本身可迁移——核心是**让光变成前景道具**。

**技法原理**：人物一直坐在同一把复古椅子上，但镜头前挡一层失焦发光体（水晶光/金色散景），画面立刻多出"隔着什么在看她"的距离感，普通室内人像变私密。光不再只是照明，而是把画面切出**清晰区 / 柔化区 / 闪烁区**三个层次。

**可抄句式**：
```
镜头前有一片失焦的{水晶/散景/烛光/霓虹}光，虚化如光斑，微微遮挡人物一部分{脸/身体}，
形成"隔着光看她"的距离感；人物位于明暗交界处，脸在光影交界里露出来，
视线先穿过光再落到人物身上；前景光保留大片金色散景，主动遮住右侧部分空间，不全部交代背景。
```

**复盘五招（逐条可迁移）**：
1. **脸放明暗交界**：`脸就在明暗交界里露出来`——高对比处放脸 = 视线锚点。
2. **服装融入环境综合色**：奶油白蕾丝 + 室内暖棕/金 = 同一综合色系，`衣服很亮却不从环境里硬跳出来`。写 prompt 把服装色和场景主色绑成一组。
3. **非直视镜头**：侧看 / 低头 / 轻微转身，破除标准棚拍感，`更像人沉在自己的状态里`。
4. **松散轮廓**：松散盘发 + 脸侧卷发，`轮廓不梳规整，和蕾丝柔光放一起人物更软`。
5. **背景不必交代完整**：`留一点挡住镜头的光，反而更容易让人想往里面看`——遮挡/留白优于全交代。

**对即梦的迁移**：
- 与预设A"前景运动模糊"同一原理：**前景遮挡层（失焦光斑 / 运动模糊）是低成本加私密感+空间层次的手段**。
- 防翻车：`前景失焦光斑`易触发"光斑盖脸"或"高光过曝"，硬约束加一句`光斑虚化柔和，不遮挡五官清晰度`。

---

## 六、写实摄影结构化模板（GPT Image 2）

**来源**：GPT Image 2 用图 prompt 生成模板（用户提供）。与即梦七层结构同构，但多了"文本/输出"字段（面向能准确画字的模型）。作为跨模型结构参考保留。

**模板字段**：
```
- 主体：[要生成的产品、人物、空间、界面或信息主题]
- 场景：[使用环境、叙事背景、受众语境]
- 构图：[画面比例、镜头距离、主体位置、层级关系]
- 风格：[材质、光线、色彩、时代感、品牌气质]
- 文本：[必须准确显示的标题、标签、按钮或说明文字]
- 细节：[关键装饰、辅助元素、信息标注、交互层]
- 输出：[清晰度、比例、完成度、可读性要求]
```

**核心约束**：
- 指定机位、镜头、光源、质感、背景和动作（与即梦"写照片"心法一致）。
- **加入可信的小瑕疵增强纪实感**——主动加瑕疵 > 过度完美，与"不过度磨皮"互补（共性规律10）。
- 需要时加入手部、文字、结构类负面约束（与块6负向块同源）。

**对即梦的迁移**：即梦固定 3:4 且默认禁文字，`文本/输出`两字段按需删掉；`可信小瑕疵`翻译进肤质块：`保留自然瑕疵和轻微不完美，不做过度润色`。

---

## 七、使用提示

- 同款场景/光线需求，先在本库找示例抄骨架（如夜间霓虹→示例2、逆光→示例7、闪光灯→示例8、三联→示例5、韩系极简→示例9、逆光花墙→示例10、单光源黑暗→示例11、人群虚化→示例12、梦幻强逆光→示例13、70s年代感→示例14、冬日雪景→示例15、湿版做旧→示例16、强逆光色彩锚点→示例17、完整相机参数→示例18、JSON嵌套+叙事道具→示例19、Velvia高饱和广角→示例20、叠穿暗示→示例21、POV+柔焦→示例22、Y2K数码相机→示例23、宫格时间线拼贴→示例24、多帧故事板→示例25、涂鸦迁移→示例26、一句话风格→示例27、炭笔画种迁移→示例28、环境隐喻→示例29、反季节反差→示例30、前景遮挡→技法五、跨模型结构→六）。
- 拼装顺序：**场景定调词（开头）→ 主角配方块 → 姿态 → 服装/织物 → 光的三件套 → 肤质/发丝细节 → 风格帧 → 负向块**。
- 画幅：示例原比例仅供参考，即梦固定 3:4，构图描述按 3:4 重写。
- 需要文字（签名/涂鸦）的示例（例4/5）如无需求，按预设库硬约束块删文字禁词。
