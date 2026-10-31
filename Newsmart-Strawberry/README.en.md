# Tomato Greenhouse Smart Control Platform

## What It Is

An AI-powered smart control platform purpose-built for tomato greenhouse cultivation. It connects to air sensors, soil sensors, and actuators inside the greenhouse, allowing AI agents to analyze real-time environmental data, make autonomous control decisions, and directly operate hardware. The platform covers the complete cultivation workflow — from environmental monitoring and growth tracking to maturity analysis and harvest dispatch — helping greenhouse managers achieve precise, automated tomato production.

## What It Can Do

### Real-time Environmental Monitoring and Alerting
The platform collects air temperature, humidity, CO2 concentration, light intensity, soil pH, EC value, and NPK nutrient levels in real time, automatically comparing them against optimal parameters for each growth stage. When any metric deviates from the normal range, the AI flags an alert and provides specific adjustment recommendations.

### AI-powered Equipment Control
Greenhouse actuators — fans, wet curtains, ventilation windows, circulation pumps — can be controlled manually or switched to AI mode. In AI mode, the agent auto-inspects environmental data every 60 seconds: turning on fans and wet curtains when temperature rises too high, supplementing CO2 when levels drop low, and issuing alerts when light is insufficient — achieving unattended closed-loop control.

### Full-cycle Growth Management
From flower bud differentiation, flowering, fruit expansion, and color turning to harvest, each stage has a dedicated AI sub-agent providing care recommendations. The system records growth stages, environmental changes, and farming operations for each zone, building complete growth archives.

### Maturity Scanning and Harvest Dispatch
Integrates with track-guided scanning carts that automatically scan tomato maturity across zones, counting identified fruits and maturity percentages. Managers can customize the harvest threshold; when a zone reaches it, the system automatically prompts harvest cart dispatch and generates zone-specific harvest plans.

### Global AI Assistant
A floating tomato ball sits in the bottom-right corner — click it and a chat panel slides out from the side. Ask anything anytime: "Why is Zone B temperature high?", "Which zones need harvesting today?", "What's the growth trend this week?" The AI responds based on real-time sensor data, knowledge base documents, and historical records. During responses, you can see which tools were called, which knowledge documents were consulted, and click on citations to view the original text excerpts.

### Knowledge Base RAG Retrieval
Upload tomato cultivation guides, pest control manuals, fertilization references, and other documents to build a knowledge base. The AI automatically searches relevant knowledge when answering questions, with every response citing its sources so you can trace the basis of every recommendation.

## Agent Fleet

The platform has 1 master agent and 6 specialized sub-agents:

| Agent | Role |
| --- | --- |
| Greenhouse Master | Orchestrates and dispatches questions to the right sub-agent |
| Dashboard Analyzer | Analyzes dashboard environmental data, generates daily recommendations and alerts |
| IoT Controller | Manages IoT devices; directly controls actuators in AI mode |
| Weather Analyzer | Retrieves and analyzes weather data, assesses greenhouse impact |
| Growth Advisor | Tracks growth stages, provides care and farming recommendations |
| Maturity Analyzer | Analyzes cart scan data, generates zone-specific harvest recommendations |
| Planting Advisor | Creates harvest dispatch plans and cultivation decisions |

Each page has a dropdown to switch which sub-agent governs that page. In the floating ball chat, the Greenhouse Master automatically assesses the question and delegates to the most appropriate sub-agent.

## Pages

- **Tomato Dashboard** — Greenhouse overview, environmental metric cards, daily AI recommendations
- **Smart Greenhouse IoT** — Real-time sensor data, manual/AI actuator control panel
- **Growth Archives** — Zone growth stage records, AI care recommendations
- **Maturity Center** — Cart scan records, maturity statistics, harvest recommendations
- **Harvest Dispatch** — Harvest task dispatch and execution tracking
- **AI Decision Logs** — Platform-wide AI conversation history, decision tracing

## Deployment

All services run in Docker containers. Data (databases, files, knowledge bases) is stored within the project directory — copy the folder to another machine and it works directly.

**Quick Start:**

1. Copy `.env.example` to `.env`, fill in your LLM API key and admin password
2. Run `docker compose up -d --build`
3. Open `http://localhost:5173` and sign in with the admin account

Hot-reload is enabled in development mode — code changes take effect automatically without manual restarts.
