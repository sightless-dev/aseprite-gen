# Visual grammar

This profile is a persistent art-direction system, not trained model weights. The initial investigation inventoried 1,014 local files: 495 PNGs, 507 JSON sidecars, and 12 TBIN maps. All 21 contact sheets were visually opened. The relevant environment/item atlases were also opened at native resolution, with 4x foliage and 8x wooden-container crops. Overview inspection does **not** mean that every animation frame or every tile in a large atlas received close inspection. TBIN files are hashed and inventoried, not decoded.

## Evidence and groups

The main coherent group is illustrated, front-biased elevated-view RPG environment art. It uses saturated warm materials, dark colored contours, readable compact silhouettes and dense but organized detail. Actors, seasonal palettes, UI/typography, effects/panoramas and technical recolor masks are distinct groups. Color-frequency extraction alone would misleadingly prioritize saturated RGB mask colors; those images are excluded from style selection. The analyzer keeps them in the complete inventory.

Exact pixel-replication comparison found six images with a whole-image 4x repetition grid and 489 without an exact integer factor in 2..8. A result of 1 is only absence of exact replication, not proof of native scale. Atlas cells and export margins must be considered when choosing dimensions. 283 PNGs contain some intermediate alpha: the binary-alpha rule below is a deliberate isolated-prop constraint, not a claim that every reference has binary alpha.

## Confirmed visual observations

- **Silhouette:** vegetation starts from continuous, asymmetrical masses. Crown volume and roots dominate recognition. Short stepped edges and pointed leaf ends interrupt broad lobes; negative spaces occur near forks and between masses.
- **Clusters:** reference leaves overlap in small pointed groups, commonly a few pixels across, rather than independent outlined dots. Highlights gather on selected upper-facing leaves. Large leaves and conifers use different cluster sizes and rhythms.
- **Contours:** deep green, brown and purple contours separate materials. A one-pixel edge is common, with thicker dark pockets at overlap and contact. Characters can have near-black outlines; that is not a mandatory foliage rule.
- **Color:** wood highlights move toward yellow/orange, shadows toward reddish or purplish brown. Vegetation shifts from cool dark green to warmer yellow-green. Whole-atlas palette counts are not object budgets.
- **Depth:** visible tops of containers coexist with taller front faces; trunks rise vertically. This is not a uniform 2:1 isometric grid. Metal bands curve around the body, with narrow highlights and darker undersides.
- **Materials:** wood has long but broken grain and dark joinery; stone uses unequal angular masses and recesses; fabric relies on larger planes and a few folds. Faces and small objects allocate contrast to recognition cues.
- **Hierarchy:** large shape, material planes, then clustered detail. Native-size readability matters more than a decorative enlarged texture.

## Chosen production rules and hypotheses

Use the machine-readable [profile](../profiles/cozy-rpg.json), revision 2 / schema 2. Its summer ramps follow observed object colors; geometry and leaf motifs are original, with no source pixels copied. Foliage and wood have eight available shades, metal four, and each output uses at most 24 visible colors. Bush foliage is yellow-green, tree foliage cooler jade-green, and barrel wood orange-red with warm dark hoops. Use a consistent upper-left light. Budgets and fixed lighting are production choices, not measured universal laws.

Use binary alpha for isolated props, one native pixel grid, no antialiasing or random dither. Build broad shade planes before inserting leaves or grain. Reserve the brightest shade for sparse focal clusters. Favor connected 2–5-pixel small highlights, but inspect exceptions such as rivets and berries rather than deleting every single pixel.

## Construction recipes

**Bush:** use an upright, nearly square rounded crown on a 48×48 canvas. Build dark underleaves, occasional woody stems and overlapping pointed leaf sprays. Vary the contour and spray positions; keep deeper pockets near the base. Add sparse berries only when requested. The old low three-lobe construction was rejected for this reference group.

**Tree:** use a tall crown on a 64×96 canvas, a slender warm trunk, embedded forks and unequal roots. Overlap individual pointed leaves over dark underleaves; vary their positions and highlight groups. Bark grooves follow the trunk. Avoid the old stack of broad polygon lobes. The current preset still produces a more regular crown and simpler bark than the selected reference.

**Barrel:** use a compact 32×32 canvas, bulging body, shallow oval lid and thicker front plane. Project individual staves around the cylinder so side staves narrow. Use orange-red wood, a golden rim and warm dark hoops; cold gray bands were a mismatch. Broken grain and an offset bung interrupt symmetry. Avoid a uniformly highlighted lid outline.

Actor, stone and cloth rules are retained for future scene authoring; the preset generator does not implement those asset classes.

## Update without losing knowledge

`analyze` hashes every input and creates a new versioned snapshot only when inputs or analyzer version change. Unchanged image measurements are reused within an analyzer version; prior manifests and authored notes remain. Open new/changed reference sheets before revising the profile. Record newly confirmed rules separately from hypotheses and contradictions, increment `revision`, and keep prior profile revisions in Git. The machine does not silently infer new artistic rules from a histogram.

Reference selection ranks local semantic tags; it is not a visual embedding model. Pass selected files or native crops to Codex for the visual decision. The CLI's parameterized presets work from the saved profile and recognized text modifiers; arbitrary prose is not interpreted by a local generative model.
