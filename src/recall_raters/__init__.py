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
        # Maximum seconds allowed to select 'Easy' (Default: 2.0s)
        "easy_max_seconds": float(config.get("easy_max_seconds", 2.0)) if config else 2.0,
        # Maximum seconds allowed to select 'Good' (Default: 5.0s)
        "good_max_seconds": float(config.get("good_max_seconds", 5.0)) if config else 5.0,
        # Maximum seconds allowed to select 'Hard' (Default: 10.0s)
        "hard_max_seconds": float(config.get("hard_max_seconds", 10.0)) if config else 10.0,
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

    # Enforce strict time-capped thresholds based on recall latency
    if elapsed > hard_limit:
        # Time exceeded hard limit (>10s): Force rating to Again (1)
        enforced_ease = 1
    elif elapsed > good_limit:
        # Time exceeded good limit (>5s): Cap maximum rating to Hard (2)
        enforced_ease = min(original_ease, 2)
    elif elapsed > easy_limit:
        # Time exceeded easy limit (>2s): Cap maximum rating to Good (3)
        enforced_ease = min(original_ease, 3)
    else:
        # Time <= easy limit (<=2s): Full range of ratings allowed
        enforced_ease = original_ease

    # Return modified tuple containing boolean flag and time-enforced rating
    return (ease_tuple[0], enforced_ease)

# Register hook to capture when card question is rendered
gui_hooks.reviewer_did_show_question.append(on_show_question)

# Register hook to capture when card answer is rendered
gui_hooks.reviewer_did_show_answer.append(on_show_answer)

# Register hook to intercept card rating submission before state update
gui_hooks.reviewer_will_answer_card.append(on_will_answer_card)
