"""Random organic shapes: a base object bent by a random stack of deformers.

A recipe is plain data (names and numbers, no `c4d` objects), so it can be
logged, saved as JSON, and rebuilt without the seed. Parameter values are
stored under their `c4d` symbol names, e.g. `DEFORMOBJECT_ANGLE`.

The ranges are curated by hand. Cinema 4D's own descriptions report limits like
+/-1e18 for most deformer parameters, which are no use for picking values.
"""

import math

import c4d
from c4d import utils

# Every shape is scaled to fit this radius after deforming, so results are
# comparable and framing stays the same whatever the deformers did.
fit_radius = 100.0

# Deformers act within a box this size, which matches the undeformed bases.
deformer_size = 200.0


def rad(degrees):
    return math.radians(degrees)


def signed(rng, low, high):
    """A value in `[low, high]` with a random sign."""
    return rng.uniform(low, high) * rng.choice((-1.0, 1.0))


def random_base(rng):
    kind = rng.choice(("sphere", "torus", "capsule", "cube", "metaball"))
    if kind == "sphere":
        return {"kind": kind, "params": {"PRIM_SPHERE_RAD": 100.0}}
    if kind == "torus":
        outer = rng.uniform(70.0, 90.0)
        return {
            "kind": kind,
            "params": {
                "PRIM_TORUS_OUTERRAD": outer,
                "PRIM_TORUS_INNERRAD": outer * rng.uniform(0.2, 0.5),
            },
        }
    if kind == "capsule":
        radius = rng.uniform(30.0, 60.0)
        return {
            "kind": kind,
            "params": {
                "PRIM_CAPSULE_RADIUS": radius,
                "PRIM_CAPSULE_HEIGHT": rng.uniform(radius * 2.5, 200.0),
            },
        }
    if kind == "cube":
        return {
            "kind": kind,
            "params": {
                "PRIM_CUBE_LEN": [rng.uniform(100.0, 200.0) for _ in range(3)],
                "PRIM_CUBE_FRAD": rng.uniform(5.0, 40.0),
            },
        }
    # A metaball of a few spheres clumped around the origin.
    balls = []
    for _ in range(rng.randint(3, 7)):
        balls.append(
            {
                "position": [rng.uniform(-60.0, 60.0) for _ in range(3)],
                "radius": rng.uniform(30.0, 70.0),
            }
        )
    return {"kind": kind, "params": {"METABALLOBJECT_THRESHOLD": 0.5}, "balls": balls}


def random_deformer(rng, kind):
    if kind == "twist":
        params = {"DEFORMOBJECT_ANGLE": rad(signed(rng, 30.0, 270.0))}
    elif kind == "bend":
        params = {
            "DEFORMOBJECT_STRENGTH": rad(signed(rng, 30.0, 180.0)),
            "DEFORMOBJECT_ANGLE": rad(rng.uniform(0.0, 360.0)),
        }
    elif kind == "bulge":
        params = {
            "DEFORMOBJECT_STRENGTH": rng.uniform(-0.6, 1.2),
            "DEFORMOBJECT_CURVATURE": rng.uniform(0.5, 1.5),
        }
    elif kind == "taper":
        params = {
            "DEFORMOBJECT_STRENGTH": rng.uniform(-0.9, 0.9),
            "DEFORMOBJECT_CURVATURE": rng.uniform(0.0, 1.0),
        }
    elif kind == "shear":
        params = {
            "DEFORMOBJECT_STRENGTH": signed(rng, 0.2, 0.6),
            "DEFORMOBJECT_CURVATURE": rng.uniform(0.0, 1.0),
        }
    elif kind == "spherify":
        params = {"SPHERIFYOBJECT_STRENGTH": rng.uniform(0.2, 0.8)}
    elif kind == "displacer":
        params = {"MGDISPLACER_DISPLACEMENT_HEIGHT": rng.uniform(4.0, 16.0)}
    else:
        raise ValueError("unknown deformer: %s" % kind)
    return {
        "kind": kind,
        "params": params,
        # Rotating each deformer sends twists and bends along different axes,
        # which matters as much as the strengths do.
        "rotation": [rng.uniform(0.0, 360.0) for _ in range(3)],
        # `SLA_NOISE_GLOBAL_SCALE` is relative to the UVs, so 1.0 is far too
        # fine on a 200 unit shape and reads as crumpled rock.
        "noise_scale": rng.uniform(4.0, 20.0) if kind == "displacer" else None,
        "noise_seed": rng.randint(0, 9999) if kind == "displacer" else None,
    }


deformer_kinds = ("twist", "bend", "bulge", "taper", "shear", "spherify")

# Chance of one displacer at the end of the stack. Displacement dominates
# everything else, so it never appears more than once.
displacer_chance = 0.3


def random_shape(rng):
    """Return a recipe for a randomized shape."""
    count = rng.randint(2, 5)
    kinds = [rng.choice(deformer_kinds) for _ in range(count)]
    if rng.random() < displacer_chance:
        kinds.append("displacer")
    return {
        "base": random_base(rng),
        # Order matters: Cinema 4D applies a parent's deformer children top to
        # bottom, so the same deformers in a different order give a new shape.
        "deformers": [random_deformer(rng, kind) for kind in kinds],
    }


def set_params(obj, params):
    for name, value in params.items():
        if isinstance(value, (list, tuple)):
            value = c4d.Vector(*value)
        obj[getattr(c4d, name)] = value


def smooth(obj):
    """Add a `Tphong` tag so Redshift's tessellation renders smooth."""
    tag = obj.MakeTag(c4d.Tphong)
    tag[c4d.PHONGTAG_PHONG_ANGLELIMIT] = False
    return tag


def build_base(base, dense):
    """Create the base object. `dense` raises segments for displacement."""
    kind = base["kind"]
    segments = 192 if dense else 96
    if kind == "sphere":
        obj = c4d.BaseObject(c4d.Osphere)
        obj[c4d.PRIM_SPHERE_SUB] = segments
    elif kind == "torus":
        obj = c4d.BaseObject(c4d.Otorus)
        obj[c4d.PRIM_TORUS_SEG] = segments * 2
        obj[c4d.PRIM_TORUS_CSUB] = segments // 2
    elif kind == "capsule":
        obj = c4d.BaseObject(c4d.Ocapsule)
        obj[c4d.PRIM_CAPSULE_SEG] = segments
        obj[c4d.PRIM_CAPSULE_HSUB] = segments
        obj[c4d.PRIM_CAPSULE_FSUB] = segments // 4
    elif kind == "cube":
        obj = c4d.BaseObject(c4d.Ocube)
        obj[c4d.PRIM_CUBE_SUBX] = segments // 2
        obj[c4d.PRIM_CUBE_SUBY] = segments // 2
        obj[c4d.PRIM_CUBE_SUBZ] = segments // 2
        obj[c4d.PRIM_CUBE_DOFILLET] = True
        obj[c4d.PRIM_CUBE_SUBF] = 8
    elif kind == "metaball":
        obj = c4d.BaseObject(c4d.Ometaball)
        obj[c4d.METABALLOBJECT_SUBEDITOR] = 8.0
        obj[c4d.METABALLOBJECT_SUBRAY] = 2.0 if dense else 3.0
        for ball in base["balls"]:
            sphere = c4d.BaseObject(c4d.Osphere)
            sphere[c4d.PRIM_SPHERE_RAD] = ball["radius"]
            sphere.SetRelPos(c4d.Vector(*ball["position"]))
            sphere.InsertUnderLast(obj)
    else:
        raise ValueError("unknown base: %s" % kind)
    obj.SetName("Base (%s)" % kind)
    set_params(obj, base["params"])
    smooth(obj)
    return obj


deformer_types = {
    "twist": c4d.Otwist,
    "bend": c4d.Obend,
    "bulge": c4d.Obulge,
    "taper": c4d.Otaper,
    "shear": c4d.Oshear,
    "spherify": c4d.Ospherify,
    "displacer": c4d.Odisplacer,
}


def build_deformer(deformer):
    kind = deformer["kind"]
    obj = c4d.BaseObject(deformer_types[kind])
    obj.SetName(kind.capitalize())
    if kind in ("twist", "bend", "bulge", "taper", "shear"):
        obj[c4d.DEFORMOBJECT_SIZE] = c4d.Vector(deformer_size)
    if kind == "spherify":
        obj[c4d.SPHERIFYOBJECT_RADIUS] = deformer_size / 2.0
    if kind == "displacer":
        noise = c4d.BaseShader(c4d.Xnoise)
        noise[c4d.SLA_NOISE_GLOBAL_SCALE] = deformer["noise_scale"]
        noise[c4d.SLA_NOISE_SEED] = deformer["noise_seed"]
        obj[c4d.ID_MG_SHADER_SHADER] = noise
        obj.InsertShader(noise)
    set_params(obj, deformer["params"])
    obj.SetRelRot(c4d.Vector(*[rad(angle) for angle in deformer["rotation"]]))
    return obj


def build(doc, recipe, name="Serendipity Shape"):
    """Create the shape in `doc` from a recipe, fit to `fit_radius`.

    Returns a null holding the base object, its deformers as children. The
    null's scale and offset do the fitting, so the recipe values stay as
    generated.
    """
    dense = any(d["kind"] == "displacer" for d in recipe["deformers"])
    root = c4d.BaseObject(c4d.Onull)
    root.SetName(name)
    base = build_base(recipe["base"], dense)
    base.InsertUnder(root)
    # `InsertUnderLast` keeps the deformers in recipe order, which is the
    # order Cinema 4D applies them in.
    for deformer in recipe["deformers"]:
        build_deformer(deformer).InsertUnderLast(base)
    doc.InsertObject(root)
    fit(doc, root, base)
    return root


def cache_points(obj, points):
    """Collect the points of `obj`'s evaluated, deformed geometry.

    Positions are in `obj`'s own space, which is all `fit` needs since it runs
    before the base object is moved. Children flagged `BIT_CONTROLOBJECT` are a
    generator's inputs, like a metaball's spheres, already folded into its cache.
    """
    cache = obj.GetDeformCache() or obj.GetCache()
    if cache is not None:
        cache_points(cache, points)
    elif isinstance(obj, c4d.PointObject):
        points.extend(obj.GetAllPoints())
    child = obj.GetDown()
    while child is not None:
        if not child.GetBit(c4d.BIT_CONTROLOBJECT):
            cache_points(child, points)
        child = child.GetNext()


def fit(doc, root, base):
    """Scale and offset `root` so the deformed shape fits `fit_radius`."""
    doc.ExecutePasses(None, False, False, True, c4d.BUILDFLAGS_NONE)
    points = []
    cache_points(base, points)
    if not points:
        return
    low = c4d.Vector(min(p.x for p in points), min(p.y for p in points),
                     min(p.z for p in points))
    high = c4d.Vector(max(p.x for p in points), max(p.y for p in points),
                      max(p.z for p in points))
    center = (low + high) * 0.5
    extent = max(high.x - low.x, high.y - low.y, high.z - low.z)
    if extent <= 0.0:
        return
    scale = 2.0 * fit_radius / extent
    base.SetRelPos(-center)
    root.SetRelScale(c4d.Vector(scale))


def describe(recipe):
    """A short one-line summary, for logs and object names."""
    kinds = [d["kind"] for d in recipe["deformers"]]
    return "%s + %s" % (recipe["base"]["kind"], ", ".join(kinds))
