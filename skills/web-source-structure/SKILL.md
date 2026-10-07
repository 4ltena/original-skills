---
name: web-source-structure
description: Organize source files when creating or restructuring maintained websites and web apps. Separate substantial styling and behavior from HTML using the project's existing conventions; not visual design or a performance audit.
---

# Web source structure

Inspect the existing entrypoints, framework, build commands and delivery requirements. Preserve working conventions and use the smallest useful structure; do not introduce a framework, bundler or folder hierarchy just to separate files.

For ordinary maintained pages, keep markup in HTML/templates, substantial styling in CSS files and behavior in JavaScript/TypeScript files. Link stylesheets with `<link rel="stylesheet" href="...">`; load JavaScript through the existing build pipeline or external scripts. Use `type="module"` for ES modules and `defer` for classic scripts when compatible with existing execution order. Do not put the whole application into large `<style>` and inline `<script>` blocks for delivery convenience.

Group files around real responsibilities, shared reuse and page/component boundaries. A small page may need only `index.html`, `styles.css` and `main.js`. Split further when distinct ownership, independent behavior or reuse warrants it; avoid one file per trivial function and duplicated shared styles.

Respect framework-native components, scoped styles and established CSS-in-JS conventions. A Vue/Svelte single-file component is an authored component boundary, not a reason to flatten the delivered application into one HTML file. Preserve generated bundles and edit their maintained sources instead.

Inline code is appropriate when explicitly required for standalone/offline delivery, email or constrained embedding, or justified by measured critical-path loading. Keep the exception narrow; if a maintained project needs a single-file export, preserve its separated editable sources. External files are not automatically faster: do not add request fragmentation or claim a performance gain without measurement.

When extracting existing code, preserve stylesheet order/cascade, script execution order, DOM readiness, module/global scope and event behavior. Rebase CSS `url()` paths, imports and asset references relative to their new locations; preserve deployment base paths and CSP compatibility. Avoid replacing required inline bootstrap/configuration blindly.

Verify the actual entrypoint through the intended server/build environment: assets load with correct paths/MIME types, no console/import errors, and affected styling/interactions still work. Browser ES modules need appropriate HTTP serving; a successful `file://` preview is not equivalent. Run existing relevant checks and inspect the built output when it is the deliverable.

References: [MDN CSS](https://developer.mozilla.org/en-US/docs/Learn_web_development/Core/Styling_basics/Getting_started), [MDN JavaScript modules](https://developer.mozilla.org/en-US/docs/Web/JavaScript/Guide/Modules), [web.dev resource loading](https://web.dev/learn/performance/optimize-resource-loading).
