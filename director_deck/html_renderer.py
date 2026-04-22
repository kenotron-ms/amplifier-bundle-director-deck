from __future__ import annotations

from pathlib import Path

from director_deck.schema import DesignTokens, Slide, SlideDeck


# ---------------------------------------------------------------------------
# Design token → CSS custom property conversion
# ---------------------------------------------------------------------------


def tokens_to_css_vars(tokens: DesignTokens) -> str:
    """
    Return a CSS ``:root { ... }`` block populated from DesignTokens.

    Typography keys use hyphens in CSS vars (e.g. ``--font-body-md-size``),
    matching the YAML key names directly.
    """
    lines: list[str] = [":root {"]

    c = tokens.colors
    lines.append(f"  --color-primary: {c.primary};")
    if c.accent:
        lines.append(f"  --color-accent: {c.accent};")
    if c.surface:
        lines.append(f"  --color-surface: {c.surface};")
    if c.on_surface:
        lines.append(f"  --color-on-surface: {c.on_surface};")

    if tokens.typography:
        for role, entry in tokens.typography.items():
            # role is e.g. "h1", "body-md" — keep hyphens in var names
            lines.append(f"  --font-{role}-family: {entry.fontFamily};")
            lines.append(f"  --font-{role}-size: {entry.fontSize};")
            lines.append(f"  --font-{role}-weight: {entry.fontWeight};")

    if tokens.spacing:
        for key, value in tokens.spacing.items():
            lines.append(f"  --spacing-{key}: {value};")

    lines.append("}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Per-slide div rendering
# ---------------------------------------------------------------------------

_SLIDE_BASE_CSS = """\
* { box-sizing: border-box; margin: 0; padding: 0; }
body { background: #111; font-family: sans-serif; }
.slide {
  width: 960px;
  height: 540px;
  position: relative;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  margin: 0 auto 4px;
  background: var(--color-primary, #0F172A);
}
.slide-content {
  padding: var(--spacing-slide-padding, 48px);
  display: flex;
  flex-direction: column;
  height: 100%;
}
.slide-title {
  font-family: var(--font-h1-family, Inter, sans-serif);
  font-size: var(--font-h1-size, 36px);
  font-weight: var(--font-h1-weight, 700);
  color: var(--color-accent, #38BDF8);
  margin-bottom: 24px;
  flex-shrink: 0;
}
.slide-body {
  display: flex;
  flex: 1;
  gap: 24px;
  overflow: hidden;
}
.slide-text { flex: 55; }
.slide-image-area {
  flex: 40;
  display: flex;
  align-items: center;
  justify-content: center;
}
.bullets { list-style: none; }
.bullet {
  font-family: var(--font-body-md-family, Inter, sans-serif);
  font-size: var(--font-body-md-size, 16px);
  font-weight: var(--font-body-md-weight, 400);
  color: var(--color-on-surface, #F1F5F9);
  margin-bottom: 12px;
  padding-left: 20px;
  position: relative;
}
.bullet::before {
  content: '\u2192';
  position: absolute;
  left: 0;
  color: var(--color-accent, #38BDF8);
}
.image-placeholder {
  width: 100%;
  min-height: 180px;
  background: var(--color-surface, #1E293B);
  border: 2px dashed var(--color-accent, #38BDF8);
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--color-on-surface, #F1F5F9);
  font-size: 13px;
  text-align: center;
  padding: 12px;
  border-radius: 4px;
}
.slide-image {
  width: 100%;
  max-height: 220px;
  object-fit: cover;
  border-radius: 4px;
}"""


def _render_slide_div(slide: Slide, *, enriched: bool = False) -> str:
    """Render a single slide as a 960×540 <div id="slide-N">."""
    bullets_html = "\n".join(
        f'          <li class="bullet">{b}</li>' for b in slide.bullets
    )

    # Backdrop: inline background-image style when enriched and asset present
    if enriched and slide.assets.backdrop:
        bg_style = (
            f" style=\"background-image: url('{slide.assets.backdrop}'); "
            f'background-size: cover; background-position: center;"'
        )
    else:
        bg_style = ""

    # Image area: real <img> when enriched + asset present, otherwise placeholder
    if enriched and slide.assets.image:
        image_html = (
            f'<img class="slide-image" src="{slide.assets.image}" '
            f'alt="{slide.image_brief}" />'
        )
    else:
        image_html = f'<div class="image-placeholder">{slide.image_brief}</div>'

    return f"""\
<div class="slide" id="slide-{slide.id}"{bg_style}>
  <div class="slide-content">
    <h1 class="slide-title">{slide.title}</h1>
    <div class="slide-body">
      <div class="slide-text">
        <ul class="bullets">
{bullets_html}
        </ul>
      </div>
      <div class="slide-image-area">
        {image_html}
      </div>
    </div>
  </div>
</div>"""


# ---------------------------------------------------------------------------
# Full HTML document
# ---------------------------------------------------------------------------


def render_deck_html(
    deck: SlideDeck,
    tokens: DesignTokens,
    *,
    enriched: bool = False,
) -> str:
    """
    Render all slides as a single HTML document (960px wide, one div per slide).

    Args:
        deck: Validated SlideDeck to render.
        tokens: Design tokens parsed from DESIGN.md.
        enriched: False = placeholder image areas; True = real <img> tags where assets set.

    Returns:
        Complete HTML document string.
    """
    css_vars = tokens_to_css_vars(tokens)
    slides_html = "\n".join(
        _render_slide_div(s, enriched=enriched) for s in deck.slides
    )
    return f"""\
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=960">
  <title>{deck.meta.title}</title>
  <style>
{css_vars}
{_SLIDE_BASE_CSS}
  </style>
</head>
<body>
{slides_html}
</body>
</html>"""


def write_deck_html(
    deck: SlideDeck,
    tokens: DesignTokens,
    output_path: Path,
    *,
    enriched: bool = False,
) -> Path:
    """Write rendered HTML to disk. Creates parent directories as needed. Returns output_path."""
    html = render_deck_html(deck, tokens, enriched=enriched)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(html, encoding="utf-8")
    return output_path
