# Last Carriage

A small browser game. Midnight; a blizzard has stopped the night train. You and three AIs share a table, each playing a
historical figure (you're assigned one at random). Three are AIs, one is human: you. Blend in.

- **Introductions**, then **4 rounds**. Each round everyone, in turn, says who they believe the human is and why. Then each
  passenger asks the person next to them (clockwise round the table) one yes-or-no question.
- After round 4 everyone votes. If you get the most votes outright, you're unmasked. A tie at the top means you escape.
- Each AI is independent: a separate API call with its own persona, temperament and private notes that no one else sees.
  They share only what is said aloud. Their private notes are shown at the end.
- Drag (or use the arrow keys) to look around the carriage and out of the windows.

## Run

It needs a local web server (ES modules don't load from `file://`):

```
cd train-game
python3 -m http.server 8000
```

Open http://localhost:8000, paste your OpenAI API key and board. The model defaults to `gpt-6-luna`; you can change the
model and the base URL (any OpenAI-compatible Chat Completions endpoint) under *Advanced*. The key goes only from your browser to that URL,
and is saved in `localStorage` only if you tick *Remember*. *Demo without a key* plays with canned lines.
