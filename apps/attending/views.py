import json
import logging
import math
import os
import re
from collections import Counter
from datetime import timezone, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pytesseract

from PIL import Image, ImageOps
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.db.models import OuterRef, Subquery, F, Count
from django.http import Http404, FileResponse

from django.shortcuts import render, get_object_or_404
from django.utils.dateparse import parse_datetime
from pyarrow.lib import Date32Array
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated, DjangoModelPermissions
from rest_framework.response import Response
from rest_framework.views import APIView

from django.db import connection

from apps.attending.models import CheckinSheet, DocketSessionState
from apps.attending.serializers import DocketSessionStateSerializer
from apps.cases.models import CourtCase, CaseSnapshot, Event
from apps.cases.serializers import (
    GroupedEventCountSerializer,
    SnapshotSerializer,
    SlimSnapshotSerializer,
)

# Create your views here.

DATA_DIR = Path("/home/felix/Dokumente/osu/eviction/court-extracted/checkin/data")


def base(request):
    return render(request, "attending/base.html")

def checkin(request):
    return FileResponse(
        open(settings.BASE_DIR / "apps/attending/templates/attending/checkin.html", "rb"),
        content_type="text/html",
    )


class FileList(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        files = CheckinSheet.objects.all()
        images = sorted(
            [{"name": f.filename, "processed": f.validated, "pk": f.pk} for f in files],
            key=lambda x: x["name"],
        )
        return Response(images)


@login_required
def data(request, filename):
    sheet = get_object_or_404(CheckinSheet, pk=filename)
    return FileResponse(sheet.photo.file)


class Save(APIView):
    permission_classes = (DjangoModelPermissions,)

    queryset = CheckinSheet.objects.all()

    def post(self, request, filename):
        sheet = get_object_or_404(CheckinSheet, pk=filename)

        sheet.processed = request.data
        sheet.validated = True
        sheet.save()
        return Response({"success": True})


def get_best_docket(ocr_values, sheet):

    # print("look for values", ocr_values)
    values_sql = ",".join(f"({v})" for v in ocr_values)

    extra = ""
    if sheet.possible_start is not None and sheet.possible_end is not None:
        extra = f"WHERE ce.start >= '{sheet.possible_start}' AND ce.start <= '{sheet.possible_end}'"

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
        {extra}
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

    # print(sql)

    with connection.cursor() as cursor:
        cursor.execute(sql)
        rows = cursor.fetchall()
        cols = [col[0] for col in cursor.description]
        results = [dict(zip(cols, row)) for row in rows]
        # print("match", results)
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
                # print("rows", results)
                numends = [r["case_num"] for r in results]
                # print("possible", numends)
                return best_start_time, list(sorted(numends))
    return None, []


def extract_sheet(sheet):
    # --- 2. RUN COLD-START OCR PROCESS ---
    img = Image.open(sheet.photo)
    img = ImageOps.exif_transpose(img)

    word_pattern = r"<span[^>]*class='ocrx_word'[^>]*title='bbox (\d+) (\d+) (\d+) (\d+)[^']*'>\s*([^\s<]+)"

    def best_rotation_eng(img, lang="eng"):
        scores = {}
        for angle in [0, 90, 180, 270]:
            rotated = img.rotate(angle)
            try:
                data = pytesseract.image_to_data(
                    rotated,
                    lang=lang,
                    config="--psm 11",
                    output_type=pytesseract.Output.DICT,
                )
            except Exception as e:
                print("ocr failed", angle, e.__repr__())
                scores[angle] = -1
                continue
            confs = [int(c) for c in data["conf"] if c not in ("-1", -1)]
            # sum of confidences rewards both "confident" and "lots of text found"
            score = sum(confs)
            scores[angle] = score
            print("angle", angle, "score", score, "n_words", len(confs))
        return max(scores, key=scores.get), scores

    def best_rotation_by_docket(img, sheet, lang="eng"):
        results = {}
        for angle in [0, 90, 180, 270]:
            rotated = img.rotate(angle, expand=True)
            try:
                hocr_bytes = pytesseract.image_to_pdf_or_hocr(
                    rotated, extension="hocr", lang=lang, config="--psm 11"
                )
            except Exception as e:
                print("ocr failed", angle, e.__repr__())
                continue
            hocr_data = hocr_bytes.decode("utf-8")
            matches = re.findall(word_pattern, hocr_data)
            rough_numbers = []
            for x0, y0, x1, y1, text in matches:
                clean_text = text.strip()
                num_match = re.search(r"([1-9][0-9]{2,})", clean_text)
                if num_match:
                    rough_numbers.append(int(num_match.group(1)))

            if not rough_numbers:
                continue

            best_start, raw_possible_numbers = get_best_docket(rough_numbers, sheet)
            # assumes get_best_docket gives some notion of match quality —
            # e.g. len(raw_possible_numbers), or a score it already returns
            score = len(raw_possible_numbers) if raw_possible_numbers else 0
            results[angle] = (score, best_start, raw_possible_numbers, rough_numbers)
            print("angle", angle, "score", score, "best_start", best_start)

        if not results:
            return None, None, None

        best_angle = max(results, key=lambda a: results[a][0])
        score, best_start, raw_possible_numbers, rough_numbers = results[best_angle]
        return best_angle, best_start, raw_possible_numbers

    # bestrot, scores = best_rotation_eng(img)
    bestrot, eventtime, pono = best_rotation_by_docket(img, sheet)
    print("chosen rotation", bestrot, eventtime, len(pono))
    rotated = img.rotate(bestrot, expand=True)

    hocr_bytes = pytesseract.image_to_pdf_or_hocr(
        rotated, extension="hocr", lang="eng", config="--psm 11"
    )
    hocr_data = hocr_bytes.decode("utf-8")

    matches = re.findall(word_pattern, hocr_data)

    rough_numbers = []
    for x0, y0, x1, y1, text in matches:
        clean_text = text.strip()
        # print("clean=", clean_text)
        num_match = re.search(r"([1-9][0-9]{2,})", clean_text)
        if num_match:
            num = num_match.group(1)
            rough_numbers.append(int(num))
    print("rough", rough_numbers)
    best_start, raw_possible_numbers = get_best_docket(rough_numbers, sheet)

    master_data = {}
    display_order = []
    ocr_found_numbers = {}

    # CRITICAL FIX: Ensure all targeted numbers are stored strictly as STRINGS
    possible_numbers = [str(n) for n in raw_possible_numbers]

    def rotate_point(x, y, w, h, angle_deg):
        cx = w / 2
        cy = h / 2

        theta = math.radians(angle_deg)

        # Translate point to origin
        dx = x - cx
        dy = y - cy

        # Rotate
        rx = dx * math.cos(theta) - dy * math.sin(theta)
        ry = dx * math.sin(theta) + dy * math.cos(theta)

        # Translate back
        return rx + cx, ry + cy

    # First pass: Collect all bounding boxes found by OCR matching our docket strings
    for x0, y0, x1, y1, text in matches:
        clean_text = text.strip()
        num_match = re.search(r"([1-9][0-9]{2,})", clean_text)
        if num_match:
            num = str(num_match.group(1))  # Keep as string
            if num in possible_numbers:
                if num not in ocr_found_numbers:
                    ocr_found_numbers[num] = []

                x = int(x0) + (int(x1) - int(x0)) // 2
                y = int(y0) + (int(y1) - int(y0)) // 2

                rx, ry = rotate_point(x, y, rotated.width, rotated.height, bestrot)

                ocr_found_numbers[num].append(
                    {
                        "x": rx,
                        "y": ry,
                        "note": clean_text.replace(num, "").replace("-", "").strip(),
                    }
                )

    # --- 3. RESTRUCTURE MASTER DATA USING UNIQUE GENERATED IDs ---
    lbl_index = 0

    for num in possible_numbers:
        num_str = str(num)

        # Check if this string number exists in our matches coordinate lists
        if num_str in ocr_found_numbers and len(ocr_found_numbers[num_str]) > 0:
            ocr_instance = ocr_found_numbers[num_str].pop(0)

            uid = f"lbl_{num_str}_{lbl_index}"
            lbl_index += 1

            master_data[uid] = {
                "id": uid,
                "number": num_str,
                "present": True,
                "note": ocr_instance["note"],
                "x": ocr_instance["x"],
                "y": ocr_instance["y"],
                "is_ocr": True,
            }
            display_order.append(uid)
        else:
            uid = f"lbl_{num_str}_{lbl_index}"
            lbl_index += 1

            master_data[uid] = {
                "id": uid,
                "number": num_str,
                "present": False,
                "note": "",
                "x": None,
                "y": None,
                "is_ocr": False,
            }
            display_order.append(uid)

    tz_ohio = ZoneInfo("America/New_York")
    return {
        "master_data": master_data,
        "display_order": display_order,
        "rotation": (-bestrot) % 360,
        "zoom": 0.5,
        "x_offset": 0,
        "y_offset": 0,
        "detected_date": (
            best_start.astimezone(tz_ohio).isoformat() if best_start else None
        ),
    }


class FileLoad(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request, filename):
        sheet = get_object_or_404(CheckinSheet, pk=filename)

        print("proc", sheet.processed)
        if sheet.processed:
            return Response(sheet.processed)

        try:
            res = extract_sheet(sheet)
        except Exception as e:
            logging.error("failed to extract sheet %s", e.__repr__())
            res = {
                "master_data": {},
                "display_order": [],
                "rotation": 0,
                "zoom": 0.5,
                "x_offset": 0,
                "y_offset": 0,
                "detected_date": None,
            }
        return Response(res)


class AllCasesUpcomingEventCountsView(APIView):
    """
    GET /events/upcoming-event-counts/

    For every case, takes only its most recent snapshot, then returns
    events (start's date >= today, so today's earlier events are included)
    grouped by start datetime with a count per group.
    """

    permission_classes = (DjangoModelPermissions,)

    queryset = Event.objects.all()

    def get(self, request):
        today = datetime(2026,5,6).date() # datetime.now().date()

        # For each snapshot, find the id of the latest snapshot belonging
        # to the same case (tie-broken by id for determinism).
        latest_snapshot_subquery = (
            CaseSnapshot.objects.filter(case=OuterRef("case"))
            .order_by("-created_at", "-id")
            .values("id")[:1]
        )

        latest_snapshot_ids = (
            CaseSnapshot.objects.annotate(latest_id=Subquery(latest_snapshot_subquery))
            .filter(id=F("latest_id"))
            .values_list("id", flat=True)
        )

        qs = (
            Event.objects.filter(
                snapshot_id__in=latest_snapshot_ids,
                start__date__gte=today,
            )
            .values("start")
            .annotate(count=Count("id"))
            .order_by("start")
        )

        serializer = GroupedEventCountSerializer(qs, many=True)
        return Response(serializer.data)


class EventsAtTimeView(APIView):
    """
    Returns all events at the given start datetime, restricted to each
    case's latest snapshot.
    """

    permission_classes = (DjangoModelPermissions,)
    queryset = Event.objects.all()

    def get(self, request):
        raw_start = request.query_params.get("start")
        if not raw_start:
            raise ValidationError({"start": "This query parameter is required."})

        start = parse_datetime(raw_start)
        if start is None:
            raise ValidationError(
                {
                    "start": "Invalid datetime format. Use ISO 8601, e.g. 2026-07-13T09:00:00."
                }
            )

        latest_snapshot_subquery = (
            CaseSnapshot.objects.filter(case=OuterRef("case"))
            .order_by("-created_at")
            .values("created_at")[:1]
        )

        # 3. Query CaseSnapshots, filtering for those that match their case's latest timestamp
        # AND have an event starting at your target time.
        matching_snapshots = (
            CaseSnapshot.objects.annotate(
                latest_created_at=Subquery(latest_snapshot_subquery)
            )
            .filter(created_at=F("latest_created_at"), event__start=start)
            .select_related("case")  # Optimizes fetching the Case
            .prefetch_related("party_set")  # Optimizes fetching all related Parties
        )

        serializer = SlimSnapshotSerializer(matching_snapshots, many=True)
        return Response(serializer.data)


class DocketSessionStateView(APIView):
    permission_classes = (DjangoModelPermissions,)
    queryset = DocketSessionState.objects.all()

    def get(self, request):
        session_start = request.query_params.get('start')
        if not session_start:
            return Response({"error": "Missing 'start' timestamp query parameter"}, status=status.HTTP_400_BAD_REQUEST)

        # Fetch existing state, or gracefully return a structured empty schema
        state, created = DocketSessionState.objects.get_or_create(session_start=session_start)
        serializer = DocketSessionStateSerializer(state)
        return Response(serializer.data)

    def post(self, request):
        session_start = request.data.get('session_start')
        if not session_start:
            return Response({"error": "Missing 'session_start' field"}, status=status.HTTP_400_BAD_REQUEST)

        state, _ = DocketSessionState.objects.get_or_create(session_start=session_start)
        serializer = DocketSessionStateSerializer(state, data=request.data, partial=True)

        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)