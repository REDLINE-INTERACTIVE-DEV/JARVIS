# JARVIS HUD artwork assets

Place the user's original, unmodified first reference image at `android/app/src/main/assets/jarvis_core.jpg`. The HUD loads this file without editing its pixels; all scanning rings and audio-reactive bars are drawn as separate animation layers. Keep the original image aspect ratio and do not crop, recolor, recompress, or redraw it.

The second reference image is a visual guide only, not a full-screen overlay. The radial bars are independently animated in Compose so they can respond to listening/speaking state.
