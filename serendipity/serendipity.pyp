"""Serendipity: random organic shapes in Redshift glass.

Registers an "Add Random Shape" command under Extensions that inserts a new
seed's shape and material into the active document.
"""

import os
import random
import sys
import time

import c4d

plugin_dir = os.path.dirname(os.path.abspath(__file__))
if plugin_dir not in sys.path:
    sys.path.insert(0, plugin_dir)

from serendipity_lib import geometry, material, redshift  # noqa: E402

# 1000001-1000010 are Maxon's IDs for testing. Register a unique ID at
# developers.maxon.net before distributing.
add_shape_id = 1000001


class AddShapeCommand(c4d.plugins.CommandData):
    def Execute(self, doc):
        seed = int(time.time() * 1000) % 1000000
        rng = random.Random(seed)
        shape = geometry.random_shape(rng)
        glass = material.random_glass(rng)

        doc.StartUndo()
        root = geometry.build(doc, shape, name="Seed %d" % seed)
        doc.AddUndo(c4d.UNDOTYPE_NEWOBJ, root)
        mat = material.build(doc, glass, name="Seed %d Glass" % seed)
        doc.AddUndo(c4d.UNDOTYPE_NEWOBJ, mat)
        redshift.assign(root, mat)
        doc.SetActiveObject(root, c4d.SELECTION_NEW)
        doc.EndUndo()

        print("[serendipity] seed %d: %s | %s"
              % (seed, geometry.describe(shape), material.describe(glass)))
        c4d.EventAdd()
        return True


if __name__ == "__main__":
    c4d.plugins.RegisterCommandPlugin(
        id=add_shape_id,
        str="Serendipity: Add Random Shape",
        info=0,
        icon=None,
        help="Insert a random organic shape in random Redshift glass",
        dat=AddShapeCommand(),
    )
