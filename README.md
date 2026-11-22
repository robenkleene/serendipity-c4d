# Serendipity C4D

A Cinema 4D plugin that generates random organic shapes in random Redshift glass. Every result comes from a seed, so anything you like can be rebuilt exactly.

## How It Works

### Shapes

A shape is a base object with a random stack of deformers under it.

- The base object is a sphere, torus, capsule, filleted cube, or metaball cluster.
- The deformers are 2–5 picks from Twist, Bend, Bulge, Taper, Shear, and Spherify, each rotated randomly. Some shapes also get a noise Displacer at the end.
- The finished shape is scaled to a fixed size.

### Glass

Glass is a Redshift Standard Material with random IOR, tint, absorption depth, dispersion (Abbe number), thin film iridescence, frosting, and coat.

### Recipes

Shapes and materials are generated as recipes first: plain data that can be logged, saved as JSON, and rebuilt without the seed. Parameter ranges are chosen by hand, because Cinema 4D reports limits like ±1e18 for most deformer parameters.

## Layout

| Path                          | Contents                                                        |
| ----------------------------- | --------------------------------------------------------------- |
| `serendipity/`                | The plugin folder that gets installed.                          |
| `serendipity/serendipity.pyp` | Registers the plugin commands.                                  |
| `serendipity/serendipity_lib` | Recipe generation and building, shared by plugin and scenes.    |
| `scenes/`                     | Headless exploration scenes, rendered with `rk-c4d-render`.     |
| `install.sh`                  | Installs the plugin into every Cinema 4D version on the system. |

## Install

```sh
./install.sh              # link to this repo, so edits apply on restart
./install.sh --copy       # copy instead
./install.sh --uninstall
```

The script installs into the `plugins` folder of every `~/Library/Preferences/Maxon/Maxon Cinema 4D <version>_<hash>` folder. Cinema 4D skips a plugin folder that is itself a symlink, so a linked install is a real folder whose contents are symlinks back to this repo.

To install by hand, copy `serendipity/` into Cinema 4D's `plugins` folder, or add this repo as a plugin search path in Preferences → Plugins.

## Use

In Cinema 4D, run Extensions → Serendipity: Add Random Shape. Its seed and a summary of its recipe are printed to the console.

## Explore

The scenes in `scenes/` render random results headlessly in a fixed studio, so seeds can be compared on shape and material alone. `SERENDIPITY_SEED` sets the first seed. Without it, every run picks a new one.

```sh
rk-c4d-render scenes/contact_sheet.py --preview              # 12 seeds in a grid
SERENDIPITY_SEED=100 rk-c4d-render scenes/contact_sheet.py   # seeds 100–111
SERENDIPITY_SEED=103 rk-c4d-render scenes/single.py          # one seed, large
```

Each render writes a `.json` beside it with every seed's recipe, and the console log lists them too.

## Distribution

Before distributing, replace the test plugin ID in `serendipity/serendipity.pyp` with a unique one from developers.maxon.net. Then distribute a zip of `serendipity/` to unzip into Cinema 4D's `plugins` folder.
