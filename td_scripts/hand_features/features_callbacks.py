# hand_features — 把 hand_tracking 的原始點，算成上課直接能用的訊號
# 由 Cheyu Wu（吳哲宇）為新媒體藝術全景課加入，建立在 torinmb/mediapipe-touchdesigner v0.6.1 之上（MIT）。
#
# 輸入（同一個 COMP 裡的 Select CHOP）：
#   sel_points   ← hand_tracking/normalized_data   每隻手 21 個點的 x、y、z（0～1）
#   sel_helpers  ← hand_tracking/helpers           hand_active、hand_velocity、pinch_midpoint…
#   sel_gestures ← hand_tracking/gestures          8 種手勢的信心分數
# 輸出：每隻手一組 hN_* 通道＋兩隻手的 hands_*＋相容第 6 堂場景的 tx、ty。
# 這支只做「當下這一格」的數學（沒有記憶）；平滑、防抖、計數交給後面的原生 CHOP（Lag、Filter、Logic、Count）。
import math

FINGERS = ['thumb', 'index_finger', 'middle_finger', 'ring_finger', 'pinky']
TIPS = {f: f + '_tip' for f in FINGERS}
GESTURES = [('Closed_Fist', 'fist'), ('Open_Palm', 'open'), ('Pointing_Up', 'point'),
            ('Thumb_Up', 'thumbup'), ('Thumb_Down', 'thumbdown'), ('Victory', 'victory'),
            ('ILoveYou', 'iloveyou')]


def onSetupParameters(scriptOp):
    return


def onPulse(par):
    return


def _clamp01(v):
    return 0.0 if v < 0 else (1.0 if v > 1 else v)


def _hyst(scriptOp, key, on_cond, off_cond):
    # 遲滯：進入和離開用不同的門檻，臨界附近不會一直跳
    state = scriptOp.fetch(key, 0)
    if state and off_cond:
        state = 0
    elif not state and on_cond:
        state = 1
    scriptOp.store(key, state)
    return float(state)


def _remap(v, lo, hi):
    if hi == lo:
        return 0.0
    return _clamp01((v - lo) / (hi - lo))


def onCook(scriptOp):
    comp = scriptOp.parent()
    pts = comp.op('sel_points')
    hlp = comp.op('sel_helpers')
    ges = comp.op('sel_gestures')
    P = comp.par
    aspect = float(P.Aspect.eval()) if P.Aspect.eval() else 16 / 9
    pinch_lo, pinch_hi = P.Pinchmin.eval(), P.Pinchmax.eval()
    pinch_on_thr = P.Pinchthreshold.eval()
    g_thr = P.Gesturethreshold.eval()
    two_lo, two_hi = P.Handsdistmin.eval(), P.Handsdistmax.eval()
    scriptOp.clear()

    def ch(op_, name, default=0.0):
        if op_ is None:
            return default
        c = op_[name]
        return c.eval() if c is not None else default

    def pt(h, name):
        # 位置換成「寬度為 1」的單位：x 乘上長寬比，距離才不會因為 16:9 被壓扁
        x = ch(pts, f'{h}:{name}:x')
        y = ch(pts, f'{h}:{name}:y')
        return x * aspect, y

    def dist(a, b):
        return math.hypot(a[0] - b[0], a[1] - b[1])

    out = {}
    centers = {}
    for n in (1, 2):
        h = f'h{n}'
        active = 1.0 if ch(hlp, f'{h}:hand_active') > 0.5 else 0.0
        o = {}
        o['active'] = active
        wrist = pt(h, 'wrist')
        mid_mcp = pt(h, 'middle_finger_mcp')
        size = dist(wrist, mid_mcp)  # 手掌大小：手離鏡頭越近越大
        o['size'] = size
        ok = active > 0 and size > 1e-4
        # 食指尖位置：x、y 0～1 與 −0.5～0.5 兩種
        ix = ch(pts, f'{h}:index_finger_tip:x')
        iy = ch(pts, f'{h}:index_finger_tip:y')
        o['x'] = ix if ok else 0.5
        o['y'] = iy if ok else 0.5
        o['tx'] = (ix - 0.5) if ok else 0.0
        o['ty'] = (iy - 0.5) if ok else 0.0
        # 手掌中心：手腕＋四個指根的平均
        palm_names = ['wrist', 'index_finger_mcp', 'middle_finger_mcp', 'ring_finger_mcp', 'pinky_mcp']
        px = sum(ch(pts, f'{h}:{p}:x') for p in palm_names) / len(palm_names)
        py = sum(ch(pts, f'{h}:{p}:y') for p in palm_names) / len(palm_names)
        o['palm_x'] = px if ok else 0.5
        o['palm_y'] = py if ok else 0.5
        centers[n] = (px * aspect, py) if ok else None
        palm = (px * aspect, py)
        # 拇指到其他四指尖的距離（除以手掌大小 ⇒ 離鏡頭遠近都一樣）
        thumb = pt(h, 'thumb_tip')
        for f in FINGERS[1:]:
            d = dist(thumb, pt(h, TIPS[f])) / size if ok else 0.0
            key = f.split('_')[0]
            o[f'thumb_{key}_raw'] = d
            o[f'thumb_{key}'] = _remap(d, pinch_lo, pinch_hi) if ok else 0.0
        o['pinch'] = o['thumb_index']           # 0＝捏緊、1＝張開
        o['pinch_raw'] = o['thumb_index_raw']
        # 張開程度：中指、無名指、小指的指尖到手掌中心的平均距離（握拳小、張開大）
        spread = sum(dist(pt(h, TIPS[f]), palm) for f in FINGERS[2:]) / 3 / size if ok else 0.0
        o['openness_raw'] = spread
        o['openness'] = _remap(spread, P.Openmin.eval(), P.Openmax.eval()) if ok else 0.0
        # 捏一下：拇指碰食指，而且其他三指是張開的（不然握拳也會被當成捏）
        # 遲滯：小於門檻才算捏下去，大於門檻×1.6 才算放開
        o['pinch_on'] = _hyst(scriptOp, f'{h}_pinch', ok and o['pinch_raw'] < pinch_on_thr and spread > P.Openmin.eval(),
                              (not ok) or o['pinch_raw'] > pinch_on_thr * 1.6)
        # 手的角度：手腕 → 中指根，0～1 對應 0～360 度（手指朝上約 0.25）
        ang = math.degrees(math.atan2(mid_mcp[1] - wrist[1], mid_mcp[0] - wrist[0])) % 360 if ok else 0.0
        o['angle'] = ang / 360.0
        o['velocity'] = ch(hlp, f'{h}:hand_velocity') if ok else 0.0
        # 手勢：超過門檻＝1；gesture＝目前最像的手勢編號（0＝沒有，1～7 依序 fist open point thumbup thumbdown victory iloveyou）
        best, best_i = 0.0, 0
        for i, (src, short) in enumerate(GESTURES, start=1):
            s = ch(ges, f'{h}:{src}') if ok else 0.0
            o[f'{short}_score'] = s
            # 遲滯：超過門檻才算，掉到門檻−0.15 以下才放開
            o[short] = _hyst(scriptOp, f'{h}_{short}', s > g_thr, s < g_thr - 0.15)
            if s > best:
                best, best_i = s, i
        o['gesture'] = float(best_i) if best > g_thr else 0.0
        for k, v in o.items():
            out[f'{h}_{k}'] = v
    # 兩隻手
    both = 1.0 if centers[1] and centers[2] else 0.0
    out['hands_both'] = both
    if both:
        a, b = centers[1], centers[2]
        d = dist(a, b)
        out['hands_distance_raw'] = d
        out['hands_distance'] = _remap(d, two_lo, two_hi)
        out['hands_mid_x'] = (a[0] + b[0]) / 2 / aspect
        out['hands_mid_y'] = (a[1] + b[1]) / 2
        out['hands_angle'] = (math.degrees(math.atan2(b[1] - a[1], b[0] - a[0])) % 360) / 360.0
    else:
        out['hands_distance_raw'] = 0.0
        out['hands_distance'] = 0.0
        out['hands_mid_x'] = 0.5
        out['hands_mid_y'] = 0.5
        out['hands_angle'] = 0.0
    # 相容第 6 堂 Feedback 場景（Rectangle Center 抓 tx、ty）：第一隻手的食指尖
    out['tx'] = out['h1_tx']
    out['ty'] = out['h1_ty']
    scriptOp.numSamples = 1
    for k, v in out.items():
        c = scriptOp.appendChan(k)
        c[0] = v
    return
