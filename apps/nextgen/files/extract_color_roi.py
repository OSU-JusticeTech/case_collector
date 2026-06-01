
import cv2
import numpy as np
import json
import argparse
import os

def order_corners_clockwise(pts):
    """
    Order 4 points as: top-left, top-right, bottom-right, bottom-left.
    pts: Nx2 array
    """
    pts = np.array(pts, dtype=np.float32)
    c = np.mean(pts, axis=0)
    d = pts - c
    angles = np.arctan2(d[:,1], d[:,0])
    # Sort by angle: TL(-pi,-pi/2), TR(-pi/2,0), BR(0,pi/2), BL(pi/2,pi)
    idx = np.argsort(angles)
    pts_sorted = pts[idx]

    # After sort by angle, ensure TL first. Among the two with smallest y, the leftmost is TL.
    # Alternatively, we can do a more stable approach:
    s = pts_sorted.sum(axis=1)      # TL has smallest sum
    diff = np.diff(pts_sorted, axis=1).ravel()  # TR has smallest diff, BL has largest diff
    tl = pts_sorted[np.argmin(s)]
    br = pts_sorted[np.argmax(s)]
    tr = pts_sorted[np.argmin(diff)]
    bl = pts_sorted[np.argmax(diff)]
    return np.array([tl, tr, br, bl], dtype=np.float32)

def mean_hex_color(img_bgr, mask):
    """
    Compute mean BGR within mask and return HEX string (#RRGGBB).
    """
    if mask.sum() == 0:
        return "#000000"
    mean_bgr = cv2.mean(img_bgr, mask=mask.astype(np.uint8))[0:3]  # (b, g, r, _)
    b, g, r = [int(round(x)) for x in mean_bgr]
    return "#{:02X}{:02X}{:02X}".format(r, g, b)

def find_colored_boxes(image_bgr, min_area=5000, approx_eps_frac=0.02):
    """
    Detect colored rectangular boxes and return list of dicts:
    { 'id': i, 'color_hex': '#RRGGBB', 'corners': [[x,y], ...] (TL,TR,BR,BL), 'bbox': [x,y,w,h] }
    """
    h, w = image_bgr.shape[:2]
    # Smooth slightly to reduce noise
    blur = cv2.GaussianBlur(image_bgr, (5,5), 0)

    # Convert to HSV; colored boxes should have higher saturation than background template
    hsv = cv2.cvtColor(blur, cv2.COLOR_BGR2HSV)

    # Generic "colorful" mask: high S (saturation), not too dark, not too bright
    # Adjust thresholds if needed:
    # S > 60 filters out grayscale/black template lines; V between 50..255 keeps visible colors
    s_min = 60
    v_min = 40
    color_mask = (hsv[:,:,1] > s_min) & (hsv[:,:,2] > v_min)

    mask = color_mask.astype(np.uint8) * 255

    # Morphology to clean up
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5,5))
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel, iterations=1)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel, iterations=1)

    # Find contours
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    rois = []
    debug_mask = np.zeros((h, w), dtype=np.uint8)

    for i, cnt in enumerate(contours):
        area = cv2.contourArea(cnt)
        if area < min_area:
            continue

        # Approximate polygon
        peri = cv2.arcLength(cnt, True)
        approx = cv2.approxPolyDP(cnt, approx_eps_frac * peri, True)

        # Try to enforce 4 corners by fallback to minAreaRect if approx != 4
        if len(approx) != 4:
            rect = cv2.minAreaRect(cnt)
            box = cv2.boxPoints(rect)  # 4x2 float
            approx = np.int32(box).reshape(-1, 1, 2)

        if len(approx) != 4:
            # Skip weird shapes
            continue

        pts = approx.reshape(-1, 2)  # shape (4,2)
        # Order corners TL, TR, BR, BL
        corners = order_corners_clockwise(pts)

        # Bounding box (int)
        x, y, bw, bh = cv2.boundingRect(pts)

        # Create a mask for this contour to compute mean color
        roi_mask = np.zeros((h, w), dtype=np.uint8)
        cv2.drawContours(roi_mask, [cnt], -1, 255, thickness=cv2.FILLED)

        color_hex = mean_hex_color(image_bgr, roi_mask)

        rois.append({
            "id": i,
            "color_hex": color_hex,
            "corners": corners.astype(int).tolist(),   # [[x,y], ...] TL,TR,BR,BL
            "bbox": [int(x), int(y), int(bw), int(bh)],
            "area": float(area)
        })

        # For debug mask (optional)
        debug_mask[roi_mask > 0] = 255

    # Sort by top-left x,y to have stable ordering across runs (optional)
    def tl_key(roi):
        tl = roi["corners"][0]
        return (tl[1], tl[0])  # sort by y, then x
    rois.sort(key=tl_key)

    return rois, mask, debug_mask

def visualize(image_bgr, rois, window_name="Colored ROIs"):
    vis = image_bgr.copy()
    for roi in rois:
        corners = np.array(roi["corners"], dtype=np.int32)
        color_hex = roi["color_hex"]
        # Draw polygon
        cv2.polylines(vis, [corners], isClosed=True, color=(0, 255, 255), thickness=2)
        # Draw corner circles and labels
        for idx, (x, y) in enumerate(corners):
            cv2.circle(vis, (x, y), 6, (0, 0, 255), -1)
            cv2.putText(vis, f"{idx}", (x+6, y-6), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (50, 50, 50), 2, cv2.LINE_AA)
        # Put the color hex near TL
        tlx, tly = corners[0]
        cv2.putText(vis, color_hex, (tlx, tly - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (40, 200, 40), 2, cv2.LINE_AA)
    return vis

def main():
    parser = argparse.ArgumentParser(description="Extract corners of color-filled ROI boxes from a template image.")
    parser.add_argument("--image", required=True, help="Path to PNG with colored boxes over template.")
    parser.add_argument("--min_area", type=int, default=5000, help="Minimum contour area to accept as a box.")
    parser.add_argument("--eps_frac", type=float, default=0.02, help="ApproxPolyDP epsilon as fraction of perimeter.")
    parser.add_argument("--save_json", default=None, help="Optional path to save ROI corners as JSON.")
    parser.add_argument("--save_debug", default=None, help="Optional path to save debug visualization PNG.")
    args = parser.parse_args()

    img = cv2.imread(args.image, cv2.IMREAD_COLOR)
    if img is None:
        raise IOError(f"Could not load image: {args.image}")

    rois, mask, dbg_mask = find_colored_boxes(img, min_area=args.min_area, approx_eps_frac=args.eps_frac)

    # Print results
    print(json.dumps({"image": os.path.basename(args.image), "count": len(rois), "rois": rois}, indent=2))

    # Visualization
    vis = visualize(img, rois, "Colored ROIs")

    # Resizable windows and reasonable default size
    cv2.namedWindow("Colored ROIs", cv2.WINDOW_NORMAL)
    cv2.resizeWindow("Colored ROIs", 1600, 900)
    cv2.imshow("Colored ROIs", vis)

    cv2.namedWindow("Color Mask", cv2.WINDOW_NORMAL)
    cv2.resizeWindow("Color Mask", 800, 600)
    cv2.imshow("Color Mask", mask)

    cv2.waitKey(0)
    cv2.destroyAllWindows()

    # Optional saves
    if args.save_json:
        with open(args.save_json, "w") as f:
            json.dump({"image": os.path.basename(args.image), "count": len(rois), "rois": rois}, f, indent=2)
        print(f"Saved JSON: {args.save_json}")

    if args.save_debug:
        cv2.imwrite(args.save_debug, vis)
        print(f"Saved debug image: {args.save_debug}")

if __name__ == "__main__":
    main()
