---
name: director-deck
version: 0.1.0
description: "Turn a text prompt into a polished PPTX with AI-generated images and Veo 3.1 video transitions"
agents:
  - agents/ghost-deck-writer.md
  - agents/slide-architect.md
  - agents/visual-director.md
  - agents/transition-director.md
  - agents/deck-stitcher.md
tools:
  - director_deck/html_renderer.py
  - director_deck/pptx_builder.py
  - director_deck/screenshot_tool.py
  - director_deck/pptx_stitcher.py
recipes:
  - recipes/director-deck.yaml
external_deps:
  - amplifier-module-tool-openai-images
  - veo (Amplifier built-in)
---

# Director Deck

An Amplifier bundle that transforms a plain-text prompt into a polished PowerPoint deck
with AI-generated images and Veo 3.1 video transitions between slides.

## Workflow

```
prompt → ghost-deck-writer → slide-architect → [Gate 1: content & identity review]
       → visual-director → slide-architect (enriched) → [Gate 2: visual review]
       → transition-director → [Gate 3: transition review]
       → deck-stitcher → final_deck.pptx
```

## Usage

```bash
amplifier recipe run recipes/director-deck.yaml \
  --context prompt="Series A pitch for a B2B SaaS devtools company"
```

## Run Directory Structure

Each run is isolated under `./runs/<date>-<slug>/`:

```
runs/2026-04-22-series-a-pitch/
├── DESIGN.md            # Visual identity (Google Stitch DESIGN.md spec)
├── slide_deck.json      # Slide content — shared contract between all agents
├── deck_wireframe.html
├── deck_wireframe.pptx
├── deck_enriched.html
├── deck_enriched.pptx
├── assets/              # Generated content images and backdrops
├── keyframes/           # Playwright PNG screenshots (Veo input)
├── transitions/         # Veo 3.1 MP4 clips
└── final_deck.pptx
```
