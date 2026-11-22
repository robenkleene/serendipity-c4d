"""A shared studio for the exploration scenes: environment, lights and camera.

Glass mostly shows what surrounds it, so the studio is an emissive sphere of
soft light strips rather than an empty background. It stays the same between
seeds so results are compared on the shape and material alone.
"""

import json
import os
import random
import sys

import c4d
from c4d import utils

# `scenes/` sits beside the plugin folder, whose `serendipity_lib` the scenes
# share with the plugin.
plugin_dir = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "serendipity"
)
if plugin_dir not in sys.path:
    sys.path.insert(0, plugin_dir)

from serendipity_lib import geometry, material, redshift  # noqa: E402

seed_var = "SERENDIPITY_SEED"
sky_radius = 20000.0
studio_size = (1024, 512)

# sRGB, decoded to linear by Redshift on load: a dark blue grey ground with
# bright strips of light, white, warm and cool.
studio_ground = (40, 44, 58)
studio_strips = [
    # (orientation, center as a fraction of the image, width in pixels, color)
    ("vertical", 0.18, 40, (255, 255, 255)),
    ("vertical", 0.42, 18, (255, 196, 140)),
    ("vertical", 0.71, 60, (150, 200, 255)),
    ("horizontal", 0.30, 14, (255, 255, 255)),
    ("horizontal", 0.62, 30, (255, 140, 200)),
]


def base_seed(ctx):
    """`SERENDIPITY_SEED` from the environment, else a new one every run."""
    value = os.environ.get(seed_var)
    if value:
        return int(value)
    return ctx.timestamp % 100000


def studio_texture_path(ctx):
    return os.path.join(os.path.dirname(ctx.scene_path), "assets", "studio.png")


def write_studio_texture(path):
    """Write the studio image to `path`: strips on a dark ground."""
    directory = os.path.dirname(path)
    if not os.path.isdir(directory):
        os.makedirs(directory)
    width, height = studio_size
    bmp = c4d.bitmaps.BaseBitmap()
    if bmp.Init(width, height, 24) != c4d.IMAGERESULT_OK:
        raise RuntimeError("could not allocate the studio bitmap")
    for y in range(height):
        for x in range(width):
            r, g, b = studio_ground
            for orientation, center, size, color in studio_strips:
                position = x if orientation == "vertical" else y
                extent = width if orientation == "vertical" else height
                distance = abs(position - center * extent)
                if distance < size:
                    # A soft edge, so refractions show gradients, not aliasing.
                    t = 1.0 - distance / size
                    t = t * t * (3.0 - 2.0 * t)
                    r = r + (color[0] - r) * t
                    g = g + (color[1] - g) * t
                    b = b + (color[2] - b) * t
            bmp.SetPixel(x, y, int(r), int(g), int(b))
    if bmp.Save(path, c4d.FILTER_PNG) != c4d.IMAGERESULT_OK:
        raise RuntimeError("could not write %s" % path)
    return path


def build_sky(doc, ctx):
    """Enclose the scene in the emissive studio sphere.

    Refraction inverts what's behind and above an object, so without an
    enclosing sphere the empty background renders as black bands in the glass.
    """
    path = studio_texture_path(ctx)
    if not os.path.isfile(path):
        write_studio_texture(path)
    mat, graph, shader = redshift.material(doc, "Studio")
    redshift.set_shader_values(
        graph,
        shader,
        {"base_color_weight": 0.0, "refl_weight": 0.0, "emission_weight": 2.0},
    )
    redshift.connect_texture(
        graph, redshift.add_texture(graph, path), shader, "emission_color"
    )
    sky = c4d.BaseObject(c4d.Osphere)
    sky.SetName("Studio")
    sky[c4d.PRIM_SPHERE_RAD] = sky_radius
    sky[c4d.PRIM_SPHERE_SUB] = 64
    doc.InsertObject(sky)
    geometry.smooth(sky)
    redshift.assign(sky, mat, c4d.TEXTURETAG_PROJECTION_SPHERICAL)
    return sky


def build_area_light(doc, name, pos, size, intensity):
    light = c4d.BaseObject(c4d.Orslight)
    light.SetName(name)
    light[c4d.REDSHIFT_LIGHT_TYPE] = c4d.REDSHIFT_LIGHT_TYPE_PHYSICAL_AREA
    light[c4d.REDSHIFT_LIGHT_PHYSICAL_AREA_SIZEX] = size
    light[c4d.REDSHIFT_LIGHT_PHYSICAL_AREA_SIZEY] = size
    light[c4d.REDSHIFT_LIGHT_PHYSICAL_INTENSITY] = intensity
    light[c4d.REDSHIFT_LIGHT_PHYSICAL_AREA_VISIBLE_IN_RENDER] = False
    light.SetAbsPos(pos)
    light.SetAbsRot(utils.VectorToHPB(-pos))
    doc.InsertObject(light)
    return light


def build_lights(doc, distance):
    build_area_light(
        doc, "Key", c4d.Vector(-0.6, 0.8, -0.5) * distance, distance * 0.5, 4.0
    )
    build_area_light(
        doc, "Rim", c4d.Vector(0.7, 0.3, 0.9) * distance, distance * 0.5, 3.0
    )


def build_camera(doc, half_width, aspect, focal=100.0):
    """A camera on -Z looking at the origin, framing `half_width` either side."""
    cam = c4d.BaseObject(c4d.Ocamera)
    cam.SetName("Camera")
    cam[c4d.CAMERA_FOCUS] = focal
    # `CAMERA_FOCUS` is in mm against a 36mm wide aperture.
    distance = half_width * focal / 18.0
    cam.SetAbsPos(c4d.Vector(0.0, 0.0, -distance))
    doc.InsertObject(cam)
    return cam, distance


def build_specimen(doc, seed, position):
    """Build one seed's shape and glass at `position`, returning its recipe."""
    rng = random.Random(seed)
    shape = geometry.random_shape(rng)
    glass = material.random_glass(rng)
    root = geometry.build(doc, shape, name="Seed %d" % seed)
    root.SetAbsPos(position)
    mat = material.build(doc, glass, name="Seed %d Glass" % seed)
    # The tag goes on the root so every child, including generated geometry,
    # inherits the material.
    redshift.assign(root, mat)
    print("[serendipity] seed %d: %s | %s"
          % (seed, geometry.describe(shape), material.describe(glass)))
    sys.stdout.flush()
    return {"seed": seed, "shape": shape, "glass": glass}


def write_recipes(ctx, recipes):
    """Save every recipe beside the render, to rebuild or study later."""
    path = ctx.output_path("json")
    with open(path, "w") as handle:
        json.dump(recipes, handle, indent=2)
    print("[serendipity] wrote %s" % path)
    sys.stdout.flush()

