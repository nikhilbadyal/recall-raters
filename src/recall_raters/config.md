# Recall Raters Configuration Guide

Configure quantitative timer thresholds for rating buttons in Anki.

### Options

- **`easy_max_seconds`**: Maximum allowed review time (in seconds) to rate a card **Easy**. (Default: `2.0`)
- **`good_max_seconds`**: Maximum allowed review time (in seconds) to rate a card **Good**. (Default: `5.0`)
- **`hard_max_seconds`**: Maximum allowed review time (in seconds) to rate a card **Hard**. Beyond this time limit, cards are automatically demoted to **Again**. (Default: `10.0`)
- **`enable_visual_disabling`**: Dynamically grays out bottom bar rating buttons in real-time as timer passes each threshold. (Default: `true`)
- **`enable_backend_enforcement`**: Enforces time caps on keyboard shortcuts (`1`, `2`, `3`, `4`, `Space`) so ratings cannot be bypassed. (Default: `true`)
