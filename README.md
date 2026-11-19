# 🌱 AgriSight — Intelligent & Adaptive Agriculture Monitoring System

**AgriSight** is an AI-powered smart agriculture platform designed to make agricultural monitoring more reliable, context-aware, and adaptive.

Unlike conventional IoT agriculture systems that simply collect sensor readings and trigger threshold-based alerts, AgriSight aims to understand the reliability of incoming data, learn from historical experiences, and improve its decision-making through continuous feedback.

The platform combines IoT sensor monitoring, computer vision, historical experience analysis, and adaptive intelligence to support more informed agricultural decisions.

---

## 🎯 Project Vision

Traditional smart agriculture systems often rely on fixed thresholds to determine whether environmental conditions are suitable for crops.

However, real-world agricultural environments are unpredictable:
- Sensors can produce noisy or unreliable readings.
- Environmental conditions fluctuate over time.
- Similar sensor readings can lead to different outcomes under different circumstances.
- Static decision-making systems struggle to adapt to changing conditions.

AgriSight addresses these challenges by introducing an experience-driven intelligence layer that evaluates current conditions against historical observations and helps improve future decisions.

## ✨ Key Features

### 1. IoT-Based Environmental Monitoring
- Collects real-time agricultural sensor readings.
- Supports ESP32-based sensor integration.
- Monitors environmental parameters such as temperature and humidity.
- Provides a foundation for continuous field monitoring.

### 2. Sensor Reliability Analysis
- Evaluates the reliability of incoming sensor data.
- Accounts for potential inconsistencies and abnormal readings.
- Incorporates sensor reliability into the overall decision-making process.

### 3. Agricultural Experience Memory
- Maintains historical agricultural experiences.
- Compares current environmental conditions with previously observed situations.
- Identifies similar historical experiences to provide contextual information.
- Uses historical evidence to make decisions more context-aware.

### 4. Adaptive Confidence Intelligence (ACI)

ACI is an intelligence layer that evaluates how trustworthy the system's current assessment is.

It combines multiple evidence sources, including:

- Sensor reliability
- Historical similarity
- Optional computer vision evidence

The system produces an overall confidence assessment, helping distinguish between reliable observations and situations that require additional attention.

### 5. Computer Vision Integration
- Supports incorporating visual evidence into agricultural assessments.
- Allows the intelligence layer to consider both sensor-based and visual information.
- Provides an additional source of evidence for more comprehensive agricultural monitoring.

### 6. Experience-Driven Learning and Recalibration
AgriSight is designed to move beyond static decision-making.

Its learning architecture explores how historical outcomes and past experiences can be used to recalibrate future decisions and improve system adaptability.

---

## 🏗️ System Architecture

AgriSight follows a modular architecture consisting of an IoT data collection layer, backend processing layer, intelligence layer, and frontend dashboard.

```text
                  ┌──────────────────────┐
                  │     ESP32 Device     │
                  │   Sensors / Data     │
                  └──────────┬───────────┘
                             │
                             ▼
                  ┌──────────────────────┐
                  │   Data Acquisition   │
                  │    & Processing      │
                  └──────────┬───────────┘
                             │
                             ▼
                  ┌──────────────────────┐
                  │     FastAPI Backend  │
                  │                      │
                  │  Sensor Processing   │
                  │  Data Management     │
                  └──────────┬───────────┘
                             │
                             ▼
             ┌──────────────────────────────┐
             │    Intelligence Layer        │
             │                              │
             │  Adaptive Confidence (ACI)   │
             │  Sensor Reliability          │
             │  Experience Memory           │
             │  Similarity Engine           │
             │  Vision Evidence             │
             │  Recalibration               │
             └──────────────┬───────────────┘
                            │
                            ▼
                  ┌──────────────────────┐
                  │    SQLite Database   │
                  │ Historical Records   │
                  │ Sensor Experiences   │
                  └──────────┬───────────┘
                             │
                             ▼
                  ┌──────────────────────┐
                  │    React Frontend    │
                  │   Monitoring UI      │
                  │   Intelligence Data  │
                  └──────────────────────┘
```

*Conceptual architecture illustrating the major system components.*

---

## 🛠️ Technology Stack

| Component | Technologies |
|---|---|
| Frontend | React, TypeScript |
| Backend | Python, FastAPI |
| Database | SQLite |
| IoT Hardware | ESP32 |
| Sensor Integration | Environmental sensors |
| Machine Learning | Python, NumPy |
| Computer Vision | Vision-based agricultural analysis |
| API Communication | REST APIs |

---

## 📂 Project Structure

```text
AgriSight/
│
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── api/
│   │   │   ├── flai_routes.py
│   │   │   └── ...
│   │   │
│   │   └── services/
│   │       └── learning/
│   │           └── flai_engine.py
│   │
│   ├── scripts/
│   │   └── simulate_esp32.py
│   │
│   ├── tests/
│   ├── agrisight.db
│   └── ...
│
└── frontend/
    └── ...
```

*Simplified structure; additional modules and files are omitted.*

---

## ⚙️ Getting Started

### Prerequisites

- Python 3.10+
- Node.js and npm
- Git

### 1. Clone the Repository

```bash
git clone https://github.com/Tushitak13/AgriSight.git
cd AgriSight
```

### 2. Set Up the Backend

```bash
cd backend

python -m venv venv
```

Activate the virtual environment:

**Windows:**
```powershell
.\venv\Scripts\Activate.ps1
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Start the backend:

```bash
uvicorn app.main:app --reload
```

### 3. Set Up the Frontend

Open another terminal:

```bash
cd frontend
npm install
npm run dev
```

### 4. Run ESP32 Simulation

AgriSight includes an ESP32 simulation script for testing sensor-data behaviour.

From the backend directory:

```bash
python scripts/simulate_esp32.py 20 --spike
```

This generates simulated sensor readings, including spike conditions, to test the system's handling of abnormal data.

*Note: Configure the database, environment variables, and frontend API URL according to your local setup.*

---

## 🔌 Important API Endpoint

### Adaptive Confidence Intelligence

**Endpoint:**

```http
GET /api/aci/current
```

Example request:

```http
GET /api/aci/current?device_id=esp32-01&include_vision=true
```

This endpoint retrieves the current Adaptive Confidence Intelligence assessment for a device.

The response includes information such as:

- Overall ACI score
- Individual evidence components
- Sensor reliability
- Historical similarity
- Whether visual evidence was used
- Cold-start status
- Number of available experiences
- Number of similar historical observations

Interactive API documentation is available through FastAPI's Swagger interface:

```text
http://127.0.0.1:8000/docs
```

---

## 🧠 What Makes AgriSight Different?

| Traditional Agriculture IoT | AgriSight |
|---|---|
| Fixed threshold-based alerts | Context-aware intelligence |
| Raw sensor readings | Sensor reliability assessment |
| Limited historical context | Experience memory |
| Static decision-making | Adaptive learning architecture |
| Sensor-only observations | Sensor and visual evidence |
| Reactive monitoring | Experience-driven improvement |

AgriSight aims to transform agricultural monitoring from simple data collection into a system that can evaluate evidence, learn from past observations, and improve its future assessments.

---

## 🚀 Future Scope

- Enhanced self-learning and recalibration mechanisms.
- Improved crop-specific intelligence.
- More advanced historical experience retrieval.
- Expanded computer vision capabilities for crop health assessment.
- Integration with additional IoT devices and sensors.
- Improved decision-making through continuous feedback.

---

## 👩‍💻 Development

AgriSight is being developed as a modular intelligent agriculture platform, with an emphasis on combining IoT, AI/ML, computer vision, and experience-driven learning.

**Repository:** [Tushitak13/AgriSight](https://github.com/Tushitak13/AgriSight)

---

*AgriSight — Making agricultural intelligence more reliable, adaptive, and experience-driven.*
