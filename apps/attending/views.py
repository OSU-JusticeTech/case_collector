import json
import os
import re
from pathlib import Path
from zoneinfo import ZoneInfo

import pytesseract

from PIL import Image, ImageOps
from django.contrib.auth.decorators import login_required
from django.http import Http404, FileResponse

from django.shortcuts import render
from pyarrow.lib import Date32Array
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from django.db import connection


# Create your views here.

DATA_DIR = Path("/home/felix/Dokumente/osu/eviction/court-extracted/checkin/data")

def base(request):
    return render(request, "attending/base.html")

class FileList(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        files = os.listdir(DATA_DIR)
        images = sorted([{"name": f, "processed": False} for f in files if f.lower().endswith(('.jpg', '.jpeg', '.png'))], key=lambda x: x["name"])
        return Response(images)

@login_required
def data(request, filename):
    FILENAME_RE = re.compile(r"^[a-zA-Z0-9._-]+$")
    if not FILENAME_RE.match(filename):
        raise Http404()
    return FileResponse(open(DATA_DIR / filename, "rb"))

class Save(APIView):
    permission_classes = (IsAuthenticated,)

    def post(self, request, filename):
        FILENAME_RE = re.compile(r"^[a-zA-Z0-9._-]+$")
        if not FILENAME_RE.match(filename):
            raise Http404()
        print(request.data)

        return Response({"success": True})



def get_best_docket(ocr_values):

    values_sql = ",".join(f"({v})" for v in ocr_values)

    sql = f"""
    WITH
    ocr_numbers(num) AS (
        VALUES {values_sql}
    ),
    event_cases AS (
        SELECT
            ce.start AS start_time,
            CAST(SUBSTR(ls.case_number, LENGTH(ls.case_number) - 5, 6) AS INTEGER) AS case_num
        FROM cases_event ce
        JOIN latest_snapshot ls
          ON ce.snapshot_id = ls.id
    ),
    ocr_count AS (
        SELECT COUNT(DISTINCT num) AS total
        FROM ocr_numbers
    )
    SELECT
        ec.start_time,
        COUNT(DISTINCT ec.case_num) AS matches,
        1.0 * COUNT(DISTINCT ec.case_num) / oc.total AS coverage
    FROM event_cases ec
    JOIN ocr_numbers o
      ON o.num = ec.case_num
    CROSS JOIN ocr_count oc
    GROUP BY ec.start_time, oc.total
    ORDER BY matches DESC, coverage DESC;
    """

    with connection.cursor() as cursor:
        cursor.execute(sql)
        rows = cursor.fetchall()
        cols = [col[0] for col in cursor.description]
        results = [dict(zip(cols, row)) for row in rows]
        #print("match", results)
        if len(results) > 0:
            if results[0]["coverage"] > 0.5:
                best_start_time = results[0]["start_time"]  # from your ranking query

                sql = """
                SELECT
                    ce.*,
                    CAST(SUBSTR(ls.case_number, LENGTH(ls.case_number) - 5, 6) AS INTEGER) AS case_num
                FROM cases_event ce
                JOIN latest_snapshot ls
                  ON ce.snapshot_id = ls.id
                WHERE ce.start = %s
                """

                cursor.execute(sql, [best_start_time])
                rows = cursor.fetchall()
                cols = [col[0] for col in cursor.description]
                results = [dict(zip(cols, row)) for row in rows]
                #print("rows", results)
                numends = [r["case_num"] for r in results]
                print("possible", numends)
                return best_start_time, list(sorted(numends))

class FileLoad(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request, filename):
        FILENAME_RE = re.compile(r"^[a-zA-Z0-9._-]+$")
        if not FILENAME_RE.match(filename):
            raise Http404()
        base_name = os.path.splitext(filename)[0]
        #docket_path = os.path.join(DATA_DIR, f"{base_name}.txtdocket.json")
        result_path = os.path.join(DATA_DIR, f"{base_name}_result.json")

        if os.path.exists(result_path):
            with open(result_path, 'r') as f:
                return Response(json.load(f))

        #if os.path.exists(docket_path):
        #    with open(docket_path, 'r') as f:
        #        possible_numbers = list(sorted([str(n) for n in json.load(f)]))
        #else:
        #    return Response({"error": f"Missing docket target file: {base_name}.txtdocket.json"}, status=404)

        img_path = os.path.join(DATA_DIR, filename)

        # Generate the hOCR data using the proper pytesseract function
        img = Image.open(img_path)
        img = ImageOps.exif_transpose(img)
        img.rotate(90)
        hocr_bytes = pytesseract.image_to_pdf_or_hocr(img, extension='hocr', config="--psm 12")
        hocr_data = hocr_bytes.decode('utf-8')

        master_data = {}
        display_order = []
        ocr_found_numbers = {}

        word_pattern = r"<span[^>]*class='ocrx_word'[^>]*title='bbox (\d+) (\d+) (\d+) (\d+)[^']*'>\s*([^\s<]+)"
        matches = re.findall(word_pattern, hocr_data)

        rough_numbers = []
        for x0, y0, x1, y1, text in matches:
            clean_text = text.strip()
            num_match = re.search(r"([1-9][0-9]{2,})", clean_text)
            if num_match:
                num = num_match.group(1)
                rough_numbers.append(int(num))

        print("rough", rough_numbers)

        best_start, possible_numbers = get_best_docket(rough_numbers)

        #possible_numbers = []

        for x0, y0, x1, y1, text in matches:
            clean_text = text.strip()
            num_match = re.search(r"([1-9][0-9]{2,})", clean_text)
            if num_match:
                num = num_match.group(1)
                if num in possible_numbers and num not in ocr_found_numbers:
                    ocr_found_numbers[num] = {
                        "x": int(x0) + (int(x1) - int(x0)) // 2,
                        "y": int(y0) + (int(y1) - int(y0)) // 2,
                        "note": clean_text.replace(num, "").replace("-", "").strip()[:3]
                    }
                    display_order.append(num)

        for num in possible_numbers:
            if num in ocr_found_numbers:
                master_data[num] = {
                    "present": True,
                    "note": ocr_found_numbers[num]["note"],
                    "x": ocr_found_numbers[num]["x"],
                    "y": ocr_found_numbers[num]["y"],
                    "is_ocr": True
                }
            else:
                master_data[num] = {
                    "present": False,
                    "note": "",
                    "x": None,
                    "y": None,
                    "is_ocr": False
                }
                display_order.append(num)

        tz_ohio = ZoneInfo("America/New_York")
        return Response({
            "master_data": master_data,
            "display_order": display_order,
            "rotation": 0,
            "zoom": 0.5,
            "detected_date": best_start.astimezone(tz_ohio).isoformat()
        })