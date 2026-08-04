# 🎧 TTS_in_PDF: High Velocity Audio Engine

[![Download Executable](https://img.shields.io/badge/Download-TTS_in_PDF--v2.47.exe-success?style=for-the-badge&logo=windows&logoColor=white)](https://github.com/Atharv-wagh/TTS_in_PDF/releases/latest)
![Python](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white)
![RAM](https://img.shields.io/badge/RAM_Usage-~1_GB-blueviolet?style=for-the-badge)


<img width="322" height="62" alt="Screenshot 2026-08-04 145848" src="https://github.com/user-attachments/assets/f2a45672-a400-4773-b58b-8d0339f80e30" />
While running the pdf reader and also the tts locally at once V/S Microsoft Edge pdf reader and tts 

## ⚡ Quick Start (No Setup Required)
Want to use TTS_in_PDF immediately without touching any code?
1. Download **[TTS_in_PDF-v1.0-Windows.zip](https://github.com/Atharv-wagh/TTS_in_PDF/releases/latest)** from the Releases section.
2. Extract the ZIP folder on your computer.
3. Double-click `TTS_in_PDF.exe` and enjoy hands-free reading!

---

## 🚀 The Vision
**TTS_in_PDF** is a lightweight, asynchronous text-to-speech (TTS) pipeline engineered to transform dense, static PDF documents into dynamic, auto-advancing audio streams. 

Built to act as a catalyst for **target-oriented, high-intensity burst-work**, TTS_in_PDF allows users to tear through massive technical documents, engineering syllabi, and competitive exam materials completely hands-free. By eliminating visual fatigue, it keeps the user locked in a state of deep focus.

---

## 📊 System Requirements & Performance
TTS_in_PDF is heavily optimized for speed and low resource consumption:
* **Memory Footprint:** Requires **~1 GB RAM** to run both the full PDF parsing engine and text-to-speech audio synthesis concurrently.
* **Operating System:** Windows 10 / 11 (64-bit).
* **Dependencies:** Self-contained executable — zero Python installation or external setup required.

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
