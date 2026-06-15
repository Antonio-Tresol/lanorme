"""Variables, attributes, and dict keys that contain SQL-ish words but are
plain Python identifiers -- not SQL strings handed to a DB.

UI code, selectors, signal names, and config keys often have ``select`` or
``update`` in their identifiers. The substring is part of an English noun,
not a SQL keyword in a payload.
"""

from __future__ import annotations


def build_form():
    select_box = {"options": ["red", "green", "blue"]}
    update_button_label = "Save changes"
    delete_modal_id = "confirm-delete"
    return select_box, update_button_label, delete_modal_id


def configure(settings):
    insert_position = settings.get("insert_position", "end")
    drop_zone = settings.get("drop_zone", "main")
    create_button = settings.get("create_button_label", "New")
    return insert_position, drop_zone, create_button


SELECTION_MODES = ("single", "multi", "none")


def on_update_signal(handler):
    handler.connect("update", lambda *a: None)


def select_from_list(items, index):
    return items[index]


class Widget:
    def update(self):
        return None

    def delete(self):
        return None
