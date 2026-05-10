# System Vital 🔬

**System Vital** is a premium, all-in-one hardware diagnostic and optimization suite built with PySide6. It combines deep hardware detection, real-time monitoring, AI-powered insights, and a comprehensive utility hub to keep your Windows system running at peak performance.

![Dashboard](docs/screenshots/Dashboard.png)

## 🚀 Features

### 📊 Advanced Dashboard
Get an instant overview of your system vitals, including CPU/GPU temperatures, RAM usage, and live hardware statistics. The dashboard provides a high-level summary of your PC's current state.

### 🩺 Intelligent Diagnostics
Run deep scans of your hardware to identify bottlenecks or potential failures. The diagnostic engine analyzes sensors, logs, and hardware specs to give you a clear picture of system health.

### 🤖 AI Chat Assistant (Multi-Provider)
Interact with a state-of-the-art AI assistant to solve complex Windows problems. Supports multiple providers including:
*   **Google Gemini 2.0**
*   **Amazon Nova**
*   **Groq (Llama 3)**
*   **NVIDIA NIM**
*   **OpenRouter**
AI Chat can analyze system logs, suggest optimizations, and even suggest specific utility tools to fix issues.

### ⚡ Professional Benchmarking
Stress test your system with dedicated benchmarks for CPU, GPU, and RAM. Compare your scores with reference data to see how your hardware stacks up against the competition.

### 🔧 Utilities Hub (177+ Tools)
A massive collection of one-click tools categorized for:
*   **Performance**: RAM cleaning, Cache clearing, Registry optimization.
*   **Services**: Manage Windows services for better speed.
*   **Advanced Tweaks**: Hidden Windows settings for power users.
*   **Accessibility**: UI enhancements and ease-of-access tools.

### ❤️ Health Score
A simplified scoring system (0-100) that evaluates your PC based on Disk Health, Thermal performance, Security status, and overall efficiency.

### 📡 Network Suite
Monitor live network traffic, ping, and connection stability. Includes tools for network optimization and troubleshooting.

## 🛠️ Module Overview

| Module | Description |
| :--- | :--- |
| `gui/` | Core PySide6 UI implementation with theme-aware styling. |
| `engine/` | Logic for AI chat integration, stress testing, and diagnostic runners. |
| `modules/` | Hardware detection, scoring systems, and online hardware comparisons. |
| `utilities/` | Implementation of 170+ system maintenance and optimization tools. |
| `benchmarks/` | Specialized scripts for CPU, GPU, and memory performance testing. |
| `utils/` | System information helpers, logging, and hardware detection wrappers. |

## 📸 Screenshots

| Dashboard | System Health |
| :---: | :---: |
| ![Dashboard](docs/screenshots/Dashboard.png) | ![System Health](docs/screenshots/System%20Health.png) |

| Utilities Hub | AI Chat Assistant |
| :---: | :---: |
| ![Utilities](docs/screenshots/Utilities.png) | ![AI Chat](docs/screenshots/AI%20Chat.png) |

| Benchmarking | Network Monitoring |
| :---: | :---: |
| ![Benchmark result](docs/screenshots/Benchmark%20result.png) | ![Network Monitering](docs/screenshots/Network%20Monitering.png) |

## ⚙️ Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/raz786786/System-Vital.git
   ```
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Run the application:
   ```bash
   python main.py
   ```

## 📄 License
This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---
*Created by Ahmed Zubair Rao, Shayan Humayun, and Muhammad Ahmad.*
