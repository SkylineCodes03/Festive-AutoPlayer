     _____ __ __ __  __ __    ___  _   __  ____
  / ___// //_//\\ \\/ // /   / _ \\/ | / / / __/
  \\__ \\/ ,<    \\  // /   / // /  |/ / / _/  
 ___/ / /| |   / // /___/ // / /|  / / /___ 
/____/_/ |_|  /_//_____/____/_/ |_/ /_____/   Autoplayer 

An extremely advanced, high-precision autoplayer for Fortnite Festival. 
Originally forked from Stellite, Skyline has been heavily re-engineered to achieve near 100% "Perfect" hit rates using a sub-millisecond precision engine and a neural auto-calibration loop.

## 🚀 What's New in Skyline? (Major Upgrades)

Skyline introduces several massive performance and accuracy upgrades over traditional rhythm game autoplayers:

* **Neural Auto-Calibration:** No more guessing your hardware latency in the config file. Skyline tracks the "ghosts" of notes after they pass and micro-adjusts its own global delay by 0.5 milliseconds in real-time. It completely zeroes in on your PC's specific input lag automatically while you play.
* **Sub-Millisecond Precision Engine:** Bypasses standard Windows `time.sleep()` limitations. By forcing the Windows OS kernel to a 1ms tick rate and utilizing `time.perf_counter()` with a custom busy-wait loop, Skyline guarantees microsecond accuracy on every keystroke.
* **Velocity Smoothing (Anti-Stutter):** Instead of trusting a single-frame calculation, Skyline calculates a rolling average of note speeds. If your PC drops a frame or micro-stutters, the bot's predictive math won't be thrown off.
* **Flawless Streak Protection:** Optimized lane cooldowns (`0.10s`) and visual confidence thresholds (`0.80`) ensure the bot never accidentally double-taps a lane or hallucinates background stage lights as notes.

## ⚙️ Setup & Installation

1. Ensure you have **Python 3.10.6** installed.
2. Clone or download this repository.
3. Run `setup.bat` to install all required dependencies (including `dxcam`, `opencv-python`, etc.).
4. Set your game to **Windowed Fullscreen** (Low-quality rendering mode is recommended to stabilize background brightness).

## 🎮 Usage

1. Run `start.bat` to open the Skyline console.
2. Press **Caps Lock** to activate the bot's vision and tracking.
3. Watch it automatically dial in your perfect latency and hit 100% Perfects.
4. Press **P** (or your custom `exit_key` in the config) to close the program.

## 📝 Important Notes

* Because of the new Neural Auto-Adjust mode, **you do not need to manually change your in-game input offset**. Leave it alone and let Skyline do the math for you.
* The bot plays best on the drums track, as hold notes are currently not fully supported by the image recognition logic.
* Supported out-of-the-box for 1080p, 1440p, and 768p standard resolutions. 

## ⚠️ Disclaimer
THIS PROJECT IS FOR EDUCATIONAL PURPOSES ONLY.
