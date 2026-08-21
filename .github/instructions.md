This project is a DIY weather station based on a Raspberry Pi with a touchscreen and various sensors. It also has a web interface for remote access and control. It then expanded to be a full fledged weather website. The web PWA can built as and android app with capacitor because it also ships a widget. Web sytling always uses tailwindcss with DaisyUI components.

Folder structure:
- src/waqd: Common Python code for the backend mainly the weather component.
- src/waqd_assets: Assets for the project, such as images, icons
- src/waqd_station: Code for the kiosk mode, which is the main mode for the device. Uses htmx and alpine.js with jinja templates, backend is written in Python with FastAPI/uvicorn
- src/waqd_website: Code for the web view, which is the main mode for the mobile app. /ui contains frontend in Vue,js with ts. /ui/android contains the capacitor code for building the android app. Backend is written in Python with FastAPI/uvicorn, but it is only used for the API and not for rendering the frontend.