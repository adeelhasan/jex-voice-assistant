# UX_UPLIFT.md: JEX HUD System Specs

## 1. Vision & Aesthetic
Transform JEX from a basic web interface into a high-end, **Americanized Jarvis HUD**. The design language is "Functional Futurism"—utilizing high-contrast typography, kinetic motion, and depth through transparency.

- **Theme:** "Deep Obsidian" (Dark Mode by default).
- **Core Energy:** Snappy, responsive, and omnipresent.
- **Visual Weight:** Light and "floaty" (glassmorphism), never heavy or blocky.

## 2. Style Constants (Tailwind CSS)
### Palette
- **Primary Background:** `#050505` (Deep Obsidian).
- **Primary Accent:** `Cyan-400` (`#00d2ff`) — Used for active system states, borders, and tags.
- **Warning/Status:** `Amber-400` (`#ffcc00`) — Used for alerts or secondary data.
- **Body Text:** `Slate-200` — High-legibility off-white.

### Typography
- **System Metadata:** Monospace (`JetBrains Mono` or `Roboto Mono`). Used for `[LABELS]` and timestamps.
- **Content:** Clean Sans-Serif (`Inter` or `System Sans`). Used for email bodies and thread text.

## 3. The "Jex Orb" (State Visualizer)
Replace the current emoji icons (🎤, 🧠, 🔊) with a single dynamic component: `JexOrb.jsx`. Use **Framer Motion** for state transitions.

| Agent State | Visual Behavior |
| :--- | :--- |
| **Idle** | A thin, dim cyan ring with a slow "heartbeat" pulse. |
| **Listening** | An active cyan ring that pulses. Add "jitter" if volume > 0. |
| **Thinking** | Two concentric dashed rings rotating in opposite directions. |
| **Speaking** | A solid central core expanding/contracting (simulated lung). |

## 4. The Data HUD (Right-Side Stream)
Information cards (Emails, Calendar, X.com, Weather) must be pinned to the **right side** of the screen in a vertical stack.

### Card Design (Glassmorphism)
- **Container:** `bg-white/5`, `backdrop-blur-xl`, `border-white/10`.
- **Labels:** **NO ICONS.** Use bracketed monospace tags for categorization.
- **Layout:** 300px width, right-aligned, stacked vertically.

### Data Mapping
- **Emails:** `[SYSTEM.MAIL]` (Cyan)
- **Calendar:** `[SYSTEM.SCHED]` (Cyan)
- **X Threads:** `[X.LOG]` (Cyan)
- **Weather:** `[METAR]` (Cyan)

## 5. Animation Spec (Framer Motion)
- **Entrance:** Cards must stagger in from the right (`x: 50` to `x: 0`) with a `0.05s` delay.
- **The "Scan":** A 1px horizontal cyan line should sweep down the card once upon appearance.
- **State Sync:** Visualizer states must tie directly to the `agentState` from the LiveKit `useVoiceAssistant` hook.

## 6. Implementation Instructions for AI Agent
1. **DRY Pattern:** Use a single `JexDisplayCard` component that takes `type`, `title`, and `body` as props.
2. **Layout:** Ensure the main container in `App.jsx` or your layout file uses a dark radial gradient: `radial-gradient(circle, #111 0%, #050505 100%)`.
3. **Dependencies:** Use `framer-motion` for all movement and `lucide-react` only if strictly necessary for UI controls (but avoid for data cards).
