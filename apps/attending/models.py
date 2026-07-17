from django.db import models

# Create your models here.


class CheckinSheet(models.Model):
    photo = models.ImageField(null=True, upload_to="checkin")
    filename = models.CharField()
    taken_at = models.DateTimeField()
    file_hash = models.CharField(max_length=64, unique=True)

    possible_start = models.DateField(null=True, blank=True)
    possible_end = models.DateField(null=True, blank=True)

    processed = models.JSONField(null=True, blank=True)
    validated = models.BooleanField(default=False)

    event_time = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return self.filename

class DocketSessionState(models.Model):
    """
    Persists session-wide docket configurations, check-ins, and local annotations.
    """
    session_start = models.DateTimeField(unique=True, help_text="ISO Start Timestamp of the Session Window")
    check_in_store = models.JSONField(default=dict, blank=True, help_text="Map of party.id -> boolean")
    attorney_check_store = models.JSONField(default=dict, blank=True, help_text="Map of attorneyName -> boolean")
    case_notes_store = models.JSONField(default=dict, blank=True, help_text="Map of item.id -> freetext note string")
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Docket State for Session: {self.session_start}"