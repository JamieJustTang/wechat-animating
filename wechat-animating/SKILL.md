---
name: wechat-animating
description: 微信公众号「长卷 SVG zine」制作总控（hub）——把一篇图文做成单个内联 SVG 长卷（如 AGI Hunt《Claude by Claude》：750×11980 纯矢量、SMIL 动画、点击交互），涵盖分镜构思 → SVG 源码 + 时间轴脚本 → 微信兼容性校验 → 编辑器预览 → 粘贴发布。触发词：公众号 SVG、微信长图、SVG zine、微信动效排版、SVG 交互排版、公众号动画、zine 长卷、微信文章动画、SVG 时间轴。
---

# 微信公众号长卷 SVG zine · 总控（Hub）

本 skill 是**路由与流程总控**，不重复子 skill 的细则。三个子 skill 各有独立职责，按需加载：

| 阶段 | 加载 | 干什么 |
|---|---|---|
| 1. 想清楚 | `wechat-animating-style` | 定视觉风格（纸张/终端/riso…）与分镜节奏；产出分镜表 |
| 2. 写出来 | `wechat-animating-authoring` | 写静态 SVG 骨架 + 时间轴 DSL，跑编译与校验脚本 |
| 3. 发出去 | `wechat-animating-editor` | 本地编辑器预览、体检、复制富文本、粘贴到公众号 |

## 这条链路解决什么问题

微信公众平台的正文是**标签白名单制富文本**，不是网页：

- 剥掉 `<script>` / `<iframe>` / 外链资源 / `on*` 事件 → **不能用 JS 做交互**
- 剥掉或改造 `<style>` 块与部分 CSS → **不能靠 CSS `@keyframes`**
- 但保留 `<svg>` 及其 `animate` / `animateTransform` 等**属性级**声明

结果：动效只能靠 **SMIL**（`<animate>` 写在标签上），交互只能靠 **`begin="click"`**。这是"SVG 交互排版"成为公众号黑科技标准解法的根本原因。

一个真实样本（AGI Hunt《Claude by Claude》，2026-09-25，参考 Ethan Mollick 的 zine《STATELESS #1》）：正文仅两段内联 SVG，主体 `viewBox="0 0 750 11980"`、287KB 源码、532 个 `<text>`、**0 张位图**、187 个动画标签——其中 101 个挂在 `dur="22.3s"` 的自动播放主时间轴上，53 处 `begin="click"` 触发连线生长，其余是呼吸/摆动/眨眼等常驻循环。

**长卷 zine 相对视频/GIF 的取舍**：

| | 长卷 SVG | 视频 / GIF |
|---|---|---|
| 清晰度 | 任意分辨率不糊 | 固定像素，压缩糊 |
| 体积 | 几百 KB（纯矢量） | 数 MB 起 |
| 交互 | 支持（click 触发） | 无 |
| 文字 | 不可选中、不可被微信搜索 | 同 |
| 制作 | agent 可直接生成源码 | 需渲染管线 |

## 端到端 SOP

```
1  定题 → 一句话命题 + 目标读者 + 时长预算（建议 15~30s 主时间轴）
2  分镜 → wechat-animating-style：选风格母题 → 写分镜表（页/屏 → 元素 → 动作 → 时码）
3  骨架 → wechat-animating-authoring：写静态 SVG（元素打 data-cue="id"），先不动
4  时间轴 → 写 timeline.json（cues / loops / interactive 三段）
5  编译 → python3 scripts/timeline_compile.py compile|inject
6  校验 → python3 scripts/validate_svg.py  （必须 0 error 才继续）
7  预览 → wechat-animating-editor 打开单文件编辑器，375px 视口过一遍
8  发布 → 复制富文本 → 粘进公众号编辑器 → 手机预览确认 → 群发/存草稿
```

**硬规则**：第 6 步校验不过，不许进第 7 步。SMIL 的 `keyTimes` 数量与 `values` 不匹配会静默失效——动画不动且无任何报错，这是最常见的坑。

## 借鉴的开源项目（已调研，勿重复造轮子）

| 项目 | 星数 | 定位 | 与我们关系 |
|---|---|---|---|
| `doocs/md` | 13.3k | 微信 Markdown 编辑器，主题 + 复制富文本 | **不产 SVG**，是 Markdown→富文本的标杆；我们的编辑器借鉴其"预览即所得 + 一键复制"交互 |
| `AAAAAnson/mbeditor` | — | 自托管 AI 公众号工具，REST API + CLI + `skill/mbeditor.skill.md` | **Agent-first 架构的直接先例**，其"纯 inline `<section>` + SVG 装饰，100% 过 sanitizer"的说法与本 skill 的白名单判断一致；我们做长卷叙事，它做通用推文 |
| `cailven/opensvg` | 17 | Vue 组件式 SVG 编辑器（零高容器/点击切换/点击伸长/连续点击GIF） | **组件化交互的思路可借鉴**，但它是"堆组件"，我们是"一整卷叙事画布"，目标不同 |
| `nexu-io/html-anything` | 8.9k | 75 skill templates × 9 surfaces 的 agentic HTML 编辑器 | **skill 模板库的组织方式**值得抄；它产出 HTML，我们产出必须过微信白名单的 SVG |

结论：这三个都不覆盖"长卷叙事 zine + 时间轴脚本化"，本 suite 补的正是这个缺口。**不要**试图重做 doocs/md。

## 三条不可违反的约束

1. **零 JS**：任何 `on*`、`href="javascript:"`、`<script>` 一律禁止，微信会剥且可能触发风控。
2. **零外链**：字体只能用系统字体栈，图片不能 `<image href="http...">`（要 base64 或纯矢量）。
3. **先静态后动效**：先把静态 SVG 做对（构图、字号、留白），再挂动画。动画是放大器，救不了烂构图。

## 常见失败模式

| 症状 | 原因 | 处置 |
|---|---|---|
| 粘贴后动画不动 | `values` 与 `keyTimes` 数量不等 | `validate_svg.py` 会报；或 `keyTimes` 非递增 |
| 手机上只显示一半 | 外层没写 `style="display:block;width:100%;height:auto"` | 见 authoring skill 的骨架模板 |
| 微信里文字错位 | 用了非系统字体 | 换系统字体栈 |
| **点击无反应** | **没有透明热区**——`visibility="hidden"` 的元素收不到点击 | 必须有 `fill-opacity="0" visibility="visible" pointer-events="all"` 的 rect；`validate_svg.py` 会报 |
| 点击只触发一次 | 缺 `restart="always"`；或播完回弹是缺 `fill="freeze"` | 两个都要 |
| 描边只画一半就断 | `stroke-dasharray` 没配 `pathLength` 归一化 | 脚本自动补；手写的要自己加 |
| 打字机光标落后一拍 | 逐字 tspan 手写了 `dx`——CJK 自然步进已有一个字宽，再加 `dx=字号` 就成双倍字距 | 删 `dx`，光标交给 `typewriter.cursor` 自动编译 |
| 截图验证时元素"消失" | 常驻循环恰好处在灭拍（如 `blink` 后半周期 opacity=0） | 换 `t mod 周期` 落在亮区的时刻再截；截帧自检见下 |
| 长卷被截断 | SVG 过高（>20000px）或源码 >1MB | 拆成 2~3 段 SVG 分段排版 |

### 截图自检（无编辑器环境时）

用 Chrome headless 冻结 SMIL 到指定时刻逐帧检查：

```bash
# 三个坑，踩过一次就记住：
# 1. 必须加 --no-sandbox（本机 Chrome GPU 沙箱会初始化失败）
# 2. headless 窗口宽最小 500，--window-size=375 会被静默钳制成 500（缩放变 2/3）
# 3. 冻结用 pauseAnimations() + setCurrentTime(t)，不要靠等
chrome --headless=new --no-sandbox --disable-gpu \
  --screenshot=shot.png --window-size=500,1868 page.html
```

页面模板：`<body style="margin:0"><div>…内联 zine.svg…</div><script>s.pauseAnimations();s.setCurrentTime(T);</script></body>`。源坐标(750) → png = ×窗口宽/750。
