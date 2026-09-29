
# 🧊 PolarTwin-OS
### Next-Generation Digital Twin & Remote Mission Control for Antarctic Research Stations

> **Developed for the Indian Antarctic Research Stations (Bharati & Maitri)**  
> *Under the operational framework of the National Centre for Polar and Ocean Research (NCPOR)*

---

## Summary

Operating scientific research stations in Antarctica is one of the most extreme logistical and operational challenges on Earth. Stationed in sub-zero environments reaching below **-40°C** with hurricane-force winds and months of total isolation, personnel rely on life-support systems where **power failure or fuel exhaustion is an existential emergency**.

**PolarTwin-OS** is an integrated Mission Control platform and Digital Twin designed to manage, monitor, and protect remote polar infrastructure. By combining **real-time spatial 3D visualization, edge-driven predictive maintenance, low-bandwidth logistics tracking, and post-quantum cybersecurity**, PolarTwin-OS bridges the 10,000 km gap between the Antarctic ice shelf and mainland command centres in India.

---

##  The Problem We Solve

1. **Extreme Geographical Isolation:** Physical resupply or emergency intervention is impossible during polar winters. Every liter of fuel and kilowatt of power must be accounted for with absolute precision.
2. **Fragile Satellite Telemetry:** Remote stations rely on high-latency, weather-vulnerable VSAT connections. Mainland commanders frequently suffer from "telemetry blackouts" or delayed data feeds.
3. **Catastrophic Equipment Degradation:** Combined Heat & Power (CHP) units and diesel generators run 24/7. Unplanned engine seizures can compromise station heating within hours.
4. **Targeted Cyber Risks:** Critical national scientific and satellite uplink assets in polar regions face growing threats from unauthorized access and signal spoofing.

---

## Key Innovations & Core Modules

PolarTwin-OS delivers a single, cohesive command console split into five operational pillars:

```
┌────────────────────────────────────────────────────────────────────────┐
│                             POLARTWIN-OS                               │
├──────────────┬──────────────┬──────────────┬─────────────┬─────────────┤
│  1. OVERVIEW │  2. 3D TWIN  │ 3. LOGISTICS │ 4. SECURITY │ 5. PREDICT  │
│  Live Power  │ Spatial CAD  │ Vessel AIS & │ Zero-Trust  │  Edge AI    │
│  & Life Grid │ Visualizer   │ Field SOS    │  & Quantum  │ Maintenance │
└──────────────┴──────────────┴──────────────┴─────────────┴─────────────┘
```

### 1.  Live Station Telemetry & Utility Grid
* **Multi-Station Oversight:** Instant toggle between **Bharati Station** (Larsemann Hills) and **Maitri Station** (Schirmacher Oasis).
* **Power & Thermal Health:** Live status gauges for multi-unit generator banks, battery distribution by sector (BioLab, Habitation, CookHouse, Warehouse), and total station load balancing.
* **Dynamic Alerting:** Color-coded micro-status alerts that immediately bubble up critical anomalies before failures cascade.

### 2.  Interactive 3D Spatial Digital Twin
* **True-to-Scale Station Architecture:** Interactive WebGL 3D models of Bharati and Maitri stations built directly into the browser.
* **Spatial Situational Awareness:** Command personnel can rotate, zoom, and visually pinpoint sensor placements, structural modules, and equipment bays without requiring heavy desktop CAD software.

### 3.  Polar Logistics, Fuel Autonomy & Expedition Safety
* **Vessel Tracking (AIS):** Tracks polar supply vessels (e.g., *RRS Sir David Attenborough*) in real time, calculating Distance-to-Station, ETA, and drift variance against authorized polar corridors.
* **Field Team SOS Monitoring:** Real-time satellite pings for out-station glaciology and meteorology expedition teams, tracking battery levels, distance traversed, and emergency crevasse alerts.
* **Fuel Depletion Forecaster:** Automated burn-rate calculations for the 300,000-liter station fuel farm, calculating operational days of autonomy remaining.

### 4.  Military-Grade Zero-Trust & Post-Quantum Security
* **Dual-Tier Role Authentication:** Distinguishes between read-only Scientific Observers and authorized Expedition Commanders (protected via Satellite Sync Codes).
* **Post-Quantum Cryptography (ML-KEM-768 / Kyber):** Future-proof encryption securing telemetry links against decryption by quantum computers.
* **VSAT Link Integrity Guardian:** Continuously inspects satellite uplink parameters (SNR ratios, latency drift, bit error rate) to identify RF interference or deliberate signal jamming.

### 5.  Edge AI Predictive Maintenance
* **Pre-Failure Anomaly Detection:** Utilizes machine learning anomaly models running locally on edge hardware to monitor engine RPM vibrations and temperature anomalies.
* **Plain-Language Diagnostic Explanations:** Instead of confusing error numbers, the system translates telemetry spikes into clear operational warnings (e.g., *"Critical Temperature Drift (+18°C) — Likely Bearing Friction or Coolant Obstruction"*).

---

##  Extreme-Environment Resilience (Offline-First)

Polar installations cannot rely on uninterrupted high-speed internet. PolarTwin-OS is architected around **Edge Independence**:

* **Local Station Autonomy:** If satellite uplinks drop entirely, station engineers maintain full local visibility and automated safety alerts via the local area network.
* **Asynchronous Resynchronization:** Data buffers locally on edge nodes and seamlessly synchronizes with mainland command once satellite links stabilize.

---

## 🛠️ Technology Stack

| Layer | Technologies Used | Purpose |
|---|---|---|
| **Mission Control Frontend** | React, Tailwind CSS, Modern Canvas Charts | Low-latency, cyber-tactical interface |
| **3D Digital Twin Engine** | Three.js (WebGL), OBJ/MTL Loaders | Spatial rendering of research stations |
| **Backend & Integration** | Python, Flask, Blueprint Architecture | Telemetry routing & mission state management |
| **Edge Intelligence** | Scikit-learn (Isolation Forest), Rule Heuristics | Real-time sensor anomaly detection |
| **Cybersecurity Gateway** | Zero-Trust Protocol, PQC (ML-KEM-768), SHA-256 | High-assurance communication & link auditing |
| **Simulation Engine** | Mathematical Haversine Geodesy, Threaded Workers | Live AIS vessel navigation & fuel burn simulation |

---

## Access Personas 

PolarTwin-OS features role-based access control out of the box:

### 1. Operational Commander (Full Tactical Clearance)
* **Personnel ID:** `NCPOR-ADMIN-001`
* **Passkey:** `PolarAdmin@123`
* **Satellite Sync Code:** `48291736`
* *Capabilities:* Execute resupply transfers, inject emergency simulation drills, inspect cryptographic keys, and override station alerts.

### 2. Public / Scientific Observer
* *One-Click Guest Access:* Allows anyone to immediately explore the live dashboard with read-only clearance.

---

## ⚡ Quick Start Guide

### Prerequisites
* Python 3.9+
* Modern web browser (Chrome, Edge, Firefox, or Safari)

### 1. Clone & Setup
```bash
# Clone the repository
gh repo clone FLoscode/Axion
cd PolarTwin-OS

# Install dependencies
pip install -r requirements.txt
```

### 2. Launch Mission Control
```bash
python app.py
```

### 3. Open Dashboard
Open your browser and navigate to:
```
http://localhost:5000
```

### Alternative
1. Download app.py in your machine.
2. Run the app.py and allow network access. 
3. the cmd will provide a localhost:5000 or any port of your choice - 8080, 2000, 5000 etc
4. the application will start.
**REMEMBER : TO ALWAYS DOWNLOAD THE STATIC.ZIP IN THE SAME DRIVE, DO NOT RUN THE PROGRAM WITHOUT FIRST DOWNLOADING STATIC.ZIP**





*(c) 2024–2026 Axion_fc Team. Designed for the Smart India Hackathon.*
