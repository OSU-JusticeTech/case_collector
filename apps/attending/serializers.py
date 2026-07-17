from rest_framework import serializers
from .models import DocketSessionState

class DocketSessionStateSerializer(serializers.ModelSerializer):
    class Meta:
        model = DocketSessionState
        fields = ['session_start', 'check_in_store', 'attorney_check_store', 'case_notes_store', 'updated_at']