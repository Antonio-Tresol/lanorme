"""Disabled def/class/decorator lines from old implementations."""

from __future__ import annotations


# @cache
# @staticmethod
# @app.route("/legacy", methods=["GET"])
def current_handler() -> str:
    return "ok"


# def legacy_handler(request):
#     return Response(status=410)


# class LegacyService:
#     def __init__(self, client):
#         self.client = client
#
#     def run(self) -> None:
#         self.client.send()


class NewService:
    """Active service."""

    # @property
    # def name(self) -> str:
    #     return self._name
    def get_name(self) -> str:
        return "new"
