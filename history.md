# Project History: Dekcheck Hardware Diagnostic Tool

This document provides a comprehensive overview of the Dekcheck Hardware Diagnostic Tool, its features, and implementation details to help AI assistants understand the codebase quickly.

## Project Overview
**Dekcheck** is a Windows-based desktop application designed for hardware monitoring, diagnostic analysis, and performance benchmarking. It leverages AI to provide intelligent insights into system health and performance.

## Core Features

### 1. Hardware Detection & Monitoring
- **Automatic Scan**: Detects CPU, GPU, RAM modules, and Storage drives.
- **Real-time Monitoring**: Tracks temperatures, usage percentages, and performance metrics.
- **Online Comparison**: Compares detected hardware against online benchmarks to determine performance tiers (e.g., Entry, Mid, High, Ultra).

### 2. AI Intelligence (Dual-Provider Support)
- **Providers**: Integrated with both **Google Gemini** (Free Tier: `gemini-2.0-flash`) and **Amazon Nova**.
- **Factory Pattern**: Uses an `AI Factory` to switch between providers seamlessly without changing consumer code.
- **Capabilities**:
    - **System Analysis**: Provides expert summaries and ratings based on hardware specs.
    - **Log Intelligence**: Analyzes Windows Event Logs to identify hardware failures vs. software instability.
    - **Sensor Log Analysis**: Interprets HWiNFO64 CSV logs to find thermal throttling or voltage anomalies.
    - **Benchmark Interpretation**: Converts raw text from Novabench or UserBenchmark into structured health reports.

### 3. Diagnostics & Maintenance
- **Issue Detection**: Identifies critical system issues and warnings.
- **Automated Fixes**: One-click solutions for common problems (e.g., DNS flushing, Explorer restart, Drive optimization, Temporary file cleaning).
- **Tool Integration**: Direct integration with HWiNFO64 for advanced sensor monitoring.

### 4. Benchmarking
- **Integrated Launchers**: Support for launching and tracking Novabench and UserBenchmark.
- **Smart Fallback**: If a tool like Novabench is not installed, the app provides a direct download link and instructions to the user.

## Technical Implementation

### Architecture
The project follows a modular structure:
- `main.py`: Entry point and main window coordination.
- `config.py`: Centralized configuration (API keys, paths, theme settings).
- `gui/`: Contains tab-based UI components (7 tabs — see below).
    - `main_window.py`: 7-tab sidebar navigation matching modern dark design.
    - `dashboard_tab.py`: Hardware overview and monitoring.
    - `diagnostics_tab.py`: Issue detection and fixes.
    - `benchmark_tab.py`: Performance testing and AI analysis.
    - `utilities_tab.py`: **NEW** — Grid of 48+ one-click tools with search & category filter.
    - `network_tab.py`: **NEW** — Network monitoring, DNS benchmark, quick fixes.
    - `health_tab.py`: **NEW** — System health score (A-F grade) with 5 real categories.
    - `settings_tab.py`: AI provider config, theme, accent colors.
- `modules/`: Core logic engines:
    - `hardware_detector.py`: WMI and psutil wrappers.
    - `scoring_system.py`: Logic for performance ranking.
    - `gemini_analyzer.py` / `nova_analyzer.py`: AI provider implementations.
    - `ai_factory.py`: Provider selection logic.
    - `diagnostic_engine.py`: Issue detection and automated fix execution.
- `utilities/`: **NEW** — Plugin-style utility modules (48 real Windows tools):
    - `__init__.py`: Central registry, category map, search/run helpers.
    - `cleaner.py`: 9 tools (temp files, recycle bin, RAM, browser cache, logs, prefetch, WinSxS, shader cache, downloads).
    - `repair.py`: 9 tools (SFC, DISM, CHKDSK, registry, BSOD dumps, DLLs, explorer, hosts, update repair).
    - `network.py`: 8 tools (DNS flush, IP reset, Wi-Fi passwords, network reset, DNS bench, proxy, ping, ports).
    - `security.py`: 8 tools (telemetry, bloatware, privacy, permissions, firewall, defender, autorun, smartscreen).
    - `performance.py`: 8 tools (startup manager, power plan, game mode, CPU unpark, visual FX, SysMain, pagefile, game bar).
    - `sysinfo.py`: 6 tools (installed apps, drivers, license, hardware summary, uptime, BIOS).
    - `drivers.py`: 5 tools (outdated drivers, export list, unsigned check, problem devices, WU update).
    - `power.py`: 5 tools (battery report, energy report, power plans, ultimate plan, sleep study).
    - `windows.py`: 7 tools (icon cache, search index, store fix, taskbar fix, time sync, notifications, discovery).
    - `storage.py`: 6 tools (SMART health, partitions, large files, folder analysis, SSD TRIM, volume health).
    - `accessibility.py`: 6 tools (high contrast, cursor size, text scaling, narrator, night light, magnifier).
    - `processes.py`: 6 tools (kill top CPU hog, memory hogs, CPU hogs, kill zombies, kill browsers, task manager).
    - `services.py`: 6 tools (restart audio, print spooler, windows update, bluetooth, explorer, failed services).
    - `customization.py`: 6 tools (dark mode, light mode, show hidden, show extensions, taskbar left/center).
    - `gaming.py`: 6 tools (dxdiag, clear dx cache, toggle hags, game bar presence, disable fso, stop xbox services).
    - `deep_maintenance.py`: 14 tools (rebuild wmi, clear wer, deep reset wu, reregister dlls, clear events, backup reg, restore reg, fix assoc, perf counters, reset gpo, clear clip, clear spooler, optimize mft, fix wmi).
    - `browser_opt.py`: 10 tools (chrome/edge/firefox cache, edge bg, deep tcp reset, reset proxy, block cookies, optimize mtu, clear ext policies, clean hosts).
    - `advanced_hardware.py`: 14 tools (dead pixel, key tester, mouse fix, reset usb, calibrate disp, pnp cache, restart gfx, eject drives, reset bt, audio fix, test mic, scan hw, disable com, thermal report).
    - `privacy_deep.py`: 10 tools (disable loc, ad id, feedback, timeline, bg apps, cam, mic, clear defender, ransomware prot, offline rootkit).
    - `context_menu.py`: 11 tools (rm cast, rm 3d, rm share, add takeown, add cmd, add copy, long paths, no last access, del empty folders, icon layouts, rebuild thumbs).
    - `advanced_tweaks.py`: 15 tools (god mode, no lock screen, no startup sound, verbose boot, no fast boot, force hiber, no aero shake, no cortana, no driver up, rm bloat, reinstall apps, no ink, clr taskbar, reset action, clr vol).
- `utils/`: Helper functions (logging, unit conversion, file management).

### Tech Stack
- **Language**: Python 3.x
- **GUI**: `CustomTkinter` (Modern Dark/Light themed UI with 7-tab sidebar, live monitoring).
- **APIs**: Google Generative AI (Gemini), Amazon Nova API.
- **Libraries**: `wmi`, `psutil`, `py-cpuinfo`, `GPUtil`, `requests`, `beautifulsoup4`, `Pillow`.

### Design Patterns
- **Factory Pattern**: Used for AI analyzers (`get_analyzer()`).
- **Plugin-style Utilities**: Each utility category is a separate module with a standardized `{id, name, desc, category, icon, color, run}` dict pattern. Total: **175 utilities** across **22 categories**.
- **Singleton-like Config**: Global `config.py` managed across the session.
- **Threaded Execution**: Long-running scans, AI calls, utility runs, and live monitoring all execute in background threads.
- **Color Blending**: `_blend_color()` helper produces valid 6-digit hex by alpha-blending against dark background (Tkinter doesn't support RGBA hex).
- **Sub-tab Pattern**: Diagnostics and Network tabs use switchable sub-tab views within a single tab container.

## Recent Major Changes
1. **Phase 3: Diagnostics Overhaul + Benchmark** (Latest): Diagnostics now has 3 sub-tabs (Scan/Quick Tools/Advanced), Benchmark has built-in CPU/RAM/Disk stress tests.
2. **Phase 2: Dashboard + Settings Redesign**: Live metrics (CPU/RAM/Disk/Net), rolling 60s chart, health ring, accent color picker, user profile selector.
3. **Phase 1: GUI Restructure**: 7-tab sidebar, Utilities Hub (77 tools), Network Suite, Health Score tab.
4. **77 Real Windows Utilities**: All tools execute real subprocess/registry/WMI commands — no simulated data.
5. **Gemini Integration**: Google Gemini as primary AI alternative to Amazon Nova.
6. **Settings Overhaul**: AI provider switching, accent color picker, alert thresholds, automation toggles.
7. **Novabench UX**: Browser-based download fallback instead of bundled installer.
8. **AI Factory**: Central factory for provider-agnostic AI calls.

