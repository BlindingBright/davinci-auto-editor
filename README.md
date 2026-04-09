# DaVinci Auto-Editor AI 🎬🤖

**The World's Most Powerful AI-Driven Assembly Engine for DaVinci Resolve.**

Automate the tedious part of video editing. Our AI engine analyzes your A-Roll, B-Roll, and Drone footage to build a professional, beat-synced, and color-ready timeline in DaVinci Resolve in seconds.

![Logo](davinci_ai_logo_options_1775746491107.png)

## ✨ Key Features

- **AI Hook Discovery**: Automatically identifies the most "dynamic" high-energy shots and places them at the start of your video to maximize viewer retention.
- **Beat-Synced Cinema**: Uses `librosa` and `faster-whisper` to analyze music rhythm and speech density, aligning cuts perfectly to the beat.
- **Motion-Intelligent B-Roll**: Visual motion detection ensures the most active moments in your footage are prioritized.
- **Native Round-Trip Engine**: Injects native Resolve transitions (Cross Dissolves, Wipes, Slides) using an FCPXML injection architecture.
- **Cinematic VFX Polish**: Automatically applies 1.340x FPV scaling, optical flow, and intelligent audio ducking.

## 🚀 Quick Start

1. **Download the Installer**: Grab the latest `.msi` from the [Releases](https://github.com/zoest/davinci-auto-editor-ai/releases) page.
2. **Open DaVinci Resolve**: Ensure DaVinci Resolve is open and a project is active.
3. **Run the App**: 
   - Point to your A-Roll, B-Roll, and Drone footage folders.
   - Select a style (Vlog, Cinematic, or Reel).
   - Click **CONSTRUCT TIMELINE**.
4. **Relax**: Watch as the AI builds your timeline frame-by-frame.

## 🛠️ Technical Setup

The app is built using **Tauri (Rust)** for the frontend and a **Python AI Engine** for the logic.

### Prerequisites (Handled Automatically)
- The app will automatically check for and install Python 3.11 if it's missing.
- It automatically creates a localized virtual environment for dependencies like `faster-whisper` and `opencv`.

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## 📜 License

Distributed under the MIT License. See `LICENSE` for more information.
