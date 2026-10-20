# Initial visual review (actual Inkscape rendering)

Reviewed all three first-pass native SVGs at 96 dpi and Figure 2 horizontal at 300 dpi; reviewed learning and horizontal final-results grayscale previews.

1. Learning: the explicit x limits 0–30 placed endpoint marker centers on the plot boundary, visibly clipping half of the first and last symbols. This is a source-spec layout issue, not a renderer failure. A new v2 spec expands the limits to −0.8–30.8 without changing any observation, statistic, tick meaning, or vertical range. The first-pass source and preview are retained as a concrete before case.
2. Figure 2: the first version relied on bar colors and the Figure 1 legend to identify the scatter groups. Baseline and Proposed have similar luminance in grayscale. To make this independent figure self-contained, both candidate v2 specs add the same three-column marker legend in unused lower space. It does not obscure observations.
3. Horizontal versus stacked: horizontal puts the final mean and all individual runs side by side for immediate comparison and uses 90 mm height. Stacked enlarges horizontal separation but uses 130 mm height and adds substantial empty space around three categories; its extra width per panel does not reveal more data. The horizontal version is provisionally selected, subject to review of the v2 legend.

No shared skill or test was modified. No unsupported API was required for these source-level fixes.
