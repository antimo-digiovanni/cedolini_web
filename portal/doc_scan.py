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
    area_img = small.shape[0] * small.shape[1]
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    gray = cv2.GaussianBlur(clahe.apply(cv2.cvtColor(small, cv2.COLOR_RGB2GRAY)), (5, 5), 0)
    # oltre alla luminosità usa anche i colori: una tessera scura su un tavolo scuro
    # si distingue spesso solo per la tinta
    lab = cv2.cvtColor(small, cv2.COLOR_RGB2LAB)
    chans = [cv2.GaussianBlur(clahe.apply(lab[..., i]), (5, 5), 0) for i in (1, 2)]

    def edge_maps():
        for lo, hi in ((30, 100), (50, 150), (75, 200), (15, 60)):
            yield cv2.Canny(gray, lo, hi)
        for lo, hi in ((20, 60), (10, 40)):
            yield np.maximum(cv2.Canny(chans[0], lo, hi), cv2.Canny(chans[1], lo, hi))

    best = None
    for edges in edge_maps():
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


def _line_through(a, b):
    import numpy as np
    d = b - a
    n = np.linalg.norm(d)
    return (float(a[0]), float(a[1]), float(d[0] / n), float(d[1] / n))


def _intersect(l1, l2):
    x1, y1, dx1, dy1 = l1
    x2, y2, dx2, dy2 = l2
    den = dx1 * dy2 - dy1 * dx2
    if abs(den) < 1e-6:
        return None
    t = ((x2 - x1) * dy2 - (y2 - y1) * dx2) / den
    return (x1 + t * dx1, y1 + t * dy1)


def refine_corners(img, corners):
    """Ricalcola i 4 bordi della tessera sulla foto a piena risoluzione.

    Per ogni lato cerca i punti di bordo vicini al lato trovato (escludendo gli angoli
    arrotondati) e ci adatta una retta; gli angoli sono le intersezioni delle rette.
    Così il ritaglio segue il bordo vero: niente tavolo ai lati e niente documento tagliato.
    """
    import cv2
    import numpy as np

    gray = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2GRAY)
    gray = cv2.GaussianBlur(gray, (5, 5), 0)
    corners = np.array(corners, dtype='float32')
    diag = float(np.hypot(*gray.shape))
    lines = []
    for i in range(4):
        a, b = corners[i], corners[(i + 1) % 4]
        length = float(np.linalg.norm(b - a))
        band = int(max(6, 0.015 * length))
        # zona attorno al lato, solo nel tratto centrale (gli angoli delle tessere sono arrotondati)
        a2, b2 = a + (b - a) * 0.12, a + (b - a) * 0.88
        x0, y0 = np.floor(np.minimum(a2, b2) - band - 2).astype(int)
        x1, y1 = np.ceil(np.maximum(a2, b2) + band + 2).astype(int)
        x0, y0 = max(x0, 0), max(y0, 0)
        x1, y1 = min(x1, gray.shape[1]), min(y1, gray.shape[0])
        roi = gray[y0:y1, x0:x1]
        line = _line_through(a, b)
        if roi.size:
            mask = np.zeros_like(roi)
            cv2.line(mask, tuple(int(v) for v in (a2 - (x0, y0))), tuple(int(v) for v in (b2 - (x0, y0))), 255, thickness=2 * band)
            # bordo = gradiente forte perpendicolare al lato
            gx = cv2.Sobel(roi, cv2.CV_32F, 1, 0, ksize=3)
            gy = cv2.Sobel(roi, cv2.CV_32F, 0, 1, ksize=3)
            d = (b - a) / max(length, 1e-6)
            normal_grad = np.abs(gx * -d[1] + gy * d[0])
            normal_grad[mask == 0] = 0
            # per ogni posizione lungo il lato, il punto di gradiente massimo
            thr = np.percentile(normal_grad[mask > 0], 90) if (mask > 0).any() else 0
            ys, xs = np.nonzero((normal_grad >= max(thr, 20)) & (mask > 0))
            if len(xs) >= 40:
                pts = np.column_stack([xs + x0, ys + y0]).astype(np.float32)
                vx, vy, cx, cy = cv2.fitLine(pts, cv2.DIST_HUBER, 0, 0.01, 0.01).ravel()
                fitted = (float(cx), float(cy), float(vx), float(vy))
                # accetta la retta solo se è quasi parallela e vicina al lato trovato
                ang = abs(vx * d[0] + vy * d[1])
                mid = (a + b) / 2
                dist = abs((mid[0] - cx) * vy - (mid[1] - cy) * vx)
                if ang > 0.995 and dist < band * 1.5:
                    line = fitted
        lines.append(line)
    refined = []
    for i in range(4):
        p = _intersect(lines[i - 1], lines[i])  # angolo i = fine del lato i-1 e inizio del lato i
        if p is None or np.hypot(p[0] - corners[i][0], p[1] - corners[i][1]) > 0.03 * diag:
            p = tuple(corners[i])
        refined.append(p)
    return np.array(refined, dtype='float32')


def warp_card(img, corners):
    import cv2
    import numpy as np

    rgb = np.array(img)
    corners = refine_corners(img, corners)
    tl, tr, br, bl = corners
    width = (np.linalg.norm(tr - tl) + np.linalg.norm(br - bl)) / 2
    height = (np.linalg.norm(bl - tl) + np.linalg.norm(br - tr)) / 2
    if height > width:  # tessera fotografata in verticale: ruota di 90°
        corners = np.array([bl, tl, tr, br], dtype='float32')
    dst = np.array([[0, 0], [OUT_W, 0], [OUT_W, OUT_H], [0, OUT_H]], dtype='float32')
    m = cv2.getPerspectiveTransform(np.array(corners, dtype='float32'), dst)
    out = cv2.warpPerspective(rgb, m, (OUT_W, OUT_H), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
    return round_corners(Image.fromarray(out))


# Raggio degli angoli: le tessere ID-1 hanno angoli di circa 3,2 mm su 85,6 mm (3,7%).
# Un pelo più largo, così copre anche lo sfondo che resta negli angoli arrotondati.
CORNER_RADIUS_RATIO = 0.045


def round_corners(img, ratio=CORNER_RADIUS_RATIO, fill=(255, 255, 255)):
    """Colora di bianco gli angoli esterni alla tessera (lo sfondo della foto) con bordo arrotondato morbido."""
    from PIL import ImageDraw

    img = img.convert('RGB')
    w, h = img.size
    r = int(round(max(w, h) * ratio))
    if r < 2:
        return img
    scale = 3  # disegno ingrandito e poi ridotto: bordo dell'arrotondamento senza scalini
    mask = Image.new('L', (w * scale, h * scale), 0)
    edge = 2 * scale  # 2 px di bordo: elimina l'eventuale riga di sfondo lungo i lati
    ImageDraw.Draw(mask).rounded_rectangle([edge, edge, w * scale - 1 - edge, h * scale - 1 - edge], radius=r * scale, fill=255)
    mask = mask.resize((w, h), Image.LANCZOS)
    background = Image.new('RGB', (w, h), fill)
    return Image.composite(img, background, mask)


def rotate_jpeg(data, degrees):
    """Ruota una foto già salvata (90, 180, 270 gradi in senso orario)."""
    img = Image.open(io.BytesIO(data)).convert('RGB').rotate(-degrees, expand=True)
    out = io.BytesIO()
    img.save(out, format='JPEG', quality=88, optimize=True)
    return out.getvalue()


# Sotto questa misura (lato lungo della tessera nella foto, in pixel) il documento è troppo
# lontano per essere leggibile: la foto va rifatta più da vicino.
MIN_CARD_LONG_SIDE = 550


def _long_side(corners):
    import numpy as np
    c = _order_corners(corners)
    return max(np.linalg.norm(c[1] - c[0]), np.linalg.norm(c[2] - c[3]),
               np.linalg.norm(c[3] - c[0]), np.linalg.norm(c[2] - c[1]))


def process_photo(data):
    """Foto caricata -> (jpeg_bytes, ritagliata: bool)."""
    img = load_image(data)
    cropped = False
    try:
        corners = find_card(img)
        if corners is not None and _long_side(corners) >= MIN_CARD_LONG_SIDE:
            img = warp_card(img, corners)
            cropped = True
    except Exception:
        logger.exception('doc_scan: ritaglio non riuscito, uso la foto originale')
    if not cropped:
        img.thumbnail((MAX_SIDE_ORIGINAL, MAX_SIDE_ORIGINAL))
    out = io.BytesIO()
    img.save(out, format='JPEG', quality=88, optimize=True)
    return out.getvalue(), cropped


def refine_from_guide(img, rect):
    """Bordi esatti della tessera quando sappiamo già dov'è (il riquadro della fotocamera).

    rect = (x0, y0, x1, y1): il riquadro dentro la foto. Per ogni lato cerca, dall'esterno
    verso l'interno, il primo bordo netto (sfondo -> tessera): così non si confonde con
    scritte o righe stampate dentro il documento. Poi adatta una retta e interseca i lati.
    """
    import cv2
    import numpy as np

    gray = cv2.GaussianBlur(cv2.cvtColor(np.array(img), cv2.COLOR_RGB2GRAY), (5, 5), 0).astype(np.float32)
    H, W = gray.shape
    x0, y0, x1, y1 = [float(v) for v in rect]
    gw, gh = x1 - x0, y1 - y0
    by, bx = 0.14 * gh, 0.10 * gw  # tolleranza: il documento può essere un po' più grande o più piccolo del riquadro

    def side_points(kind):
        pts = []
        if kind in ('top', 'bottom'):
            edge = y0 if kind == 'top' else y1
            lo, hi = int(max(0, edge - by)), int(min(H - 1, edge + by))
            cols = np.linspace(x0 + 0.15 * gw, x1 - 0.15 * gw, 80).astype(int)
            cols = cols[(cols >= 0) & (cols < W)]
            strip = gray[lo:hi + 1, cols]
            grad = np.abs(np.diff(strip, axis=0))
            if kind == 'bottom':
                grad = grad[::-1]
            if grad.size == 0:
                return pts
            thr = 0.45 * np.percentile(grad.max(axis=0), 75)
            for j, col in enumerate(cols):
                idx = np.nonzero(grad[:, j] >= max(thr, 8))[0]
                if idx.size:
                    k = idx[0]
                    y = lo + k + 0.5 if kind == 'top' else hi - k - 0.5
                    pts.append((col, y))
        else:
            edge = x0 if kind == 'left' else x1
            lo, hi = int(max(0, edge - bx)), int(min(W - 1, edge + bx))
            rows = np.linspace(y0 + 0.18 * gh, y1 - 0.18 * gh, 60).astype(int)
            rows = rows[(rows >= 0) & (rows < H)]
            strip = gray[rows, lo:hi + 1]
            grad = np.abs(np.diff(strip, axis=1))
            if kind == 'right':
                grad = grad[:, ::-1]
            if grad.size == 0:
                return pts
            thr = 0.45 * np.percentile(grad.max(axis=1), 75)
            for j, row in enumerate(rows):
                idx = np.nonzero(grad[j, :] >= max(thr, 8))[0]
                if idx.size:
                    k = idx[0]
                    x = lo + k + 0.5 if kind == 'left' else hi - k - 0.5
                    pts.append((x, row))
        return pts

    guide_lines = {
        'top': (x0, y0, 1.0, 0.0), 'bottom': (x0, y1, 1.0, 0.0),
        'left': (x0, y0, 0.0, 1.0), 'right': (x1, y0, 0.0, 1.0),
    }
    lines, found = {}, 0
    for kind in ('top', 'right', 'bottom', 'left'):
        pts = side_points(kind)
        line = guide_lines[kind]
        if len(pts) >= 15:
            arr = np.array(pts, dtype=np.float32)
            # scarta i punti lontani dalla mediana (riflessi, dita, ombre)
            coord = arr[:, 1] if kind in ('top', 'bottom') else arr[:, 0]
            med = np.median(coord)
            mad = np.median(np.abs(coord - med)) + 1.0
            keep = arr[np.abs(coord - med) <= 4 * mad + 3]
            if len(keep) >= 12:
                vx, vy, cx, cy = cv2.fitLine(keep, cv2.DIST_HUBER, 0, 0.01, 0.01).ravel()
                horiz = kind in ('top', 'bottom')
                if (abs(vx) if horiz else abs(vy)) > 0.985:  # al massimo ~10° di inclinazione
                    line = (float(cx), float(cy), float(vx), float(vy))
                    found += 1
        lines[kind] = line
    order = ['top', 'right', 'bottom', 'left']
    corners = []
    for i, kind in enumerate(order):  # angolo tra lato precedente e lato corrente: tl, tr, br, bl
        p = _intersect(lines[order[i - 1]], lines[kind])
        corners.append(p)
    # ordine: top-left (left∩top), top-right (top∩right), bottom-right, bottom-left
    tl, tr, br, bl = corners[0], corners[1], corners[2], corners[3]
    if any(c is None for c in (tl, tr, br, bl)):
        return np.array([[x0, y0], [x1, y0], [x1, y1], [x0, y1]], dtype='float32'), 0
    return np.array([tl, tr, br, bl], dtype='float32'), found


def warp_to_card(img, corners):
    """Raddrizza i 4 angoli dati sul formato ID-1 con angoli arrotondati (senza ricerca dei bordi)."""
    import cv2
    import numpy as np

    dst = np.array([[0, 0], [OUT_W, 0], [OUT_W, OUT_H], [0, OUT_H]], dtype='float32')
    m = cv2.getPerspectiveTransform(np.array(corners, dtype='float32'), dst)
    out = cv2.warpPerspective(np.array(img), m, (OUT_W, OUT_H), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
    return round_corners(Image.fromarray(out))


def process_guided_photo(data, rect):
    """Foto dalla fotocamera del portale con la posizione del riquadro: (jpeg, ritagliata=True)."""
    img = load_image(data)
    x0, y0, x1, y1 = rect
    if not (0 <= x0 < x1 <= img.width and 0 <= y0 < y1 <= img.height) or (x1 - x0) < 200:
        raise ScanError('Foto non valida: rifalla dalla fotocamera del portale.')
    corners, _found = refine_from_guide(img, rect)
    out_img = warp_to_card(img, corners)
    out = io.BytesIO()
    out_img.save(out, format='JPEG', quality=90, optimize=True)
    return out.getvalue(), True


def crop_manual(data, points):
    """Ritaglio a mano dall'amministrazione: 4 angoli toccati sulla foto (coordinate 0..1).

    Gli angoli vengono rifiniti sul bordo vero solo se la correzione è piccola (entro il 3%):
    così un tocco un po' impreciso viene aggiustato, ma il ritaglio non può «scappare».
    """
    import numpy as np

    img = load_image(data)
    if len(points) != 4:
        raise ScanError('Tocca i 4 angoli del documento.')
    pts = np.array([[float(x) * img.width, float(y) * img.height] for x, y in points], dtype='float32')
    if not ((pts >= -1).all() and (pts[:, 0] <= img.width + 1).all() and (pts[:, 1] <= img.height + 1).all()):
        raise ScanError('Angoli fuori dalla foto.')
    corners = _order_corners(pts)
    if _long_side(corners) < 120:
        raise ScanError('Il riquadro scelto è troppo piccolo.')
    try:
        refined = refine_corners(img, corners)
        limit = 0.03 * max(img.width, img.height)
        if refined is not None and np.all(np.linalg.norm(refined - corners, axis=1) <= limit):
            corners = refined
    except Exception:
        logger.exception('crop_manual: rifinitura non riuscita, uso gli angoli toccati')
    out_img = warp_to_card(img, corners)
    out = io.BytesIO()
    out_img.save(out, format='JPEG', quality=90, optimize=True)
    return out.getvalue()
