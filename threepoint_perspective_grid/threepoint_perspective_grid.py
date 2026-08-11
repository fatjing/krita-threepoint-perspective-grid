from PyQt5.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QFormLayout,
    QGridLayout,
    QCheckBox,
    QColorDialog,
    QDialogButtonBox,
    QLabel,
    QPushButton,
)
from PyQt5.QtCore import Qt, QTimer, QByteArray, QPointF
from PyQt5.QtGui import QColor, QPainter, QPen, QImage
from krita import Krita, Extension, DoubleSliderSpinBox, SliderSpinBox
import math, json, copy

class ThreePointPerspectiveGridDialog(QDialog):
    def __init__(self, params, defaults, preview_callback=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("3-Point Perspective Grid")
        self.params = params
        self.defaults = defaults
        self.preview_callback = preview_callback
        self.preview_timer = QTimer(self)
        self.preview_timer.setSingleShot(True)
        self.preview_timer.timeout.connect(self.emit_preview)

        layout = QVBoxLayout()
        form = QFormLayout()

        # Left vanishing point angle
        self.vp1_angle_spin = DoubleSliderSpinBox().widget()
        self.vp1_angle_spin.setRange(0.0, 90.0)
        self.vp1_angle_spin.setValue(self.params['vp1_angle'])
        self.vp1_angle_spin.setSingleStep(5)
        self.vp1_angle_spin.setSuffix("°")
        self.vp1_angle_spin.setToolTip("Angle from the viewing direction to the left set of grid lines")
        self.vp1_angle_spin.valueChanged.connect(self.on_vp1_angle_changed)
        form.addRow("LVP angle", self.vp1_angle_spin)

        self.vp2_label = QLabel(f"{(90.0 - self.params['vp1_angle']):.2f}°")
        form.addRow("RVP angle", self.vp2_label)

        # Camera Pitch
        self.pitch_spin = DoubleSliderSpinBox().widget()
        self.pitch_spin.setRange(-90.0, 90.0)
        self.pitch_spin.setValue(self.params['pitch'])
        self.pitch_spin.setSingleStep(5)
        self.pitch_spin.setSuffix("°")
        self.pitch_spin.setToolTip("Camera pitch")
        self.pitch_spin.valueChanged.connect(self.request_preview)
        form.addRow("Pitch", self.pitch_spin)

        # Camera Roll
        self.roll_spin = DoubleSliderSpinBox().widget()
        self.roll_spin.setRange(-180.0, 180.0)
        self.roll_spin.setValue(self.params['roll'])
        self.roll_spin.setSuffix("°")
        self.roll_spin.setToolTip("Camera roll")
        self.roll_spin.valueChanged.connect(self.request_preview)
        form.addRow("Roll", self.roll_spin)

        # Field of view
        self.fov_spin = DoubleSliderSpinBox().widget()
        self.fov_spin.setRange(0.1, 179.9)
        self.fov_spin.setValue(self.params['fov'])
        self.fov_spin.setSuffix("°")
        self.fov_spin.setToolTip("Diagonal field of view. Spans the canvas from corner to corner")
        self.fov_spin.valueChanged.connect(self.request_preview)
        form.addRow("FOV", self.fov_spin)

        # Diagonal vanishing points
        dvp_layout = QVBoxLayout()
        vert_dvp_layout = QHBoxLayout()

        self.show_dvp_check = QCheckBox("Ground plane")
        self.show_dvp_check.setChecked(self.params["show_dvp"])
        self.show_dvp_check.setToolTip("Diagonal vp on ground plane")
        self.show_dvp_check.stateChanged.connect(self.request_preview)
        dvp_layout.addWidget(self.show_dvp_check)

        self.show_ldvp_check = QCheckBox("Left wall")
        self.show_ldvp_check.setChecked(self.params["show_ldvp"])
        self.show_ldvp_check.setToolTip("Diagonal vp on left vertical plane")
        self.show_ldvp_check.stateChanged.connect(self.request_preview)
        vert_dvp_layout.addWidget(self.show_ldvp_check)

        self.show_rdvp_check = QCheckBox("Right wall")
        self.show_rdvp_check.setChecked(self.params["show_rdvp"])
        self.show_rdvp_check.setToolTip("Diagonal vp on right vertical plane")
        self.show_rdvp_check.stateChanged.connect(self.request_preview)
        vert_dvp_layout.addWidget(self.show_rdvp_check)

        dvp_layout.addLayout(vert_dvp_layout)
        form.addRow("Diagonal VP", dvp_layout)

        # Grid density
        self.grid_density_spin = SliderSpinBox().widget()
        self.grid_density_spin.setRange(2, 180)
        self.grid_density_spin.setValue(self.params['grid_density'])
        self.grid_density_spin.valueChanged.connect(self.request_preview)
        form.addRow("Grid density", self.grid_density_spin)

        # Line width
        self.line_width_spin = SliderSpinBox().widget()
        self.line_width_spin.setRange(1, 20)
        self.line_width_spin.setValue(self.params['line_width'])
        self.line_width_spin.valueChanged.connect(self.request_preview)
        form.addRow("Line width", self.line_width_spin)

        # Line opacity
        self.line_opacity_spin = DoubleSliderSpinBox().widget()
        self.line_opacity_spin.setRange(0.0, 1.0)
        self.line_opacity_spin.setValue(self.params['line_opacity'])
        self.line_opacity_spin.setSingleStep(0.05)
        self.line_opacity_spin.valueChanged.connect(self.request_preview)
        form.addRow("Line opacity", self.line_opacity_spin)

        # Color pickers
        self.colors = {k: v for k, v in self.params['colors'].items()}
        self.color_buttons = {}
        color_grid = QGridLayout()
        for i, (target, color) in enumerate(self.colors.items()):
            btn = QPushButton(target)
            fg = self.contrasting_text_color(color)
            btn.setStyleSheet(f"background-color: {color}; color: {fg}")
            btn.clicked.connect(lambda _, t=target: self.pick_color(t))
            color_grid.addWidget(btn, i // 2, i % 2)
            self.color_buttons[target] = btn
        form.addRow("Colors", color_grid)

        layout.addLayout(form)

        # Reset + OK/Cancel buttons
        reset_btn = QPushButton("Reset")
        reset_btn.clicked.connect(self.reset_to_defaults)
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        buttons_layout = QHBoxLayout()
        buttons_layout.addWidget(reset_btn)
        buttons_layout.addStretch()
        buttons_layout.addWidget(button_box)
        layout.addLayout(buttons_layout)

        self.setLayout(layout)

    def pick_color(self, target):
        color = QColorDialog.getColor(QColor(self.colors[target]), self, f"Pick color for {target}")
        if color.isValid():
            self.colors[target] = color.name()
            fg = self.contrasting_text_color(color.name())
            self.color_buttons[target].setStyleSheet(f"background-color: {color.name()}; color: {fg}")
            self.request_preview()

    def contrasting_text_color(self, bg):
        bg = QColor(bg)
        r, g, b = bg.redF(), bg.greenF(), bg.blueF()
        def linearize(c):
            return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
        luminance = 0.2126 * linearize(r) + 0.7152 * linearize(g) + 0.0722 * linearize(b)
        return "#333333" if luminance > 0.179 else "#f4f4f4"

    def on_vp1_angle_changed(self, angle):
        self.vp2_label.setText(f"{(90.0 - angle):.2f}°")
        self.request_preview()

    def request_preview(self):
        self.preview_timer.start(16)

    def emit_preview(self):
        if self.isVisible() and self.preview_callback:
            self.preview_callback(self.get_current_params())

    def restore_geometry(self):
        data = Krita.instance().readSetting("ThreePointPerspectiveGrid", "dialogGeometry", "")
        if data:
            self.restoreGeometry(QByteArray.fromBase64(data.encode()))

    def save_geometry(self):
        data = self.saveGeometry().toBase64().data().decode()
        Krita.instance().writeSetting("ThreePointPerspectiveGrid", "dialogGeometry", data)

    def get_current_params(self):
        return {
            "vp1_angle": self.vp1_angle_spin.value(),
            "pitch": self.pitch_spin.value(),
            "roll": self.roll_spin.value(),
            "fov": self.fov_spin.value(),
            "show_dvp": self.show_dvp_check.isChecked(),
            "show_ldvp": self.show_ldvp_check.isChecked(),
            "show_rdvp": self.show_rdvp_check.isChecked(),
            "grid_density": self.grid_density_spin.value(),
            "line_width": self.line_width_spin.value(),
            "line_opacity": self.line_opacity_spin.value(),
            "colors": {k: v for k, v in self.colors.items()}
        }

    def reset_to_defaults(self):
        d = self.defaults
        self.vp1_angle_spin.setValue(d["vp1_angle"])
        self.pitch_spin.setValue(d["pitch"])
        self.roll_spin.setValue(d["roll"])
        self.fov_spin.setValue(d["fov"])
        self.show_dvp_check.setChecked(d["show_dvp"])
        self.show_ldvp_check.setChecked(d["show_ldvp"])
        self.show_rdvp_check.setChecked(d["show_rdvp"])
        self.grid_density_spin.setValue(d["grid_density"])
        self.line_width_spin.setValue(d["line_width"])
        self.line_opacity_spin.setValue(d["line_opacity"])
        for target, color in d["colors"].items():
            self.colors[target] = color
            fg = self.contrasting_text_color(color)
            self.color_buttons[target].setStyleSheet(f"background-color: {color}; color: {fg}")


class ThreePointPerspectiveGridExtension(Extension):
    DEFAULT_PARAMS = {
        "vp1_angle": 30,
        "pitch": 0,
        "roll": 0,
        "fov": 78,
        "show_dvp": True,
        "show_ldvp": False,
        "show_rdvp": False,
        "grid_density": 14,
        "line_width": 1,
        "line_opacity": 1.0,
        "colors": {
            "VP1":  "#acb8ff",
            "VP2":  "#acb8ff",
            "VP3":  "#e99df5",
            "DVP":  "#f3dc85",
            "LDVP": "#c0eac7",
            "RDVP": "#afeaea",
            "AXES": "#bdc4cb",
        }
    }

    def __init__(self, parent):
        super().__init__(parent)
        self.params = self.load_settings()
        self.current_dlg = None
        self.doc = None
        self.preview_layer = None
        self.view = None
        self.notifier = None

    def setup(self):
        pass

    def createActions(self, window):
        action = window.createAction("threepoint_perspective_grid", "Three-Point Perspective Grid", "tools/scripts")
        action.triggered.connect(self.show_dialog)

    def load_settings(self):
        raw_str = Krita.instance().readSetting("ThreePointPerspectiveGrid", "params", "")
        if raw_str:
            loaded = json.loads(raw_str)
            result = {k: loaded.get(k, v) for k, v in self.DEFAULT_PARAMS.items()}
            result["colors"] = {k: loaded["colors"].get(k, v) for k, v in self.DEFAULT_PARAMS["colors"].items()}
            return result
        return copy.deepcopy(self.DEFAULT_PARAMS)

    def save_settings(self, params):
        Krita.instance().writeSetting("ThreePointPerspectiveGrid", "params", json.dumps(params))

    def show_dialog(self):
        if self.current_dlg and self.current_dlg.isVisible():
            self.current_dlg.raise_()
            return

        self.doc = Krita.instance().activeDocument()
        if not self.doc:
            return

        main_window = Krita.instance().activeWindow().qwindow()
        self.current_dlg = ThreePointPerspectiveGridDialog(self.params, self.DEFAULT_PARAMS, self.update_preview, main_window)
        self.current_dlg.accepted.connect(lambda: self.on_dialog_accepted(self.current_dlg))
        self.current_dlg.rejected.connect(self.on_dialog_rejected)
        self.current_dlg.finished.connect(lambda: self.on_dialog_finished(self.current_dlg))
        self.current_dlg.restore_geometry()
        self.current_dlg.show()

        self.update_preview(self.params)
        self.view = Krita.instance().activeWindow().activeView()
        self.notifier = Krita.instance().notifier()
        self.notifier.viewClosed.connect(self.on_view_closed)

    def on_view_closed(self, view):
        if self.current_dlg and self.view == view:
            self.doc = None
            self.preview_layer = None
            self.current_dlg.reject()

    def on_dialog_accepted(self, dialog):
        self.params = dialog.get_current_params()
        self.save_settings(self.params)
        self.render_svg_to_layer(self.doc, self.params, "Perspective Grid")
        self.remove_preview()

    def on_dialog_rejected(self):
        self.remove_preview()

    def on_dialog_finished(self, dialog):
        dialog.save_geometry()
        if self.notifier:
            self.notifier.viewClosed.disconnect(self.on_view_closed)

    def remove_preview(self):
        if self.preview_layer:
            self.preview_layer.remove()
            self.preview_layer = None

    def update_preview(self, params):
        self.render_qimage_to_layer(self.doc, params, "Perspective Grid (Preview)")

    def render_qimage_to_layer(self, doc, params, layer_name):
        if not self.preview_layer:
            previous_node = doc.activeNode()
            self.preview_layer = doc.createNode(layer_name, "paintlayer")
            doc.rootNode().addChildNode(self.preview_layer, None)
            if previous_node:
                doc.setActiveNode(previous_node)

        W, H = doc.width(), doc.height()
        image = self.build_qimage(params, W, H)
        image = image.convertToFormat(QImage.Format_RGBA8888).rgbSwapped()
        raw_bytes = image.constBits().asstring(image.sizeInBytes())

        self.preview_layer.setPixelData(QByteArray(raw_bytes), 0, 0, W, H)
        doc.refreshProjection()

    def build_qimage(self, params, width, height):
        image = QImage(width, height, QImage.Format_ARGB32_Premultiplied)
        image.fill(Qt.transparent)
        painter = QPainter(image)
        painter.setRenderHint(QPainter.Antialiasing, True)

        lines = self.compute_grid_lines(params, width, height)
        colors = params["colors"]
        line_width = params["line_width"]
        opacity = params["line_opacity"]

        for name, segments in lines.items():
            pen = QPen(QColor(colors[name]), line_width)
            pen.setCosmetic(True)
            painter.setPen(pen)
            painter.setOpacity(opacity)
            for x1, y1, x2, y2 in segments:
                painter.drawLine(QPointF(x1, y1), QPointF(x2, y2))

        painter.end()
        return image

    def render_svg_to_layer(self, doc, params, layer_name):
        svg = self.build_svg(params, doc.width(), doc.height())
        previous_node = doc.activeNode()
        layer = doc.createVectorLayer(layer_name)
        doc.rootNode().addChildNode(layer, None)
        if previous_node:
            doc.setActiveNode(previous_node)
        layer.addShapesFromSvg(svg)

    def build_svg(self, params, W, H):
        lines = self.compute_grid_lines(params, W, H)
        colors = params["colors"]
        width = params["line_width"]
        opacity = params["line_opacity"]

        svg_parts = ['<svg xmlns="http://www.w3.org/2000/svg">']
        for name, segments in lines.items():
            for x1, y1, x2, y2 in segments:
                svg_parts.append(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{colors[name]}" stroke-width="{width}" opacity="{opacity}" />')
        svg_parts.append("</svg>")

        return "".join(svg_parts)

    def compute_grid_lines(self, params, W, H):
        """Generate grid using a 3D camera matrix."""
        vp1_angle = params["vp1_angle"]
        pitch = params["pitch"]
        roll = params["roll"]
        fov = params["fov"]
        density = params["grid_density"]
        show_dvp = params["show_dvp"]
        show_ldvp = params["show_ldvp"]
        show_rdvp = params["show_rdvp"]
        cx = W / 2.0
        cy = H / 2.0

        # Focal length from diagonal field of view
        f = (math.hypot(W, H) / 2.0) / math.tan(math.radians(fov / 2.0))

        # Intrinsic matrix K
        K = [[f, 0, cx], [0, f, cy], [0, 0, 1]]

        # Camera rotation: yaw around Y -> pitch around X -> roll around Z
        R = mat_mat_mul(Rz(math.radians(roll)),
            mat_mat_mul(Rx(math.radians(pitch)),
                        Ry(math.radians(-vp1_angle))))

        # World grid directions (X-Right, Y-Up, Z-Forward)
        D1 = (0, 0, 1)          # forward -> VP1
        D2 = (1, 0, 0)          # right   -> VP2
        D3 = (0, 1, 0)          # up      -> VP3
        Ddvp = (1, 0, 1)        # ground-plane diagonal (D1 + D2)
        vertical_vec = -1 if pitch < 0 else 1   # wall diagonal pointing up or down
        Dldvp = (0, vertical_vec, 1)            # left-wall diagonal (D1 + D3)
        Drdvp = (1, vertical_vec, 0)            # right-wall diagonal (D2 + D3)

        d_list = [("RDVP", Drdvp, show_rdvp), ("LDVP", Dldvp, show_ldvp),
                  ("DVP", Ddvp, show_dvp), ("VP3", D3, True),
                  ("VP2", D2, True), ("VP1", D1, True)]     # correspond to draw order
        vp = {name: self.project_direction(D, R, K) for name, D, isShow in d_list if isShow}

        lines = {}

        # Generate rays for each VP
        for name, vp_info in vp.items():
            segments = self.generate_rays_from_vp(vp_info, W, H, density)
            if segments:
                lines[name] = segments

        lines["AXES"] = []
        horizon_line = self.generate_line_from_two_vps(vp["VP1"], vp["VP2"], W, H)
        if horizon_line:
            lines["AXES"].append(horizon_line)

        vision_center = {"is_inf": False, "point": (cx, cy), "dir_2d": None}
        vertical_center_line = self.generate_line_from_two_vps(vp["VP3"], vision_center, W, H)
        if vertical_center_line:
            lines["AXES"].append(vertical_center_line)

        return lines

    def project_direction(self, D, R, K):
        """ Project a world direction vector D into the image plane. """
        v_cam = mat_vec_mul(R, D)
        vh = mat_vec_mul(K, v_cam)
        if abs(vh[2]) < 1e-9:   # Direction parallel to image plane -> infinite VP
            dir_2d = (v_cam[0], v_cam[1])
            return {'is_inf': True, 'point': None, 'dir_2d': dir_2d}
        else:
            u = vh[0] / vh[2]
            v = vh[1] / vh[2]
            return {'is_inf': False, 'point': (u, v), 'dir_2d': None}

    def generate_rays_from_vp(self, vp, W, H, num_lines):
        segments = []
        if vp['is_inf']:            # Parallel lines
            dx, dy = vp['dir_2d']
            dx_p, dy_p = -dy, dx    # Normal perpendicular to the line direction
            cx, cy = W / 2.0, H / 2.0
            c0 = dx_p * cx + dy_p * cy  # Normal coordinate at the image center

            # Range of normal coordinate across the canvas corners
            corners = [(0, 0), (W, 0), (W, H), (0, H)]
            c_vals = [dx_p * x + dy_p * y for (x, y) in corners]
            min_c = min(c_vals)
            max_c = max(c_vals)

            step = (max_c - min_c) / num_lines
            for i in range(num_lines):
                c = min_c + i * step
                # Find a point on the line: offset from center along normal
                offset = (c - c0) / (dx_p * dx_p + dy_p * dy_p)
                px = cx + offset * dx_p
                py = cy + offset * dy_p
                clipped = clip_line(px, py, dx, dy, 0, 0, W, H)
                if clipped:
                    segments.append(clipped)
        else:                       # Finite VP – fan of rays
            vp_x, vp_y = vp['point']
            min_ang, max_ang = visible_angle_range(vp_x, vp_y, 0, 0, W, H)
            step = (max_ang - min_ang) / num_lines
            for i in range(num_lines):
                ang = min_ang + i * step
                dx = math.cos(ang)
                dy = math.sin(ang)
                clipped = clip_line(vp_x, vp_y, dx, dy, 0, 0, W, H)
                if clipped:
                    segments.append(clipped)
        return segments

    def generate_line_from_two_vps(self, p1, p2, W, H):
        if not p1['is_inf'] and not p2['is_inf']:
            x1, y1 = p1['point']
            x2, y2 = p2['point']
            return clip_line(x1, y1, x2 - x1, y2 - y1, 0, 0, W, H)
        elif p1['is_inf'] and not p2['is_inf']:
            dx, dy = p1['dir_2d']
            x2, y2 = p2['point']
            return clip_line(x2, y2, dx, dy, 0, 0, W, H)
        elif not p1['is_inf'] and p2['is_inf']:
            x1, y1 = p1['point']
            dx, dy = p2['dir_2d']
            return clip_line(x1, y1, dx, dy, 0, 0, W, H)
        return None


# Geometry helpers

def visible_angle_range(x0, y0, xmin, ymin, xmax, ymax):
    """Return (min_angle, max_angle) in radians covering the canvas from given point."""
    if (xmin < x0 < xmax and ymin < y0 < ymax):     # inside the canvas
        return 0, math.pi

    angles = []
    corners = [(xmin, ymin), (xmin, ymax), (xmax, ymax), (xmax, ymin)]
    for x, y in corners:
        ang = math.atan2(y - y0, x - x0)
        angles.append(ang if ang >= 0 else ang + 2 * math.pi)   # normalise to [0, 2π)
    angles.sort()
    angles.append(angles[0] + 2 * math.pi)      # handle wrap‑around gap

    max_gap = -1.0
    max_gap_start = 0
    for i in range(4):
        gap = angles[i + 1] - angles[i]
        if gap > max_gap:
            max_gap = gap
            max_gap_start = i

    # The visible interval is the complement of the largest gap
    min_ang = angles[max_gap_start + 1] - 2 * math.pi
    max_ang = angles[max_gap_start]
    return min_ang, max_ang

def clip_line(x0, y0, dx, dy, xmin, ymin, xmax, ymax):
    """Use Liang-Barsky parametric approach to clip a line through (x0, y0) with direction (dx, dy) to a rectangle"""
    p = [-dx, dx, -dy, dy]
    q = [x0 - xmin, xmax - x0, y0 - ymin, ymax - y0]
    t0, t1 = float("-inf"), float("inf")    # infinite line

    for i in range(4):
        if p[i] == 0:       # parallel to the boundary
            if q[i] < 0:    # outside the region
                return None
        else:
            t = q[i] / p[i]
            if p[i] < 0:    # Entering the half-space
                t0 = max(t0, t)
            else:           # Leaving the half-space
                t1 = min(t1, t)

    if t0 > t1:
        return None
    return (x0 + t0 * dx, y0 + t0 * dy,
            x0 + t1 * dx, y0 + t1 * dy)

# Rotation matrices
def Rx(angle):
    c, s = math.cos(angle), math.sin(angle)
    return [
        [1, 0,  0],
        [0, c, -s],
        [0, s,  c]]

def Ry(angle):
    c, s = math.cos(angle), math.sin(angle)
    return [
        [ c, 0, s],
        [ 0, 1, 0],
        [-s, 0, c]]

def Rz(angle):
    c, s = math.cos(angle), math.sin(angle)
    return [
        [c, -s, 0],
        [s,  c, 0],
        [0,  0, 1]]

# Helpers for matrix arithmetic
def mat_vec_mul(M, v):
    return [
        M[0][0]*v[0] + M[0][1]*v[1] + M[0][2]*v[2],
        M[1][0]*v[0] + M[1][1]*v[1] + M[1][2]*v[2],
        M[2][0]*v[0] + M[2][1]*v[1] + M[2][2]*v[2],
    ]

def mat_mat_mul(A, B):
    return [
        [A[0][0]*B[0][0] + A[0][1]*B[1][0] + A[0][2]*B[2][0],
         A[0][0]*B[0][1] + A[0][1]*B[1][1] + A[0][2]*B[2][1],
         A[0][0]*B[0][2] + A[0][1]*B[1][2] + A[0][2]*B[2][2]],
        [A[1][0]*B[0][0] + A[1][1]*B[1][0] + A[1][2]*B[2][0],
         A[1][0]*B[0][1] + A[1][1]*B[1][1] + A[1][2]*B[2][1],
         A[1][0]*B[0][2] + A[1][1]*B[1][2] + A[1][2]*B[2][2]],
        [A[2][0]*B[0][0] + A[2][1]*B[1][0] + A[2][2]*B[2][0],
         A[2][0]*B[0][1] + A[2][1]*B[1][1] + A[2][2]*B[2][1],
         A[2][0]*B[0][2] + A[2][1]*B[1][2] + A[2][2]*B[2][2]],
    ]
