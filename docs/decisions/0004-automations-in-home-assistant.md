# 0004. Automations in Home Assistant (YAML in git), Node-RED optional

- **Status:** accepted
- **Date:** 2026-11-22

## Context

Automations can be built with Home Assistant's own automation engine (automations, scripts, scenes, blueprints) or
with **Node-RED**, a visual flow editor that connects to HA. Many users like Node-RED's flow editor for complex logic.

This repository's goals: every change is reviewable in git history, and AI agents can read and change the setup as
text.

## Decision

Build automations with **Home Assistant's built-in engine**, stored as **YAML in git**.

- Automations, scripts and scenes are readable YAML. A diff shows exactly what changed ("humidity threshold
  60 → 55"). Node-RED stores all flows in one large JSON file (`flows.json`) that includes the canvas layout, so
  its diffs are hard to read.
- AI agents write and modify HA YAML automations reliably. Node-RED's JSON is much harder for them.
- HA's editor covers most needs: a visual editor with a YAML mode, templates, scripts, scenes and blueprints.
- Remote scenarios from the Telegram bot ([0003](0003-remote-access-via-telegram-bot.md)) map naturally to **HA
  scripts**: the bot calls a script, and the logic stays in one place.

## Node-RED as an option

Add Node-RED (a container plus the
[Home Assistant nodes](https://github.com/zachowj/node-red-contrib-home-assistant-websocket)) if some logic becomes
awkward in HA: long multi-step state machines, heavy data processing, or integrations HA doesn't have.

- It **coexists** with HA automations. There's no need to move everything: keep simple automations in HA and put
  only the complex ones in Node-RED. Node-RED flows can call HA scripts and react to HA events.
- There is **no automatic converter** from HA automations to Node-RED flows. Moving an automation means rebuilding
  it as a flow (an AI agent can help, using the YAML as the spec).
- If it's added, keep `flows.json` in git anyway, and describe each flow's purpose in its notes, since the JSON diffs
  alone won't tell.
