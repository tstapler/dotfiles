# Design System Reasoning Rules

The full reasoning rules behind Step 2 (Generate Design System) in `SKILL.md`. Apply
in order: PATTERN → STYLE → COLORS → TYPOGRAPHY → ANTI-PATTERNS.

**PATTERN** — Match product type to landing page pattern:
- SaaS/Tool → Feature-Rich Showcase or Interactive Product Demo
- Service/Consulting/B2B → Trust & Authority or Social Proof-Focused
- Consumer product → Hero-Centric or Conversion-Optimized
- Creative/Agency/Portfolio → Storytelling-Driven or Minimal & Direct
- Simple app/MVP → Minimal & Direct

**STYLE** — Match to industry (apply `style-match` rule from §4):
- Wellness / Beauty / Spa → Soft UI Evolution, Neumorphism
- SaaS / Tech / AI → Glassmorphism, Minimalism, AI-Native UI
- Finance / Banking / Legal → Minimalism, Swiss Modernism 2.0 (no AI gradients, no neon)
- Healthcare / Medical → Accessible & Ethical, Soft UI Evolution (no dark mode)
- Gaming / Entertainment → Cyberpunk UI, Dark Mode (OLED), Vibrant & Block-based
- E-commerce / Retail → Flat Design, Claymorphism, Conversion-Optimized
- Portfolio / Creative Agency → Brutalism, Neubrutalism, Motion-Driven, Editorial Grid
- Food / Restaurant → Organic Biophilic, Skeuomorphism (warm palettes)
- Education / Children → Claymorphism, Flat Design (high contrast, friendly)
- NFT / Web3 / Crypto → Cyberpunk UI, Dark Mode, Aurora UI

**COLORS** — Apply `color-semantic` rule from §6 (industry mood):
- Wellness: soft pinks (#E8B4B8), sage greens (#A8D5BA), warm whites, gold accents
- Finance: deep navy (#1A2B4B), cool grays, minimal accent (trust blue or green)
- Healthcare: clinical white, trust blue (#4A90D9), soft green (#6BB18E)
- Tech/SaaS (light): crisp white, electric blue (#2563EB) or violet, dark text
- Tech/SaaS (dark): near-black (#0F0F0F), neon accent (#00D4FF or #7C3AED)
- Food: warm orange (#E07A5F), cream (#FFF8F0), rich brown, appetizing reds
- Creative/Portfolio: high contrast, bold primary, minimal palette
- Always verify 4.5:1 contrast ratio for body text; NEVER use gray-on-gray

**TYPOGRAPHY** — Select Google Fonts pairing matching the style mood:
- Luxury / Wellness: Cormorant Garamond + Montserrat (elegant, calming)
- Modern SaaS / Startup: Inter + Inter (clean, scales well)
- Editorial / Blog: Playfair Display + Source Sans Pro (authoritative, readable)
- Friendly / Consumer / App: DM Sans + DM Serif Display (warm, approachable)
- Technical / Dev Tool: JetBrains Mono + Inter (precise, professional)
- Bold / Agency: Cabinet Grotesk + Satoshi (contemporary, strong)
- Children / Playful: Nunito + Nunito (rounded, friendly)

**ANTI-PATTERNS** — Apply industry-specific exclusions:
- Banking/Finance: no AI purple/pink gradients, no neon, no playful rounded corners
- Healthcare: no aggressive animations, no dark mode (accessibility concern), no neon
- Children's apps: no adult color schemes, no harsh contrast, no dense typography
- Enterprise B2B: no glassmorphism overuse, no decorative animations, no brutalism
