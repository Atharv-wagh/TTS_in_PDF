# 🎧 ZenReader: High-Velocity PDF reading Engine

![Python](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white)
![AI Integration](https://img.shields.io/badge/Edge_TTS-0078D4?style=for-the-badge&logo=microsoft&logoColor=white)
![Status](https://img.shields.io/badge/Status-MVP_Live-success?style=for-the-badge)

## 🚀 The Vision
**ZenReader** is a lightweight, asynchronous text-to-speech (TTS) pipeline engineered to transform dense, static PDF documents into dynamic, auto-advancing audio streams. 

Built to act as a catalyst for **target-oriented, high-intensity burst-work**, ZenReader allows users to tear through massive technical documents, engineering syllabi, and competitive exam materials completely hands-free. By eliminating visual fatigue, it keeps the user locked in a state of deep focus.

---

## ⚡ Core Architecture
The system operates as an intelligent relay between raw file data and an asynchronous audio engine, relying on three distinct mechanical pillars:

1. **📄 Document Parsing:** Systematically strips complex visual formatting from PDFs to extract raw, uncorrupted string data.
2. **🔪 Data Chunking:** Utilizes delimiter-based logic to segment massive blocks of text into sequential, digestible sentence arrays.
3. **🗣️ Asynchronous Relay:** Feeds indexed arrays into a local/Edge TTS engine, waiting for precise audio generation and playback before automatically triggering the subsequent line.

---

## 🛠️ The Tech Stack
* **Core Logic:** Python
* **Audio Engine:** Edge TTS / Local Inference
* **Deployment:** Standalone Executable (PyInstaller)

---

## 🎯 Next Targets (Roadmap)
- [ ] **UI/UX Overhaul:** Integrate a sleek, cinematic front-end interface utilizing modern component libraries.
- [ ] **AI Summarization:** Pipe extracted text through an LLM to generate instant chapter summaries before audio playback.
- [ ] **Cloud Sync:** Implement Supabase backend logic to save user progress and audio preferences across sessions.

---
*Architected and developed by Atharv Wagh.*
