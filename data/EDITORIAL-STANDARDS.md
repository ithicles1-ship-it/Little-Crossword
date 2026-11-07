# Little Crossword — editorial standards (2026-11-07)

This specification protects the puzzle style and answer quality.

## Answers and shapes

- Classic is a **5-by-5 mini with exactly 5 Across and 5 Down**.
- Shape is flexible: do **not** impose a 24/25-filled-square target.
- Four-letter and five-letter answers are preferred. One or two three-letter
  answers are welcome when they produce natural crossings. They are not forbidden,
  nor is an exact 3/4/5 ratio mandated.
- Prefer familiar everyday words, natural word forms, fair references to names,
  geography and culture, and occasional recognisable specialist terms.
- Do not use technical-but-valid spellings, fragments, obscure conjugations or
  culturally narrow meanings merely to satisfy a crossing.
- No repeated answer across the 100 Classic puzzles, unless the owner explicitly
  changes this requirement.

## Clues and hints

- **Every Classic clue is individually authored**. Never ship a raw Wiktionary
  first sense or an automatic 'word begins with ...' puzzle clue.
- Clues should be brief, conversational and slightly clever. Vary definitions,
  puns, cultural references, double meanings, context and wordplay. Avoid
  mechanical repeated templates.
- The optional hint should help the solver but never reveal the whole answer.
- A clue/hint must not include its exact answer as a whole word.
- Independently validate crossword crossings, answer lengths and numbering.
- The approved clue/hint source is `data/classic-curated-fallbacks.json`.
  `data/classics100.json` is the complete verified playable snapshot.
- There are currently 1,000 distinct Classic answer words and 1,000 individually
  authored clue/hint pairs. The word list itself still has editorial-review flags
  in `data/editorial-policy.json`; specifically, some archaic, technical or
  adult terms should be replaced in a future *solution revision*.

## Publishing and progress

- Classic is a reviewed library, not a procedural daily word lottery.
- Never automatically regenerate or overwrite its answer solutions. Its
  generation workflow requires manual authorisation. Replacing any solution
  must version its progress key so old saved letters aren't misapplied.
- Keep existing iPhone native input, repeated Backspace and saved progress.

## Newsroom

- Fetch dated headlines from real publishers; each credited source must link to
  its real original article.
- Extract candidate news words from those headlines **before** choosing a grid.
- Try to construct the crossword with two independently sourced headline answers;
  if this isn't feasible, permit one actually verified headline answer.
- Fill the remaining Across/Down entries from the editorial answer-and-clue bank.
  Do not invent articles, headlines or anchor words to satisfy the grid.
- If the article-first construction fails, the old matched-existing path may be
  used only when clearly labelled as a fallback, never as 'news-first'.
- Preserve one published crossword per UK calendar date, including archived
  source links. No OpenAI API or Netlify account is required.

## QA

`node scripts/check_v13.js` tests all Classic answers, crossings and distinct
clues/hints. `python scripts/test_news_first.py` tests news-first construction
using synthetic headlines without internet or a paid API.
