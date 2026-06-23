# Frontend Integration Notes

This is the small checklist for connecting the frontend to the PulsePanel backend.

## 1. Keep Backend Running

From the repo root, run:

```cmd
uvicorn pulsepanel_orchestrator.api:app --host 127.0.0.1 --port 8989 --reload
```

Backend base URL:

```text
http://127.0.0.1:8989
```

Health check:

```text
GET http://127.0.0.1:8989/health
```

If health returns `status: ok`, backend is alive.

## 2. Send Patient Data

Frontend should send a `POST` request to:

```text
http://127.0.0.1:8989/analyze
```

Example JSON:

```json
{
  "record_id": "R001",
  "patient_id": "P001",
  "query": "Patient has chest pain and dizziness",
  "symptoms": ["chest pain", "dizziness"],
  "vitals": {
    "SpO2": 90,
    "HR": 112,
    "temp": 38.2,
    "bp": "150/95"
  },
  "source": "frontend"
}
```

Required fields:

```text
record_id
patient_id
query
```

Optional fields:

```text
symptoms
vitals
source
visit_id
```

## 3. What Frontend Should Display

From the response, display:

```text
labels
results
explanation
errors
```

Frontend does not need to do clinical rules, embeddings, OpenAI calls, or Qdrant calls.

Just collect patient info, send JSON to `/analyze`, and show the returned results.

## 4. Simple Fetch Example

```js
const payload = {
  record_id: "R001",
  patient_id: "P001",
  query: "Patient has chest pain and dizziness",
  symptoms: ["chest pain", "dizziness"],
  vitals: {
    SpO2: 90,
    HR: 112,
    temp: 38.2,
    bp: "150/95"
  },
  source: "frontend"
};

const response = await fetch("http://127.0.0.1:8989/analyze", {
  method: "POST",
  headers: {
    "Content-Type": "application/json"
  },
  body: JSON.stringify(payload)
});

const data = await response.json();
console.log(data);
```

## 5. Response Shape

The backend returns JSON like this:

```json
{
  "record_id": "R001",
  "patient_id": "P001",
  "labels": [
    {
      "label": "hypoxia",
      "risk_concept": "respiratory distress"
    }
  ],
  "results": [
    {
      "rank": 1,
      "title": "Possible respiratory distress",
      "condition": "respiratory_distress",
      "score": 0.82,
      "explanation": "..."
    }
  ],
  "errors": []
}
```

Good UI sections:

```text
Clinical Labels
Top Results
Explanation
Errors or Warnings
```

## 6. Common Problems

If the frontend gets connection error:

```text
Backend is probably not running.
```

Run:

```cmd
uvicorn pulsepanel_orchestrator.api:app --host 127.0.0.1 --port 8989 --reload
```

If backend returns validation errors, check that these fields are present:

```text
record_id
patient_id
query
```

If Qdrant/OpenAI is not ready yet, frontend can still call the same API. Backend team will handle that part.
