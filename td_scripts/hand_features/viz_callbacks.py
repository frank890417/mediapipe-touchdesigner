# hand_features 視覺化：把手的點、骨架、拇指↔食指的距離、手的角度、兩手之間的距離畫出來
# 畫在透明底上（RGBA），再用 Over TOP 疊到攝影機畫面上。用 TD 內建的 OpenCV（cv2）畫。
import math
import numpy as np
import cv2

FINGERS = {
    'thumb': ['wrist', 'thumb_cmc', 'thumb_mcp', 'thumb_ip', 'thumb_tip'],
    'index_finger': ['wrist', 'index_finger_mcp', 'index_finger_pip', 'index_finger_dip', 'index_finger_tip'],
    'middle_finger': ['middle_finger_mcp', 'middle_finger_pip', 'middle_finger_dip', 'middle_finger_tip'],
    'ring_finger': ['ring_finger_mcp', 'ring_finger_pip', 'ring_finger_dip', 'ring_finger_tip'],
    'pinky': ['wrist', 'pinky_mcp', 'pinky_pip', 'pinky_dip', 'pinky_tip'],
}
PALM = ['index_finger_mcp', 'middle_finger_mcp', 'ring_finger_mcp', 'pinky_mcp']
# BGR＋alpha（cv2 用 BGR）：第一隻手琥珀色、第二隻手青色、兩手之間白色
COLORS = {1: (60, 190, 255, 255), 2: (255, 220, 80, 255)}
WHITE = (255, 255, 255, 255)
GESTURE_NAMES = ['', 'FIST', 'OPEN', 'POINT', 'THUMB UP', 'THUMB DOWN', 'VICTORY', 'I LOVE YOU']


def onSetupParameters(scriptOp):
    return


def onPulse(par):
    return


def onCook(scriptOp):
    comp = scriptOp.parent()
    pts = comp.op('sel_points')
    f = comp.op('null_features')
    W = int(comp.par.Vizw.eval())
    H = int(comp.par.Vizh.eval())
    S = W / 1280.0  # 線寬、字級跟著解析度縮放
    img = np.zeros((H, W, 4), dtype=np.uint8)

    def val(op_, name, d=0.0):
        c = op_[name] if op_ is not None else None
        return c.eval() if c is not None else d

    def px(h, name):
        x = val(pts, f'{h}:{name}:x')
        y = val(pts, f'{h}:{name}:y')
        return int(x * W), int((1 - y) * H)  # TD 的 y 0 在下面，影像的列 0 在上面

    def label(text, p, color, scale=0.6):
        sc = scale * S * 1.4
        th = max(1, int(2 * S))
        (tw, tht), _ = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, sc, th)
        x, y = p[0] - tw // 2, p[1] - int(12 * S)
        cv2.rectangle(img, (x - 6, y - tht - 6), (x + tw + 6, y + 6), (0, 0, 0, 170), -1)
        cv2.putText(img, text, (x, y), cv2.FONT_HERSHEY_SIMPLEX, sc, color, th, cv2.LINE_AA)

    centers = {}
    for n in (1, 2):
        h = f'h{n}'
        if val(f, f'{h}_active') < 0.5:
            continue
        col = COLORS[n]
        thin = max(1, int(2 * S))
        # 骨架
        for chain in FINGERS.values():
            for a, b in zip(chain, chain[1:]):
                cv2.line(img, px(h, a), px(h, b), col, thin, cv2.LINE_AA)
        for a, b in zip(PALM, PALM[1:]):
            cv2.line(img, px(h, a), px(h, b), col, thin, cv2.LINE_AA)
        # 21 個點
        names = set(sum(FINGERS.values(), [])) | set(PALM)
        for nm in names:
            cv2.circle(img, px(h, nm), max(2, int(4 * S)), WHITE, -1, cv2.LINE_AA)
        # 拇指 ↔ 食指：粗線＋中點圓（圓的大小＝張開程度）＋數字
        t, i = px(h, 'thumb_tip'), px(h, 'index_finger_tip')
        pinch = val(f, f'{h}_pinch')
        on = val(f, f'{h}_pinch_on') > 0.5
        lc = (80, 255, 120, 255) if on else col
        cv2.line(img, t, i, lc, max(2, int(5 * S)), cv2.LINE_AA)
        mid = ((t[0] + i[0]) // 2, (t[1] + i[1]) // 2)
        cv2.circle(img, mid, int((8 + 40 * pinch) * S), lc, max(1, int(2 * S)), cv2.LINE_AA)
        label(('PINCH ' if on else 'pinch ') + f'{pinch:.2f}', mid, lc)
        # 手的角度：手腕 → 中指根的方向，畫一條延長線＋角度
        w, m = px(h, 'wrist'), px(h, 'middle_finger_mcp')
        dx, dy = m[0] - w[0], m[1] - w[1]
        L = math.hypot(dx, dy) or 1
        tip = (int(w[0] + dx / L * 160 * S), int(w[1] + dy / L * 160 * S))
        cv2.arrowedLine(img, w, tip, col, max(1, int(3 * S)), cv2.LINE_AA, tipLength=0.15)
        deg = val(f, f'{h}_angle') * 360
        label(f'angle {deg:.0f}', (w[0], w[1] + int(40 * S)), col)
        # 手勢名稱
        g = int(round(val(f, f'{h}_gesture')))
        if 0 < g < len(GESTURE_NAMES):
            label(GESTURE_NAMES[g], (w[0], w[1] + int(80 * S)), WHITE, 0.8)
        cx = int(val(f, f'{h}_palm_x') * W)
        cy = int((1 - val(f, f'{h}_palm_y')) * H)
        centers[n] = (cx, cy)
        cv2.circle(img, (cx, cy), int(10 * S), col, -1, cv2.LINE_AA)
    # 兩手之間
    if 1 in centers and 2 in centers:
        a, b = centers[1], centers[2]
        cv2.line(img, a, b, WHITE, max(1, int(3 * S)), cv2.LINE_AA)
        mid = ((a[0] + b[0]) // 2, (a[1] + b[1]) // 2)
        label(f'hands {val(f, "hands_distance"):.2f}', mid, WHITE, 0.7)
    # 左上角：計數
    hud = f'pinch count {int(val(f, "h1_pinch_count"))}   fist count {int(val(f, "h1_fist_count"))}'
    cv2.putText(img, hud, (int(20 * S), int(40 * S)), cv2.FONT_HERSHEY_SIMPLEX, 0.8 * S * 1.4, WHITE, max(1, int(2 * S)), cv2.LINE_AA)
    # cv2 是 BGRA、列 0 在上；TD 要 RGBA、列 0 在下
    img = np.flipud(img)[:, :, [2, 1, 0, 3]]
    scriptOp.copyNumpyArray(np.ascontiguousarray(img))
    return
