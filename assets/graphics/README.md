# Resident shell artwork

`satellite-dish.svg` is the standalone blue/white dish graphic. Its checked-in
PNG is a raster export; the build compiles it to the fixed VERA palette at 40×40.
To regenerate after editing the vector:

```sh
inkscape assets/graphics/satellite-dish.svg --export-filename=assets/graphics/satellite-dish.png
```

`../branding/roddy-badge.svg` preserves the paths from the local RODDY brand pack's
`badge/outline/roddy_badge_classic_cream_red_outline.svg`, with the cropped
artboard used by the storefront and cream lettering. Its PNG is exported with:

```sh
inkscape assets/branding/roddy-badge.svg --export-area-page --export-width=96 --export-filename=assets/branding/roddy-badge.png
```

Inkscape is needed only when editing these vectors. Ordinary builds use the
checked-in PNGs and Pillow. The skyline scenes are generated separately by
`tools/build_assets.py` and packed into `WCSC00.BIN` through `WCSC27.BIN`.
