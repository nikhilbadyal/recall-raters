# ⏱️ Recall Raters - Anki Timer-Based Ease Disabler

Anki add-on designed to eliminate self-deception during flashcard reviews. **Recall Raters** dynamically disables rating buttons (**Easy**, **Good**, **Hard**, **Again**) in real-time as your review timer ticks and enforces backend time caps to prevent cheating via keyboard shortcuts.

Ideal for high-density competitive exams (**UPSC**, **USMLE/NEET-PG**, **Law**, **Languages**) where rapid, reflex-level factual retrieval is mandatory.

---

## 🎯 Quantitative Rating Matrix

Recall Raters enforces a strict, objective, latency-based rating framework:

| Rating | Time Threshold | Allowed Action | Behavioral Meaning |
| :---: | :---: | :--- | :--- |
| **`Easy`** | **0.0s – 2.0s** | All buttons active (**Easy**, **Good**, **Hard**, **Again**) | Instant, reflex-level recall. |
| **`Good`** | **2.0s – 5.0s** | **Good**, **Hard**, **Again** (**Easy** disabled) | Smooth, confident recall without hesitation. |
| **`Hard`** | **5.0s – 10.0s** | **Hard**, **Again** (**Easy** & **Good** disabled) | Correct recall, but required noticeable effort/strain. |
| **`Again`** | **> 10.0s** | **Again** only (All other buttons disabled) | **Fail.** Memory trace is too slow for exam speed. |

```
 0s ------------ 2s ------------ 5s ------------ 10s ------------>
[     EASY      ][     GOOD     ][     HARD     ][    AGAIN    ]
    (< 2s)          (2s - 5s)       (5s - 10s)       (> 10s or Wrong)
```

---

## ✨ Features

- **Live UI Button Disabling:** Buttons in Anki's Reviewer bottom webview automatically gray out and disable interaction in real-time as the timer progresses.
- **Backend Anti-Cheat Enforcement:** Prevents bypassing rules using keyboard shortcuts (`1`, `2`, `3`, `4`, `Space`). Any rating higher than the allowed time threshold is automatically demoted.
- **Fully Configurable:** Easily tweak time limits (`easy_max_seconds`, `good_max_seconds`, `hard_max_seconds`) from Anki's standard **Add-on Configuration** dialog.
- **Anki 2.1+ & FSRS Compatible:** Built using native Anki Python `gui_hooks` and compatible with both classic SM-2 and modern FSRS schedulers.

---

## 📦 Installation Guide

### Option 1: Direct Folder Installation (Manual)
1. Open **Anki**.
2. Go to **Tools** ➔ **Add-ons** (or press `Ctrl+Shift+A` / `Cmd+Shift+A`).
3. Click **View Files** at the bottom right to open Anki's `addons21` directory.
4. Create a new folder named `recall_raters`.
5. Copy all files from `src/recall_raters/` into `addons21/recall_raters/`:
   - `__init__.py`
   - `manifest.json`
   - `config.json`
   - `config.md`
6. Restart Anki.

---

### Option 2: Install via `.ankiaddon` Package
1. Download the latest `recall_raters.ankiaddon` from the [GitHub Releases](../../releases) tab.
2. In Anki, go to **Tools** ➔ **Add-ons**.
3. Drag and drop the `recall_raters.ankiaddon` file into the Add-ons window (or click **Install from file...**).
4. Restart Anki.

---

## ⚙️ Configuration

To adjust time thresholds:
1. In Anki, go to **Tools** ➔ **Add-ons**.
2. Select **Recall Raters - Timer-Based Ease Disabler**.
3. Click **Config** at the bottom right.
4. Edit the JSON values as needed and click **OK**:

```json
{
  "easy_max_seconds": 2.0,
  "good_max_seconds": 5.0,
  "hard_max_seconds": 10.0,
  "enable_visual_disabling": true,
  "enable_backend_enforcement": true
}
```

---

## 🛠️ Building & Auto-Installing

To build the `.ankiaddon` package from source and optionally auto-install it to your local Anki application:

```bash
# Clone the repository
git clone https://github.com/nikhil/recall-raters.git
cd recall-raters

# 1. Build the .ankiaddon package only
python3 scripts/build_addon.py

# 2. Build, kill running Anki instance, and auto-install
python3 scripts/build_addon.py --install

# 3. Build & install without killing running Anki instance
python3 scripts/build_addon.py --install --no-kill

# 3. Build AND install to a custom target directory
python3 scripts/build_addon.py --install-dir "/Users/nikhil/Library/Application Support/Anki2/addons21"
```

The compiled package will be saved in `dist/recall_raters.ankiaddon`, and `--install` / `--install-dir` will automatically copy the add-on files to your Anki `addons21` directory.

---

## 🤖 CI/CD Workflow

The repository includes pre-configured GitHub Actions workflows:
- **`build-release.yml`**: Automatically builds the `.ankiaddon` archive on every push, creates GitHub Releases on version tags (e.g. `v1.0.0`), and automatically publishes to **AnkiWeb**.
  - **Required Secrets**:
    - `ANKIWEB_USERNAME`: Your AnkiWeb account username/email.
    - `ANKIWEB_PASSWORD`: Your AnkiWeb account password.
  - **Optional Variables / Secrets**:
    - `ANKIWEB_ADDON_ID`: The numeric code assigned by AnkiWeb after the first upload (set this to update the existing add-on instead of creating a duplicate).
- **`lint.yml`**: Runs `flake8` static code analysis to enforce clean Python syntax.

---

## 📄 License

Distributed under the [MIT License](LICENSE).
