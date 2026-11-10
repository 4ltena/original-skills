# Font stacks

Put the Latin face first, then the CJK face, then the generic family. Reversed, the Latin glyphs bundled in a CJK font override the digits and letters. Write CJK family names in English; quote any name containing a space.

## Japanese pages
```css
--font-sans: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial,
  "Hiragino Sans", "Hiragino Kaku Gothic ProN", "Noto Sans JP", "Yu Gothic UI", Meiryo, sans-serif;
--font-mono: "JetBrains Mono", "SF Mono", ui-monospace, Menlo, Consolas, "Liberation Mono", monospace;
```

## Simplified Chinese pages
Use the same Latin part, then:
`"PingFang SC", "Hiragino Sans GB", "Microsoft YaHei UI", "Microsoft YaHei", "Noto Sans CJK SC", "Noto Sans SC", "Source Han Sans CN"`

## When the brief asks for a distinctive typeface
These stacks are the system fallback and the default for product UI. A chosen display or text face goes first (Latin part), keeps this order, and falls back to the stack above. Japanese body text needs line-height of about 1.7 and no letter-spacing tricks borrowed from Latin design. Free sources: Fontshare, Google Fonts.
