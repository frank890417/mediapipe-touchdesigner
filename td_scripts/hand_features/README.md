# hand_features：手勢、距離、位置，拖進來就能用

> 吳哲宇（Cheyu Wu）為「新媒體藝術全景課」加的模組，建立在 [torinmb/mediapipe-touchdesigner](https://github.com/torinmb/mediapipe-touchdesigner) v0.6.1 之上（MIT）。
> 原本的 `hand_tracking` 給的是 21 個點的原始座標；這個模組把常用的「拿來控制東西的訊號」先算好，全部都是 0～1 或 0／1，直接拖去綁參數。

## 怎麼用

1. 把 `toxes/hand_features.tox` 拖進有 `MediaPipe` 和 `hand_tracking` 的那一層。
2. 它會自己找旁邊的 `hand_tracking`（參數「hand_tracking 元件」可以改）。
3. 用 `features_out`（CHOP）拿數字、用 `viz_out`（TOP）看畫面上的點、線、距離。

## 輸出通道（`hN` 是第幾隻手，h1、h2）

| 通道 | 範圍 | 意思 |
|---|---|---|
| `tx`、`ty` | −0.5～0.5 | 第一隻手的食指尖，跟滑鼠一樣可以直接綁 Rectangle／Circle 的 Center |
| `hN_x`、`hN_y` | 0～1 | 食指尖位置 |
| `hN_tx`、`hN_ty` | −0.5～0.5 | 同上，置中版本 |
| `hN_palm_x`、`hN_palm_y` | 0～1 | 手掌中心 |
| `hN_pinch` | 0～1 | 拇指到食指的距離：0＝捏緊、1＝張開（已除以手掌大小，離鏡頭遠近都一樣） |
| `hN_thumb_middle`、`hN_thumb_ring`、`hN_thumb_pinky` | 0～1 | 拇指到中指、無名指、小指 |
| `hN_openness` | 0～1 | 手張開的程度：0＝握拳、1＝全開 |
| `hN_angle` | 0～1 | 手的角度（手腕→中指根），0.25＝手指朝上 |
| `hN_velocity` | 0～1 | 手移動的速度 |
| `hN_active` | 0／1 | 手在不在畫面裡 |
| `hN_pinch_on` | 0／1 | 捏一下（拇指碰食指、其他手指張開；有防抖和遲滯） |
| `hN_fist`、`hN_open`、`hN_point`、`hN_thumbup`、`hN_thumbdown`、`hN_victory`、`hN_iloveyou` | 0／1 | 手勢（MediaPipe 手勢分類＋門檻＋遲滯） |
| `hN_gesture` | 0～7 | 目前的手勢編號：0 沒有、1 握拳、2 張開、3 指上、4 讚、5 倒讚、6 YA、7 I love you |
| `h1_pinch_count`、`h1_fist_count` | 0～場景數−1 | 每捏一下／握一下 +1，循環——直接接 Switch 的 Index 換場景 |
| `hands_both` | 0／1 | 兩隻手都在 |
| `hands_distance` | 0～1 | 兩隻手的距離 |
| `hands_mid_x`、`hands_mid_y` | 0～1 | 兩隻手的中點 |
| `hands_angle` | 0～1 | 兩隻手連線的角度 |
| `*_raw`、`*_score`、`hN_size` | 原始值 | 校正門檻時看的 |

## 雙手框出的多邊形

| 輸出 | 是什麼 |
|---|---|
| `poly_mask_out`（TOP） | 兩隻手的拇指尖＋食指尖圍成的四邊形：白色、外面透明。四個點依角度排序，手怎麼擺都不會交叉。只有一隻手時預設不畫（參數「單手也畫」打開＝拇指、食指、手腕三角形） |
| `poly_composite_out`（TOP） | 合成範例：框裡變洋紅色像素點、框外是原畫面（Matte TOP：輸入 1 框內、輸入 2 框外、輸入 3 遮罩） |

自己合成：把 `poly_mask_out` 接到 Matte TOP 的第三個輸入，第一個輸入放「框裡要出現的效果」，第二個輸入放原畫面。

## 參數

平滑（秒）、防抖（秒）、捏合的最小／最大距離、捏一下的門檻、張開的最小／最大、手勢門檻（預設 0.5）、雙手距離的最小／最大、場景數、計數歸零、視覺化解析度。
預設值是 2026-11-24 在一台 M4 Max＋Logitech MX Brio、坐在桌前（手離鏡頭約 50–80 公分）實測校正的；你的鏡頭和距離不一樣時，看 `*_raw` 的數字調最小／最大。

## 效能建議

- `MediaPipe` 只開你要用的模型（預設全開會跟不上）。
- 解析度 640×360、Target FPS 30：手部偵測約 8–15 ms，跟得上即時（同一台 1280×720／60 全開是 70–83 ms）。
- 視覺化 960×540 每格不到 2 ms；不用看畫面時可以不接 `viz_out`。

## 原始碼

- `features_callbacks.py`：每一格的數學（Script CHOP）
- `viz_callbacks.py`：視覺化（Script TOP，用 TD 內建的 OpenCV 畫）
- 平滑、防抖、計數是元件裡的 Lag、Logic、Count CHOP。
