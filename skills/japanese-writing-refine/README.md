# japanese-writing-refine

Proofread and refine existing Japanese prose. Reviews of AI-like phrasing in completed novels are limited to vocabulary, connectives and sentence endings.

## Install

From this component's root:

```sh
mkdir -p ~/.agents/skills
cp -R skills/japanese-writing-refine ~/.agents/skills/
```

For other Agent Skills clients, copy the skill into that client's designated directory. Restart the client if discovery has not refreshed.

## Use

- Request proofreading to check typos, grammar and inconsistent notation.
- Request refinement to improve readability while preserving meaning and facts.
- Request a limited completed-novel review to check only the three categories above.

Other requested novel-refinement processes come first; they are optional dependencies. This skill does not detect authorship, conduct external fact checking or independently audit arguments. Meaning-changing decisions remain with the writer.

License: [MIT](LICENSE).
