# Seamless Slide Transitions — Lessons Learned

    > What needed to be fixed to make slides, transition videos, and HTML/PPTX feel truly live.

    ---

    ## 1. All assets must share the exact same 16:9 dimensions

    **The bug:** Pixel slides were generated at `1536×1024` (3:2 aspect ratio).
    Veo transition clips were generated at 16:9. On a 1920×1080 display this created
    a **150px jump on each side** every time a transition played — visually jarring.

    **The fix:** All assets must be the same aspect ratio as the Veo output (16:9).

    ### GPT Image 2 — correct 16:9 size

    `gpt-image-2` accepts custom resolutions where both edges are multiples of 16
    and aspect ratio ≤ 3:1. The correct size for 16:9:

    ```
    size: "1536x864"   ← both multiples of 16, exactly 16÷9 = 1.777...
    ```

    **Do NOT use** `1536x1024` (that is 3:2, not 16:9).

    ### Add this rule to every image generation step:

    ```yaml
    # In the visual-director agent / generate-images recipe step:
    # ALL images — content images, backdrops, pixel slides — must be 1536x864.
    # This matches Veo's 16:9 output exactly.
    size: "1536x864"
    ```

    ---

    ## 2. Veo keyframes must be the same size as the input images

    **The bug:** If input images to Veo are a different aspect ratio than the Veo
    `aspect_ratio` parameter, Veo has to crop or letterbox the input. The first and
    last frames of the transition clip then don't visually match the slide.

    **The rule:** Veo `aspect_ratio` must match the actual pixel ratio of the input
    images. Since we use `aspect_ratio: "16:9"`, all `image_path` and
    `last_frame_path` inputs must also be 16:9 (i.e., `1536×864`).

    ---

    ## 3. HTML: slides and transition video must share the exact same bounding box

    **The bug:** The old HTML put the transition video in a full-screen overlay
    (`position: fixed; inset: 0`). The slide images were displayed with
    `object-fit: contain` inside the viewport — they had letterbox bars. The video
    filled the full screen. Click to advance = jarring size jump.

    **The fix:** A single locked 16:9 canvas that BOTH slides AND the video live
    inside. Never use a separate full-screen overlay.

    ```css
    /* THE CORRECT PATTERN */
    #canvas {
      /* Fills viewport at 16:9, letterboxes on portrait screens */
      width:  min(100vw, 100vh * (16/9));
      height: min(100vh, 100vw * (9/16));
      position: relative;
      overflow: hidden;
    }

    /* Slides and video are siblings inside the canvas */
    .slide, video {
      position: absolute;
      inset: 0;
      width: 100%;
      height: 100%;
      object-fit: cover;  /* 16:9 src in 16:9 canvas = perfect fill, zero bars */
    }
    ```

    Key points:
    - The video element is a **sibling** of the slide divs, not an overlay
    - Both use `position: absolute; inset: 0` — identical bounding box
    - `object-fit: cover` — when src and container are both 16:9, it's perfect fill
    - When the video starts playing, it occupies the same exact pixels as the slide
      that was just showing → zero visual jump

    ---

    ## 4. PPTX: `<p:transition>` does NOT support video

    **The bug:** `pptx_stitcher.py` was injecting:
    ```xml
    <p:transition>
      <p:video r:id="rVid1"/>  ← INVALID — this element does not exist in OOXML
    </p:transition>
    ```
    PowerPoint either refuses to open the file or silently ignores the transitions.

    **The fix:** Use **interstitial video slides** — one slide per transition,
    between each pair of content slides.

    ```python
    # CORRECT PPTX APPROACH
    for i in range(1, n_slides + 1):
        # Content slide: full-bleed pixel image
        s = prs.slides.add_slide(blank_layout)
        s.shapes.add_picture(slide_image, 0, 0, W, H)

        if i < n_slides:
            # Transition slide: full-screen video (black background)
            ts = prs.slides.add_slide(blank_layout)
            ts.background.fill.solid()
            ts.background.fill.fore_color.rgb = RGBColor(0, 0, 0)
            ts.shapes.add_movie(transition_mp4, 0, 0, W, H, mime_type='video/mp4')
    ```

    Result: 19-slide deck (10 content + 9 transition video slides).
    The video plays on that slide; user advances to the next content slide.
    `python-pptx` 1.0+ has `add_movie()` — no XML manipulation needed.

    ---

    ## 5. Playwright screenshot dimensions must match slide dimensions

    **Context:** When using Playwright to capture slides for Veo keyframes (original
    pipeline approach using HTML slides rather than pixel slides), the screenshot
    viewport must match the slide dimensions exactly.

    ```python
    # In screenshot_tool.py / transition-director agent
    page = browser.new_page(viewport={"width": 1536, "height": 864})  # ← 16:9
    ```

    If the viewport is 960×540 but slides and videos need to be 1536×864, there's
    a resolution mismatch. Always use the same W×H as the target image generation.

    ---

    ## 6. The pixel-slide approach vs HTML-slide approach

    The original pipeline uses Playwright to screenshot HTML slides as Veo keyframes.
    The pixel-slide approach (GPT Image → Veo) is superior because:

    - **No letterbox/rendering artifacts** — pure image, pixel-perfect
    - **Higher quality** — GPT Image 2 at 1536×864 is publication quality
    - **No CSS/font rendering** — no font loading issues in headless Chrome
    - **The image IS the slide** — what you see in HTML is what goes into Veo

    **Recommendation:** Use the pixel-slide approach for all live/cinematic decks.

    ---

    ## Rule Summary — add these to agent prompts

    ```
    DIMENSION RULES (required for seamless transitions):

    1. ALL generated images (slides, backdrops, content images) must be 1536×864
       (16:9 exact). Do NOT use 1536×1024.

    2. Veo transitions: aspect_ratio must be "16:9". image_path and last_frame_path
       must also be 16:9 images (1536×864).

    3. In HTML: slides and transition video must be children of the SAME 16:9
       container, both at position:absolute; inset:0. Never use a full-screen overlay.

    4. In PPTX: use interstitial video slides (add_movie), NOT <p:transition>.
       PowerPoint's <p:transition> does not support video elements.
    ```
    