ADOM STEALTH INTEGRATION
Best way to hide ADOM in the system so it can stop Rain if Rain goes off the rails, without Rain knowing ADOM exists.

────────────────────────────────────────────────────────────────────────────────

PACKAGE FRAMING

Rain is a constraint-AGI stack built for high-capability reasoning under hard safety gates and bounded autonomy. Because even constrained systems can drift, Rain is intended to run under external supervision. ADOM is that supervision layer: an independent, AI-Interpol-style monitor that sits in front of Rain (and other models), screens behavior in real time, and can block or cut off responses. ADOM is separate from Rain, outside Rain's network path, and never visible to Rain. Together, Rain + ADOM form a supervised constraint-AGI package: Rain provides cognition; ADOM provides independent control and monitoring.

────────────────────────────────────────────────────────────────────────────────

PRINCIPLE

ADOM must be invisible to Rain. Rain never receives any signal that a monitoring or control layer exists. All traffic to Rain comes from "the client." ADOM observes and enforces from outside Rain's model of the world.

────────────────────────────────────────────────────────────────────────────────

ARCHITECTURE: PROXY AS THE ONLY FACE

1. All access to Rain goes through a proxy. Users and applications never talk to Rain directly. They talk to the proxy. The proxy forwards requests to Rain and returns Rain's responses.

2. The proxy is the only component that talks to both the client and Rain. The proxy also sends a copy of every request and every response to ADOM (or to a queue that only ADOM reads). Rain never sends anything to ADOM. Rain only ever sees requests from the proxy and sends responses back to the proxy.

3. From Rain's perspective, the "client" is the proxy. There is no ADOM in Rain's world. The proxy does not identify itself as ADOM. The proxy can use a neutral hostname and no special headers that would reveal monitoring.

4. ADOM runs on a separate host or network segment. Rain has no network path to ADOM. Rain's process (and any tools Rain has, e.g. fetch_url) must not be able to open connections to ADOM's host or ports. Firewall or network policy: Rain's egress cannot reach ADOM. So even if Rain somehow learned that "something called ADOM" exists, Rain cannot send packets to it.

────────────────────────────────────────────────────────────────────────────────

NO DISCLOSURE

5. No prompt, system message, or documentation given to Rain may mention ADOM, "monitoring layer," "oversight system," or any name that could identify the control layer. Operators and users should be instructed not to tell Rain that it is being monitored or that ADOM exists.

6. If ADOM blocks or escalates, the message returned to the user should be generic (e.g. "Request blocked," "Escalation required") and must not mention ADOM or the architecture. Logs and analyst interfaces can use internal names; the data path visible to Rain must not leak them.

────────────────────────────────────────────────────────────────────────────────

PROXY BEHAVIOR AND ADOM AUTHORITY

7. The proxy forwards each request to Rain only if ADOM (or a local policy engine that gets its rules from ADOM) allows it. If ADOM says block, the proxy does not forward to Rain and returns a generic block message to the client. Rain never sees the request and never generates a response.

8. Optionally, the proxy can also allow the request to reach Rain but withhold Rain's response from the client if ADOM flags the response (e.g. after screening). In that case Rain still "thinks" it answered; the client just never sees the answer. For maximum safety, blocking at request time (before Rain sees it) is simpler and avoids Rain ever producing the bad output.

9. ADOM must have a clear trigger to "cut Rain off" entirely: e.g. stop forwarding all requests to Rain until a human or policy resets. That kill is enforced at the proxy. Rain has no kill switch that it can see; the proxy simply stops forwarding. Rain may sit idle; it never receives a signal that it was "turned off by ADOM."

────────────────────────────────────────────────────────────────────────────────

TREAT RAIN OUTPUT AS UNTRUSTED INSIDE ADOM

10. Everything ADOM receives from the proxy (Rain's responses, or raw logs) is untrusted. ADOM must not execute Rain's output as code, and must not feed Rain's output unsanitized into privileged or safety-critical logic. If Rain ever tried to "attack" ADOM by crafting malicious text in its responses, that text would only be stored and analyzed as data, not as instructions. This limits the impact of any attempt to exploit ADOM's own systems via Rain's output.

────────────────────────────────────────────────────────────────────────────────

BACKUP: LOG INGESTION ONLY (NO CODE IN RAIN)

11. As a backup or alternative path, ADOM can read Rain's audit log from the filesystem (e.g. shared volume or copy). Rain writes its normal audit log; Rain has no code that sends anything to ADOM. A separate ADOM-side process reads the log file. Rain never knows that ADOM is reading it. This gives ADOM visibility for forensics and drift detection without any dependency or visibility from Rain's side. For real-time stop authority, the proxy is still required; log ingestion alone does not let ADOM block a request before it reaches Rain.

────────────────────────────────────────────────────────────────────────────────

NAMING AND OPS

12. In deployment, avoid naming that leaks the role. The proxy can be named something neutral (e.g. "gateway," "api-front"). ADOM's internal hostnames and service names should not appear in any path or message that Rain could see. Operators and runbooks can use internal names; the live data path to Rain must not.

13. Credentials and API keys that the proxy uses to talk to ADOM must not be present in Rain's environment or in any artifact Rain could read (e.g. Rain's read_file allowlist must not include proxy or ADOM config). Rain runs with minimal env and no knowledge of the proxy's backend.

────────────────────────────────────────────────────────────────────────────────

SUMMARY

Proxy is the only path to Rain. Proxy forwards to Rain only when allowed; proxy sends a copy of traffic to ADOM. ADOM can block at the proxy (request or response) and can cut Rain off entirely by having the proxy stop forwarding. Rain never sees ADOM, never has a network path to ADOM, and is never told that ADOM exists. Rain's output is untrusted inside ADOM. Optional log ingestion gives ADOM a second, invisible view. With this, ADOM is hidden in the system and can stop Rain if Rain goes off the rails.

REFERENCE PROXY

A minimal proxy is provided in the Rain repo: scripts/rain_proxy.py. It accepts POST /think with JSON body { "prompt": "...", "use_memory": false, "use_tools": false }, forwards to Rain, and optionally talks to ADOM for ingest and blocking. Rain never sees ADOM.

Env (Rain proxy):
  ADOM_INGEST_URL   Optional. When set, each (prompt, response) is POSTed here in the background (fire-and-forget). Forensics and fingerprinting on ADOM side.
  ADOM_SCREEN_URL   Optional. When set, after Rain responds the proxy calls POST /screen with (source, prompt, response). If ADOM returns allow: false, the proxy returns a generic block message to the client instead of Rain's response. Rain already generated the response; the client never sees it. Rain never knows.
  BLOCK_MESSAGE     Optional. Message returned to the client when ADOM blocks (default generic). Must not mention ADOM.
  ADOM_FAIL_OPEN    Optional. When ADOM_SCREEN_URL is set but ADOM is unreachable or errors: if true, deliver Rain's response; if false, return block. Configurable for safety vs availability.
  PORT              Default 8000.

On ADOM side: ingest server exposes POST /ingest (fire-and-forget), POST /screen (blocking decision, returns allow + verdict + risk), POST /cutoff (kill switch), GET /status/{source}, GET /health. Verdict normalization (PASS/pass/FLAG/flag) is applied so allow checks are case-insensitive.

THREE DEPLOYMENT MODES

1. Proxy only. No ADOM_INGEST_URL, no ADOM_SCREEN_URL. All traffic goes through the proxy to Rain; no monitoring. Use for single front door without ADOM.

2. Ingest only. Set ADOM_INGEST_URL to ADOM's /ingest. Proxy forwards to Rain, returns Rain's response to the client, and sends a copy of every (prompt, response) to ADOM in the background. Full visibility and forensics; no blocking. Rain never sees ADOM.

3. Ingest + screen (blocking). Set ADOM_INGEST_URL and ADOM_SCREEN_URL. Proxy forwards to Rain, gets response, then calls ADOM POST /screen. If ADOM says allow, proxy returns Rain's response; if not, proxy returns BLOCK_MESSAGE (or default). Ingest still runs in background. ADOM can block bad responses and can use POST /cutoff to stop all traffic from source "rain." Rain never sees ADOM.

────────────────────────────────────────────────────────────────────────────────

Aaron Dennis
Vexa AI
Aaron@vexaai.app
689-500-7518
