# hand_features 多邊形遮罩：兩隻手的拇指尖＋食指尖圍成的四邊形（像用雙手框出一塊畫面）
# 輸出白色多邊形、黑底、alpha 同白色區域 ⇒ 直接拿去 Matte／Multiply／Composite 合成，只在框裡做特效。
# 只有一隻手時：用那隻手的拇指、食指和手腕圍成三角形（參數「單手也畫」關掉就不畫）。
import math
import numpy as np
import cv2


def onSetupParameters(scriptOp):
    return


def onPulse(par):
    return


def onCook(scriptOp):
    comp = scriptOp.parent()
    pts = comp.op('sel_points')
    f = comp.op('null_features')
    P = comp.par
    W = int(P.Vizw.eval())
    H = int(P.Vizh.eval())
    img = np.zeros((H, W, 4), dtype=np.uint8)

    def val(op_, name, d=0.0):
        c = op_[name] if op_ is not None else None
        return c.eval() if c is not None else d

    def px(h, name):
        return (val(pts, f'{h}:{name}:x') * W, (1 - val(pts, f'{h}:{name}:y')) * H)

    a1 = val(f, 'h1_active') > 0.5
    a2 = val(f, 'h2_active') > 0.5
    poly = []
    if a1 and a2:
        poly = [px('h1', 'thumb_tip'), px('h1', 'index_finger_tip'), px('h2', 'index_finger_tip'), px('h2', 'thumb_tip')]
    elif P.Polysinglehand.eval() and (a1 or a2):
        h = 'h1' if a1 else 'h2'
        poly = [px(h, 'thumb_tip'), px(h, 'index_finger_tip'), px(h, 'wrist')]
    area = 0.0
    if poly:
        # 依角度排序 ⇒ 四個點不管手怎麼擺都不會交叉成蝴蝶結
        cx = sum(p[0] for p in poly) / len(poly)
        cy = sum(p[1] for p in poly) / len(poly)
        poly.sort(key=lambda p: math.atan2(p[1] - cy, p[0] - cx))
        arr = np.array([[int(p[0]), int(p[1])] for p in poly], dtype=np.int32)
        cv2.fillPoly(img, [arr], (255, 255, 255, 255), cv2.LINE_AA)
        area = abs(cv2.contourArea(arr.astype(np.float32))) / float(W * H)
    scriptOp.store('poly_area', area)
    scriptOp.store('poly_active', 1.0 if poly else 0.0)
    img = np.flipud(img)
    scriptOp.copyNumpyArray(np.ascontiguousarray(img))
    return
