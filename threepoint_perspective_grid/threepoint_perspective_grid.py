from PyQt5.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QFormLayout,
    QGridLayout,
    QCheckBox,
    QColorDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QLabel,
    QPushButton,
    QSlider,
    QSpinBox,
)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QColor
from krita import Krita, Extension
import math, json

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

        # VP1 angle (determines the orientation of the ground‑plane grid)
        self.vp1_angle_spin = QDoubleSpinBox()
        self.vp1_angle_spin.setRange(0.1, 89.9)
        self.vp1_angle_spin.setValue(self.params['vp1_angle'])
        self.vp1_angle_spin.setSingleStep(5)
        self.vp1_angle_spin.setSuffix("°")
        self.vp1_angle_spin.setToolTip("Angle from the viewing direction to the left set of grid lines.")
        self.vp1_angle_spin.valueChanged.connect(lambda val: self.on_vp1_angle_changed(val))
        form.addRow("LVP angle", self.vp1_angle_spin)

        self.vp1_angle_slider = QSlider(Qt.Horizontal)
        self.vp1_angle_slider.setRange(1, 899)
        self.vp1_angle_slider.setValue(round(self.params['vp1_angle'] * 10))
        self.vp1_angle_slider.valueChanged.connect(lambda val: self.on_vp1_angle_changed(val / 10.0))
        form.addRow("", self.vp1_angle_slider)

        self.vp2_label = QLabel(f"{(90.0 - self.params['vp1_angle']):.2f}°")
        form.addRow("RVP angle", self.vp2_label)

        # Camera Pitch
        self.pitch_spin = QDoubleSpinBox()
        self.pitch_spin.setRange(-89.9, 89.9)
        self.pitch_spin.setValue(self.params['pitch'])
        self.pitch_spin.setSingleStep(5)
        self.pitch_spin.setSuffix("°")
        self.pitch_spin.setToolTip("Camera pitch. Positive = look up (horizon moves down).")
        self.pitch_spin.valueChanged.connect(self.request_preview)
        form.addRow("Pitch", self.pitch_spin)

        # Camera Roll
        self.roll_spin = QDoubleSpinBox()
        self.roll_spin.setRange(-180.0, 180.0)
        self.roll_spin.setValue(self.params['roll'])
        self.roll_spin.setSingleStep(5)
        self.roll_spin.setSuffix("°")
        self.roll_spin.setToolTip("Camera roll. Positive = counter‑clockwise rotation of the image.")
        self.roll_spin.valueChanged.connect(self.request_preview)
        form.addRow("Roll", self.roll_spin)

        # Field of view
        self.fov_spin = QDoubleSpinBox()
        self.fov_spin.setRange(1, 179)
        self.fov_spin.setValue(self.params['fov'])
        self.fov_spin.setSingleStep(5)
        self.fov_spin.setSuffix("°")
        self.fov_spin.setToolTip("Diagonal field of view. Spans the canvas from corner to corner.")
        self.fov_spin.valueChanged.connect(self.request_preview)
        form.addRow("FOV", self.fov_spin)

        # Vertical plane diagonals
        diag_layout = QHBoxLayout()

        self.show_ldvp_check = QCheckBox("Left wall")
        self.show_ldvp_check.setChecked(self.params["show_ldvp"])
        self.show_ldvp_check.stateChanged.connect(self.request_preview)
        diag_layout.addWidget(self.show_ldvp_check)

        self.show_rdvp_check = QCheckBox("Right wall")
        self.show_rdvp_check.setChecked(self.params["show_rdvp"])
        self.show_rdvp_check.stateChanged.connect(self.request_preview)
        diag_layout.addWidget(self.show_rdvp_check)

        form.addRow("Diagonal VP", diag_layout)

        # Grid density
        self.grid_density = QSpinBox()
        self.grid_density.setRange(2, 180)
        self.grid_density.setValue(self.params['grid_density'])
        self.grid_density.valueChanged.connect(self.request_preview)
        form.addRow("Grid density", self.grid_density)

        # Line width
        self.line_width_spin = QSpinBox()
        self.line_width_spin.setRange(1, 20)
        self.line_width_spin.setValue(self.params['line_width'])
        self.line_width_spin.setToolTip("Stroke width for all grid lines (pixels).")
        self.line_width_spin.valueChanged.connect(self.request_preview)
        form.addRow("Line width", self.line_width_spin)

        # Line opacity
        self.line_opacity_spin = QDoubleSpinBox()
        self.line_opacity_spin.setRange(0.0, 1.0)
        self.line_opacity_spin.setValue(self.params['line_opacity'])
        self.line_opacity_spin.setSingleStep(0.1)
        self.line_opacity_spin.setDecimals(2)
        self.line_opacity_spin.setToolTip("Opacity for all grid lines (0 = fully transparent, 1 = fully opaque).")
        self.line_opacity_spin.valueChanged.connect(self.request_preview)
        form.addRow("Line opacity", self.line_opacity_spin)

        # Color pickers
        self.colors = {target: color for target, color in self.params['colors'].items()}
        color_grid = QGridLayout()
        for i, (target, color) in enumerate(self.colors.items()):
            btn = QPushButton(target)
            btn.setObjectName(target)  # for findChild in reset
            fg = self.contrasting_text_color(color)
            btn.setStyleSheet(f"background-color: {color}; color: {fg}")
            btn.clicked.connect(lambda _, t=target, b=btn: self.pick_color(t, b))
            color_grid.addWidget(btn, i // 2, i % 2)
        form.addRow("Colors", color_grid)

        layout.addLayout(form)

        # Reset + OK/Cancel buttons
        reset_btn = QPushButton("Reset")
        reset_btn.clicked.connect(self.reset_to_defaults)
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.handle_accept)
        button_box.rejected.connect(self.reject)
        buttons_layout = QHBoxLayout()
        buttons_layout.addWidget(reset_btn)
        buttons_layout.addStretch()
        buttons_layout.addWidget(button_box)
        layout.addLayout(buttons_layout)

        self.setLayout(layout)
        self.preview_timer.start(0)

    def pick_color(self, target, button):
        color = QColorDialog.getColor(QColor(self.colors[target]), self, f"Pick color for {target}")
        if color.isValid():
            self.colors[target] = color.name()
            fg = self.contrasting_text_color(color.name())
            button.setStyleSheet(f"background-color: {color.name()}; color: {fg}")
            self.request_preview()

    def contrasting_text_color(self, bg):
        bg = QColor(bg)
        r, g, b = bg.redF(), bg.greenF(), bg.blueF()
        def linearize(c):
            return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
        luminance = 0.2126 * linearize(r) + 0.7152 * linearize(g) + 0.0722 * linearize(b)
        return "#333333" if luminance > 0.179 else "#f4f4f4"

    def on_vp1_angle_changed(self, angle):
        self.vp1_angle_spin.blockSignals(True)
        self.vp1_angle_spin.setValue(angle)
        self.vp1_angle_spin.blockSignals(False)

        self.vp1_angle_slider.blockSignals(True)
        self.vp1_angle_slider.setValue(round(angle * 10))
        self.vp1_angle_slider.blockSignals(False)

        self.vp2_label.setText(f"{(90.0 - angle):.2f}°")
        self.request_preview()

    def request_preview(self):
        self.preview_timer.start(300)

    def emit_preview(self):
        if self.isVisible() and self.preview_callback:
            self.preview_callback(self.get_current_params())

    def get_current_params(self):
        return {
            "vp1_angle": self.vp1_angle_spin.value(),
            "pitch": self.pitch_spin.value(),
            "roll": self.roll_spin.value(),
            "fov": self.fov_spin.value(),
            "show_ldvp": self.show_ldvp_check.isChecked(),
            "show_rdvp": self.show_rdvp_check.isChecked(),
            "grid_density": self.grid_density.value(),
            "line_width": self.line_width_spin.value(),
            "line_opacity": self.line_opacity_spin.value(),
            "colors": {k: v for k, v in self.colors.items()}
        }

    def handle_accept(self):
        self.params = self.get_current_params()
        self.accept()

    def reset_to_defaults(self):
        d = self.defaults
        self.vp1_angle_spin.setValue(d["vp1_angle"])
        self.pitch_spin.setValue(d["pitch"])
        self.roll_spin.setValue(d["roll"])
        self.fov_spin.setValue(d["fov"])
        self.show_ldvp_check.setChecked(d["show_ldvp"])
        self.show_rdvp_check.setChecked(d["show_rdvp"])
        self.grid_density.setValue(d["grid_density"])
        self.line_width_spin.setValue(d["line_width"])
        self.line_opacity_spin.setValue(d["line_opacity"])
        for target, color in d["colors"].items():
            self.colors[target] = color
            btn = self.findChild(QPushButton, target)
            if btn:
                fg = self.contrasting_text_color(color)
                btn.setStyleSheet(f"background-color: {color}; color: {fg}")


class ThreePointPerspectiveGridExtension(Extension):
    DEFAULT_PARAMS = {
        "vp1_angle": 30,
        "pitch": 0,
        "roll": 0,
        "fov": 78,
        "show_ldvp": False,
        "show_rdvp": False,
        "grid_density": 12,
        "line_width": 1,
        "line_opacity": 1.0,
        "colors": {
            "VP1":  "#acb8ff",
            "VP2":  "#acb8ff",
            "VP3":  "#e99df5",
            "DVP":  "#f3dc85",
            "LDVP": "#c0eac7",
            "RDVP": "#afeaea",
            "HL":   "#bdc4cb",
        }
    }

    def __init__(self, parent):
        super().__init__(parent)
        self.params = self.load_settings()
        self.current_dlg = None
        self.doc = None

    def setup(self):
        pass

    def createActions(self, window):
        action = window.createAction("threepoint_perspective_grid", "Three-Point Perspective Grid", "tools/scripts")
        action.triggered.connect(self.show_dialog)

    def load_settings(self):
        params_json = Krita.instance().readSetting("ThreePointPerspectiveGrid", "params", "")
        if params_json:
            return json.loads(params_json)
        return {k: (v.copy() if isinstance(v, dict) else v) for k, v in self.DEFAULT_PARAMS.items()}

    def save_settings(self, params):
        Krita.instance().writeSetting("ThreePointPerspectiveGrid", "params", json.dumps(params))

    def show_dialog(self):
        doc = Krita.instance().activeDocument()
        if not doc:
            return

        if self.current_dlg and self.current_dlg.isVisible():
            self.current_dlg.raise_()
            return

        self.doc = doc
        self.remove_grid_preview(doc)

        main_window = Krita.instance().activeWindow().qwindow()
        self.current_dlg = ThreePointPerspectiveGridDialog(self.params, self.DEFAULT_PARAMS, self.update_grid_preview, main_window)
        self.current_dlg.accepted.connect(self.on_dialog_accepted)
        self.current_dlg.rejected.connect(self.on_dialog_rejected)
        self.current_dlg.finished.connect(self.on_dialog_finished)
        self.current_dlg.show()

    def on_dialog_accepted(self):
        self.current_dlg = None
        self.save_settings(self.params)
        layer = self.get_vector_layer(self.doc, "Perspective Grid (Preview)")
        if layer is not None:
            layer.setName("Perspective Grid")

    def on_dialog_rejected(self):
        self.current_dlg = None
        self.remove_grid_preview(self.doc)

    def on_dialog_finished(self):
        self.current_dlg = None

    def remove_grid_preview(self, doc):
        layer = self.get_vector_layer(doc, "Perspective Grid (Preview)")
        if layer is not None:
            layer.remove()

    def update_grid_preview(self, params):
        self.render_grid_to_layer(self.doc, params, "Perspective Grid (Preview)")

    def get_vector_layer(self, doc, layer_name):
        for child in doc.rootNode().childNodes():
            if child.name() == layer_name and child.type() == "vectorlayer":
                return child
        return None

    def render_grid_to_layer(self, doc, params, layer_name):
        svg = self.build_svg(doc, params)
        layer = self.get_vector_layer(doc, layer_name)
        if layer is not None:
            layer.remove()
        layer = doc.createVectorLayer(layer_name)
        previous_node = doc.activeNode()
        doc.rootNode().addChildNode(layer, None)
        if previous_node:
            doc.setActiveNode(previous_node)
        layer.addShapesFromSvg(svg)

    def build_svg(self, doc, params):
        lines = self.compute_grid_lines(params, doc.width(), doc.height())
        colors = params["colors"]
        width = params["line_width"]
        opacity = params["line_opacity"]

        svg_parts = ['<svg xmlns="http://www.w3.org/2000/svg">']

        # Vanishing lines
        for vp_name, segments in lines["vp_rays"].items():
            for (x1, y1, x2, y2) in segments:
                svg_parts.append(
                    f'<line x1="{x1:.2f}" y1="{y1:.2f}" x2="{x2:.2f}" y2="{y2:.2f}" '
                    f'stroke="{colors[vp_name]}" stroke-width="{width}" opacity="{opacity}"/>'
                )

        # Horizon line
        if lines["horizon"]:
            x1, y1, x2, y2 = lines["horizon"]
            svg_parts.append(
                f'<line x1="{x1:.2f}" y1="{y1:.2f}" x2="{x2:.2f}" y2="{y2:.2f}" '
                f'stroke="{colors["HL"]}" stroke-width="{width}" opacity="{opacity}"/>'
            )

        # Vertical center line
        if lines["vertical_center"]:
            x1, y1, x2, y2 = lines["vertical_center"]
            svg_parts.append(
                f'<line x1="{x1:.2f}" y1="{y1:.2f}" x2="{x2:.2f}" y2="{y2:.2f}" '
                f'stroke="{colors["HL"]}" stroke-width="{width}" opacity="{opacity}"/>'
            )

        svg_parts.append('</svg>')
        return "".join(svg_parts)

    def compute_grid_lines(self, params, W, H):
        """Generate grid using a 3D camera matrix."""
        vp1_angle = params["vp1_angle"]
        pitch = params["pitch"]
        roll = params["roll"]
        fov = params["fov"]
        density = params["grid_density"]
        show_ldvp = params["show_ldvp"]
        show_rdvp = params["show_rdvp"]

        cx = W / 2.0
        cy = H / 2.0

        # Focal length from diagonal field of view
        f = (math.hypot(W, H) / 2.0) / math.tan(math.radians(fov / 2.0))

        # Intrinsic matrix K
        K = [[f, 0, cx], [0, f, cy], [0, 0, 1]]

        # Camera rotation: pitch around X, roll around Z (Y-up, Z-forward)
        def Rx(angle):
            c = math.cos(angle); s = math.sin(angle)
            return [[1, 0, 0], [0, c, -s], [0, s, c]]
        def Rz(angle):
            c = math.cos(angle); s = math.sin(angle)
            return [[c, -s, 0], [s, c, 0], [0, 0, 1]]
        R = mat_mat_mul(Rz(math.radians(-roll)), Rx(-math.radians(pitch)))

        # Homogeneous projection of world direction D into image plane
        def project_direction(D):
            v_cam = mat_vec_mul(R, list(D))
            vh = mat_vec_mul(K, v_cam)
            if abs(vh[2]) < 1e-12:
                return (float('inf'), float('inf'))
            return (vh[0] / vh[2], vh[1] / vh[2])

        # Grid direction vectors (world space, Y-up, Z = view direction)
        a = math.radians(vp1_angle)
        D1 = (-math.sin(a), 0, math.cos(a))              # left grid lines
        D2 = ( math.cos(a), 0, math.sin(a))              # right grid lines (orthogonal)
        D3 = (0, 1, 0)                                   # vertical (world up)
        Ddvp = (D1[0] + D2[0], 0, D1[2] + D2[2])         # ground-plane diagonal

        vertical_vec = -D3[1] if pitch > 0 else D3[1]    # whether wall diagonals point upward or downward
        Dldvp = (D1[0], D1[1] + vertical_vec, D1[2])     # left-wall diagonal
        Drdvp = (D2[0], D2[1] + vertical_vec, D2[2])     # right-wall diagonal

        vp_positions = {
            "VP1": project_direction(D1),
            "VP2": project_direction(D2),
            "VP3": project_direction(D3),
            "DVP": project_direction(Ddvp),
        }
        if show_ldvp:
            vp_positions["LDVP"] = project_direction(Dldvp)
        if show_rdvp:
            vp_positions["RDVP"] = project_direction(Drdvp)

        # Gather rays for each VP
        vp_rays = {}
        for vp_name, vp in vp_positions.items():
            if vp[0] == float('inf') or vp[1] == float('inf'):
                continue
            min_ang, max_ang = visible_angle_range(vp[0], vp[1], 0, 0, W, H)
            span = max_ang - min_ang
            num_lines = density * 2 if span >= math.pi - 1e-12 else density
            step = span / num_lines
            segments = []
            for i in range(num_lines):
                ang = min_ang + i * step
                dx = math.cos(ang)
                dy = math.sin(ang)
                clipped = clip_line(vp[0], vp[1], dx, dy, 0, 0, W, H)
                if clipped:
                    segments.append(clipped)
            vp_rays[vp_name] = segments

        # Horizon line
        vp1 = vp_positions["VP1"]
        vp2 = vp_positions["VP2"]
        horizon = clip_line(vp1[0], vp1[1], vp2[0] - vp1[0], vp2[1] - vp1[1], 0, 0, W, H)

        # Vertical center line
        vp3 = vp_positions["VP3"]
        if vp3[0] != float('inf') and vp3[1] != float('inf'):
            vertical_center = clip_line(cx, cy, vp3[0] - cx, vp3[1] - cy, 0, 0, W, H)
        else:
            v_up = mat_vec_mul(R, [0.0, 1.0, 0.0])
            vertical_center = clip_line(cx, cy, v_up[0], v_up[1], 0, 0, W, H)

        return {
            "vp_rays": vp_rays,
            "horizon": horizon,
            "vertical_center": vertical_center,
        }


# Geometry helpers

def visible_angle_range(x0, y0, xmin, ymin, xmax, ymax):
    """Return (min_angle, max_angle) in radians covering the canvas from given point."""
    EPS = 1e-12
    # If the point is inside the canvas, all directions are visible
    if (xmin - EPS <= x0 <= xmax + EPS and
        ymin - EPS <= y0 <= ymax + EPS):
        return 0, 2 * math.pi

    angles = []
    corners = [(xmin, ymin), (xmin, ymax), (xmax, ymax), (xmax, ymin)]
    for x, y in corners:
        ang = math.atan2(y - y0, x - x0)
        angles.append(ang if ang >= 0 else ang + 2 * math.pi)    # normalise to [0, 2π)
    angles.sort()
    # Duplicate the first angle + 2π to handle the wrap‑around gap
    angles.append(angles[0] + 2 * math.pi)

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
    """Clip a line through (x0, y0) with direction (dx, dy) to the canvas."""
    length = math.hypot(dx, dy)
    if length < 1e-12:
        return None
    ux = dx / length
    uy = dy / length

    # Compute the t values where the line reaches each of the four edges
    t_values = []
    if abs(ux) > 1e-12:
        t_values.append((xmin - x0) / ux)      # left edge
        t_values.append((xmax - x0) / ux)      # right edge
    if abs(uy) > 1e-12:
        t_values.append((ymin - y0) / uy)      # top edge
        t_values.append((ymax - y0) / uy)      # bottom edge

    if not t_values:
        return None

    max_abs_t = max(abs(t) for t in t_values)
    half_length = max_abs_t * 1.1      # Extend by a small margin to avoid numerical misses at corners
    end1 = (x0 - half_length * ux, y0 - half_length * uy)
    end2 = (x0 + half_length * ux, y0 + half_length * uy)
    return liang_barsky_clip(end1[0], end1[1], end2[0], end2[1], xmin, ymin, xmax, ymax)

def liang_barsky_clip(x1, y1, x2, y2, xmin, ymin, xmax, ymax):
    """Clip line segment to rectangle."""
    dx = x2 - x1
    dy = y2 - y1
    p = [-dx, dx, -dy, dy]
    q = [x1 - xmin, xmax - x1, y1 - ymin, ymax - y1]
    u1, u2 = 0.0, 1.0

    for i in range(4):
        if p[i] == 0:
            if q[i] < 0:
                return None
        else:
            t = q[i] / p[i]
            if p[i] < 0:
                u1 = max(u1, t)
            else:
                u2 = min(u2, t)

    if u1 > u2:
        return None
    return (x1 + u1 * dx, y1 + u1 * dy,
            x1 + u2 * dx, y1 + u2 * dy)

# Helpers for 3×3 matrix arithmetic
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
