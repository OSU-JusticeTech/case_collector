import json
import time
from datetime import datetime
import logging
from pathlib import Path

import cv2
import numpy as np
from django.core.management import BaseCommand
from pdf2image import convert_from_path

from apps.nextgen.models import ScanDocketEntry, MagdecAnalysis, RoiCount


def load_rois(rois_json_path: str) -> list[dict]:
    with open(rois_json_path, "r") as f:
        data = json.load(f)
    rois = data.get("rois", [])
    # Validate corners
    for roi in rois:
        corners = roi.get("corners", [])
        if len(corners) != 4:
            raise ValueError(f"ROI id={roi.get('id')} does not have 4 corners.")
    return rois

def polygon_mask(shape_hw, corners_xy: np.ndarray) -> np.ndarray:
    """
    Create a binary mask for a polygon defined by corners (4x2) in image coordinates.
    shape_hw: (H, W)
    """
    mask = np.zeros(shape_hw, dtype=np.uint8)
    pts = corners_xy.reshape(-1, 1, 2).astype(np.int32)
    cv2.fillPoly(mask, [pts], 255)
    return mask

def count_nonwhite_pixels(gray: np.ndarray, roi_mask: np.ndarray, white_threshold: int = 250) -> int:
    """
    Count pixels inside roi_mask that are NOT white, using a threshold.
    - mode="grayscale": uses gray < white_threshold
    - mode="rgb_all": count where all channels < threshold
    - mode="rgb_any": count where any channel < threshold
    """
    assert gray.shape[:2] == roi_mask.shape, "Mask and image must align"

    #gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
    nonwhite = (gray < white_threshold)

    # Apply mask
    nonwhite_in_roi = nonwhite & (roi_mask > 0)
    return int(np.count_nonzero(nonwhite_in_roi))

def process_image(img, rois: list[dict], white_threshold: int) -> dict:
    #img = cv2.imread(image_path, cv2.IMREAD_COLOR)
    H, W = img.shape[:2]

    # Build per-ROI masks once (and reuse)
    results = {
        "counts": []  # list aligned to rois order used here
    }

    for roi in rois:
        corners = np.array(roi["corners"], dtype=np.float32)  # [[x,y], ...] TL,TR,BR,BL
        # Validate corners inside image bounds
        if np.any(corners[:, 0] < 0) or np.any(corners[:, 0] >= W) or np.any(corners[:, 1] < 0) or np.any(corners[:, 1] >= H):
            raise ValueError(f"ROI id={roi.get('id')} has corners outside image bounds for")

        mask = polygon_mask((H, W), corners)
        count = count_nonwhite_pixels(img, mask, white_threshold=white_threshold)
        results["counts"].append({
            "roi_id": roi.get("id"),
            "color_hex": roi.get("color_hex"),
            "count_nonwhite": count
        })

    return results


class Command(BaseCommand):
    help = "Extracts magistrate decisions"

    def handle(self, *args, **options):
        logging.info("start extracting")

        template_path = str(Path(__file__).resolve().parent.parent.parent / "files")

        template = cv2.imread(template_path + "/template.png", cv2.IMREAD_GRAYSCALE)
        template_check = cv2.imread(template_path + "/template-checker.png", cv2.IMREAD_GRAYSCALE)

        #print(template)
        #print(template_check)

        orb = cv2.ORB_create(
            nfeatures=5000,
            scaleFactor=1.2,
            nlevels=8
        )
        kp_template, des_template = orb.detectAndCompute(template, None)

        rois = load_rois(template_path + "/rois.json")

        for sde in ScanDocketEntry.objects.filter(filename__contains=" DMAGDEC ", magdec_analyses__isnull=True):
            #print(sde.text)
            print(sde.filename)

            pages = convert_from_path(sde.scan.path)
            for pno, page in enumerate(pages):
                print("page number", pno)
                scan = cv2.cvtColor(np.array(page), cv2.COLOR_RGB2GRAY)
                #print(scan)

                #cv2.namedWindow("Scan", cv2.WINDOW_NORMAL)
                #cv2.imshow("Scan", scan)

                kp_scan, des_scan = orb.detectAndCompute(scan, None)

                #print(f"Template keypoints: {len(kp_template)}")
                #print(f"Scan keypoints: {len(kp_scan)}")

                bf = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True)
                matches = bf.match(des_template, des_scan)

                # Sort matches by distance (lower = better)
                matches = sorted(matches, key=lambda x: x.distance)

                # Keep only the best matches
                num_good_matches = int(len(matches) * 0.15)
                good_matches = matches[:num_good_matches]

                #print(f"Good matches used: {len(good_matches)}")

                #match_vis = cv2.drawMatches(
                #    template, kp_template,
                #    scan, kp_scan,
                #    good_matches, None,
                #    flags=cv2.DrawMatchesFlags_NOT_DRAW_SINGLE_POINTS
                #)
                #cv2.namedWindow("Feature Matches", cv2.WINDOW_NORMAL)
                #cv2.imshow("Feature Matches", match_vis)

                # --------------------------------------------------------
                # 5. Estimate affine transform (rotation + scale)
                # --------------------------------------------------------
                src_pts = np.float32(
                    [kp_scan[m.trainIdx].pt for m in good_matches]
                ).reshape(-1, 1, 2)

                dst_pts = np.float32(
                    [kp_template[m.queryIdx].pt for m in good_matches]
                ).reshape(-1, 1, 2)

                # Estimate affine transformation
                M, inliers = cv2.estimateAffinePartial2D(
                    src_pts,
                    dst_pts,
                    method=cv2.RANSAC,
                    ransacReprojThreshold=5.0
                )

                if M is None:
                    raise RuntimeError("Could not estimate affine transformation")

                #print("Estimated affine transform:\n", M)

                # --------------------------------------------------------
                # 6. Warp scan to template coordinate system
                # --------------------------------------------------------
                aligned_scan = cv2.warpAffine(
                    scan,
                    M,
                    (template.shape[1], template.shape[0]),
                    flags=cv2.INTER_LINEAR
                )

                kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (9, 9))

                dilated_align = cv2.dilate(255 - aligned_scan, kernel)
                # diffimg = ((255-template.astype(np.float32)) - (blur_aligned.astype(np.float32))) .clip(min=0).astype(np.uint8)

                diffimg = ((255 - template_check).astype(np.int32) - dilated_align.astype(np.int32)).clip(min=0).astype(
                    np.uint8)
                #print("subtract", diffimg)

                summ = diffimg.sum()
                #print("sum of diff", summ)

                #print("data", {"good_matches": len(good_matches), "M": M.tolist(), "diffsum": int(summ)})

                result = process_image(aligned_scan, rois, white_threshold=250)

                magdec = MagdecAnalysis.objects.create(
                    page_number = pno,
                    good_matches=len(good_matches),
                    diff_sum=int(summ),
                    m11=M[0][0],
                    m12=M[0][1],
                    m13=M[0][2],
                    m21=M[1][0],
                    m22=M[1][1],
                    m23=M[1][2],
                )
                sde.magdec_analyses.add(magdec)

                for item in result["counts"]:
                    RoiCount.objects.create(
                        result=magdec,
                        roi_id=item["roi_id"],
                        color_hex=item["color_hex"],
                        count_nonwhite=item["count_nonwhite"],
                    )

                #print(result, "result")
                #break
                #page.save("page_image.jpg", "jpg")
            break
        #scan = cv2.imread(scan_path, cv2.IMREAD_GRAYSCALE)
        #cv2.waitKey(0)
        #cv2.destroyAllWindows()
