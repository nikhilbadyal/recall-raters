# Import standard Python time module to measure exact review latency in wall-clock seconds
import time

# Import main Anki GUI application window object
from aqt import mw

# Import Anki GUI hook manager to subscribe to reviewer events
from aqt import gui_hooks

# Global variable storing the system epoch timestamp when the current card question appeared
card_start_time = 0.0

# Global variable storing the epoch timestamp when the user clicked 'Show Answer'
answer_reveal_time = 0.0

def get_config():
    """
    Retrieves user configuration from Anki's Add-on manager with fail-safe defaults.
    Ensures the add-on never crashes if user config keys are missing or malformed.
    """
    # Fetch configuration dictionary from Anki addon manager using current module name
    config = mw.addonManager.getConfig(__name__) if mw and mw.addonManager else {}
    
    # Return dictionary merged with robust fallback default threshold values
    return {
        # Maximum seconds allowed to select 'Easy' (Default: 2s)
        "easy_max_seconds": int(config.get("easy_max_seconds", 2)) if config else 2,
        # Maximum seconds allowed to select 'Good' (Default: 5s)
        "good_max_seconds": int(config.get("good_max_seconds", 5)) if config else 5,
        # Maximum seconds allowed to select 'Hard' (Default: 10s)
        "hard_max_seconds": int(config.get("hard_max_seconds", 10)) if config else 10,
        # Whether to enable real-time JavaScript visual button disabling in bottom webview
        "enable_visual_disabling": bool(config.get("enable_visual_disabling", True)) if config else True,
        # Whether to enforce backend time caps on rating shortcut keypresses
        "enable_backend_enforcement": bool(config.get("enable_backend_enforcement", True)) if config else True,
    }

def on_show_question(card):
    """
    Hook handler triggered when Anki renders a new card question.
    Records the precise start timestamp and starts the live ticking timer on the Question View screen.
    """
    global card_start_time, answer_reveal_time
    # Capture current Unix timestamp in seconds with millisecond precision
    card_start_time = time.time()
    answer_reveal_time = 0.0

    # Retrieve configuration values for time thresholds and visual features
    config = get_config()
    
    # If visual disabling feature is turned off in config, skip JS injection
    if not config["enable_visual_disabling"]:
        return

    # Extract threshold limits from configuration
    easy_limit = config["easy_max_seconds"]
    good_limit = config["good_max_seconds"]
    hard_limit = config["hard_max_seconds"]

    # Construct JavaScript payload to run live timer on Question View screen
    js_code = f"""
    (function() {{
        // Record precise timestamp when question view started in JS epoch milliseconds
        window.cardStartTime = Date.now();

        // Clear existing interval timer if running from previous card
        if (window.recallRatersTimer) {{
            clearInterval(window.recallRatersTimer);
        }}

        // Helper function to render a minimal, native-styled live timer badge
        function renderCustomTimerBadge(elapsedSec, easyLimit, goodLimit, hardLimit) {{
            var badge = document.getElementById("recall-raters-timer-badge");
            if (!badge) {{
                badge = document.createElement("div");
                badge.id = "recall-raters-timer-badge";
                badge.style.cssText = `
                    display: inline-flex;
                    align-items: center;
                    justify-content: center;
                    padding: 3px 10px;
                    margin: 6px auto 2px auto;
                    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
                    font-size: 12px;
                    font-weight: 500;
                    color: #a1a1aa;
                    background: rgba(255, 255, 255, 0.06);
                    border: 1px solid rgba(255, 255, 255, 0.12);
                    border-radius: 12px;
                    user-select: none;
                    vertical-align: middle;
                `;
                
                // Locate container next to 'Show Answer' button or in middle/bottom bar
                var targetContainer = document.querySelector("#middle") || document.querySelector(".stat") || document.body;
                if (targetContainer) {{
                    targetContainer.appendChild(badge);
                }}
            }}

            var secs = Math.floor(elapsedSec);
            
            // Format subtle non-flashy text label matching native theme
            if (elapsedSec <= {easy_limit}) {{
                badge.textContent = secs + "s (Easy)";
                badge.style.color = "#a1a1aa";
            }} else if (elapsedSec <= {good_limit}) {{
                badge.textContent = secs + "s (Good)";
                badge.style.color = "#a1a1aa";
            }} else if (elapsedSec <= {hard_limit}) {{
                badge.textContent = secs + "s (Hard)";
                badge.style.color = "#a1a1aa";
            }} else {{
                badge.textContent = secs + "s (Again)";
                badge.style.color = "#f87171";
            }}
        }}

        // Function to update Question screen live timer
        function updateQuestionTimer() {{
            var elapsedSec = (Date.now() - window.cardStartTime) / 1000;
            renderCustomTimerBadge(elapsedSec, {easy_limit}, {good_limit}, {hard_limit});
        }}

        // Run immediate update pass when question appears
        updateQuestionTimer();
        
        // Register repeating timer interval every 100 milliseconds for live ticking
        window.recallRatersTimer = setInterval(updateQuestionTimer, 100);
    }})();
    """
    # Clean up any lingering badge from top QA webview
    cleanup_top_webview()
    # Safely execute JavaScript strictly inside bottom bar webview
    eval_in_bottom_bar(js_code)

def cleanup_top_webview():
    """
    Removes any custom timer badge element from the top QA webview (mw.reviewer.web)
    to ensure the badge never appears near the question text.
    """
    if mw and hasattr(mw, "reviewer") and mw.reviewer and hasattr(mw.reviewer, "web") and mw.reviewer.web:
        mw.reviewer.web.eval("""
            (function() {
                var el = document.getElementById("recall-raters-timer-badge");
                if (el) { el.remove(); }
            })();
        """)

def eval_in_bottom_bar(js_code):
    """
    Executes JavaScript strictly inside the bottom bar webview (mw.bottomWeb),
    ensuring elements (like the timer badge) render ONLY in the bottom toolbar container.
    """
    if not mw:
        return

    # 1. Evaluate on main bottomWeb (bottom bar webview in Anki Qt)
    if hasattr(mw, "bottomWeb") and mw.bottomWeb:
        mw.bottomWeb.eval(js_code)
        return

    # 2. Evaluate on reviewer.bottomWeb if present
    if hasattr(mw, "reviewer") and mw.reviewer and hasattr(mw.reviewer, "bottomWeb") and mw.reviewer.bottomWeb:
        mw.reviewer.bottomWeb.eval(js_code)
        return

    # 3. Evaluate on legacy reviewer.bottom_bar.web if present
    if hasattr(mw, "reviewer") and mw.reviewer and hasattr(mw.reviewer, "bottom_bar") and mw.reviewer.bottom_bar:
        if hasattr(mw.reviewer.bottom_bar, "web") and mw.reviewer.bottom_bar.web:
            mw.reviewer.bottom_bar.web.eval(js_code)
            return

def on_show_answer(card):
    """
    Hook handler triggered when the user reveals the card answer.
    Stops the live timer, freezes the recall latency badge, and locks allowed rating buttons.
    """
    global card_start_time, answer_reveal_time
    answer_reveal_time = time.time()
    
    # Retrieve configuration values for time thresholds and visual features
    config = get_config()
    
    # If visual button disabling is turned off in config, skip JS injection
    if not config["enable_visual_disabling"]:
        return

    # Calculate exact recall latency (in seconds) spent before clicking 'Show Answer'
    recall_latency = max(0.0, answer_reveal_time - card_start_time)

    # Extract threshold limits from configuration
    easy_limit = config["easy_max_seconds"]
    good_limit = config["good_max_seconds"]
    hard_limit = config["hard_max_seconds"]

    # Construct JavaScript payload to stop live timer and freeze UI button states
    js_code = f"""
    (function() {{
        // STOP repeating interval timer so timer freezes when Show Answer is clicked
        if (window.recallRatersTimer) {{
            clearInterval(window.recallRatersTimer);
            window.recallRatersTimer = null;
        }}

        // Exact recall duration in seconds frozen at the moment Show Answer was pressed
        var frozenElapsedSec = {recall_latency};

        // Helper function to recursively query elements across standard DOM, Shadow DOM roots, and iFrames
        function queryAllDeep(selector, root) {{
            root = root || document;
            var elements = Array.from(root.querySelectorAll(selector));
            
            // Traverses shadow root boundaries on all child nodes
            var allNodes = Array.from(root.querySelectorAll("*"));
            for (var i = 0; i < allNodes.length; i++) {{
                if (allNodes[i].shadowRoot) {{
                    elements = elements.concat(queryAllDeep(selector, allNodes[i].shadowRoot));
                }}
            }}
            return elements;
        }}

        // Helper function to locate answer buttons using deep DOM, Shadow DOM, data attributes, and text
        function findAnswerButtons() {{
            var result = {{ again: null, hard: null, good: null, easy: null }};
            
            // Query all button candidate elements deep across Shadow DOM and iFrames
            var candidates = queryAllDeep("button, .ansbtn, [role='button'], a.btn, [data-ease]");
            
            // Scan candidates for data-ease attributes, IDs, or visible text
            for (var i = 0; i < candidates.length; i++) {{
                var el = candidates[i];
                var easeAttr = el.getAttribute("data-ease") || el.dataset.ease || el.id || "";
                var text = (el.innerText || el.textContent || "").trim().toLowerCase();
                
                if (!result.again && (easeAttr === "1" || easeAttr === "ease1" || text.includes("again") || text === "1")) result.again = el;
                if (!result.hard  && (easeAttr === "2" || easeAttr === "ease2" || text.includes("hard")  || text === "2")) result.hard  = el;
                if (!result.good  && (easeAttr === "3" || easeAttr === "ease3" || text.includes("good")  || text === "3")) result.good  = el;
                if (!result.easy  && (easeAttr === "4" || easeAttr === "ease4" || text.includes("easy")  || text === "4")) result.easy  = el;
            }}
            
            return result;
        }}

        // Helper function to apply disabled visual state, CSS !important properties, and capture-phase event listeners
        function setButtonDisabled(btn, disabled) {{
            if (!btn) return;
            
            // Attach capture-phase click and pointer event interceptor to button once
            if (!btn.__recallRatersInterceptor) {{
                btn.__recallRatersInterceptor = true;
                var interceptor = function(e) {{
                    if (btn.getAttribute("data-recall-raters-disabled") === "true") {{
                        e.preventDefault();
                        e.stopPropagation();
                        e.stopImmediatePropagation();
                        return false;
                    }}
                }};
                btn.addEventListener("click", interceptor, true);
                btn.addEventListener("mousedown", interceptor, true);
                btn.addEventListener("pointerdown", interceptor, true);
            }}
            
            if (disabled) {{
                btn.disabled = true;
                btn.setAttribute("disabled", "true");
                btn.setAttribute("data-recall-raters-disabled", "true");
                btn.style.setProperty("opacity", "0.15", "important");
                btn.style.setProperty("filter", "grayscale(100%)", "important");
                btn.style.setProperty("pointer-events", "none", "important");
                btn.style.setProperty("cursor", "not-allowed", "important");
                if (btn.parentElement) {{
                    btn.parentElement.style.setProperty("pointer-events", "none", "important");
                }}
            }} else {{
                btn.disabled = false;
                btn.removeAttribute("disabled");
                btn.removeAttribute("data-recall-raters-disabled");
                btn.style.setProperty("opacity", "1.0", "important");
                btn.style.setProperty("filter", "none", "important");
                btn.style.setProperty("pointer-events", "auto", "important");
                btn.style.setProperty("cursor", "pointer", "important");
                if (btn.parentElement) {{
                    btn.parentElement.style.setProperty("pointer-events", "auto", "important");
                }}
            }}
        }}

        // Helper function to render a minimal, native-styled live timer badge
        function renderCustomTimerBadge(elapsedSec, easyLimit, goodLimit, hardLimit) {{
            var badge = document.getElementById("recall-raters-timer-badge");
            if (!badge) {{
                badge = document.createElement("div");
                badge.id = "recall-raters-timer-badge";
                badge.style.cssText = `
                    display: inline-flex;
                    align-items: center;
                    justify-content: center;
                    padding: 3px 10px;
                    margin: 6px auto 2px auto;
                    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
                    font-size: 12px;
                    font-weight: 500;
                    color: #a1a1aa;
                    background: rgba(255, 255, 255, 0.06);
                    border: 1px solid rgba(255, 255, 255, 0.12);
                    border-radius: 12px;
                    user-select: none;
                    vertical-align: middle;
                `;
                
                // Attach badge into middle container or document body
                var targetContainer = document.querySelector("#middle") || document.querySelector(".stat") || document.body;
                if (targetContainer) {{
                    targetContainer.appendChild(badge);
                }}
            }}

            var secs = Math.floor(elapsedSec);
            
            // Format subtle non-flashy text label matching native theme
            if (elapsedSec <= easyLimit) {{
                badge.textContent = secs + "s (Easy)";
                badge.style.color = "#a1a1aa";
            }} else if (elapsedSec <= goodLimit) {{
                badge.textContent = secs + "s (Good)";
                badge.style.color = "#a1a1aa";
            }} else if (elapsedSec <= hardLimit) {{
                badge.textContent = secs + "s (Hard)";
                badge.style.color = "#a1a1aa";
            }} else {{
                badge.textContent = secs + "s (Again)";
                badge.style.color = "#f87171";
            }}
        }}

        // Render frozen timer badge at exact recall latency
        renderCustomTimerBadge(frozenElapsedSec, {easy_limit}, {good_limit}, {hard_limit});

        // Locate answer buttons and freeze allowed rating states
        var btns = findAnswerButtons();
        if (btns.easy) {{
            setButtonDisabled(btns.easy, frozenElapsedSec > {easy_limit});
        }}
        if (btns.good) {{
            setButtonDisabled(btns.good, frozenElapsedSec > {good_limit});
        }}
        if (btns.hard) {{
            setButtonDisabled(btns.hard, frozenElapsedSec > {hard_limit});
        }}
    }})();
    """
    
    # Clean up any lingering badge from top QA webview
    cleanup_top_webview()
    # Safely execute JavaScript strictly inside bottom bar webview
    eval_in_bottom_bar(js_code)

def on_will_answer_card(ease_tuple, reviewer, card):
    """
    Backend enforcement hook: Intercepts card rating submissions.
    Ensures ratings triggered via keyboard shortcuts (1, 2, 3, 4, Space) strictly obey time caps.
    
    Parameters:
      ease_tuple: Tuple (continue_answering: bool, ease: int)
      reviewer: Anki Reviewer instance
      card: Current Card instance
      
    Returns:
      Modified tuple (continue_answering, enforced_ease)
    """
    global card_start_time, answer_reveal_time
    
    # Retrieve configuration thresholds
    config = get_config()
    
    # If backend enforcement is disabled, allow original rating unchanged
    if not config["enable_backend_enforcement"]:
        return ease_tuple

    # Compute recall latency based on when Show Answer was pressed
    if answer_reveal_time > 0.0:
        elapsed = answer_reveal_time - card_start_time
    else:
        elapsed = time.time() - card_start_time
    
    # Unpack user requested ease rating (1 = Again, 2 = Hard, 3 = Good, 4 = Easy)
    original_ease = ease_tuple[1]
    enforced_ease = original_ease
    
    # Extract configured thresholds
    easy_limit = config["easy_max_seconds"]
    good_limit = config["good_max_seconds"]
    hard_limit = config["hard_max_seconds"]

    # Cancel rating submission if user presses shortcut key for a disabled ease rating
    if original_ease == 4 and elapsed > easy_limit:
        # 'Easy' (4) rating is disabled (> 2.0s latency): Block shortcut keypress completely
        return (False, original_ease)
    elif original_ease == 3 and elapsed > good_limit:
        # 'Good' (3) rating is disabled (> 5.0s latency): Block shortcut keypress completely
        return (False, original_ease)
    elif original_ease == 2 and elapsed > hard_limit:
        # 'Hard' (2) rating is disabled (> 10.0s latency): Block shortcut keypress completely
        return (False, original_ease)

    # Allowed rating: Permit card answering with requested rating
    return (True, original_ease)

# Import Qt GUI widget modules for custom settings dialog
from aqt.qt import (
    QDialog,
    QVBoxLayout,
    QFormLayout,
    QSpinBox,
    QCheckBox,
    QLabel,
    QDialogButtonBox,
)

def show_config_dialog():
    """
    Displays a graphical PyQt Settings dialog allowing the user to configure custom time thresholds
    using natural whole numbers (integers: 2s, 5s, 10s) and feature toggles.
    """
    if not mw:
        return

    # Retrieve current active configuration dictionary
    config = get_config()

    # Instantiate QDialog parented to Anki main window
    dialog = QDialog(mw)
    dialog.setWindowTitle("Recall Raters Settings")
    dialog.setMinimumWidth(380)

    layout = QVBoxLayout()
    form_layout = QFormLayout()

    # Easy Max Seconds SpinBox input control (integer natural numbers)
    easy_spin = QSpinBox()
    easy_spin.setRange(1, 300)
    easy_spin.setSingleStep(1)
    easy_spin.setSuffix(" s")
    easy_spin.setValue(int(config["easy_max_seconds"]))
    form_layout.addRow(QLabel("Easy Max Time (sec):"), easy_spin)

    # Good Max Seconds SpinBox input control (integer natural numbers)
    good_spin = QSpinBox()
    good_spin.setRange(1, 300)
    good_spin.setSingleStep(1)
    good_spin.setSuffix(" s")
    good_spin.setValue(int(config["good_max_seconds"]))
    form_layout.addRow(QLabel("Good Max Time (sec):"), good_spin)

    # Hard Max Seconds SpinBox input control (integer natural numbers)
    hard_spin = QSpinBox()
    hard_spin.setRange(1, 300)
    hard_spin.setSingleStep(1)
    hard_spin.setSuffix(" s")
    hard_spin.setValue(int(config["hard_max_seconds"]))
    form_layout.addRow(QLabel("Hard Max Time (sec):"), hard_spin)

    # Feature Toggles Checkboxes
    visual_check = QCheckBox("Enable visual button disabling")
    visual_check.setChecked(config["enable_visual_disabling"])
    form_layout.addRow(visual_check)

    backend_check = QCheckBox("Enable backend shortcut enforcement")
    backend_check.setChecked(config["enable_backend_enforcement"])
    form_layout.addRow(backend_check)

    layout.addLayout(form_layout)

    # Qt5 / Qt6 compatible QDialogButtonBox setup
    try:
        save_flag = QDialogButtonBox.StandardButton.Save
        cancel_flag = QDialogButtonBox.StandardButton.Cancel
    except AttributeError:
        save_flag = QDialogButtonBox.Save
        cancel_flag = QDialogButtonBox.Cancel

    button_box = QDialogButtonBox(save_flag | cancel_flag)
    button_box.accepted.connect(dialog.accept)
    button_box.rejected.connect(dialog.reject)
    layout.addWidget(button_box)

    dialog.setLayout(layout)

    # If user clicks Save, write updated configuration to Anki Add-on Manager
    if dialog.exec():
        new_config = {
            "easy_max_seconds": int(easy_spin.value()),
            "good_max_seconds": int(good_spin.value()),
            "hard_max_seconds": int(hard_spin.value()),
            "enable_visual_disabling": bool(visual_check.isChecked()),
            "enable_backend_enforcement": bool(backend_check.isChecked()),
        }
        mw.addonManager.writeConfig(__name__, new_config)

# Register hook to capture when card question is rendered
gui_hooks.reviewer_did_show_question.append(on_show_question)

# Register hook to capture when card answer is rendered
gui_hooks.reviewer_did_show_answer.append(on_show_answer)

# Register hook to intercept card rating submission before state update
gui_hooks.reviewer_will_answer_card.append(on_will_answer_card)

# Register custom GUI config action in Anki Add-on Manager
if mw and hasattr(mw, "addonManager") and mw.addonManager:
    mw.addonManager.setConfigAction(__name__, show_config_dialog)

# Add menu action under Anki's main 'Tools' menu
if mw and hasattr(mw, "form") and hasattr(mw.form, "menuTools"):
    action = mw.form.menuTools.addAction("Recall Raters Settings...")
    action.triggered.connect(show_config_dialog)
