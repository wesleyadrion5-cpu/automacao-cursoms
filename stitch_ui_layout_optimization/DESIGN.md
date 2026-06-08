---
name: Titanium Industrial Control
colors:
  surface: '#0b1326'
  surface-dim: '#0b1326'
  surface-bright: '#31394d'
  surface-container-lowest: '#060e20'
  surface-container-low: '#131b2e'
  surface-container: '#171f33'
  surface-container-high: '#222a3d'
  surface-container-highest: '#2d3449'
  on-surface: '#dae2fd'
  on-surface-variant: '#c3c6d7'
  inverse-surface: '#dae2fd'
  inverse-on-surface: '#283044'
  outline: '#8d90a0'
  outline-variant: '#434655'
  surface-tint: '#b4c5ff'
  primary: '#b4c5ff'
  on-primary: '#002a78'
  primary-container: '#2563eb'
  on-primary-container: '#eeefff'
  inverse-primary: '#0053db'
  secondary: '#ffb95f'
  on-secondary: '#472a00'
  secondary-container: '#ee9800'
  on-secondary-container: '#5b3800'
  tertiary: '#4fdbc8'
  on-tertiary: '#003731'
  tertiary-container: '#007b6e'
  on-tertiary-container: '#b1fff1'
  error: '#ffb4ab'
  on-error: '#690005'
  error-container: '#93000a'
  on-error-container: '#ffdad6'
  primary-fixed: '#dbe1ff'
  primary-fixed-dim: '#b4c5ff'
  on-primary-fixed: '#00174b'
  on-primary-fixed-variant: '#003ea8'
  secondary-fixed: '#ffddb8'
  secondary-fixed-dim: '#ffb95f'
  on-secondary-fixed: '#2a1700'
  on-secondary-fixed-variant: '#653e00'
  tertiary-fixed: '#71f8e4'
  tertiary-fixed-dim: '#4fdbc8'
  on-tertiary-fixed: '#00201c'
  on-tertiary-fixed-variant: '#005048'
  background: '#0b1326'
  on-background: '#dae2fd'
  surface-variant: '#2d3449'
typography:
  headline-lg:
    fontFamily: Space Grotesk
    fontSize: 24px
    fontWeight: '700'
    lineHeight: 32px
    letterSpacing: 0.02em
  headline-md:
    fontFamily: Space Grotesk
    fontSize: 18px
    fontWeight: '600'
    lineHeight: 24px
  body-base:
    fontFamily: Inter
    fontSize: 14px
    fontWeight: '400'
    lineHeight: 20px
  label-caps:
    fontFamily: Inter
    fontSize: 11px
    fontWeight: '700'
    lineHeight: 16px
    letterSpacing: 0.05em
  log-text:
    fontFamily: Inter
    fontSize: 13px
    fontWeight: '400'
    lineHeight: 18px
rounded:
  sm: 0.125rem
  DEFAULT: 0.25rem
  md: 0.375rem
  lg: 0.5rem
  xl: 0.75rem
  full: 9999px
spacing:
  unit: 4px
  gutter: 16px
  margin-page: 24px
  card-padding: 20px
  stack-gap: 12px
---

## Brand & Style

The design system is built for Isaura V106, a high-stakes automation environment where precision and reliability are paramount. The brand personality is **technical, authoritative, and high-performance**. It targets power users who need to monitor complex bot workflows at a glance without visual fatigue.

The visual style is **Corporate / Modern with subtle Glassmorphism**. It utilizes a deep, layered dark mode to create a "command center" aesthetic. This approach minimizes eye strain while allowing vibrant, high-contrast action colors to guide the user's eye to critical controls and status indicators. The interface feels solid and engineered, reflecting the "TITANIUM" branding.

## Colors

The palette is optimized for a low-light, high-tech environment. The core is a **Deep Navy/Charcoal base** which provides the necessary depth for layered components.

*   **Primary (Electric Blue):** Reserved for primary system actions and navigation highlights.
*   **Secondary (Amber/Orange):** Used for database actions and warnings to ensure they stand out against the blue-leaning base.
*   **Tertiary (Teal):** Used for secondary bot controls and monitoring tools.
*   **Log Area:** A pure black background (`#000000`) is used for the "Log da Isaura" section to maximize contrast with white or green mono-spaced text, ensuring technical readability.

## Typography

The typography strategy balances technical precision with modern aesthetics. **Space Grotesk** is used for headlines and branding (e.g., TITANIUM V106) to evoke a futuristic, engineered feel. **Inter** is the workhorse for the rest of the interface, chosen for its extreme legibility at small sizes and its neutral, professional tone.

The log area utilizes a slightly smaller size of Inter with increased line height to ensure dense information remains parsable. Important status labels use uppercase styling with increased letter spacing to differentiate metadata from actionable content.

## Layout & Spacing

This design system employs a **Fluid Grid with fixed sidebar constraints**. The layout is split into a narrow control sidebar (280px) and a wide, expansive dashboard area for main operations and the log output.

Spacing follows a strict 4px base unit to maintain technical alignment. Elements are grouped into high-contrast cards. The "Log da Isaura" section is anchored to the bottom of the viewport, spanning the full width of the main content area to prioritize chronological data visibility.

## Elevation & Depth

Visual hierarchy is achieved through **Tonal Layering and Low-Contrast Outlines**. 
*   **Level 0 (Canvas):** The deepest navy background.
*   **Level 1 (Cards):** Slightly lighter navy with a 1px border (`rgba(255,255,255,0.1)`) to define boundaries.
*   **Level 2 (Active Controls):** Elements that are interactive use subtle inner glows and vibrant background colors.

Shadows are used sparingly; when applied, they are highly diffused and tinted with the primary color to simulate a "glowing" tech display rather than a traditional material shadow.

## Shapes

The design system adopts a **Soft** shape language. A corner radius of 4px to 8px is standard across all containers and buttons. This creates a balance between the "hard" feel of industrial software and the "soft" user-friendly nature of modern SaaS. Buttons use a consistent 6px radius, while the main dashboard cards use 8px for a distinct container feel.

## Components

### Buttons
Buttons are high-visibility blocks. 
*   **Primary:** Solid fills using the accent colors (Blue, Orange, Teal).
*   **Secondary:** Ghost buttons with tinted borders and semi-transparent fills.
*   **Status Buttons:** Buttons that toggle (like the Start/Stop controls) use high-saturation red or green only when in a critical state change.

### Cards
Cards are the primary grouping mechanism. Each card should have a header area with a small icon and uppercase label. The background of the card should be a subtle gradient to imply depth.

### Log Area (Log da Isaura)
A dedicated, high-contrast container. It features a sticky header with status indicators. The text within the log uses a color-coded system: 
*   `Green`: Success/Active
*   `Yellow`: Warning/Processing
*   `Red`: Error/Stopped
*   `White`: General Info

### Progress Indicators
Thin, vibrant bars that span the width of their parent container, using glowing gradients to indicate active automation processes.