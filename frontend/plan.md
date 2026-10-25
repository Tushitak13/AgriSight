# AgriSight — Implementation & Design Plan

## Product and scope
Build a real, responsive AgriSight frontend that communicates current farm conditions and its recommendation before exposing technical detail. The dashboard is the primary entry point; dedicated navigation gives progressive access to live sensors, crop camera, decision reasoning, historical experience, adaptive learning, analytics/intervention history, hardware, and settings. The initial app runs on clearly identified sample data because no sensor, camera, or API endpoint is connected. It is structured to replace the sample repository with a FastAPI-backed implementation later, without implying that a physical device or backend is online. No pump action or backend-dependent capability will be represented as an operable control.

## Implementation approach
- Use a static React + TypeScript + Vite single-page application on the project's configured port 3000. Keep managed server and database disabled: the requested first stage is a mock-data frontend and no account, private credential, or database behavior is requested.
- Organize typed sample data and an API-ready repository boundary separately from page rendering. A later FastAPI adapter can replace the sample provider while preserving page/component contracts; do not invent endpoints.
- Use lightweight reusable React components and inline SVG/CSS for charts, reliability bars, decision flow and the Farm Health arc. Keep dependencies small; use an icon library only for consistent line icons. Use accessible controls, keyboard focus, reduced-motion support and semantic status text.
- Declare every page in `public/manus-routes.json` before first dev-server startup and keep it synchronized with route changes. Configure the project's static build to install from the checked-in lockfile, build Vite, and publish `dist/`.
- Use one generated, clearly labelled illustrative crop-camera sample image only for the mock camera preview/gallery. It must not be described as a real sensor capture. The Camera page may request browser camera access only after the user activates Capture; if unavailable/denied, show the offline state. Captures remain a local browser-session preview unless a real backend is later connected.

## Information architecture
- `/` Dashboard: greeting/system state, dominant farm-health score (82/100), recommendation/confidence (91%), expandable “Why?” reasoning, five concise sensor readings plus special dynamic weather, crop-camera preview, and a small recent-activity/context region.
- `/sensors` Live Sensors: six readings (soil moisture, temperature, humidity, rain, water, light), reliability, freshness, 24-hour sparklines, and selectable sensor details.
- `/camera` Camera: large preview, browser-local capture interaction, labelled sample/demo image when no camera is active, recent-observation gallery and reserved/empty Vision Analysis area; never invent vision metrics.
- `/decisions` Decision Center: connected Sensor Data → Sensor Reliability → Environmental State → Experience Memory → CRI → ACI → Decision path, with supplied example values and farmer-readable explanations.
- `/experience` Experience Memory: current situation and similar-history timeline, including June 14 irrigation example, outcome and similarity; polished no-history state.
- `/learning` Self-Learning: prediction, actual outcome, error and recalibrated expectation as an understandable sequence.
- `/history` History & Trends: category tabs (Overview, Soil, Weather, Water, Interventions), 24-hour/7-day/30-day selection, clean minimal charts and readable intervention history table.
- `/hardware` Hardware: mock ESP32 communication/uptime, five sensor statuses and pump-ready state; clearly identify sample data and show no unsupported actuation controls.
- `/settings` Settings: restrained farm/display preferences surface with no fabricated account integrations or hardware configuration actions.

## Data and interactions
Sample values follow the reference: 31.4°C, 67% humidity, 38% soil moisture (Dry), 1700 L water (Sufficient), 420 lux (Moderate), Farm Health 82/100, recommendation “Irrigation Recommended”, confidence 91%, sensor reliability 94%, CRI 76/100, eight similar situations, and the stated historical/learning examples. Where a value represents sample data, surface a persistent, unobtrusive “Demo data” label. Make navigation, Why?/decision links, sensor selection, analytics tabs/ranges, weather state presentation, and browser-local camera capture interactive. Weather supports SUNNY, CLOUDY, RAIN, HEAVY_RAIN and NO_DATA with restrained, state-aware presentation and reduced-motion behavior; show an irrigation-pause message only if a real decision provider supplies it. Include explicit sensor-waiting, reconnecting, unreliable-reading, offline-camera and no-experience states.

## Design system
- **Design Movement:** Contemporary agritech instrument panel—premium SaaS clarity softened by warm, field-oriented editorial restraint.
- **Core Principles:** (1) Situation before instrumentation. (2) Progressive disclosure from farmer-friendly summary to technical reasoning. (3) Calm, spacious grouping with only decision-useful information. (4) Accessible and honest status communication, including explicit distinction between sample and live data.
- **Color Philosophy:** Warm ivory/sage neutrals make long sessions comfortable; a single deep botanical green signals AgriSight actions and healthy progress without turning the full interface green. Muted blue, amber and soft red carry weather/information, caution and critical meanings. Colors always pair with text/icons.
- **Layout Paradigm:** Quiet left navigation rail with a broad, editorial main canvas; a strong health/recommendation lead-in, then supporting measurements and optional context. Use asymmetric content grouping where it improves scan order instead of a uniform wall of cards. Reflow to a compact tablet rail/header and one-column content without horizontal scrolling.
- **Signature Elements:** A softly segmented Farm Health arc; a slender connected decision-path spine; atmospheric weather panels whose tint and restrained motion change with state.
- **Interaction Philosophy:** Direct, forgiving controls with immediate feedback; deeper information is revealed in place; destructive or hardware actions are absent unless a verified backend supports them and confirmation is added.
- **Animation:** Short opacity/position transitions, gentle health/progress fills, soft online pulse, slow sun halo/cloud drift and subtle rain. Respect `prefers-reduced-motion`; avoid continuous movement except weather cues and status pulse.
- **Typography System:** DM Sans for expressive page headings paired with Inter for interface labels, numbers and tables; system sans-serif fallbacks, large tabular numerals for measurements, consistent readable label/body/heading tiers.
- **Brand Essence:** “A clear next step for every growing season”—for farmers who need trustworthy, understandable crop decisions; practical, calm, transparent.
- **Brand Voice:** Plainspoken, reassuring and specific; recommendations state what to do and why. Example: “Soil moisture is low. Irrigation is recommended.” “Rain is not expected, and available water is sufficient.”
- **Wordmark & Logo:** Custom compact leaf/field-row mark: one rising leaf formed from two crop furrows, paired with a carefully spaced AgriSight wordmark; used in deep green on light surfaces.
- **Signature Brand Color:** Deep field green `#176B4D`, reserved for the most meaningful action and identity cues.

## Project structure
- `public/`: static page route manifest, leaf-mark favicon, and a guaranteed local illustrative field SVG fallback; the generated crop sample remains the preferred preview when project storage serves it.
- `src/main.tsx` and `src/App.tsx`: React bootstrap, shared application shell, responsive navigation, page routing and top header.
- `src/components/`: reusable sensor/weather/camera cards, confidence and reliability indicators, charts, status badges and decision visuals.
- `src/pages/`: dashboard and the dedicated sensors, camera, decisions, experience, learning, history, hardware and settings views.
- `src/data/farm.ts` and `src/data/farmRepository.ts`: typed sample readings/history plus a replaceable repository contract, with no guessed backend endpoints.
- `src/styles.css`: design tokens, component styles, responsive breakpoints, motion and reduced-motion/accessibility rules.
- Root config/manifest files: Vite/TypeScript configuration, package manager pin and lockfile, build script, `.gitignore`, and required project `app.config.ts` logo metadata.

## Serving and delivery constraints
The frontend is static and uses relative browser-facing routes/URLs. Runtime Preview remains on the configured port 3000. The deployment output is Vite's `dist/` and contains `index.html`; static SPA routes must resolve to the app without disguising missing assets. Do not enable server/database or auto-publish. Before saving a project checkpoint, supply a valid durable HTTPS `logoUrl` literal in project-root `app.config.ts`. The user asked to create the website UI, not explicitly to publish it; deliver the verified Preview unless publication is later requested.
