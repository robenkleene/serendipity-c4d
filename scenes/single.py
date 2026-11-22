"""One seed, large.

    SERENDIPITY_SEED=1203 rk-c4d-render scenes/single.py
"""

import c4d

import stage


def build(doc, ctx):
    recipes = [stage.build_specimen(doc, stage.base_seed(ctx), c4d.Vector(0.0))]
    stage.write_recipes(ctx, recipes)
    stage.build_sky(doc, ctx)
    cam, distance = stage.build_camera(doc, 160.0, float(ctx.width) / ctx.height)
    stage.build_lights(doc, distance)
    return cam
