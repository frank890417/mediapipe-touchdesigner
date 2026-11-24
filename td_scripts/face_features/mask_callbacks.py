# face_features：嘴巴遮罩（內唇一圈 20 個點）＋視覺化（點、嘴巴輪廓、數字）
import numpy as np
import cv2

INNER_LIP = [78, 191, 80, 81, 82, 13, 312, 311, 310, 415, 308, 324, 318, 402, 317, 14, 87, 178, 88, 95]
KEY = [1, 33, 133, 362, 263, 61, 291, 13, 14, 234, 454, 10, 152]


def onSetupParameters(scriptOp):
    return


def onPulse(par):
    return


def onCook(scriptOp):
    comp = scriptOp.parent()
    pts = comp.op('in_points')
    f = comp.op('null_features')
    W, H = int(comp.par.Vizw.eval()), int(comp.par.Vizh.eval())
    viz = scriptOp.name == 'viz_overlay'
    img = np.zeros((H, W, 4), dtype=np.uint8)
    act = f['face_active'] is not None and f['face_active'].eval() > 0.5
    if act and pts is not None and pts.numSamples >= 468:
        X, Y = pts['x'], pts['y']
        P = lambda i: (int(X[i] * W), int((1 - Y[i]) * H))
        poly = np.array([P(i) for i in INNER_LIP], dtype=np.int32)
        if viz:
            S = W / 1280.0
            for i in range(0, pts.numSamples, 3):
                cv2.circle(img, P(i), max(1, int(1.5 * S)), (255, 255, 255, 140), -1, cv2.LINE_AA)
            for i in KEY:
                cv2.circle(img, P(i), max(2, int(5 * S)), (60, 190, 255, 255), -1, cv2.LINE_AA)
            on = f['mouth_open_on'].eval() > 0.5
            col = (80, 255, 120, 255) if on else (255, 220, 80, 255)
            cv2.polylines(img, [poly], True, col, max(1, int(3 * S)), cv2.LINE_AA)
            mc = P(13)
            def label(t, pt, c):
                sc = 0.6 * S * 1.4
                th = max(1, int(2 * S))
                (tw, tht), _ = cv2.getTextSize(t, cv2.FONT_HERSHEY_SIMPLEX, sc, th)
                x, y = pt[0] - tw // 2, pt[1]
                cv2.rectangle(img, (x - 6, y - tht - 6), (x + tw + 6, y + 6), (0, 0, 0, 170), -1)
                cv2.putText(img, t, (x, y), cv2.FONT_HERSHEY_SIMPLEX, sc, c, th, cv2.LINE_AA)
            lo = P(152)
            label(f"open {f['mouth_open'].eval():.2f}  round {f['mouth_round'].eval():.2f}  O {f['mouth_funnel'].eval():.2f}", (lo[0], lo[1] + int(40 * S)), col)
            label(f"blink {f['blink_l'].eval():.2f}/{f['blink_r'].eval():.2f}  smile {f['smile'].eval():.2f}", (lo[0], lo[1] + int(80 * S)), (255, 255, 255, 255))
        else:
            cv2.fillPoly(img, [poly], (255, 255, 255, 255), cv2.LINE_AA)
    img = np.flipud(img)
    if viz:
        img = img[:, :, [2, 1, 0, 3]]
    scriptOp.copyNumpyArray(np.ascontiguousarray(img))
    return
