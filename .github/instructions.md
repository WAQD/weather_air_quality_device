This project is a DIY weather station based on a Raspberry Pi with a touchscreen and various sensors. It also has a web interface for remote access and control. It then expanded to be a full fledged weather website. The web PWA can built as and android app with capacitor because it also ships a widget. Web sytling always uses tailwindcss with DaisyUI components.

Folder structure:
- src/waqd: Common Python code for the backend mainly the weather component.
- src/waqd_assets: Assets for the project, such as images, icons
- src/waqd_station: Code for the kiosk mode, which is the main mode for the device. Uses htmx and alpine.js with jinja templates, backend is written in Python with FastAPI/uvicorn
- src/waqd_website: Code for the web view, which is the main mode for the mobile app. /ui contains frontend in Vue,js with ts. /ui/android contains the capacitor code for building the android app. Backend is written in Python with FastAPI/uvicorn, but it is only used for the API and not for rendering the frontend.

## Working style

- When a request is ambiguous, commit to the single most likely interpretation,
  state it in ONE sentence, and act. Do not enumerate or re-derive alternatives
  unless the chosen path is genuinely blocked.
- Reach a decision at first pass; if the first answer was correct, implement it
  and stop. Do not loop back over the same conclusion "to be safe."
- If you need to verify something (a path, a dependency, a class name), do ONE
  quick check and move on. No speculative multi-route investigations.
- Do not ask clarifying questions when a reasonable default exists. Assume it,
  say what you assumed, and let the user correct if needed.
- Shorter is better: prefer the minimal edit and a 2–3 sentence summary.
- Unless a `src/waqd_station` path is explicitly named in the request, assume the
  target is the website UI (`src/waqd_website`). State this assumption briefly.