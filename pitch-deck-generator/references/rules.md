# Rules

Each rule exists because violating it produced a visibly wrong slide. The
regression is recorded with the rule — a rule without its failure case tends
to get "simplified" away by whoever reads it next.

## 1. Never invent a fact

Every value comes from `get_brand` or from the conversation. No third source.

> `get_brand` returned `employees: 10001`. The slide shipped "33,000+
> employees", recalled from an AI model's training data. Plausible,
> fabricated, and invisible to a proofreader.

Missing field → leave empty, report it. For user values the stakes are
higher: a wrong fee is a commitment nobody made. Ask rather than infer, and
never carry a value over from a different client's deck.

## 2. Fetch assets by direct download of the `src` URLs

Use the `src` URLs from `get_brand` **exactly as returned** — `curl` them to
disk. The `?c=` query parameter is a per-response credential; editing or
rebuilding the URL breaks it.

- `build_logo_urls` output is display-only. Fetching it programmatically 302s
  to a hotlink-policy page.
- Do not route image bytes through `get_asset_base64` into a file: multi-
  kilobyte base64 payloads corrupt under transcription and burn context for
  no benefit. (This failed three separate ways before the direct-curl rule
  existed.)
- An un-credentialed CDN URL does not fail cleanly: the 302 target is not on
  your allowlist, so the proxy returns a 403 **that reads like a network
  block**. Diagnose a 403 as a bad token before suspecting the network.

## 3. Theme names the asset's colour, not the background

Verified empirically: `theme=light` is a white mark (for dark grounds),
`theme=dark` is near-black (for light grounds).

> A light-preferring symbol token placed logic-side-up would render
> near-black on near-black. Mastercard hid the bug — its mark is coloured —
> so it would only surface on a monochrome client, exactly when nobody is
> looking.

Fallback chains never cross type: no symbol at either theme leaves the slot
empty rather than borrowing the icon.

## 4. Overlay slots, never replace them

The slot shape often carries design — a fill, a solid border, a rounded
corner. Replacing the `<p:sp>` with a `<p:pic>` deletes all of it.

> Replacing shapes deleted three logo tiles' backgrounds. The logos rendered
> correctly onto nothing.

Keep the shape, blank its text, append the fitted `<p:pic>` on top.

## 5. Fit belongs to the slot, not the token

The same token can need opposite treatments in different frames. Derive fit
from the frame: banner/icon → cover; ellipse → cover; large square → tight
contain; else contain with a safe-box.

> Cover-fit on a 1.05:1 "square" stretched a symbol; cover on a true square
> then cropped 19% off a 1.62:1 symbol. Tight contain was right for both.

## 6. Images are fitted geometrically, never stretched

Native dimensions are read from the file on disk, never assumed.

- **Contain**: `scale = min(safe_w/nat_w, safe_h/nat_h)`, centre in frame.
- **Cover**: `scale = max(...)`, centre-crop overflow via `<a:srcRect>`
  (units: thousandths of a percent).
- A cover-fit shape with its own solid stroke gets the frame inflated by the
  stroke width first — OOXML centres strokes on the boundary, and a same-size
  picture leaves half the stroke visible as a ring.

For every placed image, `ext_cx/ext_cy` must equal the native ratio within
1% unless a `srcRect` crop is present.

## 7. Text frames are sized for the token, not the content

Measure the rendered width in a real font (`ImageFont.getlength`) and grow
the frame toward the next slot or the card edge. A guessed advance width is
how text overflows.

## 8. Never resize type to satisfy the preview

If the template's fonts are not installed, the previewer substitutes wider
ones and text *appears* to overflow when it fits perfectly in PowerPoint.

> A phantom wrap led to a title being cut 45pt → 24pt. The render "looked
> fixed" while the deliverable had a title half its designed size.

`fc-list | grep -i <font>` returns 0 → the preview is not authoritative. If
content genuinely does not fit, shorten the content or widen the frame —
never shrink the type.

## 9. Scope edits to one shape

Templates repeat attribute patterns. A global regex or bare `str.replace`
across a slide hits unintended targets.

> A global brace-strip meant to clean placeholder tokens corrupted the XML
> around a slide's static social-media icons — shapes that had nothing to do
> with any token.

Isolate the target shape, edit within that substring, splice back. And merge
split runs before substituting: editors split tokens mid-string across
`<a:r>` runs, so `{start_date}` may never appear whole in any single `<a:t>`.

## 10. Dashed means placeholder

A dashed outline on a slot is instrumentation, not design. The builder
strips dash-family outlines from slots it fills (never fills, never solid
strokes) and leaves them on unfilled slots so gaps stay visibly marked.

> The first filled decks shipped with dashed boxes around every client logo —
> template documentation printed onto a client deliverable.

## Pre-ship checklist

1. Builder output: no unfilled tokens you didn't expect.
2. `validate.py out.pptx --original template.pptx` passes.
3. Template fonts installed before trusting any render (`fc-list`).
4. Every image aspect preserved (the builder asserts this).
5. Render to images and actually look at every slide.
