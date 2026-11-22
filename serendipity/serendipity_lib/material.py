"""Random Redshift glass.

A recipe is a plain `{port name: value}` dict for the `standardmaterial` node,
so it can be logged, saved as JSON, and rebuilt without the seed.
"""

import colorsys

from . import redshift


def random_color(rng, hue, saturation=(0.3, 0.9), value=(0.6, 1.0)):
    """An RGB tuple around `hue`, picked in HSV so it never turns muddy."""
    return colorsys.hsv_to_rgb(
        hue % 1.0, rng.uniform(*saturation), rng.uniform(*value)
    )


def random_glass(rng):
    """Return a recipe for a randomized glass material."""
    hue = rng.random()
    recipe = {
        # Clear glass: no diffuse, full refraction. Redshift has no separate
        # refraction IOR here, `refl_ior` drives both.
        "base_color_weight": 0.0,
        "refr_weight": 1.0,
        "refl_weight": 1.0,
        "refl_roughness": 0.0,
        "refr_thin_walled": False,
        "shadow_opacity": 0.0,
        # The defaults cut off before the far side of a solid object.
        "refr_depth": 16,
        "refl_depth": 8,
        "refl_ior": rng.uniform(1.3, 2.4),
        "refr_color": random_color(rng, hue),
        # `ss_depth` is the distance at which `refr_color` is reached, so a
        # short depth darkens thick parts more than thin ones. Zero tints
        # evenly. Objects are fit to about 200 units.
        "ss_depth": rng.choice([0.0, rng.uniform(20.0, 300.0)]),
        "refr_roughness": 0.0,
        # `refr_abbe` of 0 turns dispersion off; lower non-zero values split
        # colors more strongly.
        "refr_abbe": 0.0,
        "thinfilm_thickness": 0.0,
        "thinfilm_ior": 1.5,
        "coat_weight": 0.0,
    }
    if rng.random() < 0.6:
        recipe["refr_abbe"] = rng.uniform(6.0, 40.0)
    if rng.random() < 0.5:
        # Thin film in nanometers, the soap bubble iridescence.
        recipe["thinfilm_thickness"] = rng.uniform(150.0, 900.0)
        recipe["thinfilm_ior"] = rng.uniform(1.2, 2.0)
    if rng.random() < 0.25:
        recipe["refr_roughness"] = rng.uniform(0.05, 0.35)
    if rng.random() < 0.25:
        recipe["coat_weight"] = 1.0
        recipe["coat_color"] = random_color(
            rng, hue + rng.uniform(0.2, 0.5), saturation=(0.2, 0.7)
        )
    return recipe


def build(doc, recipe, name="Serendipity Glass"):
    """Create a Redshift material in `doc` from a recipe and return it."""
    mat, graph, shader = redshift.material(doc, name)
    values = {}
    for key, value in recipe.items():
        if isinstance(value, (tuple, list)):
            value = redshift.color(value)
        values[key] = value
    redshift.set_shader_values(graph, shader, values)
    return mat


def describe(recipe):
    """A short one-line summary, for logs and object names."""
    parts = ["ior %.2f" % recipe["refl_ior"]]
    if recipe["refr_abbe"]:
        parts.append("abbe %.0f" % recipe["refr_abbe"])
    if recipe["thinfilm_thickness"]:
        parts.append("film %.0fnm" % recipe["thinfilm_thickness"])
    if recipe["refr_roughness"]:
        parts.append("rough %.2f" % recipe["refr_roughness"])
    if recipe["coat_weight"]:
        parts.append("coat")
    if recipe["ss_depth"]:
        parts.append("depth %.0f" % recipe["ss_depth"])
    return ", ".join(parts)
