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
  padding: 28px 36px;
  display: flex;
  flex-direction: column;
  height: 100%;
  overflow: hidden;
}
.slide-title {
  font-family: var(--font-h1-family, Inter, sans-serif);
  font-size: 18px;
  font-weight: 700;
  color: var(--color-accent, #38BDF8);
  margin-bottom: 14px;
  flex-shrink: 0;
  line-height: 1.3;
}
.slide-body {
  display: flex;
  flex: 1;
  gap: 24px;
  min-height: 0;
}
.slide-text {
  flex: 55;
  overflow: hidden;
}
.slide-image-area {
  flex: 40;
  display: flex;
  align-items: center;
  justify-content: center;
}
.bullets { list-style: none; }
.bullet {
  font-family: var(--font-body-md-family, Inter, sans-serif);
  font-size: 13px;
  font-weight: var(--font-body-md-weight, 400);
  color: var(--color-on-surface, #F1F5F9);
  margin-bottom: 8px;
  padding-left: 14px;
  position: relative;
  line-height: 1.4;
}
.bullet::before {
  content: '\u2022';
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
  padding: 36px 56px;
  text-align: center;
  gap: 0;
}
.slide.layout-hero .hero-statement {
  font-family: var(--font-h1-family, Inter, sans-serif);
  font-size: 26px;
  font-weight: 700;
  color: var(--color-accent, #38BDF8);
  line-height: 1.25;
  max-width: 820px;
}
.slide.layout-hero .hero-sub {
  margin-top: 14px;
  font-family: var(--font-body-md-family, Inter, sans-serif);
  font-size: 13px;
  color: var(--color-on-surface, #F1F5F9);
  opacity: 0.85;
  max-width: 760px;
  line-height: 1.5;
}
/* STATEMENT layout (section divider) */
.slide.layout-statement .statement-content {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 36px 56px;
}
.slide.layout-statement .statement-text {
  font-family: var(--font-h1-family, Inter, sans-serif);
  font-size: 28px;
  font-weight: 700;
  color: var(--color-on-surface, #F1F5F9);
  text-align: center;
  border-left: 4px solid var(--color-accent, #38BDF8);
  padding-left: 24px;
  max-width: 740px;
  line-height: 1.3;
}
/* STAT CALLOUT layout */
.slide.layout-stat-callout .stat-content {
  position: absolute;
  inset: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 12px;
  padding: 36px 56px;
}
.slide.layout-stat-callout .stat-number {
  font-family: var(--font-h1-family, Inter, sans-serif);
  font-size: 80px;
  font-weight: 800;
  color: var(--color-accent, #38BDF8);
  line-height: 1;
}
.slide.layout-stat-callout .stat-label {
  font-family: var(--font-body-md-family, Inter, sans-serif);
  font-size: 13px;
  color: var(--color-on-surface, #F1F5F9);
  text-align: center;
  max-width: 680px;
  line-height: 1.5;
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
  padding: 20px 36px;
  background: linear-gradient(transparent, rgba(0,0,0,0.85));
}
.slide.layout-full-bleed .full-bleed-title {
  font-family: var(--font-h1-family, Inter, sans-serif);
  font-size: 22px;
  font-weight: 700;
  color: #ffffff;
  line-height: 1.3;
}
/* TIMELINE layout */
.slide.layout-timeline .slide-title,
.slide.layout-process-flow .slide-title {
  font-size: 16px;
}
.slide.layout-timeline .bullet,
.slide.layout-process-flow .bullet {
  font-size: 12px;
  margin-bottom: 6px;
}
"""


def _render_slide_div(slide: "Slide", *, enriched: bool = False) -> str:
    """Render a single slide as a 960×540 <div id='slide-N'> using the slide's layout_type.

    Embeds transition timing as data attributes so the HTML player can drive
    each transition at the correct duration without hardcoding:
      data-transition-duration="2.5"   (seconds, from slide.transition_duration_s)
      data-transition-easing="ease_in_out"

    These are read by deck_live.html's JS to set the correct video timing.
    """
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

    # Transition timing data attributes — read by deck_live.html JS to set
    # each transition's duration. duration is the outgoing video duration in
    # seconds (after ffmpeg retiming); easing is informational.
    dur = slide.transition_duration_s if slide.transition_duration_s is not None else ""
    trans_attrs = (
        f' data-transition-duration="{dur}"'
        f' data-transition-easing="{slide.transition_easing}"'
    )

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
        # Render each bullet as its own label line — don't join them into one blob
        label_lines = slide.bullets if slide.bullets else [slide.title]
        labels_html = "".join(
            f'<div class="stat-label">{b}</div>' for b in label_lines
        )
        return f"""\
<div class="slide {layout_class}" id="slide-{slide.id}"{bg_style}>
  {badge}
  <div class="stat-content">
    <div class="stat-number">{stat}</div>
    {labels_html}
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

    # -- DEFAULT: bullets / process_flow / timeline ---------------------------
    # Enriched: backdrop is the visual atmosphere (CSS background-image set).
    # Text runs full-width over it. No right-panel AI image competing with type.
    # Wireframe: image placeholder visible so brief is reviewable at Gate 1.
    bullets_html = "\n".join(
        f'          <li class="bullet">{b}</li>' for b in slide.bullets
    )
    if enriched:
        return (
            f'<div class="slide {layout_class}" id="slide-{slide.id}"{bg_style}>\n'
            f'  {badge}\n'
            f'  <div class="slide-content">\n'
            f'    <h1 class="slide-title">{slide.title}</h1>\n'
            f'    <div class="slide-body">\n'
            f'      <div class="slide-text" style="flex: 1;">\n'
            f'        <ul class="bullets">\n'
            + bullets_html + "\n"
            + '        </ul>\n'
              '      </div>\n'
              '    </div>\n'
              '  </div>\n'
              '</div>'
        )
    image_html = f'<div class="image-placeholder">{slide.image_brief}</div>'
    return (
        f'<div class="slide {layout_class}" id="slide-{slide.id}"{bg_style}>\n'
        f'  {badge}\n'
        f'  <div class="slide-content">\n'
        f'    <h1 class="slide-title">{slide.title}</h1>\n'
        f'    <div class="slide-body">\n'
        f'      <div class="slide-text">\n'
        f'        <ul class="bullets">\n'
        + bullets_html + "\n"
        + '        </ul>\n'
          '      </div>\n'
          f'      <div class="slide-image-area">\n'
          f'        {image_html}\n'
          '      </div>\n'
          '    </div>\n'
          '  </div>\n'
          '</div>'
    )


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



# ---------------------------------------------------------------------------
# Live presentation player (pixel_slides + transitions)
# ---------------------------------------------------------------------------
# ---------------------------------------------------------------------------
# Live presentation player (pixel_slides + transitions)
# ---------------------------------------------------------------------------


def write_live_html(
    deck: "SlideDeck",
    run_dir: "Path",
    output_path: "Path",
    tokens: "DesignTokens | None" = None,
) -> "Path":
    """Write a self-contained HTML presentation player.

    Architecture matches the seamless HK-deck approach:
      - Locked 16:9 canvas: width/height from min() CSS so aspect ratio
        is correct at any viewport size with no JS measurement needed.
      - All slides always in DOM as position:absolute layers; opacity
        controls which is visible (no display:none repaint cost).
      - Single <video> element reused for all transitions at z-index 2.
      - Preloads next transition while user reads current slide.
      - Seamless: video opacity stays 0 until canplay fires (first frame
        decoded = current slide pixel-perfect match); at onended the next
        slide is made active beneath the video (last frame = next slide),
        then the video is hidden. Zero black frames.
    """
    slides = deck.slides
    n      = len(slides)
    title  = deck.meta.title
    accent = (tokens.colors.accent or "#F59E0B") if tokens else "#F59E0B"

    # -- Slide divs (all in DOM, opacity controls visibility) -----------------
    slide_divs = []
    for i, slide in enumerate(slides):
        active = " active" if i == 0 else ""
        slide_divs.append(
            '<div class="layer slide{}" id="s{}">'.format(active, slide.id)
            + '<img src="display_slides/slide-{}.png" alt="">'.format(slide.id)
            + "</div>"
        )
    slides_html = "\n  ".join(slide_divs)

    # -- Dot divs -------------------------------------------------------------
    dot_divs = []
    for i, slide in enumerate(slides):
        active = " active" if i == 0 else ""
        dot_divs.append('<div class="dot{}" data-n="{}"></div>'.format(active, slide.id))
    dots_html = "\n  ".join(dot_divs)

    # -- The HTML template (NO f-strings — use PLACEHOLDER substitution) ------
    # Placeholders: {{TITLE}}, {{TOTAL}}, {{SLIDES}}, {{DOTS}}, {{ACCENT}}
    # These are replaced below with .replace(), not .format(), so JS ${} is safe.
    template = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>{{TITLE}}</title>
<style>
* { margin: 0; padding: 0; box-sizing: border-box; }

body {
  background: #000;
  width: 100vw; height: 100vh;
  overflow: hidden;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: none;
}

/* Locked 16:9 canvas — all layers live here */
#canvas {
  position: relative;
  width:  min(100vw, 100vh * (16/9));
  height: min(100vh, 100vw * (9/16));
  background: #000;
  overflow: hidden;
  flex-shrink: 0;
}

/* Every child fills the canvas pixel-perfectly */
.layer {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
}

/* Slides: opacity controls visibility — no layout repaint */
.slide        { opacity: 0; z-index: 1; }
.slide.active { opacity: 1; }
.slide img    { width: 100%; height: 100%; object-fit: cover; display: block; }

/* Single video element, always in DOM, above slides */
#trans-video {
  object-fit: cover;
  opacity: 0;
  z-index: 2;
  background: transparent;
}

/* UI chrome */
#counter {
  position: fixed; bottom: 18px; right: 20px;
  color: rgba(255,255,255,0.35); font: 12px/1 sans-serif;
  letter-spacing: 0.07em; z-index: 100; pointer-events: none;
}
#dots {
  position: fixed; bottom: 20px; left: 50%;
  transform: translateX(-50%);
  display: flex; gap: 8px; z-index: 100;
}
.dot {
  width: 7px; height: 7px; border-radius: 50%;
  background: rgba(255,255,255,0.2);
  cursor: pointer; transition: background .25s, transform .25s;
}
.dot.active { background: {{ACCENT}}; transform: scale(1.35); }
.dot:hover  { background: rgba(255,255,255,0.55); }
.nav-btn {
  position: fixed; top: 50%; transform: translateY(-50%);
  width: 44px; height: 72px;
  background: rgba(255,255,255,0.07);
  border: none; color: rgba(255,255,255,0.5);
  font-size: 22px; cursor: pointer;
  opacity: 0; transition: opacity .25s, background .2s;
  z-index: 100; border-radius: 4px;
}
body:hover .nav-btn { opacity: 1; }
.nav-btn:hover    { background: rgba(255,255,255,0.18); color: #fff; }
.nav-btn:disabled { opacity: 0 !important; }
#btn-prev { left: 10px; }
#btn-next { right: 10px; }
#skip-hint {
  position: fixed; bottom: 48px; left: 50%;
  transform: translateX(-50%);
  color: rgba(255,255,255,0.35); font: 11px/1 sans-serif;
  letter-spacing: .12em; text-transform: uppercase;
  opacity: 0; transition: opacity .3s;
  z-index: 100; pointer-events: none;
}
#skip-hint.show { opacity: 1; }
#cursor {
  position: fixed; width: 9px; height: 9px; border-radius: 50%;
  background: {{ACCENT}}; opacity: .7;
  pointer-events: none; z-index: 9999;
  transform: translate(-50%,-50%);
  transition: width .12s, height .12s;
}
</style>
</head>
<body>

<div id="cursor"></div>

<div id="canvas">
  {{SLIDES}}
  <video id="trans-video" class="layer" playsinline preload="auto"></video>
</div>

<div id="dots">
  {{DOTS}}
</div>
<div id="counter">1 / {{TOTAL}}</div>
<div id="skip-hint">space · → to skip</div>
<button class="nav-btn" id="btn-prev">&#8249;</button>
<button class="nav-btn" id="btn-next">&#8250;</button>

<script>
'use strict';

const TOTAL   = {{TOTAL}};
const videoEl = document.getElementById('trans-video');
const hint    = document.getElementById('skip-hint');
const counter = document.getElementById('counter');
const btnPrev = document.getElementById('btn-prev');
const btnNext = document.getElementById('btn-next');
const cursor  = document.getElementById('cursor');

let cur  = 1;
let busy = false;

// Wire up dot clicks
document.querySelectorAll('.dot').forEach(d => {
  d.addEventListener('click', () => { if (!busy) jumpTo(+d.dataset.n); });
});

function updateUI() {
  counter.textContent = cur + ' / ' + TOTAL;
  document.querySelectorAll('.dot').forEach((d, i) => {
    d.classList.toggle('active', i + 1 === cur);
  });
  btnPrev.disabled = (cur <= 1);
  btnNext.disabled = (cur >= TOTAL);
}

function showSlide(n) {
  document.getElementById('s' + cur).classList.remove('active');
  cur = n;
  document.getElementById('s' + cur).classList.add('active');
  updateUI();
}

function bufferNext(from, to) {
  if (from < 1 || to > TOTAL) return;
  const src = videoSrc(from, to);
  if (!videoEl.src.endsWith(src)) { videoEl.src = src; videoEl.load(); }
}

function videoSrc(from, to) {
  return `transitions/slide-${from}-to-${to}.mp4`;
}

function playTransition(from, to, onDone) {
  busy = true;
  hint.classList.add('show');
  const src = videoSrc(from, to);

  videoEl.onended  = null;
  videoEl.onerror  = null;
  videoEl.oncanplay = null;

  const onError = () => { cleanupVideo(); showSlide(to); busy = false; bufferNext(to, to+1); };

  videoEl.onended = () => {
    showSlide(to);
    requestAnimationFrame(() => {
      requestAnimationFrame(() => {
        cleanupVideo(); busy = false; bufferNext(to, to+1); onDone();
      });
    });
  };
  videoEl.onerror = onError;

  const startWhenReady = () => {
    videoEl.style.opacity = '1';
    videoEl.play().catch(onError);
  };

  if (!videoEl.src.endsWith(src)) { videoEl.src = src; }
  videoEl.style.opacity = '0';

  if (videoEl.readyState >= 2) {
    startWhenReady();
  } else {
    videoEl.oncanplay = () => { videoEl.oncanplay = null; startWhenReady(); };
    if (videoEl.readyState === 0) videoEl.load();
  }
}

function cleanupVideo() {
  videoEl.style.opacity = '0';
  hint.classList.remove('show');
  videoEl.onended = null; videoEl.onerror = null; videoEl.oncanplay = null;
}

function advance() {
  if (busy)        { skip(cur + 1); return; }
  if (cur >= TOTAL) return;
  const next = cur + 1;
  playTransition(cur, next, () => {});
}

function retreat() {
  if (busy) { skip(cur); return; }
  if (cur <= 1) return;
  showSlide(cur - 1);
  bufferNext(cur - 1, cur);
}

function jumpTo(n) {
  if (n === cur || n < 1 || n > TOTAL) return;
  if (busy) skip(n);
  else { showSlide(n); bufferNext(n, n+1); }
}

function skip(targetSlide) {
  if (!busy) return;
  videoEl.pause(); cleanupVideo(); busy = false;
  if (targetSlide != null) { showSlide(targetSlide); bufferNext(targetSlide, targetSlide+1); }
}

document.addEventListener('keydown', e => {
  const fwd = e.key==='ArrowRight'||e.key===' '||e.key==='ArrowDown';
  const bck = e.key==='ArrowLeft'||e.key==='ArrowUp';
  if (fwd) { e.preventDefault(); advance(); }
  if (bck) { e.preventDefault(); retreat(); }
  if (e.key==='f'||e.key==='F') {
    if (!document.fullscreenElement) document.documentElement.requestFullscreen?.();
    else document.exitFullscreen?.();
  }
});

document.getElementById('canvas').addEventListener('click', advance);
btnPrev.addEventListener('click', e => { e.stopPropagation(); retreat(); });
btnNext.addEventListener('click', e => { e.stopPropagation(); advance(); });

document.addEventListener('mousemove', e => {
  cursor.style.left = e.clientX+'px'; cursor.style.top = e.clientY+'px';
});
document.addEventListener('mousedown', () => { cursor.style.width=cursor.style.height='15px'; });
document.addEventListener('mouseup',   () => { cursor.style.width=cursor.style.height='9px'; });

updateUI();
bufferNext(1, 2);
</script>
</body>
</html>"""

    html = (template
            .replace("{{TITLE}}",  title)
            .replace("{{TOTAL}}",  str(n))
            .replace("{{SLIDES}}", slides_html)
            .replace("{{DOTS}}",   dots_html)
            .replace("{{ACCENT}}", accent))

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(html, encoding="utf-8")
    return output_path
