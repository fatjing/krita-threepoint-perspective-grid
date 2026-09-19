# Three-Point Perspective Grid for Krita

A Krita plugin that draws a mathematically accurate 3-point perspective grid on your canvas.

You get a live preview while tweaking the sliders, and when you click OK the grid is committed to a vector layer so it stays crisp at any zoom level.

## Features

- Full camera control with adjustable FOV, yaw, pitch and roll
- Configurable auxiliary vanishing points for drawing sloped surfaces
- Customizable appearance settings for grid lines
- Smooth live preview while adjusting parameters

## Installation

1. Download the repo: [zip](https://github.com/fatjing/krita-threepoint-perspective-grid/archive/refs/heads/master.zip)
2. Follow the steps: [How to install a Python plugin](https://docs.krita.org/en/user_manual/python_scripting/install_custom_python_plugin.html#how-to-install-a-python-plugin)

## Usage

1. Open or create a document
2. Go to **Tools ▸ Scripts ▸ Three-Point Perspective Grid**
3. Adjust the sliders — the preview updates on the active document
4. Click **OK** to commit the grid to a vector layer, or **Cancel** to discard the preview

## Key Parameters Explained

| Parameter | Description |
|---|---|
| **FOV** | Diagonal field of view. Spans the canvas from corner to corner. Smaller values = telephoto (zoomed in, vanishing points farther away/off-canvas). Larger values = wide-angle (zoomed out, stronger distortion, vanishing points closer to the canvas center). |
| **LVP angle** | Camera yaw. The angle from the viewing direction to the left set of grid lines. |
| **RVP angle** | Automatically kept at `90° − LVP angle` - the two vanishing points are perpendicular in a 3-point setup. |
| **Pitch** | Camera pitch. Controls whether the viewer is looking up or down. |
| **Roll** | Camera roll. Rotates the whole grid around the view axis. |
| **Incline** | Angle of the auxiliary vanishing points relative to the ground plane. Used for inclined planes. |

## License

MIT License

Copyright (c) 2026 fatjing

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
