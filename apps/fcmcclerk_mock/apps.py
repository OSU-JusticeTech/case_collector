import sys

from django.apps import AppConfig

from apps.fcmcclerk_mock.fake_state import generate_random_fixture


class FcmcclerkMockConfig(AppConfig):
    name = "apps.fcmcclerk_mock"

    def ready(self):
        argv = sys.argv

        command = argv[1] if len(argv) > 1 else None

        if command in ["runserver", "test"]:
            from . import fake_state


            # Generate the random fixture on startup
            fake_state.EVICTION_FIXTURE = generate_random_fixture()
