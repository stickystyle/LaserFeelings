# Missing Features in dm_textual.py vs dm_cli.py

## High-Priority Gaps

### 1. **Narration Display** ❌
**Status**: NOT IMPLEMENTED in Textual UI

The CLI displays full narration workflow:
- Character actions with directives (dm_cli.py:862)
- Formatted dice roll suggestions (dm_cli.py:416)
- Character reactions in narrative form (dm_cli.py:900-912)

**Textual Status**: Only shows placeholder logs, missing structured display.

---

### 2. **Dice Roll Handling - Multiple Mechanisms** ⚠️ PARTIALLY IMPLEMENTED

#### A. Character-Suggested Rolls (Using Lasers & Feelings mechanics)
**CLI Has**: `_execute_character_suggested_roll()` (dm_cli.py:1067-1165)
- Extracts task_type, prepared/expert/helping flags from action_dict
- Loads character number from config
- Calls `roll_lasers_feelings()`
- Displays LASER FEELINGS special results with GM questions

**Textual Status**: Only shows "accept/override/success/fail" prompts, doesn't execute the roll itself

#### B. DM Override Rolls
**CLI Has**: `/roll <dice>` command support (dm_cli.py:620-657)
- Parses custom dice notation (e.g., "2d6+3")
- Uses `roll_dice()` function
- Displays individual rolls and total

**Textual Status**: Partially implemented - accepts "override <number>" but only for 1-6 values, not full dice notation

#### C. LASER FEELINGS Outcomes
**CLI Has**:
- Detection of LASER FEELINGS condition (dm_cli.py:1187-1197)
- Prompts DM for answer to character's question (dm_cli.py:1201-1229)
- `_display_lasers_feelings_result()` (dm_cli.py:1167-1199)
- Passes `laser_feelings_result` to orchestrator

**Textual Status**: NOT IMPLEMENTED - no special handling for LASER FEELINGS outcomes

---

### 3. **Dice Roll Suggestion Display** ⚠️ PARTIALLY IMPLEMENTED

**CLI Has** - `format_dice_suggestion()` (dm_cli.py:350-416):
```
  Dice Roll Suggestion:
  - Task Type: Lasers (logic/tech)
  - Prepared: ✓ "Found some tools lying around"
  - Expert: ✓ "Studied mechanical systems"
  - Helping Zara-7: ✓ "Can pick the lock while you hold the door"
  - Suggested Roll: 3d6 Lasers
```

**Textual Status**:
- `show_roll_suggestion()` exists but only shows basic info (dm_textual.py:183-218)
- Missing: prepared/expert/helping breakdown
- Missing: task_type explanation (logic/tech vs social/emotion)

---

### 4. **Session State Loading** ❌ NOT IMPLEMENTED

**CLI Has**:
- `_load_character_names()` (dm_cli.py:953-989) - loads character configs from disk
- `_load_agent_to_character_mapping()` (dm_cli.py:991-1023) - builds agent→character lookup
- Character ID resolution throughout the UI

**Textual Status**:
- `_character_names` dict exists but is never populated
- Would cause "Unknown" character names throughout the UI

---

### 5. **Command Input Validation** ⚠️ PARTIALLY IMPLEMENTED

**CLI Has**:
- Phase validation in `_is_command_valid_for_phase()` (dm_cli.py:703-724)
- Command suggestions on error (dm_cli.py:1283-1290)
- Specific error messages per phase

**Textual Status**:
- Phase validation exists but is incomplete
- `_clarification_mode` flag prevents other commands but no formal validation
- Missing helpful error messages

---

### 6. **OOC Strategic Discussion Summary** ❌ NOT IMPLEMENTED

**CLI Has** - `_display_ooc_summary()` (dm_cli.py:1231-1281):
- Displays OOC messages from completed turn
- Shows timestamps, agent names, strategic discussion
- Part of turn completion summary

**Textual Status**:
- `update_ooc_log()` polls and displays OOC messages live (dm_textual.py:616-633)
- Missing: Turn-end summary display
- Missing: Historical OOC message archive

---

### 7. **Error Recovery & Suggestions** ⚠️ MINIMAL

**CLI Has**:
- Specific recovery suggestions for each error type (dm_cli.py:1283-1290)
- Phase-aware suggestions (dm_cli.py:726-743)
- Command format hints in error messages

**Textual Status**:
- Basic error display with `[red]✗[/red]` formatting
- No specific recovery suggestions
- Generic error messages

---

### 8. **Adjudication Phase Handling** ⚠️ NEEDS WORK

**CLI Has** - Complete adjudication loop (dm_cli.py:1303-1418):
1. Display character actions with dice suggestions
2. Accept `/roll` command (with/without notation)
3. Execute character-suggested roll if bare `/roll`
4. Handle LASER FEELINGS outcomes
5. Parse DM override dice

**Textual Status**:
- Only handles suggestion acceptance/override
- Doesn't execute rolls
- Doesn't handle LASER FEELINGS
- No outcome narration support

---

### 9. **Outcome Narration Phase** ❌ NOT IMPLEMENTED

**CLI Has** - `_prompt_for_dm_input_at_phase()` handles "dm_outcome" (dm_cli.py:1555-1579):
- Special prompt for outcome narration
- Waits for DM to describe what happens
- Passes to orchestrator

**Textual Status**: NOT IMPLEMENTED - no special handling for outcome phase

---

### 10. **LASER FEELINGS Question Phase** ❌ NOT IMPLEMENTED

**CLI Has** (dm_cli.py:1581-1621):
- Detects LASER FEELINGS roll outcome
- Extracts character's question from turn result
- Prompts DM for honest answer
- Passes answer back to orchestrator

**Textual Status**: NOT IMPLEMENTED - no special handling for this phase

---

## Medium-Priority Gaps

### 11. **Status Panel Updates** ⚠️ MINIMAL

**CLI Has** - Continuous status display via phase transitions
**Textual Status**: Has `update_turn_status()` but only shows basic info - missing:
- Rich phase descriptions
- Active player count
- Current actions in progress

---

### 12. **Keyboard Shortcuts** ⚠️ INCOMPLETE

**Textual Bindings** (dm_textual.py:68-74):
- `ctrl+r` - Quick Roll (placeholder)
- `ctrl+s` - Success (placeholder)
- `ctrl+f` - Fail (placeholder)
- `ctrl+i` - Info (partially implemented)

**Status**: All are placeholders or incomplete - not wired to actual commands

---

### 13. **Input History & Editing** ❌ NOT IMPLEMENTED

**CLI Has**: Standard readline support through Python's `input()` function
**Textual Status**: Using Textual `Input` widget - would need custom history handler

---

## Low-Priority Gaps

### 14. **Session Save/Load** ❌ NOT IMPLEMENTED (both)
Referenced in CLI code (dm_cli.py:47, 52) but marked as TODO

### 15. **Help Command** ❌ NOT IMPLEMENTED (both)
Referenced in CLI code (dm_cli.py:47, 54) but marked as TODO

---

## Summary of Work Needed

| Feature | CLI | Textual | Priority |
|---------|-----|---------|----------|
| Character Actions Display | ✓ Rich | ⚠️ Basic | High |
| Dice Roll Suggestion | ✓ Detailed | ⚠️ Basic | High |
| Character-Suggested Rolls (L&F) | ✓ Full | ❌ None | High |
| DM Override Rolls | ✓ Full | ⚠️ Limited | High |
| LASER FEELINGS Handling | ✓ Full | ❌ None | High |
| Outcome Narration Phase | ✓ Full | ❌ None | High |
| Character Config Loading | ✓ Loads | ❌ None | High |
| Session Info Display | ✓ Rich | ⚠️ Basic | Medium |
| Error Recovery Suggestions | ✓ Full | ⚠️ Basic | Medium |
| OOC Summary Display | ✓ Summary | ⚠️ Live-only | Medium |
| Keyboard Shortcuts | ❌ N/A | ⚠️ Stubbed | Low |

---

## Implementation Roadmap

### Phase 1 (Critical - Turn won't work without these)
1. Load character configs in Textual (like CLI does)
2. Implement actual Lasers & Feelings dice roll in Textual
3. Add LASER FEELINGS outcome handling
4. Implement outcome narration phase

### Phase 2 (Important - UX improvements)
1. Enhance dice roll suggestion display with breakdown
2. Add error recovery suggestions
3. Implement quick keyboard shortcuts
4. Add LASER FEELINGS question handling

### Phase 3 (Nice-to-have)
1. Save/load session support
2. Help command
3. Input history/editing
4. Archive OOC messages
