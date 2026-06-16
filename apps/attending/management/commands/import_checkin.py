import hashlib
from pathlib import Path
from datetime import datetime

from django.core.files import File
from django.core.management.base import BaseCommand
from django.utils import timezone

import exifread

from apps.attending.models import CheckinSheet

def compute_hash(path, chunk_size=1024 * 1024):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(chunk_size):
            h.update(chunk)
    return h.hexdigest()

def get_taken_at(path):
    with open(path, "rb") as f:
        tags = exifread.process_file(f)

    dt = tags.get("EXIF DateTimeOriginal")
    subsec = tags.get("EXIF SubSecTimeOriginal")

    if not dt:
        return timezone.now()

    ts = datetime.strptime(str(dt), "%Y:%m:%d %H:%M:%S")

    if subsec:
        ts = ts.replace(microsecond=int(str(subsec).ljust(6, "0")[:6]))

    return timezone.make_aware(ts)


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument("folder", type=str)

    def handle(self, *args, **options):
        folder = Path(options["folder"])

        image_exts = {".jpg", ".jpeg", ".png", ".webp"}

        created = 0
        skipped = 0

        for path in folder.iterdir():
            if not path.is_file() or path.suffix.lower() not in image_exts:
                continue

            file_hash = compute_hash(path)

            # ---- DUPLICATE CHECK (fast) ----
            if CheckinSheet.objects.filter(file_hash=file_hash).exists():
                skipped += 1
                continue

            taken_at = get_taken_at(path)

            with path.open("rb") as f:
                obj = CheckinSheet(
                    filename=path.name,
                    taken_at=taken_at,
                    file_hash=file_hash,
                )
                obj.photo.save(path.name, File(f), save=False)
                obj.save()

            created += 1

        self.stdout.write(f"Created: {created}, Skipped: {skipped}")