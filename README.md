# Director Deck

An Amplifier bundle that transforms a text prompt — or an existing PPTX or HTML presentation — into a polished PowerPoint deck with AI-generated slide images and cinematic video transitions between every slide.

Inspired by [Dan Shapiro's DirectorDeck process](https://x.com/danshapiro).

## What It Makes

Each run produces:

- **`final_deck.pptx`** — A 19-slide file for a 10-content-slide deck: content slides interleaved with video transition slides, auto-advancing in Presenter mode
- **`deck_live.html`** — An interactive HTML player with the same slide + transition experience in the browser

---

## How It Works

```
Input (text / PPTX / HTML)
  │
  ▼
ghost-deck-writer     →  slide_deck.json + DESIGN.md
  │
slide-architect       →  wireframe HTML + PPTX
  │
  ▼  [Gate 1: Review wireframe]
  │
visual-director       →  GPT Image 2 renders per slide (2560×1440, 16:9)
  │
  ▼  [Gate 2: Review images]
  │
transition-director   →  Veo 3.1 cinematic transitions between slides
  │
  ▼  [Gate 3: Review transitions]
  │
deck-stitcher         →  final_deck.pptx + deck_live.html
```

Three human approval gates let you review and iterate at each stage before committing to the next.

---

## Three Input Modes

| Mode | What you provide | What happens |
|---|---|---|
| **Text prompt** | A plain description of your presentation | Ghost-deck-writer creates 8–12 slides from scratch with full design identity |
| **PPTX file** | An existing `.pptx` | Content, speaker notes, theme colors, and fonts are extracted; slide count is preserved |
| **HTML presentation** | A URL or local file (Reveal.js, Director Deck HTML, etc.) | Playwright screenshots each slide; DOM text is extracted; slide count is preserved |

---

## Installation

**Prerequisites:**

- Python 3.11+
- Playwright Chromium (for HTML capture and wireframe screenshots)
- An Amplifier setup with `gpt-image` and `veo` modules

`ffmpeg` and `ffprobe` are pulled in transitively via the `static-ffmpeg`
Python package — no system install required. If a system `ffmpeg` is already
on `PATH` it takes precedence.

```bash
# Install the bundle
amplifier bundle add git+https://github.com/microsoft/director@main --app

# Install Python dependencies (includes static-ffmpeg → ffmpeg + ffprobe)
pip install director-deck

# Install Playwright browser
playwright install chromium
```

---

## Quick Start

```
Run the director-deck recipe with your input:

"Make a 10-slide deck about our Series A pitch. Focus on market opportunity,
product, and traction. Use a clean, modern blue and white palette."
```

Or in a session, invoke the recipe directly:

```yaml
# From a text prompt
recipes:
  path: director-deck:recipes/director-deck.yaml
  context:
    input_type: prompt
    user_input: "Your presentation description here"

# From an existing PPTX
recipes:
  path: director-deck:recipes/director-deck.yaml
  context:
    input_type: pptx
    input_file: /path/to/existing.pptx

# From an existing HTML presentation
recipes:
  path: director-deck:recipes/director-deck.yaml
  context:
    input_type: html
    input_file: /path/to/presentation.html
```

### Continuing a Run

If you've already generated content and want to re-run visuals and transitions from an existing run directory:

```yaml
recipes:
  path: director-deck:recipes/director-deck-continue.yaml
  context:
    run_dir: runs/2026-04-22-series-a-pitch
```

---

## Run Directory Structure

Every run lands in `runs/<date>-<slug>/`:

```
runs/2026-04-22-series-a-pitch/
├── DESIGN.md               # Visual identity: colors, typography, spacing (Google Stitch spec)
├── slide_deck.json         # Shared data contract — enriched by each pipeline stage
├── deck_wireframe.html     # Layout preview before image generation
├── deck_wireframe.pptx
├── pixel_slides/           # GPT Image 2 renders at 2560×1440
├── display_slides/         # Center-cropped to 1536×864 for PPTX
├── keyframes/              # 1536×864 Veo input frames
├── transitions_raw/        # Raw 8-second Veo clips
├── transitions/            # Post-processed: retimed, eased, no audio
├── final_deck.pptx         # Content slides + interstitial video slides
└── deck_live.html          # Interactive HTML player
```

---

## Pipeline Agents

| Agent | Responsibility |
|---|---|
| `ghost-deck-writer` | Creates slide content, speaker notes, and `DESIGN.md` visual identity. Selects a storytelling framework (answer-first, tension-resolution, progressive-discovery, etc.) and 9 possible layout types. |
| `slide-architect` | Builds wireframe HTML and PPTX previews for Gate 1 review. |
| `visual-director` | Generates 2 GPT Image 2 renders per slide — a content image and a backdrop — at 2560×1440. Can target specific slides to redo. |
| `transition-director` | Captures keyframe PNGs and drives Veo 3.1 image-to-video interpolation between each pair of slides. Makes editorial pacing decisions based on layout type pairs. |
| `deck-stitcher` | Assembles the final PPTX with interstitial video slides and runs post-processing fixes. Generates the live HTML player. |

---

## Technical Notes

### Strict 16:9 Throughout

Every image in the pipeline must be 16:9 or transitions will show a visible edge jump at 1920×1080. GPT Image 2 is called with `size: "2560x1440"` (the only 16:9 option in its enum); Pillow crops and resizes to 1536×864 for Veo input.

### Interstitial Video Slides

A 10-slide deck produces **19 PPTX slides**: 10 content slides and 9 interstitial video slides. Each video slide is a blank slide with a full-bleed MP4 embedded via `add_movie()`.

This is the only valid approach in OOXML — `<p:transition>` does not support embedded video. The `pptx_stitcher.py` module (which attempted to inject video inside transition XML) is kept for reference only and is explicitly avoided.

### PPTX Post-Processing

`pptx_fixer.py` patches four known `python-pptx` bugs after assembly:
1. `hlinkClick r:id=""` — broken click-to-play
2. `delay="indefinite"` — video doesn't autoplay
3. Shared poster frame — all video slides show the same thumbnail
4. Missing auto-advance — presenter must click manually

### Transition Easing

Veo provides 8 seconds of source material per transition. `video_processor.py` holds the first and last 0.4s at natural speed and compresses the middle to achieve smooth ease-in-out — using real Veo frames without interpolation artifacts.

### Veo Prompt Discipline

The words `presentation`, `slide`, `deck`, `infographic`, `PowerPoint`, `chart`, and `data visualization` are banned from all Veo prompts. They cause Veo to hallucinate slide-like content in intermediate frames, breaking the cinematic illusion.

---

## Project Structure

```
director/
├── bundle.md                    # Amplifier bundle manifest
├── pyproject.toml
├── agents/                      # 5 AI agent definitions
│   ├── ghost-deck-writer.md
│   ├── slide-architect.md
│   ├── visual-director.md
│   ├── transition-director.md
│   └── deck-stitcher.md
├── recipes/
│   ├── director-deck.yaml       # Main recipe (4 stages, 3 approval gates)
│   └── director-deck-continue.yaml  # Continue from existing run_dir
├── director_deck/               # Python package
│   ├── schema.py                # Pydantic v2 models (SlideDeck, Slide, DesignTokens)
│   ├── html_renderer.py         # Wireframe and live HTML generation
│   ├── pptx_builder.py          # PPTX construction
│   ├── pptx_fixer.py            # Post-processing for 4 python-pptx bugs
│   ├── screenshot_tool.py       # Playwright slide capture
│   └── video_processor.py       # ffmpeg retiming and easing
├── tests/
└── runs/                        # All generated decks land here
```

---

## Dependencies

| Dependency | Purpose |
|---|---|
| `python-pptx` | Build and modify PowerPoint files |
| `pydantic` | `slide_deck.json` schema and validation |
| `Pillow` | Image resizing and center-cropping for Veo keyframes |
| `playwright` | Headless Chromium for HTML capture and wireframe screenshots |
| `pyyaml` | `DESIGN.md` frontmatter parsing |
| `static-ffmpeg` | Ships `ffmpeg` + `ffprobe` binaries for transition clip retiming and easing — no system install required |
| GPT Image 2 (`amplifier-module-tool-gpt-image`) | Slide image generation at 2560×1440 |
| Veo 3.1 (`amplifier-module-tool-veo`) | Cinematic interpolation video between slides |
