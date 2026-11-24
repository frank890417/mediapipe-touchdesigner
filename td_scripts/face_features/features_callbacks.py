# face_features — 把 face_tracking 的 478 個點與 52 個表情分數，算成上課直接能用的臉部訊號
# 吳哲宇（Cheyu Wu）為新媒體藝術全景課加入，建立在 torinmb/mediapipe-touchdesigner v0.6.1 之上（MIT）。
# 輸入：in_points ← facePoints（x、y、z 三條通道，478 個取樣＝點的編號；y 0 在下）
#       in_blend  ← blend_shapes（jawOpen、mouthFunnel、eyeBlinkLeft…）
#       in_matrix ← transformation_matricies（頭的旋轉）
import math

INNER_LIP = [78, 191, 80, 81, 82, 13, 312, 311, 310, 415, 308, 324, 318, 402, 317, 14, 87, 178, 88, 95]


def onSetupParameters(scriptOp):
    return


def onPulse(par):
    return


def _clamp01(v):
    return 0.0 if v < 0 else (1.0 if v > 1 else v)


def _remap(v, lo, hi):
    return 0.0 if hi == lo else _clamp01((v - lo) / (hi - lo))


def _hyst(scriptOp, key, on_cond, off_cond):
    s = scriptOp.fetch(key, 0)
    if s and off_cond:
        s = 0
    elif not s and on_cond:
        s = 1
    scriptOp.store(key, s)
    return float(s)


def onCook(scriptOp):
    comp = scriptOp.parent()
    P = comp.par
    pts = comp.op('in_points')
    bs = comp.op('in_blend')
    mx = comp.op('in_matrix')
    aspect = float(P.Aspect.eval()) or 16 / 9
    scriptOp.clear()
    scriptOp.numSamples = 1
    out = {}
    n = pts.numSamples if pts is not None and pts.numChans >= 2 else 0
    X = pts['x'] if n else None
    Y = pts['y'] if n else None

    def p(i):
        return (X[i] * aspect, Y[i])

    def raw(i):
        return (X[i], Y[i])

    def d(a, b):
        return math.hypot(a[0] - b[0], a[1] - b[1])

    def blend(name):
        c = bs[name] if bs is not None else None
        return c.eval() if c is not None else 0.0

    active = 1.0 if n >= 468 and (X[1] != 0 or Y[1] != 0) else 0.0
    out['face_active'] = active
    if active:
        fw = d(p(234), p(454)) or 1e-4                    # 臉寬：除掉它 ⇒ 離鏡頭遠近都一樣
        nose = raw(1)
        mouth_c = ((X[13] + X[14]) / 2, (Y[13] + Y[14]) / 2)
        open_raw = d(p(13), p(14)) / fw                   # 上下唇內緣
        inner_w = d(p(78), p(308)) / fw                   # 內唇寬
        width_raw = d(p(61), p(291)) / fw                 # 嘴角到嘴角
        ratio = open_raw / max(inner_w, 1e-4)             # 越接近 1 越圓
        poly = [p(i) for i in INNER_LIP]
        area = 0.0
        for k in range(len(poly)):
            x1, y1 = poly[k]
            x2, y2 = poly[(k + 1) % len(poly)]
            area += x1 * y2 - x2 * y1
        area = abs(area) / 2 / (fw * fw)
        out.update({
            'face_x': nose[0], 'face_y': nose[1], 'face_tx': nose[0] - 0.5, 'face_ty': nose[1] - 0.5,
            'face_size': fw / aspect,
            'mouth_x': mouth_c[0], 'mouth_y': mouth_c[1], 'mouth_tx': mouth_c[0] - 0.5, 'mouth_ty': mouth_c[1] - 0.5,
            'mouth_open_raw': open_raw, 'mouth_open': _remap(open_raw, P.Mouthopenmin.eval(), P.Mouthopenmax.eval()),
            'mouth_width_raw': width_raw, 'mouth_width': _remap(width_raw, P.Mouthwidthmin.eval(), P.Mouthwidthmax.eval()),
            'mouth_round_raw': ratio, 'mouth_round': _remap(ratio, P.Roundmin.eval(), P.Roundmax.eval()) * (1.0 if open_raw > P.Mouthopenmin.eval() * 1.5 else 0.0),
            'mouth_area_raw': area, 'mouth_area': _remap(area, 0.0, P.Areamax.eval()),
            'eye_l_x': X[468] if n > 468 else X[159], 'eye_l_y': Y[468] if n > 468 else Y[159],
            'eye_r_x': X[473] if n > 473 else X[386], 'eye_r_y': Y[473] if n > 473 else Y[386],
            'head_roll': ((math.degrees(math.atan2(Y[263] - Y[33], (X[263] - X[33]) * aspect)) + 180) % 360) / 360.0,
        })
    else:
        for k in ['face_x', 'face_y', 'mouth_x', 'mouth_y', 'eye_l_x', 'eye_l_y', 'eye_r_x', 'eye_r_y', 'head_roll']:
            out[k] = 0.5
        for k in ['face_tx', 'face_ty', 'mouth_tx', 'mouth_ty', 'face_size', 'mouth_open_raw', 'mouth_open', 'mouth_width_raw',
                  'mouth_width', 'mouth_round_raw', 'mouth_round', 'mouth_area_raw', 'mouth_area']:
            out[k] = 0.0
    # MediaPipe 表情分數（0～1）
    out['jaw_open'] = blend('jawOpen') if active else 0.0
    out['mouth_funnel'] = blend('mouthFunnel') if active else 0.0   # 嘟成 O 型
    out['mouth_pucker'] = blend('mouthPucker') if active else 0.0   # 噘嘴
    out['smile'] = (blend('mouthSmileLeft') + blend('mouthSmileRight')) / 2 if active else 0.0
    out['blink_l'] = blend('eyeBlinkLeft') if active else 0.0
    out['blink_r'] = blend('eyeBlinkRight') if active else 0.0
    out['brow_up'] = blend('browInnerUp') if active else 0.0
    out['cheek_puff'] = blend('cheekPuff') if active else 0.0
    # 頭的轉向（transformation matrix），0.5＝正面
    if active and mx is not None and mx.numChans >= 12:
        m = {c.name: c.eval() for c in mx.chans()}
        yaw = math.degrees(math.asin(max(-1, min(1, -m.get('m20', 0)))))
        pitch = math.degrees(math.atan2(m.get('m21', 0), m.get('m22', 1)))
        out['head_yaw'] = _clamp01(0.5 + yaw / 90)
        out['head_pitch'] = _clamp01(0.5 + pitch / 90)
    else:
        out['head_yaw'] = 0.5
        out['head_pitch'] = 0.5
    # 開關（遲滯）
    thr = P.Mouthonthreshold.eval()
    out['mouth_open_on'] = _hyst(scriptOp, 'mouth', active and out['jaw_open'] > thr, (not active) or out['jaw_open'] < thr * 0.6)
    out['mouth_round_on'] = _hyst(scriptOp, 'round', active and out['mouth_funnel'] > 0.35, (not active) or out['mouth_funnel'] < 0.2)
    out['blink_on'] = _hyst(scriptOp, 'blink', active and min(out['blink_l'], out['blink_r']) > 0.5, (not active) or max(out['blink_l'], out['blink_r']) < 0.3)
    out['smile_on'] = _hyst(scriptOp, 'smile', active and out['smile'] > 0.5, (not active) or out['smile'] < 0.3)
    for k, v in out.items():
        c = scriptOp.appendChan(k)
        c[0] = v
    return
