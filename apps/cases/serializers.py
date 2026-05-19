from rest_framework import serializers

from apps.cases.models import CaseSnapshot, Party, DocketEntry, Event, Finance, Disposition, CourtCase


class DispositionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Disposition
        fields = "__all__"

class FinanceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Finance
        fields = "__all__"

class EventSerializer(serializers.ModelSerializer):
    class Meta:
        model = Event
        fields = "__all__"

class DocketSerializer(serializers.ModelSerializer):
    class Meta:
        model = DocketEntry
        fields = "__all__"

class PartySerializer(serializers.ModelSerializer):
    class Meta:
        model = Party
        fields = "__all__"

class CaseSerializer(serializers.ModelSerializer):
    class Meta:
        model = CourtCase
        fields = "__all__"

class SnapshotSerializer(serializers.ModelSerializer):
    case = CaseSerializer()
    parties = PartySerializer(source="party_set", many=True)
    docket = DocketSerializer(source="docketentry_set", many=True)
    events = EventSerializer(source="event_set", many=True)
    finances = FinanceSerializer(source="finance_set", many=True)
    dispositions = DispositionSerializer(source="disposition_set", many=True)

    class Meta:
        model = CaseSnapshot
        fields = "__all__"