# Monkey Balls

A plugin for the [Ballest plugin manager](https://github.com/AnythingGoes-ballest/ballest-plugin-manager): AiAi,
MeeMee, Baby and GonGon from Super Monkey Ball (GameCube), each running inside a clear ball. They're added to the
**balls** tab of the **Customize** page through
[Cosmetic Kit](https://github.com/AnythingGoes-ballest/ballest-cosmetic-kit).

Each ball is clear glass with a tinted lower half, as on the original game's box art, and the tinted half rolls with
the ball. The monkey inside stays upright and faces where the ball is going. Its arms and legs swing as it runs,
faster and further the faster the ball rolls; at rest it just sways a little.

The monkeys follow the official 2001 character art: spiral ears, black oval eyes and a heart-shaped face.

| Ball | Look | Lower half |
|---|---|---|
| AiAi | dark brown fur, an open grin, an orange shirt with a white A | red |
| MeeMee | light tan fur, lashes, a pink skirt and pink flowers | pink |
| Baby | creamy white fur, a big head, a dummy and a blue nappy | blue |
| GonGon | dark fur, heavy brows, big fists, a red shirt with a yellow G | green |

AiAi's red is from the box art; the other three colours are chosen for this plugin.

Fan-made: Super Monkey Ball and its characters belong to SEGA. The models are simple shapes built for this plugin.

## Install

In the game: footer **plugins** > **browse** > Monkey Balls > **install** (Cosmetic Kit comes with it).
Needs the plugin manager host 0.13.1 or newer.

## Files

- `main.as`: adds the balls.
- `models/`: one model per monkey. The format is in the plugin manager's
  [custom cosmetics guide](https://anythinggoes-ballest.github.io/ballest-plugin-manager/guides/cosmetics/).
- `*_preview.png`: the tile pictures, drawn from the models by `make_previews.py` (Python with NumPy and Pillow).

## License

MIT
