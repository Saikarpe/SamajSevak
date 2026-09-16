# SamajSevak — AI-Powered Public Grievance Intelligence Platform

> **Hack2Ignite · Problem Statement AI-04:** Design an AI-powered public grievance analysis and resolution recommendation platform.

## Problem

Municipal grievance cells receive thousands of free-text complaints across channels (web, app, WhatsApp, call centre). Today they are triaged manually: routing is inconsistent, urgent life-safety issues wait in the same queue as minor ones, duplicate complaints waste field visits, and nobody notices a cluster of complaints pointing at one systemic problem until it's too late.

## Planned approach

- Classify each complaint into a category and route it to the right department with an SLA.
- Score priority in an explainable way (not a black box) using risk keywords, vulnerable groups, sentiment and duplicate clustering.
- Recommend a resolution plan from department SOPs and what has worked for similar complaints before.
- Detect emerging hotspots (e.g. a disease outbreak) before they become crises.
- Give citizens a transparent tracking experience and officers a prioritised, actionable queue.

## Planned tech stack

- **Backend:** Python, FastAPI, scikit-learn (classification + similarity), SQLite
- **Frontend:** React, Vite
- **Optional:** Gemini/OpenAI for citizen-reply drafting

*(This README will be filled in with setup instructions, architecture and screenshots as the build progresses.)*
