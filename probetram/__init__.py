# coding=utf-8
from __future__ import absolute_import

import flask
import octoprint.plugin
import re

from octoprint.events import Events


class ProbeTramPlugin(octoprint.plugin.TemplatePlugin,
                      octoprint.plugin.SettingsPlugin,
                      octoprint.plugin.AssetPlugin,
                      octoprint.plugin.EventHandlerPlugin,
                      octoprint.plugin.SimpleApiPlugin):

    def __init__(self):
        self.is_probing = False
        self.probe_queue = []
        self.status_flag = False

        self.last_probed_point = -1
        self.current_point = -1

    def on_api_command(self, command, data):
        if command == "probe_point":
            valid_point = "point" in data.keys() and str(data["point"]).isnumeric()
            if not valid_point:
                return flask.jsonify(result="FAIL", desc="Invalid Coordinates")
            else:
                return flask.jsonify(self.add_point_to_queue(int(data["point"])))

        elif command == "probe_all":
            responses = {"points": [], "result": "PASS"}
            for i in [0, 1, 2, 3]:
                responses["points"].append(self.add_point_to_queue(i, is_batch=True))
            responses["points"].append(self.add_point_to_queue(4, is_batch=True, is_batch_tail=True))
            return flask.jsonify(responses)

    def add_point_to_queue(self, point_num, is_batch=False, is_batch_tail=False):
        x_coord = self._settings.get([f"X{int(point_num)}"])
        y_coord = self._settings.get([f"Y{int(point_num)}"])
        command = f"G30 X{x_coord} Y{y_coord}"

        point_data = {
            "point": point_num,
            "gcode": command,
            "isBatch": is_batch,
            "isBatchTail": is_batch_tail
        }

        event = octoprint.events.Events.PLUGIN_PROBETRAM_RECEIVED_POINT
        self._event_bus.fire(event, payload=point_data)

        return dict(result="PASS", desc=f"Probing Point ({x_coord},{y_coord})")

    def handle_received_point_event(self, point_data):
        if self.is_probing:
            self.probe_queue.append(point_data)
            return
        self.probe(point_data)

    def handle_probe_complete_event(self):
        self.is_probing = False
        self.last_probed_point = self.current_point
        if len(self.probe_queue) == 0:
            self.current_point = -1
            return
        self.probe(self.probe_queue.pop(0))

    def probe(self, point_data):
        self._printer.commands(point_data["gcode"])
        self.is_probing = True
        self.current_point = point_data["point"]

    def on_event(self, event, payload):
        if event == "PrinterStateChanged":
            if payload["state_id"] == "OPERATIONAL":
                self.status_flag = True
                self._event_bus.fire(octoprint.events.Events.PLUGIN_PROBETRAM_UI_AVAILABILITY_CHANGE, payload={"available": True})
            elif self.status_flag:
                self.status_flag = False
                self._event_bus.fire(octoprint.events.Events.PLUGIN_PROBETRAM_UI_AVAILABILITY_CHANGE, payload={"available": False})
                # self._event_bus.fire(octoprint.events.Events.PRINTER_STATE_CHANGED)

        if not event.startswith("plugin_probetram"):
            return

        event = event.replace("plugin_probetram_", "")
        if event == "received_point":
            self.handle_received_point_event(payload)
            return

        if event == "probe_complete":
            self.handle_probe_complete_event()
            return

    def on_receive_gcode(self, comm, line, *args, **kwargs):
        event = octoprint.events.Events.PLUGIN_PROBETRAM_PROBE_COMPLETE
        result = re.match(r"Bed X: ([\d.-]*) Y: ([\d.-]*) Z: ([\d.-]*)", line)

        if result is not None:
            self.is_probing = False

            x = float(result.group(1))
            y = float(result.group(2))
            z = float(result.group(3))

            self._event_bus.fire(event, payload={"point": self.current_point, "x": x, "y": y, "z": z})

        return line

    def register_custom_events(*args, **kwargs):
        return ["probe_complete", "received_point", "ui_availability_change"]

    def get_settings_defaults(self):

        bed_margin = 30
        printer = self._printer_profile_manager.get_current_or_default()
        x_max = printer["volume"]["width"]
        y_max = printer["volume"]["depth"]

        settings_dict = {
            "X0": str(bed_margin),
            "Y0": str(y_max - bed_margin),
            "X1": str(x_max - bed_margin),
            "Y1": str(y_max - bed_margin),
            "X2": str(bed_margin),
            "Y2": str(bed_margin),
            "X3": str(x_max - bed_margin),
            "Y3": str(bed_margin),
            "X4": str(x_max / 2),
            "Y4": str(y_max / 2)
        }

        return settings_dict

    def get_template_configs(self):
        return [
            dict(type="navbar", custom_bindings=False),
            dict(type="settings", custom_bindings=False)
        ]

    def get_assets(self):
        return dict(
            css=["css/probetram.css", "css/font-awesome.min.css"],
            js=["js/probetram.js"]
        )

    def get_api_commands(self):
        return dict(
            probe_point=["point"],
            probe_all=[])


__plugin_name__ = "Probe Tramming"
__plugin_author__ = "Max DeVos"
__plugin_url__ = ""
__plugin_description__ = "Allows users to probe selected corners of the bed with a bed-leveling sensor for physical leveling"
__plugin_license__ = "AGPLv3"
__plugin_pythoncompat__ = ">=3.7,<4"
__plugin_version__ = "1.0.0"


def __plugin_load__():
    global __plugin_implementation__
    __plugin_implementation__ = ProbeTramPlugin()

    global __plugin_hooks__
    __plugin_hooks__ = {
        "octoprint.comm.protocol.gcode.received": __plugin_implementation__.on_receive_gcode,
        "octoprint.events.register_custom_events": __plugin_implementation__.register_custom_events
    }
