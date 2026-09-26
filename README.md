#  ASCII Studio

![Python](https://img.shields.io/badge/Python-3.9+-3776AB?style=for-the-badge&logo=python&logoColor=white)
![CustomTkinter](https://img.shields.io/badge/GUI-CustomTkinter-blue?style=for-the-badge)
![License](https://img.shields.io/badge/License-MIT-green.svg?style=for-the-badge)

**ASCII Studio** is a modern, high-performance desktop application designed to convert image files into detailed ASCII art and ANSI color representations. Built with Python and CustomTkinter, it features multi-core CPU processing, customizable width scaling, terminal-style diagnostics (`afetch`), and color palette selection.

---

##  Features

- ** Multi-Core CPU Rendering:** Parallel image processing leveraging `ProcessPoolExecutor` for maximum speed.
- ** Rich Palette Select:** 10+ visual color modes including *Matrix Green*, *Full ANSI Color*, *Cyber Cyan*, *Neon Pink*, and *Amber Yellow*.
- ** Overdrive Width Mode:** Break beyond standard slider limits and specify custom render widths (e.g., 3000px+).
- ** Dark & Light Mode:** Seamless theme switching with custom title bar styling.
- ** Export Options:** Save ASCII outputs as plaintext `.txt` files or rendered high-res `.png` images.
- ** Terminal Diagnostic Mode:** Fastfetch-style (`afetch`) system specifications visualizer built into the main view.

---

##  Installation & Setup

### Prerequisites
- Python 3.9 or higher

### 1. Clone the Repository
```bash
git clone [https://github.com/2-2nm/ASCII-Studio.git](https://github.com/2-2nm/ASCII-Studio.git)
cd ASCII-Studio
