# Portfolio copy — status and open items

**What this file is.** `Great-Bucket/podium-coach` is an independent copy of
`00Zero/podium-coach` (Adam Burgh's repo), not a GitHub fork. This file records what
is settled about that copy and what is still open. Written 2026-09-17.

**We went with an independent copy over a GitHub fork** because a fork carries a
permanent "forked from" line that frames the work as derivative. The cost is that the
two repos can silently diverge, which a fork would have made visible — accepted
deliberately.

## Stamp

| Thing | Value | Checked |
|---|---|---|
| `origin` (Adam) `main` | `1906ca3` | 2026-09-17 |
| `portfolio` (Great-Bucket) `main` | `1906ca3` | 2026-09-17 |
| Branches on both | `main`, `adam/audio` `96f87da`, `reed/server` `e31dfbb` | 2026-09-17 |
| Commits on `main` | 28 | 2026-09-17 |
| Authorship | 19 Adam Burgh <adam.burgh@gmail.com>, 9 devbox <dev@789ismine.com> | 2026-09-17 |
| Visibility | `Great-Bucket` private; `00Zero` **public since 2026-09-12** | 2026-09-17 |

Adam has agreed to the independent copy. It stays **private** for now.

All three branches were pushed 2026-09-17 over HTTPS, because the 1Password SSH agent
cannot sign from an agent session — see `canon/reference/deployment-patterns.md` §8 in
dev-central. Every SHA matches Adam's repo exactly.

## Open items

### 1. Security review before this could ever go public

A briefing document for a reviewing agent exists and is still accurate against
`1906ca3`. A first-pass scan found `.env` never committed, zero hits for eight
credential prefix patterns across every blob on every ref, and no transcripts, images
or video in history. The contents of `docs/`, `CLAUDE.md` and `server/static/*.html`
have not been read by anyone.

**The framing that matters:** Adam's copy has been public since 2026-09-12. If a
reviewer finds a live credential, that credential is **already exposed** and must be
**rotated, not merely deleted from history**. This is not a preventative review.

### 2. Commit identity — unresolved

The 9 non-Adam commits are authored `devbox <dev@789ismine.com>`. GitHub attributes
commits by **email address, never by author name**, so whether these link to the
`Great-Bucket` profile depends entirely on whether that address is a verified email on
the account. This could not be checked from an agent session — the `gh` token lacks
the `user` scope.

Only matters once someone other than Reed can see the repo.

**We would go with adding and verifying the address at github.com/settings/emails over
rewriting the commits**, because verification links all 9 commits retroactively without
altering a single SHA, whereas a rewrite changes every SHA after the first rewritten
commit and permanently breaks comparison with Adam's copy.

### 3. License — deferred

No LICENSE or COPYING file exists in either repo, so default copyright applies: all
rights reserved. Deferred deliberately, no option chosen yet.

**This is Adam's call as much as Reed's**, given the 19/9 authorship split.

### 4. README credit — not written

The original plan called for a README section naming Adam Burgh as co-author and
linking `https://github.com/00Zero/podium-coach` as the original. Not written, pending
Reed's say-so, because it would be the first commit whose *content* diverges from
Adam's history.

Note the README already reads "by Reed O'Beirne and Adam Burgh" in its opening section;
what is missing is an explicit credit block and a link back to the original repo.

## Related

- The concept video built from this project was finished and published to Vimeo
  2026-09-17. Its source media lives outside this repo, under
  `My-General-Tasks_<account>/podium-coach_20260912-hackathon_video-media/`.
