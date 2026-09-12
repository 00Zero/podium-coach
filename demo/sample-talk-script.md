# Sample talk script — 90 seconds, record on a phone

Read this out loud at a slightly-too-fast pace. Include the fillers as written. Do not pause during the "no pause" block. This gives the metrics something to catch.

Written to hit the four judging criteria: a working agent in a real environment (1), an environment that changes what the agent can do (2), deterministic control and failure handling (3), and a presenter who stays in control (4).

Outline for `demo/sample-outline.txt`:
```
Why this matters (0.5)
Demo (0.75)
Ask (0.25)
```

---

**[Why this matters — 0:00–0:30]**

So, um, thanks for having me. I've been to, like, thirty AI Tinkerers events, and I run my own, and I've watched hundreds of people give talks. And nobody on stage can see the clock. They can't see the room. They definitely can't hear themselves say "um" fourteen times. The organizer waves from the back and it changes nothing. And a chatbox can't help you here — not because it isn't smart, but because it wasn't in the room. So we put the agent on the podium.

**[Demo — 0:30–1:15] (no pauses, run it together)**

It coaches from the context of the room, so, um, right now it's hearing me through the Google Meet tab and a second phone is pointed at you all scoring how many of you are looking up versus on your laptops, and it shows me a countdown and one cue, six words max, because six words is all you can read at a glance while you're still talking, and here's the part I actually care about — code decides *when* to speak, not the model. Words per minute, fillers, seconds since I paused, how far off my outline I am. Those thresholds are in a config file you can open and read. The model only picks the words, and if that call fails, a fixed line shows instead, so the phone never, you know, shows me an error mid-sentence.

Nine seconds into my last run it said "Slow down. 174 wpm." It was right.

**[Ask — 1:15–1:30]**

And when I stop, it tells me which thirty seconds you actually cared about and what I was saying right then — which you, uh, cannot get from a chatbox, because it requires having been here. So the ask is simple. If you give talks, try it. If you organize events, put a phone on the podium. And if you're a judge, this is the part where you lean in. Thanks.
