"""A grid of consecutive seeds, to survey what the generator makes.

    rk-c4d-render scenes/contact_sheet.py --preview
    SERENDIPITY_SEED=1200 rk-c4d-render scenes/contact_sheet.py

Seeds run left to right, top to bottom, from `SERENDIPITY_SEED` (a new one
each run when it's unset). The log and the `.json` beside the render list each
seed's recipe.
"""

import c4d

import stage

columns = 4
rows = 3
spacing = 260.0


def build(doc, ctx):
    first = stage.base_seed(ctx)
    recipes = []
    for index in range(columns * rows):
        column = index % columns
        row = index // columns
        position = c4d.Vector(
            (column - (columns - 1) / 2.0) * spacing,
            ((rows - 1) / 2.0 - row) * spacing,
            0.0,
        )
        recipes.append(stage.build_specimen(doc, first + index, position))
    stage.write_recipes(ctx, recipes)
    stage.build_sky(doc, ctx)
    cam, distance = stage.build_camera(
        doc, columns * spacing / 2.0, float(ctx.width) / ctx.height
    )
    stage.build_lights(doc, distance)
    return cam
