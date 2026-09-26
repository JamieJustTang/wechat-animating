# 微信正文 sanitiser：放行 / 拦截清单

来源：对实际推文源码（含 AGI Hunt《Claude by Claude》样本）的逆向观察 + 开源社区共识（mbeditor 自称"100% 过微信 sanitizer 白名单"的做法与本表一致）。**微信未公开该白名单，以下为经验值，以实测为准。**

新样式上线前，务必用手机预览真机确认一次。

## 放行（可用）

| 类别 | 内容 |
|---|---|
| 结构标签 | `section` `div` `p` `span` `br` `h1~h6` `blockquote` `ul` `ol` `li` |
| SVG 标签 | `svg` `g` `path` `rect` `circle` `ellipse` `line` `polyline` `polygon` `text` `tspan` `defs` `linearGradient` `radialGradient` `stop` `clipPath` `mask` `use` |
| SMIL 标签 | `animate` `animateTransform` `animateMotion` `set` `mpath` |
| 内联样式 | `style="..."` 属性（部分 CSS 会被改写，见下） |
| 自定义属性 | `data-*` 会被保留（我们靠 `data-cue` 做时间轴锚点，已实测可用） |

## 拦截 / 剥离

| 类别 | 内容 | 后果 |
|---|---|---|
| 脚本 | `<script>`、`on*`、`href="javascript:"` | 剥离，且可能触发内容风控 |
| 嵌入 | `<iframe>` `<object>` `<embed>` `<video>` `<audio>` | 剥离 |
| 表单 | `<form>` `<input>` `<button>` `<select>` | 剥离 |
| 外链资源 | `<image href="http...">`、`url(http...)`、`<link>`、Web Font | 图片不显示 / 字体回退 |
| 部分 CSS | `position:fixed`、`z-index`、`!important`、伪元素 | 改写或丢弃 |
| `<style>` 块 | 多数情况被清空 | **所以不能用 CSS `@keyframes`，只能用 SMIL** |
| `class` | 常被清洗 | 样式必须内联 `style` 或写成 SVG 表现属性（`fill=` `stroke=`） |

**关键推论**：因为 `<style>` 不可靠，动效只能写在标签属性上（SMIL），颜色字体只能写成 SVG 表现属性或内联 style。

## 已知限制（数值经验值）

| 项 | 上限 | 超了怎么办 |
|---|---|---|
| 单段 SVG `viewBox` 高度 | ~20000px | 拆成 2~3 段 SVG，中间用 `<section>` 分隔 |
| SVG 源码体积 | ~1MB（建议 <500KB） | 精简路径小数位、合并同色元素、删无用 `defs` |
| 正文总图片数 | 微信另有计数限制 | 长卷 SVG 算 1 个区块，反而是优势 |
| 字号（750 设计稿） | ≥22（对应手机 11px） | 低于此在手机上不可读 |

## 系统字体（唯一的字体来源）

```
'PingFang SC','Noto Sans CJK SC',sans-serif   中文黑体
'Songti SC','Noto Serif CJK SC',serif         中文宋体
Menlo,'Courier New',monospace                 等宽（终端风 zine 的命根子）
```

不要写 `font-family: "阿里巴巴普惠体"` 之类——外链字体必挂。也不要指望 `font-weight` 全档位可用，中文通常只有 400/700 两档，用 `PingFang SC` + `font-weight="700"` 是稳的。

## 粘贴发布的操作路径

1. 编辑器里"复制为富文本"（`text/html` 到剪贴板）
2. 打开公众号后台图文编辑器，光标定位，`Cmd+V`
3. **必须**点"预览"发到手机真机看一次——桌面预览与真机渲染有差异（尤其 SMIL 时序和字体）
4. 确认无误后存草稿 / 群发

第三方编辑器（秀米/135/i排版/壹伴）的"代码模式"也可用，但直接粘富文本最省事。若 SVG 被编辑器二次清洗，改用"粘贴为 HTML 源码"入口。
