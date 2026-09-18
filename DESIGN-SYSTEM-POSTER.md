# FuturePath / AXIS — Design System Poster

## 1. Brand direction

**Product:** AXIS — Academic & X-Career Intelligent System  
**Purpose:** Giúp học sinh hiểu năng lực, khám phá nghề nghiệp và lập lộ trình phát triển có dữ liệu hỗ trợ.  
**Tone:** Tin cậy, học thuật, hiện đại, thân thiện, định hướng hành động.  
**Visual keywords:** Career clarity · Data-guided growth · Calm confidence · Human progress.

## 2. Logo and naming

- Tên sản phẩm chính: **AXIS**
- Mô tả ngắn: **Academic & X-Career Intelligent System**
- Tên nền tảng trong nội dung dài: **FuturePath**
- Viết hoa AXIS khi dùng ở tiêu đề, logo, badge và navigation.
- Không dùng Portfolio Editor như một sản phẩm riêng; CV Builder là công cụ hồ sơ chính.

## 3. Color palette

| Token | Hex | RGB | Vai trò |
|---|---|---|---|
| Deep Steel Blue | `#0B3D66` | `11, 61, 102` | Primary, CTA, link, focus |
| Deep Navy | `#061D33` | `6, 29, 51` | Hero, heading emphasis, footer |
| Ice Blue | `#EEF6FF` | `238, 246, 255` | Primary soft background |
| Cool Highlight | `#C5D8EA` | `197, 216, 234` | Border highlight, secondary accent |
| Mint | `#EAF6F8` | `234, 246, 248` | Success/support panels |
| Mint Deep | `#77C0CD` | `119, 192, 205` | Progress and positive accent |
| Canvas | `#F6F7F9` | `246, 247, 249` | Page background |
| Surface | `#FFFFFF` | `255, 255, 255` | Cards, modals, forms |
| Cream | `#FFFDFC` | `255, 253, 252` | Warm neutral sections |
| Text | `#0B1220` | `11, 18, 32` | Primary text |
| Text Soft | `#5B6770` | `91, 103, 112` | Supporting text |
| Line | `#E6E9EE` | `230, 233, 238` | Borders and separators |
| Success | `#0F9D58` | `15, 157, 88` | Valid, completed, positive |
| Error | `#B91C1C` | `185, 28, 28` | Error, destructive state |

### Recommended poster swatches

```text
████ #061D33  Deep Navy
████ #0B3D66  Deep Steel Blue
████ #77C0CD  Mint Deep
████ #C5D8EA  Cool Highlight
████ #EAF6F8  Mint
████ #EEF6FF  Ice Blue
████ #F6F7F9  Canvas
████ #FFFFFF  Surface
```

## 4. Typography

- Primary font: **Inter**
- Weights: 300, 400, 600, 700, 800, 900
- Display heading: 800–900
- Section heading: 700–800
- Body: 400
- Supporting label: 600–700
- Recommended line height:
  - Heading: `1.1–1.25`
  - Body: `1.5–1.7`
- Avoid all-caps paragraphs; reserve uppercase for short labels and badges.

## 5. Layout system

- Base spacing rhythm: 8 px.
- Spacing scale: `8 / 16 / 24 / 32 / 40 / 48 / 64`.
- Main content max width: approximately `1200–1280 px`.
- Desktop page gutters: `32–64 px`.
- Mobile page gutters: `16–20 px`.
- Card radius: `12–16 px`.
- Pill radius: `999 px`.
- Input/button minimum height: `44 px`.
- Interactive controls must preserve visible focus states.

## 6. Component composition

### Header

- White or surface background.
- AXIS mark aligned left.
- Primary navigation centered or next to the brand.
- Authentication actions aligned right.
- Mobile navigation opens as a contained panel; it must not create duplicate overlays.

### Hero

- Deep navy or ice-blue background.
- One clear headline.
- One supporting paragraph.
- One primary CTA and one secondary action.
- Use generous whitespace; avoid more than two competing visual focal points.

### Cards

- White surface on canvas background.
- Thin `#E6E9EE` border.
- Subtle shadow using low-opacity navy.
- Title, supporting metadata, then action.
- Use mint or ice-blue panels for explanatory content.

### Dashboard

- Summary metrics first.
- AXIS dimensions presented consistently as `S1–S5`.
- Progress and match scores use blue/mint accents.
- Risk or gap states use amber/red sparingly.
- Keep tables readable on mobile by stacking or horizontal scrolling.

### CV Builder

- Editor controls on a cool grey/blue workspace.
- Preview uses white paper with true A4 proportions:
  - Width: `210 mm`
  - Height: `297 mm`
- On mobile, scale the preview down without changing the internal paper ratio.
- Print mode removes editor chrome and preserves physical A4 size.

### Footer

- Deep navy background.
- Muted light text.
- Contact action remains visually prominent.
- Keep legal/support links grouped and scannable.

## 7. Interaction states

| State | Visual treatment |
|---|---|
| Default | Surface background, line border |
| Hover | Slight elevation, stronger primary border |
| Focus | Primary blue outline/ring |
| Active | Deep navy or primary fill |
| Disabled | Reduced contrast, no elevation |
| Success | Mint background, green text |
| Error | Soft red background, dark red text |
| Loading | Preserve layout size; use bounded spinner/skeleton |

## 8. Poster composition suggestion

### A3 portrait

1. Top 15%: AXIS logo, tagline, deep navy band.
2. Next 25%: mission statement and three value pillars:
   - Understand yourself.
   - Explore careers.
   - Build your path.
3. Middle 35%: palette swatches + AXIS `S1–S5` diagram.
4. Next 15%: typography, spacing and card examples.
5. Bottom 10%: FuturePath URL/QR code and short product statement.

### A4 landscape

- Left 40%: brand story, logo, typography.
- Center 30%: color palette.
- Right 30%: UI cards, buttons, dashboard and A4 CV preview.

## 9. Accessibility rules

- Maintain readable contrast for body text.
- Do not communicate status by color alone.
- Use labels and `aria-*` states for dialogs and menus.
- Keep touch targets at least `44 × 44 px`.
- Preserve keyboard focus visibility.
- Avoid placing light text on Cool Highlight without a dark text color.

## 10. Source references

- Shared theme tokens: `css/global.css`
- CV Builder tokens: `css/cv-builder-editor.css`
- Shared header: `components/header.html`
- Shared footer: `components/footer.html`
- Shared component loader: `js/components.js`
