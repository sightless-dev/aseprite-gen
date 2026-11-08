# Actual visual review

## Summer correction, revision 2

The user rejected the initial bush, tree and barrel because they visibly differed from the selected environment atlas. The old review understated that mismatch. Muted polygon foliage, low/broad proportions and cold barrel hoops were structural errors, not details that extra highlights could fix.

The current [gallery](../examples/summer-v2/index.html) and [comparison](../examples/summer-v2/comparison.png) contain only original artwork. Local reference comparisons use the same 4× nearest-neighbor scale for every column, without normalizing object sizes. The final native PNGs and enlarged comparisons were actually opened.

| Asset | Current canvas | Implemented change | Remaining visual difference |
|---|---|---|---|
| Bush | 48×48 | Upright rounded silhouette, saturated yellow-green ramp, dark underleaves and overlapping pointed sprays | Contour is smoother and leaf placement more regular than the reference |
| Broadleaf tree | 64×96 | Tall jade crown, separate pointed leaves, embedded branches, warm slender trunk and unequal roots | Leaf sprays still suggest repeated diagonals; bark and root transitions are simpler |
| Wooden barrel | 32×32 | Compact convex body, projected staves, orange-red wood, golden rim and warm dark hoops | Grain is coarser and rim/hoop edges more regular |

The profile now controls geometry and leaf spacing/sizes, not just palette and metadata. The default generator uses the rebuilt construction. Earlier sources and layers remain intact under `examples/`; revision 2 has new sources under `examples/summer-v2/`. Final sources were reopened through actual MCP and their rendered pixels compared with their PNG exports. Each new `.review.json` separates technical invariants from these subjective observations. The single-color-pixel warning is retained: pointed leaf and wood highlights account for many such pixels, but texture regularity remains a visual limitation.

The focused generation tests passed (11 tests, including native editor reopening, no skips). Technical success does not establish artistic fidelity, and the new revision has not received user approval. Its color, proportion and construction changes are directly visible; it is not an exact reproduction of the reference artist's rendering.

## Historical review of the rejected version

The three initial assets were rendered by Aseprite through real MCP and revised. The old [comparison](../examples/comparison.png) is retained as historical evidence, not as the current style target.

| Asset | Native size | Before: observed weakness | Implemented change | Remaining limitation |
|---|---|---|---|---|
| Berry bush | 48×32 | Empty shadow areas, triangular crown, repetitive highlight arcs | More connected leaf groups, a crown-edge leaf, broader selective light clusters | Lower skirt is heavy; cluster rhythm can still look mechanical |
| Broadleaf tree | 64×80 | Sparse crown texture, repeated lobes and flat trunk | Denser staggered leaf groups, interrupted bark grooves, root highlights | Lobe construction is more geometric and darker than the reference group |
| Wooden barrel | 32×40 | Smooth body and evenly spaced seams, uniformly simple lid | Broken grain, local rim highlights and cooler narrow hoop glints | Lower detail density and fewer organic irregularities than the reference |

`*-before` preserves a sparse first pass; `*-detailed` preserves a denser middle pass. Historical correction arrays are in `*.corrections.json` and were sent to `refine_sprite` on the named `art direction` layer. Original layers/sources remained intact. Their `*.scene.json` combines the actual intermediate scene with that patch. The replay script uses those stored corrections; they are no longer the current generator's construction.

All three final PNGs passed exact size, binary alpha, transparent background and palette-budget checks. `.review.json` records measurements and the separate subjective assessment. Such measurements can flag disconnected pixels or single-color noise; they do not prove coherent lighting, appealing shape or style fidelity.

An independent skill forward-test generated two 48×32 autumn berry bushes, opened their actual native and enlarged source renders, made one targeted berry-highlight change, and exported the result. Exactly one intended pixel changed; the four original source/PNG hashes stayed unchanged and the exported PNG matched the refined PNG. It identified a wrong project-root traversal in the skill, which was corrected to `../../..`. It also independently observed modest seed diversity and repetitive diagonal foliage bands.

Those technical and forward-test results remain valid for the historical version. They did not establish the style match that the user expected; the subsequent rejection is the reason for revision 2.
