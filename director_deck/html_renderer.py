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

_LAYOUT_CSS = """\
/* Layout type badge (wireframe only) */
.layout-badge {
  position: absolute;
  top: 8px;
  right: 8px;
  background: rgba(255,255,255,0.15);
  color: var(--color-accent, #38BDF8);
  font-size: 10px;
  font-weight: 600;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  padding: 3px 8px;
  border-radius: 3px;
  pointer-events: none;
}
/* HERO layout */
.slide.layout-hero .hero-content {
  position: absolute;
  inset: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: var(--spacing-slide-padding, 64px);
  text-align: center;
}
.slide.layout-hero .hero-statement {
  font-family: var(--font-h1-family, Inter, sans-serif);
  font-size: var(--font-h1-size, 48px);
  font-weight: var(--font-h1-weight, 700);
  color: var(--color-accent, #38BDF8);
  line-height: 1.15;
  max-width: 800px;
}
.slide.layout-hero .hero-sub {
  margin-top: 20px;
  font-family: var(--font-body-md-family, Inter, sans-serif);
  font-size: var(--font-body-md-size, 18px);
  color: var(--color-on-surface, #F1F5F9);
  opacity: 0.8;
}
/* STATEMENT layout (section divider) */
.slide.layout-statement .statement-content {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: var(--spacing-slide-padding, 64px);
}
.slide.layout-statement .statement-text {
  font-family: var(--font-h1-family, Inter, sans-serif);
  font-size: calc(var(--font-h1-size, 48px) * 1.15);
  font-weight: var(--font-h1-weight, 700);
  color: var(--color-on-surface, #F1F5F9);
  text-align: center;
  border-left: 5px solid var(--color-accent, #38BDF8);
  padding-left: 32px;
  max-width: 700px;
}
/* STAT CALLOUT layout */
.slide.layout-stat-callout .stat-content {
  position: absolute;
  inset: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 16px;
  padding: var(--spacing-slide-padding, 64px);
}
.slide.layout-stat-callout .stat-number {
  font-family: var(--font-h1-family, Inter, sans-serif);
  font-size: 120px;
  font-weight: 800;
  color: var(--color-accent, #38BDF8);
  line-height: 1;
}
.slide.layout-stat-callout .stat-label {
  font-family: var(--font-body-md-family, Inter, sans-serif);
  font-size: var(--font-body-md-size, 18px);
  color: var(--color-on-surface, #F1F5F9);
  text-align: center;
  max-width: 600px;
}
/* QUOTE layout */
.slide.layout-quote .quote-content {
  position: absolute;
  inset: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: var(--spacing-slide-padding, 64px);
  gap: 24px;
}
.slide.layout-quote .quote-mark {
  font-size: 100px;
  color: var(--color-accent, #38BDF8);
  line-height: 0.5;
  align-self: flex-start;
}
.slide.layout-quote .quote-text {
  font-family: var(--font-h1-family, Inter, sans-serif);
  font-size: 28px;
  font-style: italic;
  color: var(--color-on-surface, #F1F5F9);
  text-align: center;
  max-width: 680px;
  line-height: 1.4;
}
.slide.layout-quote .quote-attribution {
  font-family: var(--font-body-md-family, Inter, sans-serif);
  font-size: 14px;
  color: var(--color-accent, #38BDF8);
  letter-spacing: 0.05em;
  text-transform: uppercase;
}
/* COMPARISON layout */
.slide.layout-comparison .comparison-body {
  display: flex;
  flex: 1;
  gap: 2px;
}
.slide.layout-comparison .comparison-col {
  flex: 1;
  background: var(--color-surface, #1E293B);
  padding: 24px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.slide.layout-comparison .comparison-col-title {
  font-family: var(--font-h1-family, Inter, sans-serif);
  font-size: 20px;
  font-weight: 700;
  color: var(--color-accent, #38BDF8);
  padding-bottom: 8px;
  border-bottom: 1px solid rgba(255,255,255,0.1);
}
/* FULL BLEED layout */
.slide.layout-full-bleed .full-bleed-overlay {
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  padding: 32px var(--spacing-slide-padding, 64px);
  background: linear-gradient(transparent, rgba(0,0,0,0.8));
}
.slide.layout-full-bleed .full-bleed-title {
  font-family: var(--font-h1-family, Inter, sans-serif);
  font-size: 36px;
  font-weight: 700;
  color: #ffffff;
}
"""


def _render_slide_div(slide: "Slide", *, enriched: bool = False) -> str:
    """Render a single slide as a 960×540 <div id='slide-N'> using the slide's layout_type."""
    layout = slide.layout_type

    # Backdrop style (enriched mode)
    if enriched and slide.assets.backdrop:
        bg_style = (
            f' style="background-image: url(\'{slide.assets.backdrop}\'); '
            f'background-size: cover; background-position: center;"'
        )
    else:
        bg_style = ""

    # Layout type badge (always visible — helps during wireframe review)
    badge = f'<div class="layout-badge">{layout.replace("_", " ")}</div>'

    layout_class = f"layout-{layout.replace('_', '-')}"

    # ── HERO layout ──────────────────────────────────────────────────────────
    if layout == "hero":
        statement = slide.hero_statement or slide.title
        sub = slide.bullets[0] if slide.bullets else ""
        return f"""\
<div class="slide {layout_class}" id="slide-{slide.id}"{bg_style}>
  {badge}
  <div class="hero-content">
    <p class="hero-statement">{statement}</p>
    {f'<p class="hero-sub">{sub}</p>' if sub else ''}
  </div>
</div>"""

    # ── STATEMENT layout (section divider) ───────────────────────────────────
    if layout == "statement":
        text = slide.hero_statement or slide.title
        return f"""\
<div class="slide {layout_class}" id="slide-{slide.id}"{bg_style}>
  {badge}
  <div class="statement-content">
    <h2 class="statement-text">{text}</h2>
  </div>
</div>"""

    # ── STAT CALLOUT layout ──────────────────────────────────────────────────
    if layout == "stat_callout":
        stat = slide.hero_statement or (slide.bullets[0] if slide.bullets else slide.title)
        context = " ".join(slide.bullets[1:]) if len(slide.bullets) > 1 else slide.title
        return f"""\
<div class="slide {layout_class}" id="slide-{slide.id}"{bg_style}>
  {badge}
  <div class="stat-content">
    <div class="stat-number">{stat}</div>
    <div class="stat-label">{context}</div>
  </div>
</div>"""

    # ── QUOTE layout ─────────────────────────────────────────────────────────
    if layout == "quote":
        quote = slide.hero_statement or (slide.bullets[0] if slide.bullets else slide.title)
        attribution = slide.bullets[1] if len(slide.bullets) > 1 else ""
        return f"""\
<div class="slide {layout_class}" id="slide-{slide.id}"{bg_style}>
  {badge}
  <div class="quote-content">
    <div class="quote-mark">\u201c</div>
    <blockquote class="quote-text">{quote}</blockquote>
    {f'<div class="quote-attribution">— {attribution}</div>' if attribution else ''}
  </div>
</div>"""

    # ── COMPARISON layout ────────────────────────────────────────────────────
    if layout == "comparison":
        mid = len(slide.bullets) // 2
        left_items = slide.bullets[:mid] if slide.bullets else []
        right_items = slide.bullets[mid:] if slide.bullets else []
        left_html = "".join(f'<li class="bullet">{b}</li>' for b in left_items)
        right_html = "".join(f'<li class="bullet">{b}</li>' for b in right_items)
        # Split title at "vs" or "/" for column headers
        parts = [p.strip() for p in slide.title.replace(" vs ", " / ").split("/", 1)]
        left_title = parts[0] if parts else "Before"
        right_title = parts[1] if len(parts) > 1 else "After"
        return f"""\
<div class="slide {layout_class}" id="slide-{slide.id}"{bg_style}>
  {badge}
  <div class="slide-content">
    <h1 class="slide-title">{slide.title}</h1>
    <div class="comparison-body">
      <div class="comparison-col">
        <div class="comparison-col-title">{left_title}</div>
        <ul class="bullets">{left_html}</ul>
      </div>
      <div class="comparison-col">
        <div class="comparison-col-title">{right_title}</div>
        <ul class="bullets">{right_html}</ul>
      </div>
    </div>
  </div>
</div>"""

    # ── FULL BLEED layout ────────────────────────────────────────────────────
    if layout == "full_bleed":
        if enriched and slide.assets.image:
            img_style = (
                f' style="background-image: url(\'{slide.assets.image}\'); '
                f'background-size: cover; background-position: center;"'
            )
        else:
            img_style = ""
        return f"""\
<div class="slide {layout_class}" id="slide-{slide.id}"{img_style}>
  {badge}
  <div class="full-bleed-overlay">
    <h1 class="full-bleed-title">{slide.hero_statement or slide.title}</h1>
  </div>
</div>"""

    # ── DEFAULT: bullets, process_flow, timeline (title + bullets + image) ───
    bullets_html = "\n".join(
        f'          <li class="bullet">{b}</li>' for b in slide.bullets
    )
    if enriched and slide.assets.image:
        image_html = (
            f'<img class="slide-image" src="{slide.assets.image}" '
            f'alt="{slide.image_brief}" />'
        )
    else:
        image_html = f'<div class="image-placeholder">{slide.image_brief}</div>'

    return f"""\
<div class="slide {layout_class}" id="slide-{slide.id}"{bg_style}>
  {badge}
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
{_LAYOUT_CSS}
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
