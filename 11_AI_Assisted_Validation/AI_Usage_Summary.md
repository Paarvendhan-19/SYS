# AI Usage & Transparency Note

## Overview
In accordance with Hackathon rules, our team (Vetrivel, Nithiya, and Saaiprasath) utilized AI as a strict validation and formatting assistant. All architectural logic, concurrency decisions, and infrastructure choices (Redis, OCC with Jitter, Outbox) were determined by the team's engineering judgement.

## Scope of AI Assistance
1. **Simulation Script Generation:** We instructed the AI to build a multithreaded Python script using `concurrent.futures` to mathematically prove that our Redis DECR traffic-shedding logic safely handles 10,000 concurrent threads competing for 100 units.
2. **Boilerplate Formatting:** The AI assisted in cleanly formatting our Markdown files for API specifications, ADRs, and SOLID mapping into production-ready documentation.
3. **Diagram Syntax:** We defined the specific components and flow paths, and the AI generated the exact Mermaid/UML syntax required to render the diagrams accurately.

Our team takes full ownership of all code, documentation, and logic presented in this submission.
