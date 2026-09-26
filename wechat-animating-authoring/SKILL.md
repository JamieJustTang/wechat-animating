---
name: wechat-animating-authoring
description: 为微信公众号长卷 SVG zine 产出「合格的 SVG 源码 + 时间轴脚本」。含静态骨架模板、SMIL 动效配方库、时间轴 DSL 规范，以及两个可执行脚本（timeline_compile.py 把时间轴编译成 SMIL 属性并注入 SVG；validate_svg.py 做微信白名单与 SMIL 合法性校验）。触发词：写 SVG zine、公众号 SVG 源码、SMIL 动画、时间轴脚本、keyTimes、begin=click、动画编译、SVG 校验、微信白名单、zine 源码。
---

# 长卷 SVG zine 写作规范

**核心方法：先静态，后动效，动效交给脚本。**

不要手写 `keyTimes`。手写 101 个 `keyTimes="0;0.0888;0.0987;1"` 是错一次死一次的活，而且错了不报错、只是不动。正确姿势是：

1. 写静态 SVG 骨架，给要动的元素打 `data-cue="id"` 标记
2. 写 `timeline.json`（人能读懂的时码表）
3. `timeline_compile.py` 编译并注入 → 生成带动画的最终 SVG
4. `validate_svg.py` 体检 → 0 error 才算完

## 一、骨架模板（照抄这一段起步）

```svg
<svg font-family="'PingFang SC','Noto Sans CJK SC',sans-serif"
     xmlns="http://www.w3.org/2000/svg"
     viewBox="0 0 750 11980"
     aria-label="zine"
     style="display:block;width:100%;height:auto;overflow:hidden;">
  <!-- 全部内容 -->
</svg>
```

**四个必填项，缺一不可**：

| 项 | 作用 | 漏了会怎样 |
|---|---|---|
| `viewBox` | 长卷坐标系 | 无缩放适配，手机上裁切 |
| `style="display:block;width:100%;height:auto"` | 撑满微信正文宽度（375px 基准）| 只显示局部 / 高度塌陷 |
| `overflow:hidden` | 防溢出元素撑破容器 | 版心错位 |
| 系统字体栈 | 微信不外链字体 | 字体回退，排版崩 |

**版心**：微信正文可视宽度约 375px，设计稿按 **750** 宽（2x），左右安全边距 40~74px（即内容区 750-2×74=602）。

**可用系统字体栈**：

```
中文黑体  'PingFang SC','Noto Sans CJK SC',sans-serif
中文宋体  'Songti SC','Noto Serif CJK SC',serif
等宽      Menlo,'Courier New',monospace
```

**配色**：从 `wechat-animating-style` 取，不要自己拍脑袋。一套 zine 只用 1 个主色 + 1 个纸底 + 1 个墨色 + 1 个灰。

## 二、静态元素的写法要点

- **文字用 `<text>` + `<tspan leaf="">`**：`<tspan leaf="">` 这个空属性是微信 sanitiser 的兼容性写法，加上更稳。
- **不用 `<foreignObject>`**：微信支持不稳，多行文字请自己 `<text>` 分行。
- **不用 `<image href="http...">`**：外链会被拦。位图要么转 base64（体积爆炸，慎用），要么**不用位图**（推荐，纯矢量才是 zine 的味道）。
- **坐标**：全部整数或一位小数。SMIL 对数值格式宽容，但手写时别搞 `1.1999999`。
- **装饰层**：可以另起一段更矮的 SVG 做背景水印层（样本文章用了 750×8377 的 `aria-label="far"` 背景层，只有 opacity 0.045 的"然而/但是"字样和网络节点图），主体再叠一层。

## 三、动效：三层模型

参考样本的分层，任何 zine 的动效都归这三类：

| 层 | 机制 | 典型用途 |
|---|---|---|
| **主时间轴** | 所有 `animate` 共用同一个 `dur`（如 22.3s）、`begin="0s"`、`repeatCount="indefinite"`，靠 `keyTimes` 排各自的出现时刻 | 自动播放的叙事：标题浮现、段落依次入场、画面推进 |
| **点击触发** | `begin="click"` + `fill="freeze"` + `restart="always"` | 读者点一下才发生的事：连线生长、答案揭晓、翻面 |
| **常驻循环** | 各自独立的 `dur`（1s~5s）、`repeatCount="indefinite"` | 氛围：呼吸位移、钟摆、光标闪烁、眨眼睛 |

**为什么主时间轴要共用一个 `dur`**：SMIL 没有全局时间轴概念，每个元素各跑各的。让它们共用同一个周期值，靠 `keyTimes` 的归一化比例（0~1）定位，就"伪造"出了一个全局时间轴。周期 = 叙事总长（15~30s 为宜）。

## 四、时间轴 DSL

写 `timeline.json`（完整规范见 `references/timeline-dsl.md`）：

```json
{
  "timeline": { "duration": 22.3, "loop": true },
  "cues": [
    { "id": "hero",  "at": 0.0, "dur": 1.6, "effect": "fade-in" },
    { "id": "sub",   "at": 1.8, "dur": 1.2, "effect": "rise" },
    { "id": "line1", "at": 3.2, "dur": 1.4, "effect": "draw", "length": 248 }
  ],
  "typewriter": [
    { "id": "term-reply", "at": 8.8, "per": 0.3, "cursor": "term-cursor" }
  ],
  "loops": [
    { "id": "term-cursor", "effect": "blink",   "dur": 1.1 },
    { "id": "node",   "effect": "breathe", "dur": 3.6, "dy": -12 }
  ],
  "interactive": [
    { "ids": ["a1","a2","a3"], "trigger": "click",
      "effect": "draw-stagger", "stagger": 0.12, "dur": 5.25, "length": 300 }
  ]
}
```

然后：

```bash
# 编译（只输出属性方案，人工检查）
python3 scripts/timeline_compile.py compile timeline.json

# 注入（把 <animate> 插进带 data-cue 的 SVG）
python3 scripts/timeline_compile.py inject timeline.json skeleton.svg -o zine.svg

# 校验
python3 scripts/validate_svg.py zine.svg
```

## 五、效果库（effect 一览）

### 挂主时间轴的（`cues`）

| effect | 作用 | 生成 |
|---|---|---|
| `fade-in` | 淡入并保持 | opacity `0;0;1;1` |
| `fade-out` | 淡出并消失 | opacity `1;1;0;0` |
| `appear` | 硬切出现（无渐变） | visibility discrete `hidden;hidden;visible;visible` |
| `vanish` | 硬切消失 | visibility discrete 反向 |
| `flash` | 在该 cue 的时间窗内闪灭一下 | opacity `1;1;0;0;1;1` |
| `rise` | 上浮淡入（12px） | opacity + translate 双 animate |
| `sink` | 下沉淡出 | 同上反向 |
| `draw` | 线条沿路径生长 | `pathLength="100"` + stroke-dashoffset `100;100;0;0` |
| `wipe` | 整块从左扫出 | opacity + translate X |

### 打字机（`typewriter`，独立于 cues 的一段）

文字逐字出现 + 光标跟随。源码只写 `<text data-cue="id"><tspan>全文</tspan></text>`，编译时自动拆字：

```json
{ "id": "term-reply", "at": 8.8, "per": 0.3, "cursor": "term-cursor" }
```

- `per` 每字间隔秒（0.2~0.35 接近真人打字）
- `cursor` 可选：光标元素每出一字平移一个 font-size，通常再配 `loops` 的 `blink`
- **坑**：别给 tspan 手写 `dx`（CJK 自然步进已有一个字宽，再加就双倍字距、光标永远落后一拍）；文本用纯中文（光标步进按等宽假设）

详见 `references/timeline-dsl.md` 的 `typewriter[]` 一节。

### 独立常驻（`loops`）

| effect | 生成 | 备注 |
|---|---|---|
| `blink` | opacity `1;1;0;0` @ `0;.5;.5;1` | 光标 |
| `flicker` | opacity `1;1;0;1;1` @ `0;.92;.95;.98;1` | 偶尔眨一下（样本用的就是这个） |
| `breathe` | translate `0 0;0 dy;0 0` | 需 `dy` |
| `swing` | rotate `-a cx cy;a cx cy;-a cx cy` | 需 `pivot: [cx,cy]`、`amp` |
| `spin` | rotate `0 cx cy;360 cx cy` | 需 `pivot` |
| `pulse` | opacity `1;0.4;1` | 呼吸灯 |

### 点击触发（`interactive`）

| effect | 生成 |
|---|---|
| `draw-stagger` | N 条线依次生长，第 i 条延迟 `i*stagger` |
| `reveal-stagger` | N 个元素依次硬切出现 |
| `reveal` | 单个元素点击后显现（可配 `restart:"always"` 重播） |

**点击类的硬约束（不做就点不动）**：`visibility="hidden"` 的元素收不到点击。所以脚本会把整组元素包成 **N 层嵌套 g**，最内层放一个透明热区：

```svg
<rect x="0" y="0" width="750" height="2400"
      fill="#000" fill-opacity="0" visibility="visible" pointer-events="all"/>
```

点热区 → 事件沿冒泡穿过每一层 → 各层 animate 同时 begin → 靠各自递增的 `keyTimes` 依次显现。

因此写 `skeleton.svg` 时：

- 交互组的元素要**相邻**，顺序与 `ids` 一致
- 元素自身**不要**预先写 `visibility="hidden"` 或 `stroke-dashoffset`（写在元素上会盖掉层 g 的动画结果，永远不显示）
- 想限定点击区域，用 `"hotspot": [x, y, w, h]`；默认覆盖全卷

## 六、校验清单（`validate_svg.py` 自动跑）

- 禁用标签：`script` `iframe` `object` `embed` `link` `form` `input` `video` `audio`
- 禁用属性：所有 `on*`
- 外链资源：`url(http` / `href="http`（`xmlns` 除外）
- 字体：非系统字体栈告警
- 结构：必须有 `viewBox`；必须有 `display:block` 与 `width:100%`
- SMIL：每条 `animate` 的 `values` 段数 == `keyTimes` 段数；`keyTimes` 单调不减；首为 0 尾为 1
- 体积：源码 >1MB 告警（微信会卡）
- 高度：`viewBox` 高度 >20000 告警（建议拆卷）

## 七、交付前自查

- [ ] 静态版本单独看一遍，构图/字号/留白站得住
- [ ] 主时间轴周期 ≥ 内容读完的时间（一般 15~30s）
- [ ] 点击交互有文字提示（如"点一下…"），否则读者不知道能点
- [ ] `validate_svg.py` 输出 0 error
- [ ] 375px 视口下字号 ≥ 22（设计稿 750 宽下 ≥ 22 即手机 11px，是下限）
