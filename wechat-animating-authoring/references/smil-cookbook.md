# 手写 SMIL 配方库（脚本兜底用）

优先用 `timeline_compile.py`。以下配方用于：脚本覆盖不到的特殊效果、调试、或者读别人源码时反推意图。

## 0. 铁律

- `values` 的段数 **必须等于** `keyTimes` 的段数。不等 → 整条 animate 静默失效（不报错，就是不动）。
- `keyTimes` 首段必须是 `0`，末段必须是 `1`，中间单调不减。
- `calcMode="discrete"` 用于"跳变"（visibility、多帧切换）；默认 `linear` 用于渐变。
- 元素初始状态要写在标签上（如 `visibility="hidden"`、`opacity="0"`），否则动画开始前会先闪一下真身。

## 1. 主时间轴上的"第 N 秒出现并保持"

周期 T=22.3s，想让元素在 2.0s 出现、用 1.2s 淡入、之后保持：

```
a = 2.0/22.3 = 0.0897
b = 3.2/22.3 = 0.1435
```

```svg
<g data-cue="x">
  <animate attributeName="opacity" begin="0s" dur="22.3s" repeatCount="indefinite"
           values="0;0;1;1" keyTimes="0;0.0897;0.1435;1"/>
  ...内容...
</g>
```

四段值的语义：`0→a` 隐、`a→b` 渐显、`b→1` 显。这个"四段式"是长卷自动播放的基本单元。

## 2. 只在某个瞬间闪一下（不做状态变化）

4.2s 周期里，92%~95% 灭一下：

```svg
<animate attributeName="opacity" begin="0s" dur="4.2s" repeatCount="indefinite"
         values="1;1;0;1;1" keyTimes="0;0.92;0.95;0.98;1"/>
```

五段：`0→.92` 亮、`.92→.95` 灭、`.95→.98` 亮回、`.98→1` 保持。用来做"眨眼睛""信号抖动"。

## 3. 呼吸位移

```svg
<animateTransform attributeName="transform" type="translate" begin="0s" dur="3.6s"
                  repeatCount="indefinite" values="0 0;0 -12;0 0"/>
```

注意：`animateTransform` 挂在 `<g>` 上，**不要**同时在该 `<g>` 上写 `transform="..."` 静态属性，会被覆盖。要叠加位移就把静态变换放到外层 `<g>`。

## 4. 钟摆

```svg
<animateTransform attributeName="transform" type="rotate" begin="0s" dur="2.6s"
                  repeatCount="indefinite"
                  values="-8 648 176;10 648 176;-8 648 176"/>
```

`rotate` 的 values 格式是 `"角度 中心x 中心y"`，中心坐标必须给，否则绕原点甩飞。

## 5. 线条生长（描边动画）

```svg
<g visibility="hidden" stroke-dasharray="100 100" stroke-dashoffset="100">
  <animate attributeName="visibility" values="hidden;visible;visible"
           keyTimes="0;0.0476;1" calcMode="discrete"
           begin="click" dur="5.25s" fill="freeze" restart="always"/>
  <animate attributeName="stroke-dashoffset" values="100;100;0;0"
           keyTimes="0;0.0476;0.1668;1"
           begin="click" dur="5.25s" fill="freeze" restart="always"/>
  <path d="M512 986Q393 86..." pathLength="100" fill="none" stroke-width="8"/>
</g>
```

要点：

- `pathLength="100"` 把任意长度归一化到 100，`dasharray/dashoffset` 就能写死 100，不用去算真实弧长。
- 用 `<g>` 挂 `visibility` 和 `dashoffset`，`<path>` 只管画。
- `fill="none"` 别漏，否则描边路径会被填充成实心块。

## 5b. 点击热区（点击类动画的前提）

**不做这一步，所有 `begin="click"` 都是死的。** `visibility="hidden"` 的元素不参与命中测试，点击永远落不到它身上。

```svg
<rect x="0" y="0" width="750" height="2400"
      fill="#000" fill-opacity="0" visibility="visible" pointer-events="all"/>
```

- `fill-opacity="0"`：不可见
- `visibility="visible"`：必须显式声明，否则不参与命中
- `pointer-events="all"`：透明填充默认不吃点击，这句是开关

放在**最内层**（所有待触发元素的后代位置），点击后事件冒泡经过每一层祖先 g，于是各层的 `begin="click"` 一并触发：

```svg
<g visibility="hidden">                      <!-- 层 1：先出 -->
  <animate begin="click" keyTimes="0;0;1" .../>
  元素 1
  <g visibility="hidden">                    <!-- 层 2：后出 -->
    <animate begin="click" keyTimes="0;0.0229;1" .../>
    元素 2
    <rect 热区/>
  </g>
</g>
```

想让点击只影响局部，把热区尺寸改成那块区域即可（多个独立热区互不干扰）。

## 6. 连续点击 = 多帧播放

`restart="always"` + 每次点击重播一段固定动画，用它模拟"翻页/多帧"：

```svg
<animate attributeName="opacity" values="1;0;1" keyTimes="0;0.5;1"
         begin="click" dur="0.6s" restart="always" fill="freeze"/>
```

配合多组元素各自的 `keyTimes` 偏移，就能做出"点一下换一格"的逐帧效果（opensvg 的"连续点击 GIF 组件"就是这个原理）。

## 7. 逐行打字机

N 行文字，每行一条 visibility，延迟递增：

第 i 行（共 N 行，总长 D，行间隔 g）：`s_i = i*g/D`

```svg
<animate attributeName="visibility" values="hidden;visible;visible"
         keyTimes="0;{s_i};1" calcMode="discrete"
         begin="0s" dur="22.3s" repeatCount="indefinite"/>
```

每行初始 `visibility="hidden"`。想让光标跟到最后一行，就把光标元素（一个 `<rect>`）用 `translate` 动画在行间跳动，或者直接给光标挂 `blink`。

## 8. 调试技巧

- 把 `repeatCount="indefinite"` 临时改成 `"1"`、`dur` 改成 `"2s"`，动画会放慢 10 倍，容易看清时序。
- 在桌面 Chrome 打开 SVG 文件，DevTools 里选中带 animate 的元素，`Elements` 面板会显示 SMIL 但不会显示当前值——靠肉眼看。
- 微信里不动、桌面动：99% 是白名单问题，跑 `validate_svg.py`。
- 微信和桌面都不动：99% 是 `values`/`keyTimes` 段数不匹配。
