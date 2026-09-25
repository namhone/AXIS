# AXIS — Frontend Summary

- Project root
  - index.html
  - css/global.css
  - pages/
    - profile.html
    - assessment.html
    - development.html
    - careers.html
    - career-detail.html
    - about.html
  - backups: *.html.bak, *.html.corrupt.bak
  - export: AXIS-export.zip

- Header layout (new)
  - header.topbar (sticky white)
    - .header-brand (left): <a.brand-link> with .brand-mark + .brand-copy
    - .header-nav (center, flex:1): <a.nav-item> (icon .nav-ico + label)
    - .header-auth (right): .auth-area (id="authArea") with auth buttons / user panel

- Core CSS classes
  - :root: theme vars (colors, --accent-rgb, font import Inter)
  - .topbar, .header-brand, .header-nav, .header-auth
  - .nav-item, .nav-ico, .active, .hidden
  - .auth-area, .auth-btn, .primary-btn, .ghost-btn
  - .skill-pill (skill tags), .input-compact (forms)
  - .progress-track, .progress-fill (uses --progress)
  - .hero-card, .tool-card, .mini-panel, .user-menu, .summary-item

- JS behavior (short)
  - Auth: demo persists to localStorage key `axis.signed_in`; setSignedIn()/setSignedOut() toggle DOM and storage; authArea id used as toggle
  - Progress: elements use data-progress; JS sets CSS var `--progress` on .progress-fill; CSS reads var for width
  - Nav: .header-nav is single source; script attaches click + keyboard handlers to .nav-item, toggles .active, closes userMenu
  - Safety: scripts guarded for missing elements (null checks) after sidebar removal

- Backups & exports
  - Original backup copies: *.html.bak (pre-meta), *.html.corrupt.bak (pre-mojibake-fix)
  - Export ZIP: D:\FileCuaNam\KhoaHocKiThuat\AXIS-export.zip

---
Generated as a concise reference for UI/design QA and handoff.

