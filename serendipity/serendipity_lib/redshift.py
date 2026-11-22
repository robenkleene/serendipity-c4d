"""Helpers for building Redshift node materials through the `maxon` API."""

import c4d
import maxon

# Redshift's materials are node graphs living in their own node space, and every
# node and port id is prefixed with this.
rs_space = maxon.NodeSpaceIdentifiers.RedshiftMaterial
rs = "com.redshift3d.redshift4c4d.nodes.core."


def material(doc, name):
    """Create a Redshift node material, returning it with its graph and shader.

    `CreateDefaultGraph` builds a `standardmaterial` wired into the graph's
    `output`, which is the returned shader node. It asserts on anything but
    `c4d.Mmaterial`.
    """
    mat = c4d.BaseMaterial(c4d.Mmaterial)
    mat.SetName(name)
    node_mat = mat.GetNodeMaterialReference()
    node_mat.CreateDefaultGraph(rs_space)
    graph = node_mat.GetGraph(rs_space)

    shader = None
    for child in graph.GetViewRoot().GetChildren():
        if "standardmaterial" in str(child.GetId()):
            shader = child
            break
    if shader is None:
        raise RuntimeError("no standardmaterial node in the default graph")

    doc.InsertMaterial(mat)
    return mat, graph, shader


def port(node, name):
    found = node.GetInputs().FindChild(name)
    if found.IsNullValue():
        raise RuntimeError("no such port: %s" % name)
    return found


def shader_port(shader, name):
    """Look up a `standardmaterial` input by its short name, e.g. `refl_ior`."""
    return port(shader, rs + "standardmaterial." + name)


def set_shader_values(graph, shader, values):
    """Apply a `{short port name: value}` dict in one graph transaction."""
    with graph.BeginTransaction() as transaction:
        for name, value in values.items():
            shader_port(shader, name).SetPortValue(value)
        transaction.Commit()


def color(rgb):
    return maxon.Color(rgb[0], rgb[1], rgb[2])


def assign(obj, mat, projection=c4d.TEXTURETAG_PROJECTION_UVW):
    tag = obj.MakeTag(c4d.Ttexture)
    tag[c4d.TEXTURETAG_MATERIAL] = mat
    tag[c4d.TEXTURETAG_PROJECTION] = projection
    return tag


def add_texture(graph, path, repeats=1.0):
    """Add a `texturesampler` reading the image at `path`."""
    with graph.BeginTransaction() as transaction:
        sampler = graph.AddChild(
            maxon.Id(), maxon.Id(rs + "texturesampler"), maxon.DataDictionary()
        )
        transaction.Commit()
    with graph.BeginTransaction() as transaction:
        # The path is a `path` child of the `tex0` bundle port, and must be a
        # `maxon.Url`, not a `str`.
        port(sampler, rs + "texturesampler.tex0").FindChild("path").SetPortValue(
            maxon.Url(path)
        )
        port(sampler, rs + "texturesampler.scale").SetPortValue(
            maxon.Vector(repeats, repeats, 1.0)
        )
        transaction.Commit()
    return sampler


def connect_texture(graph, sampler, shader, name):
    """Wire a texture sampler's color into a `standardmaterial` input."""
    with graph.BeginTransaction() as transaction:
        out = sampler.GetOutputs().FindChild(rs + "texturesampler.outcolor")
        out.Connect(shader_port(shader, name))
        transaction.Commit()
