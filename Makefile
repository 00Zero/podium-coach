# Podium Coach — Adam's half. `make demo` is the one that has to keep working.
PY := .venv/bin/python

.PHONY: install stub demo demo-fast mic tab recap clean hello

install:                       ## create .venv and install the audio/recap deps
	uv venv --python /usr/bin/python3 .venv
	VIRTUAL_ENV=.venv uv pip install -r audio/requirements.txt

stub:                          ## stand-in for Reed's server, port 3000
	$(PY) audio/stub_server.py

demo:                          ## replay the sample talk into PODIUM_SERVER_URL, in real time
	$(PY) demo/replay.py

demo-fast:                     ## same, as fast as Deepgram will go
	$(PY) demo/replay.py --fast

mic:                           ## live from the laptop microphone
	$(PY) audio/transcribe.py --mic --outline demo/sample-outline.txt

tab:                           ## Google Meet tab capture, then open http://localhost:3100
	$(PY) audio/chunk_server.py

recap:                         ## build recap/out/recap.html from the server's event log
	$(PY) recap/render.py

hello:                         ## prove the server is reachable before sending anything real
	curl -sS -X POST $${PODIUM_SERVER_URL:-http://localhost:3000}/events \
	  -H 'Content-Type: application/json' \
	  -d '{"type":"transcript_chunk","ts":"2026-09-12T20:00:00.000Z","payload":{"text":"hello from adam"}}'
	@echo

clean:
	rm -f events.jsonl audio/events.local.jsonl
	rm -rf recap/out __pycache__ audio/__pycache__
