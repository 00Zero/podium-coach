# Git workflow for two people and four hours

## Branches

- `main` — always runnable. Both merge into it.
- `adam/audio` — Adam: `audio/`, `config/`, `recap/`, `demo/`, `README.md`, `docs/`.
- `reed/server` — Reed: `server/` (API, `/audience`, `/presenter`, cue loop, scoring).

Name = owner/area. Not feature names, not dates.

## The rule that matters: merge when something works, not at the end

"Merge at the end" is how a two-person hackathon ends with two working halves and one broken whole at 3:20. Instead: every time a step works — the stub server logs an event, the phone posts a frame, the transcript prints — merge to `main` right then. Small merges of disjoint directories never conflict. One big merge at 3:00 will.

```
git checkout main && git pull
git merge adam/audio          # or reed/server
git push
git checkout adam/audio       # back to work
git merge main                # pick up the other person's latest
```

## Directory ownership

Nobody edits the other's directory without saying so first. The only shared files are `docs/CONTRACT.md` and `config/cues.json`; changes to those are announced out loud.

## Conflicts

If one happens, it's in a shared file. Take the other person's version, re-apply your change on top, don't argue with the diff.

## Commits

Small, often, plain messages: "audio: chunked mic transcription posting events". Never commit `.env`; `.env.example` is the template.
