from PyQt5.QtWidgets import (
    QDialog, QFormLayout, QDoubleSpinBox, QSpinBox, QDialogButtonBox,
    QPushButton, QVBoxLayout, QColorDialog, QLabel, QSlider
)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QColor
from krita import Krita, Extension
import math

class ThreePointPerspectiveGridDialog(QDialog):
    def __init__(self, params, preview_callback=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("3-Point Perspective Grid")
        self.params = params
        self.preview_callback = preview_callback

        self.preview_timer = QTimer(self)
        self.preview_timer.setSingleShot(True)
        self.preview_timer.timeout.connect(self.emit_preview)

        layout = QVBoxLayout()
        form = QFormLayout()

        # VP1 angle (from vertical to left vanishing point)
        self.vp1_angle_spin = QDoubleSpinBox()
        self.vp1_angle_spin.setRange(0.1, 89.9)
        self.vp1_angle_spin.setValue(self.params['vp1_angle'])
        self.vp1_angle_spin.setSuffix("°")
        self.vp1_angle_spin.setToolTip("Angle from vertical to VP1 (left side)")
        self.vp1_angle_spin.valueChanged.connect(lambda val: self.on_vp1_angle_changed(val))
        form.addRow("VP1 angle", self.vp1_angle_spin)

        self.vp1_angle_slider = QSlider(Qt.Horizontal)
        self.vp1_angle_slider.setRange(1, 899)
        self.vp1_angle_slider.setValue(round(self.params['vp1_angle'] * 10))
        self.vp1_angle_slider.valueChanged.connect(lambda val: self.on_vp1_angle_changed(val / 10.0))
        form.addRow("", self.vp1_angle_slider)

        self.vp2_label = QLabel(f"{(90.0 - self.params['vp1_angle']):.2f}")
        form.addRow("VP2 angle", self.vp2_label)

        # Tilt angle (horizon above/below center of vision)
        self.tilt_spin = QDoubleSpinBox()
        self.tilt_spin.setRange(-89.9, 89.9)
        self.tilt_spin.setValue(self.params['tilt'])
        self.tilt_spin.setSingleStep(5)
        self.tilt_spin.setSuffix("°")
        self.tilt_spin.setToolTip("Positive = high angle view (horizon above center)")
        self.tilt_spin.valueChanged.connect(self.request_preview)
        form.addRow("Tilt angle", self.tilt_spin)

        # Cone of vision
        self.cone_spin = QDoubleSpinBox()
        self.cone_spin.setRange(1, 179)
        self.cone_spin.setValue(self.params['cone_of_vision'])
        self.cone_spin.setSuffix("°")
        self.cone_spin.setToolTip("Field of view exactly spans the canvas width. Smaller = telephoto (flatter), larger = wide‑angle (more distortion).")
        self.cone_spin.valueChanged.connect(self.request_preview)
        form.addRow("Cone of vision", self.cone_spin)

        # Grid density
        self.lines_per_vp = QSpinBox()
        self.lines_per_vp.setRange(2, 360)
        self.lines_per_vp.setValue(self.params['lines_per_vp'])
        self.lines_per_vp.valueChanged.connect(self.request_preview)
        form.addRow("Lines per VP", self.lines_per_vp)

        layout.addLayout(form)

        # Color pickers
        color_layout = QFormLayout()
        self.colors = self.params['colors']
        for name, default in self.colors.items():
            btn = QPushButton()
            btn.setStyleSheet(f"background-color: {default.name()}")
            btn.clicked.connect(lambda _, n=name, b=btn: self.pick_color(n, b))
            color_layout.addRow(f"{name} color", btn)
        layout.addLayout(color_layout)

        # OK / Cancel
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.handle_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self.setLayout(layout)
        self.preview_timer.start(0)

    def on_vp1_angle_changed(self, angle):
        self.vp1_angle_spin.blockSignals(True)
        self.vp1_angle_spin.setValue(angle)
        self.vp1_angle_spin.blockSignals(False)

        self.vp1_angle_slider.blockSignals(True)
        self.vp1_angle_slider.setValue(round(angle * 10))
        self.vp1_angle_slider.blockSignals(False)

        self.vp2_label.setText(f"{(90.0 - angle):.2f}°")

        self.request_preview()

    def pick_color(self, name, button):
        col = QColorDialog.getColor(self.colors[name], self, f"Pick color for {name}")
        if col.isValid():
            self.colors[name] = col
            button.setStyleSheet(f"background-color: {col.name()}")
            self.request_preview()

    def request_preview(self):
        self.preview_timer.start(400)

    def emit_preview(self):
        if self.isVisible() and self.preview_callback:
            self.preview_callback(self.get_current_params())

    def get_current_params(self):
        return {
            "vp1_angle": self.vp1_angle_spin.value(),
            "tilt": self.tilt_spin.value(),
            "cone_of_vision": self.cone_spin.value(),
            "lines_per_vp": self.lines_per_vp.value(),
            "colors": self.colors,   # colors dict is updated in place
        }

    def handle_accept(self):
        self.params.update(self.get_current_params())
        self.accept()


class ThreePointPerspectiveGridExtension(Extension):
    def __init__(self, parent):
        super().__init__(parent)
        self.params = {
            "vp1_angle": 15,
            "tilt": 0,
            "cone_of_vision": 78,
            "lines_per_vp": 12,
            "colors": {
                "VP1": QColor(204, 221, 255),
                "VP2": QColor(204, 221, 255),
                "VP3": QColor(249, 204, 255),
                "VPD": QColor(255, 238, 204),
                "HL": QColor(128, 128, 128),
            },
        }
        self.current_dlg = None
        self.doc = None

    def setup(self):
        pass

    def createActions(self, window):
        action = window.createAction("threepoint_perspective_grid", "Three-Point Perspective Grid", "tools/scripts")
        action.triggered.connect(self.show_dialog)

    def show_dialog(self):
        doc = Krita.instance().activeDocument()
        if not doc:
            return

        if self.current_dlg and self.current_dlg.isVisible():
            self.current_dlg.raise_()
            return

        self.doc = doc
        self.remove_preview_layer(doc)

        main_window = Krita.instance().activeWindow().qwindow()
        self.current_dlg = ThreePointPerspectiveGridDialog(
            self.params,
            self.update_preview,
            main_window
        )
        self.current_dlg.accepted.connect(lambda: self.on_dialog_accepted(self.doc))
        self.current_dlg.rejected.connect(self.on_dialog_rejected)
        self.current_dlg.finished.connect(self.on_dialog_finished)
        self.current_dlg.show()

    def on_dialog_accepted(self, doc):
        """Dialog accepted: rename preview layer to final name, or create final grid if no preview."""
        self.current_dlg = None

        root = doc.rootNode()
        for child in root.childNodes():
            if child.name() == "Perspective Grid (preview)" and child.type() == "vectorlayer":
                child.setName("Perspective Grid")
                return
        self.render_svg_to_layer(doc, self.params, "Perspective Grid")

    def on_dialog_rejected(self):
        self.current_dlg = None
        self.remove_preview_layer(self.doc)

    def on_dialog_finished(self):
        self.current_dlg = None

    def remove_preview_layer(self, doc):
        root = doc.rootNode()
        for child in root.childNodes():
            if child.name() == "Perspective Grid (preview)" and child.type() == "vectorlayer":
                root.removeChildNode(child)

    def update_preview(self, params):
        self.remove_preview_layer(self.doc)
        self.render_svg_to_layer(self.doc, params, "Perspective Grid (preview)")

    def render_svg_to_layer(self, doc, params, layer_name):
        svg = self.build_svg(doc, params)
        vector_layer = doc.createVectorLayer(layer_name)
        vector_layer.addShapesFromSvg(svg)
        previous_node = doc.activeNode()
        doc.rootNode().addChildNode(vector_layer, None)
        if previous_node:
            doc.setActiveNode(previous_node)

    def build_svg(self, doc, params):
        vp1_angle = params["vp1_angle"]
        tilt = params["tilt"]
        cone_of_vision = params["cone_of_vision"]
        lines = params["lines_per_vp"]
        colors = params["colors"]

        W = doc.width()
        H = doc.height()
        cx = W / 2    # center of vision
        cy = H / 2    # center of vision
        corners = [(0, 0), (W, 0), (W, H), (0, H)]

        # Station point distance to the picture plane
        distance_sp = (W / 2) / math.tan(math.radians(cone_of_vision / 2.0))

        # Horizon y
        y_hl = cy - distance_sp * math.tan(math.radians(tilt))

        # VP3 (vertical vanishing point)
        if abs(tilt) < 1e-6:
            vp3 = None
        else:
            vp3 = (cx, cy + distance_sp * math.tan(math.radians(90 - tilt)))

        # Distance of vertical station point to Horizon Line
        d_vsp = distance_sp / math.cos(math.radians(tilt))

        # Vanishing points on horizon
        vp1 = (cx - d_vsp * math.tan(math.radians(vp1_angle)), y_hl)
        vp2 = (cx + d_vsp * math.tan(math.radians(90 - vp1_angle)), y_hl)
        vpd = (cx + d_vsp * math.tan(math.radians(45 - vp1_angle)), y_hl)

        vp_positions = {
            "VP1": vp1,
            "VP2": vp2,
            "VPD": vpd,
        }
        if vp3 is not None:
            vp_positions["VP3"] = vp3

        # Build SVG paths
        svg_parts = ['<svg xmlns="http://www.w3.org/2000/svg">']

        # Generate rays from the vanishing points
        for vp_name, point in vp_positions.items():
            color_hex = colors[vp_name].name()
            ray_segments = self.equal_angle_rays(point, corners, lines)
            for (x1, y1), (x2, y2) in ray_segments:
                svg_parts.append(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" ' f'stroke="{color_hex}" stroke-width="2" opacity="1"/>')

        hl_color = colors["HL"].name()
        svg_parts.append(f'<line x1="0" y1="{y_hl}" x2="{W}" y2="{y_hl}" stroke="{hl_color}" stroke-width="1" opacity="0.8"/>') # horizon line
        svg_parts.append(f'<line x1="{cx}" y1="0" x2="{cx}" y2="{H}" stroke="{hl_color}" stroke-width="1" opacity="0.6"/>')     # vertical line
        svg_parts.append('</svg>')

        return "".join(svg_parts)

    def equal_angle_rays(self, point, corners, lines):
        px, py = point
        canvas_width, canvas_height = corners[2]
        num_lines = lines

        # if vp is inside the canvas, wrap the whole 360 circle
        if (0 <= px <= canvas_width and 0 <= py <= canvas_height):
            min_ang = 0
            max_ang = 2 * math.pi
            num_lines = 2 * lines
        else:
            angles = [math.atan2(y - py, x - px) for (x, y) in corners]
            min_ang = min(angles)
            max_ang = max(angles)
            if max_ang - min_ang > math.pi:
                # Normalize angles to [0, 2π)
                angles = [a if a >= 0 else a + 2 * math.pi for a in angles]
                min_ang = min(angles)
                max_ang = max(angles)

        step = (max_ang - min_ang) / num_lines
        rays = []

        for i in range(num_lines + 1):
            ang = min_ang + i * step
            segment = self.ray_rect_intersection(point, ang, corners)
            if segment is not None:
                rays.append(segment)

        return rays

    def ray_rect_intersection(self, point, angle, corners):
        """Find intersection of the ray (starting at VP) with the canvas bounding box."""
        px, py = point
        x_min, y_min = corners[0]
        x_max, y_max = corners[2]

        # ray direction vector
        dx = math.cos(angle)
        dy = math.sin(angle)

        t_min = float('-inf')
        t_max = float('inf')

        # Check X-axis slab
        if abs(dx) < 1e-9:
            if px < x_min or px > x_max:
                return None
        else:
            t1 = (x_min - px) / dx
            t2 = (x_max - px) / dx
            t_min = max(t_min, min(t1, t2))
            t_max = min(t_max, max(t1, t2))

        # Check Y-axis slab
        if abs(dy) < 1e-9:
            if py < y_min or py > y_max:
                return None
        else:
            t1 = (y_min - py) / dy
            t2 = (y_max - py) / dy
            t_min = max(t_min, min(t1, t2))
            t_max = min(t_max, max(t1, t2))

        # If t_max < 0, the rectangle is completely behind the ray
        # If t_min > t_max, the ray misses the rectangle completely
        if t_min > t_max or t_max < 0:
            return None

        # Case 1: Ray origin is outside the rectangle (t_min >= 0)
        if t_min >= 0:
            p_entry = (px + t_min * dx, py + t_min * dy)
            p_exit = (px + t_max * dx, py + t_max * dy)
            return (p_entry, p_exit)
        # Case 2: Ray origin is inside the rectangle (t_min < 0 and t_max >= 0)
        else:
            p_entry = (px, py)
            p_exit = (px + t_max * dx, py + t_max * dy)
            return (p_entry, p_exit)
