# 时间轴 DSL 规范 v1

文件：`timeline.json`（UTF-8，无注释）。目的是**让人写时码、让机器算 keyTimes**。

## 顶层结构

```json
{
  "timeline":    { "duration": 22.3, "loop": true },
  "cues":        [ ... ],
  "typewriter":  [ ... ],
  "loops":       [ ... ],
  "interactive": [ ... ]
}
```

三段对应 SMIL 的三种驱动方式，语义互不重叠：**一个元素只能属于其中一段**。

---

## `timeline`

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `duration` | number | 是 | 主时间轴周期（秒）。建议 15~30。样本文章用 22.3 |
| `loop` | bool | 否，默认 true | true → `repeatCount="indefinite"`；false → `repeatCount="1"` |

所有 `cues` 共享这个周期，靠 `at`/`dur` 换算成 `keyTimes` 的 0~1 比例。

---

## `cues[]` — 挂主时间轴的一次性动作

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `id` | string | 是 | 对应 SVG 里的 `data-cue="id"` |
| `at` | number | 是 | 起始秒，0 ≤ at < duration |
| `dur` | number | 是 | 动作持续秒 |
| `effect` | string | 是 | 见效果表 |
| `length` | number | 仅 `draw` | 路径长度；不填则用 `pathLength="100"` 归一化 |
| `dx` / `dy` | number | 仅 `rise`/`sink`/`wipe` | 位移量，默认 dy=12 / dx=100 |

**编译规则**：令 `T = timeline.duration`，`a = at/T`，`b = (at+dur)/T`（自动 clamp 到 1）。
每个 cue 至少产出一条：

```
<animate attributeName="..." begin="0s" dur="{T}s" repeatCount="indefinite"
         values="{4 段}" keyTimes="0;{a};{b};1" />
```

四段是关键：`0→a` 保持初态、`a→b` 过渡、`b→1` 保持末态。这样在一个无限循环的大周期里，元素"只在该出现的时候出现"。

需要 `a == 0` 时 `keyTimes` 写成 `0;0;b;1`（允许相等，SMIL 允许非严格递增，只要不递减）。

### 效果表

| effect | attributeName | values | calcMode | 备注 |
|---|---|---|---|---|
| `fade-in` | opacity | `0;0;1;1` | linear | |
| `fade-out` | opacity | `1;1;0;0` | linear | |
| `appear` | visibility | `hidden;hidden;visible;visible` | discrete | 元素初始要写 `visibility="hidden"` |
| `vanish` | visibility | `visible;visible;hidden;hidden` | discrete | |
| `flash` | opacity | `1;1;0;0;1;1` | linear | keyTimes `0;a;a;b;b;1` |
| `rise` | opacity + transform | `0;0;1;1` + `0 {dy};0 {dy};0 0;0 0` | linear | 产出 2 条 animate |
| `sink` | opacity + transform | `1;1;0;0` + `0 0;0 0;0 {dy};0 {dy}` | linear | 产出 2 条 |
| `draw` | stroke-dashoffset | `L;L;0;0` | linear | 元素需 `pathLength="100"`；另产 1 条 visibility 保显示 |
| `wipe` | opacity + transform | `0;0;1;1` + `-{dx} 0;-{dx} 0;0 0;0 0` | linear | |

---

## `loops[]` — 独立常驻循环

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `id` | string | 是 | `data-cue` |
| `effect` | string | 是 | 见下表 |
| `dur` | number | 是 | 自身周期，与主时间轴无关 |
| `dy` | number | `breathe` | 位移量，默认 -12 |
| `amp` | number | `swing` | 摆幅角度，默认 8 |
| `pivot` | [x,y] | `swing`/`spin` | 旋转中心，**必填** |
| `from` / `to` | number | `pulse` | 默认 1 / 0.4 |

产出：`<animate ... begin="0s" dur="{dur}s" repeatCount="indefinite" />`，`keyTimes` 与 `values` 段数按效果固定。

| effect | 产出 |
|---|---|
| `blink` | opacity `values="1;1;0;0" keyTimes="0;.5;.5;1"` |
| `flicker` | opacity `values="1;1;0;1;1" keyTimes="0;.92;.95;.98;1"` |
| `breathe` | animateTransform translate `values="0 0;0 {dy};0 0" dur` |
| `swing` | animateTransform rotate `values="-{amp} cx cy;{amp} cx cy;-{amp} cx cy"` |
| `spin` | animateTransform rotate `values="0 cx cy;360 cx cy"` |
| `pulse` | opacity `values="{from};{to};{from}" keyTimes="0;.5;1"` |

**`flicker` 的 keyTimes 含义**：一个 4.2s 周期里，前 92% 全亮，92%~95% 灭，95%~98% 亮回——即每 4.2 秒"眨一次眼"。这是让静态插画显得活着的最省力手法。

---

## `typewriter[]` — 打字机逐字出现

把一段文字拆成逐字 `<tspan>`，每个字挂一条 discrete visibility animate，第 i 个字在 `at + i*per` 时刻出现。**在 `inject` 之后执行**（它会重写 text 内部结构，所以 CLI 里排在 inject 后面自动跑）。

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `id` | string | 是 | 对应 `<text data-cue="id"><tspan>文字</tspan></text>` |
| `at` | number | 是 | 第一个字出现的秒 |
| `per` | number | 否，默认 0.28 | 每字间隔秒；0.2~0.35 接近真人打字 |
| `cursor` | string | 否 | 光标元素的 `data-cue`，每出一字平移一个 font-size |

源码写法（tspan 是占位符，编译时被拆开）：

```svg
<text x="104" y="1656" font-size="38" font-weight="700" data-cue="p3-hello"><tspan>你好。</tspan></text>
<rect data-cue="p3-cursor" x="104" y="1632" width="16" height="34" fill="#1c1b18"/>
```

编译产出（第 i 个字，`a_i = (at + i*per)/T`）：

```
<tspan>你<animate attributeName="visibility" values="hidden;visible;visible"
        keyTimes="0;{a_0};1" calcMode="discrete" begin="0s" dur="{T}s" .../></tspan>
...
<rect data-cue="p3-cursor" ...>
  <animateTransform type="translate" calcMode="discrete"
        values="0 0;{fs} 0;{2fs} 0;...;{n*fs} 0;{n*fs} 0"
        keyTimes="0;{a_0};{a_1};...;{a_{n-1}};1" .../>
</rect>
```

要点与坑：

1. **不要给 tspan 手写 `dx`**。CJK 字形本身自然步进一个字宽，hidden 的字仍占位（不会回流）；再加 `dx=字号` 会把字距拉成两倍，光标就永远落后一拍（v1 踩过的坑）。
2. **光标步进按等宽假设**（每字 = font-size）：打字机文本请用纯中文/全角字符；中英混排会漂移。
3. **光标位置 = text 的起点 + 已出字数×字号**：光标 rect 的 `x` 写 text 起点，平移交给动画，不要手摆到终点。
4. 光标通常再配一条 `loops` 的 `blink`（1.1s 周期、后半周期 opacity=0）。注意**截图验证时选亮拍**：`t mod 1.1 < 0.55` 才可见，别把灭拍误判成"光标丢了"。
5. 若 text 元素本身还有 `cues` 里的 `appear`，打字机的逐字 visibility 会与之叠加——text 整体先 appear，逐字再依次显现，两者不冲突。

---

## `interactive[]` — 点击触发

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `ids` | [string] | 是 | 一组 `data-cue`，按顺序错开 |
| `trigger` | string | 否 | 目前只支持 `click` |
| `effect` | string | 是 | `draw-stagger` / `reveal-stagger` / `reveal` |
| `stagger` | number | 错开类 | 相邻元素的延迟秒，默认 0.12 |
| `dur` | number | 是 | 单次播放总长（含所有 stagger） |
| `length` | number | `draw-stagger` | 默认 100（配合 `pathLength="100"`） |
| `freeze` | bool | 否，默认 true | → `fill="freeze"` |

产出（第 i 个元素，延迟 `s_i = i*stagger/D`）：

```
<animate attributeName="visibility" values="hidden;visible;visible"
         keyTimes="0;{s_i};1" calcMode="discrete"
         begin="click" dur="{D}s" fill="freeze" restart="always" />
<animate attributeName="stroke-dashoffset" values="100;100;0;0"
         keyTimes="0;{s_i};{s_i+0.19};1"
         begin="click" dur="{D}s" fill="freeze" restart="always" />
```

三个属性一个都不能少：

- `begin="click"` → 点击才开始（**微信里唯一的交互入口**）
- `fill="freeze"` → 播完停在末态，不回弹
- `restart="always"` → 可以反复点

### 关键：透明热区 + 嵌套层（不做这个就点不动）

**`<g visibility="hidden">` 收不到点击。** 把 `begin="click"` 挂在 hidden 元素上，点了永远不触发——这是最常见的"点了没反应"。

样本文章的真实解法是**嵌套 N 层 g + 最内层放一个透明热区 rect**：

```svg
<g visibility="hidden" stroke-dasharray="100 100" stroke-dashoffset="100">
  <animate ... keyTimes="0;0;1"        begin="click" .../>   <!-- 第 1 条 -->
  <g data-cue="attn-1"><path .../></g>
  <g visibility="hidden" stroke-dasharray="100 100" stroke-dashoffset="100">
    <animate ... keyTimes="0;0.0229;1" begin="click" .../>   <!-- 第 2 条 -->
    <g data-cue="attn-2"><path .../></g>
    <rect x="0" y="0" width="750" height="2400"
          fill="#000" fill-opacity="0" visibility="visible" pointer-events="all"/>
  </g>
</g>
```

热区 rect 的三个要点：

| 属性 | 作用 |
|---|---|
| `fill-opacity="0"` | 完全透明，不挡视觉 |
| `visibility="visible"` | 必须显式可见，否则不参与命中测试 |
| `pointer-events="all"` | 强制接收点击（透明填充默认不接收） |

点击热区后，事件沿 DOM **冒泡**依次穿过每一层 g，于是 N 条 `begin="click"` 的 animate **同时被触发**，再靠各自递增的 `keyTimes` 依次显现。所以 stagger 不是 SMIL 的延迟能力，而是**嵌套结构 + 冒泡**造出来的。

脚本会自动生成这层结构，你只需要保证：

1. 交互组的元素在源码里**相邻且顺序与 `ids` 一致**
2. 元素自身**不要**预先写 `visibility="hidden"` / `stroke-dashoffset`（层 g 会提供；写在元素上会覆盖层 g 的动画结果，导致永远不显示）
3. 热区默认覆盖全卷；要限定区域用 `"hotspot": [x, y, w, h]`

`validate_svg.py` 会检查：有 `begin="click"` 却没有 `pointer-events="all"` → 直接报 error。

**配套要求**：元素初始必须 `visibility="hidden"`，且画面上要有文字提示（样本写的是 `[ 点一下，看它们在看谁 ]`），否则读者不知道这东西能点。

---

## 完整示例

```json
{
  "timeline": { "duration": 22.3, "loop": true },
  "cues": [
    { "id": "cover-title", "at": 0.0, "dur": 1.8, "effect": "fade-in" },
    { "id": "cover-sub",   "at": 1.6, "dur": 1.2, "effect": "rise" },
    { "id": "ch1-body",    "at": 3.4, "dur": 1.6, "effect": "appear" },
    { "id": "ch1-arrow",   "at": 5.0, "dur": 1.2, "effect": "draw", "length": 248 },
    { "id": "ch2-body",    "at": 8.0, "dur": 1.6, "effect": "appear" },
    { "id": "cover-title", "at": 14.0, "dur": 1.0, "effect": "fade-out" }
  ],
  "typewriter": [
    { "id": "term-reply", "at": 8.8, "per": 0.3, "cursor": "term-cursor" }
  ],
  "loops": [
    { "id": "term-cursor", "effect": "blink",   "dur": 1.1 },
    { "id": "orb-a",   "effect": "breathe", "dur": 3.6, "dy": -12 },
    { "id": "orb-a",   "effect": "flicker", "dur": 4.2 },
    { "id": "bell",    "effect": "swing",   "dur": 2.6, "amp": 9, "pivot": [648, 176] }
  ],
  "interactive": [
    { "ids": ["attn-1","attn-2","attn-3","attn-4"],
      "trigger": "click", "effect": "draw-stagger",
      "stagger": 0.12, "dur": 5.25, "length": 100 }
  ]
}
```

同一个 `id` 可以在 `cues` 里出现多次（如先入后出），也可以在 `cues` 与 `loops` 里各出现一次（如先淡入，之后常驻呼吸）。编译器会把多条 animate 并列插入同一元素。
