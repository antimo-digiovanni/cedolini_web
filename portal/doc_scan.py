"""Ritaglio e raddrizzamento automatico delle foto dei documenti (stile app di scansione).

Trova il bordo della tessera nella foto, la raddrizza in prospettiva e la porta al
formato ID-1 (85,6 x 54 mm, come carta d'identità e patente). Se il bordo non viene
trovato con sicurezza, restituisce la foto originale (solo ruotata secondo l'EXIF e
ridimensionata), così non si perde mai un documento per un ritaglio sbagliato.
"""

import io
import logging

from PIL import Image, ImageOps

logger = logging.getLogger(__name__)

CARD_RATIO = 85.6 / 54.0
OUT_W = 1712
OUT_H = int(round(OUT_W / CARD_RATIO))
MAX_SIDE_ORIGINAL = 2000
MAX_INPUT_PIXELS = 40_000_000


class ScanError(ValueError):
    pass


def load_image(data):
    """Apre un'immagine caricata, verificandola e applicando l'orientamento EXIF."""
    Image.MAX_IMAGE_PIXELS = MAX_INPUT_PIXELS
    try:
        probe = Image.open(io.BytesIO(data))
        probe.verify()
        img = Image.open(io.BytesIO(data))
        img = ImageOps.exif_transpose(img)
        img = img.convert('RGB')
    except Exception as exc:
        raise ScanError('Il file non è una foto valida.') from exc
    if img.width < 400 or img.height < 250:
        raise ScanError('La foto è troppo piccola: avvicinati al documento e riprova.')
    return img


def _order_corners(pts):
    import numpy as np
    pts = np.array(pts, dtype='float32').reshape(4, 2)
    s = pts.sum(axis=1)
    d = np.diff(pts, axis=1).ravel()
    return np.array([pts[np.argmin(s)], pts[np.argmin(d)], pts[np.argmax(s)], pts[np.argmax(d)]], dtype='float32')


def find_card(img):
    """Restituisce i 4 angoli della tessera (coordinate dell'immagine) oppure None."""
    import cv2
    import numpy as np

    rgb = np.array(img)
    h, w = rgb.shape[:2]
    scale = 900.0 / max(h, w)
    small = cv2.resize(rgb, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_AREA) if scale < 1 else rgb.copy()
    if scale >= 1:
        scale = 1.0
    gray = cv2.cvtColor(small, cv2.COLOR_RGB2GRAY)
    gray = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8)).apply(gray)
    gray = cv2.GaussianBlur(gray, (5, 5), 0)
    area_img = small.shape[0] * small.shape[1]

    best = None
    for lo, hi in ((30, 100), (50, 150), (75, 200), (15, 60)):
        edges = cv2.Canny(gray, lo, hi)
        edges = cv2.dilate(edges, np.ones((3, 3), np.uint8), iterations=2)
        edges = cv2.morphologyEx(edges, cv2.MORPH_CLOSE, np.ones((7, 7), np.uint8))
        contours, _ = cv2.findContours(edges, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
        for c in sorted(contours, key=cv2.contourArea, reverse=True)[:10]:
            area = cv2.contourArea(c)
            if area < 0.18 * area_img or area > 0.98 * area_img:
                continue
            peri = cv2.arcLength(c, True)
            quad = None
            for eps in (0.02, 0.03, 0.045):
                approx = cv2.approxPolyDP(c, eps * peri, True)
                if len(approx) == 4 and cv2.isContourConvex(approx):
                    quad = approx
                    break
            if quad is None:
                # tessera con angoli arrotondati: usa il rettangolo minimo che la contiene
                rect = cv2.minAreaRect(c)
                box = cv2.boxPoints(rect)
                if cv2.contourArea(box) <= 0 or area / cv2.contourArea(box) < 0.88:
                    continue
                quad = box
            corners = _order_corners(quad)
            wa = np.linalg.norm(corners[1] - corners[0]); wb = np.linalg.norm(corners[2] - corners[3])
            ha = np.linalg.norm(corners[3] - corners[0]); hb = np.linalg.norm(corners[2] - corners[1])
            if min(wa, wb, ha, hb) <= 0:
                continue
            ratio = max((wa + wb) / 2, (ha + hb) / 2) / min((wa + wb) / 2, (ha + hb) / 2)
            if not (1.25 <= ratio <= 1.95):
                continue
            if best is None or area > best[0]:
                best = (area, corners)
        if best:
            break
    if not best:
        return None
    return best[1] / scale


def warp_card(img, corners):
    import cv2
    import numpy as np

    rgb = np.array(img)
    # stringe leggermente verso il centro per non lasciare il bordo del tavolo
    corners = np.array(corners, dtype='float32')
    center = corners.mean(axis=0)
    corners = center + (corners - center) * 0.985
    tl, tr, br, bl = corners
    width = (np.linalg.norm(tr - tl) + np.linalg.norm(br - bl)) / 2
    height = (np.linalg.norm(bl - tl) + np.linalg.norm(br - tr)) / 2
    if height > width:  # tessera fotografata in verticale: ruota di 90°
        corners = np.array([bl, tl, tr, br], dtype='float32')
    dst = np.array([[0, 0], [OUT_W - 1, 0], [OUT_W - 1, OUT_H - 1], [0, OUT_H - 1]], dtype='float32')
    m = cv2.getPerspectiveTransform(np.array(corners, dtype='float32'), dst)
    out = cv2.warpPerspective(rgb, m, (OUT_W, OUT_H), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
    return Image.fromarray(out)


def rotate_jpeg(data, degrees):
    """Ruota una foto già salvata (90, 180, 270 gradi in senso orario)."""
    img = Image.open(io.BytesIO(data)).convert('RGB').rotate(-degrees, expand=True)
    out = io.BytesIO()
    img.save(out, format='JPEG', quality=88, optimize=True)
    return out.getvalue()


def process_photo(data):
    """Foto caricata -> (jpeg_bytes, ritagliata: bool)."""
    img = load_image(data)
    cropped = False
    try:
        corners = find_card(img)
        if corners is not None:
            img = warp_card(img, corners)
            cropped = True
    except Exception:
        logger.exception('doc_scan: ritaglio non riuscito, uso la foto originale')
    if not cropped:
        img.thumbnail((MAX_SIDE_ORIGINAL, MAX_SIDE_ORIGINAL))
    out = io.BytesIO()
    img.save(out, format='JPEG', quality=88, optimize=True)
    return out.getvalue(), cropped
