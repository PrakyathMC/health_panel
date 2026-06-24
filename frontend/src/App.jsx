import { useEffect, useMemo, useRef, useState } from 'react';

const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8989';

const quickSymptoms = ['Headache', 'Fever', 'Chest pain', 'Fatigue', 'Cough'];

const patients = [
    { name: 'Aarav Mehta', status: 'Stable', time: '09:20', risk: 'Low' },
    { name: 'Maya Shah', status: 'Needs review', time: '10:05', risk: 'Medium' },
    { name: 'Rohan Iyer', status: 'Follow-up', time: '11:30', risk: 'Low' },
];

const stats = [
    { label: 'Patients today', value: '24', trend: '+8%' },
    { label: 'Avg. wait', value: '12m', trend: '-4m' },
    { label: 'Open cases', value: '7', trend: '3 urgent' },
];

const navItems = ['Dashboard', 'Intake', 'Patients', 'Records', 'Add Info', 'Settings'];

function splitSymptoms(value) {
    return value
        .split(/\n|,/)
        .map((item) => item.trim())
        .filter(Boolean);
}

function compact(list) {
    return Array.from(new Set(list.filter(Boolean)));
}

function formatValue(value) {
    if (value === null || value === undefined || value === '') {
        return '-';
    }

    if (Array.isArray(value)) {
        return value.length ? value.join(', ') : '-';
    }

    if (typeof value === 'object') {
        return JSON.stringify(value);
    }

    return String(value);
}

function Sidebar({ activePage, onNavigate, collapsed, onToggle }) {
    return (
        <aside className="sidebar">
            <button
                className="sidebar-toggle"
                type="button"
                onClick={onToggle}
                aria-label={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
                title={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
            >
                {collapsed ? '>>' : '<<'}
            </button>
            <div className="brand">
                <span className="brand-mark">P</span>
                <span className="brand-name">PulsePanel</span>
            </div>
            <nav className="nav-list" aria-label="Primary navigation">
                {navItems.map((item) => (
                    <button
                        className={`nav-item ${item === activePage ? 'active' : ''}`}
                        key={item}
                        type="button"
                        onClick={() => onNavigate(item)}
                        title={item}
                    >
                        <span className="nav-short">{item[0]}</span>
                        <span className="nav-label">{item}</span>
                    </button>
                ))}
            </nav>
        </aside>
    );
}

function PageHeader({ activePage, backendStatus, backendMessage, onPatientDetails }) {
    return (
        <header className="topbar">
            <div>
                <p className="eyebrow">Clinical workspace</p>
                <h1>{activePage === 'Dashboard' ? 'Health Panel' : activePage}</h1>
            </div>
            <div className="topbar-actions">
                <span className={`status-chip status-${backendStatus}`}>{backendMessage}</span>
                <button className="btn-primary" type="button" onClick={onPatientDetails}>
                    Open Intake
                </button>
                <div className="clinician-pill">
                    <span className="status-dot" />
                    Dr. Health online
                </div>
            </div>
        </header>
    );
}

function StatCard({ label, value, trend }) {
    return (
        <article className="stat-card">
            <span>{label}</span>
            <strong>{value}</strong>
            <small>{trend}</small>
        </article>
    );
}

function AddInfoPage() {
    return (
        <section className="panel details-panel">
            <div className="section-heading">
                <div>
                    <p className="eyebrow">Patient intake</p>
                    <h2>Add complete patient info</h2>
                </div>
                <span className="summary-pill">New entry</span>
            </div>

            <form className="details-form">
                <div className="form-section form-wide">
                    <strong>Basic details</strong>
                </div>
                <label>
                    Full name
                    <input type="text" placeholder="Patient full name" />
                </label>
                <label>
                    Age
                    <input type="number" min="0" placeholder="Age" />
                </label>
                <label>
                    Gender
                    <select defaultValue="">
                        <option value="" disabled>
                            Select gender
                        </option>
                        <option>Female</option>
                        <option>Male</option>
                        <option>Other</option>
                    </select>
                </label>
                <label>
                    Phone number
                    <input type="tel" placeholder="Contact number" />
                </label>
                <label>
                    Email
                    <input type="email" placeholder="Patient email" />
                </label>
                <label>
                    Patient ID
                    <input type="text" placeholder="Example: PP-1024" />
                </label>
                <label>
                    Visit type
                    <select defaultValue="Consultation">
                        <option>Consultation</option>
                        <option>Follow-up</option>
                        <option>Emergency</option>
                        <option>Lab review</option>
                    </select>
                </label>
                <label>
                    Blood group
                    <input type="text" placeholder="Example: O+" />
                </label>
                <label className="form-wide">
                    Address
                    <textarea placeholder="Patient address" rows={4} />
                </label>

                <div className="form-section form-wide">
                    <strong>Vitals and clinical info</strong>
                </div>
                <label>
                    Blood pressure
                    <input type="text" placeholder="Example: 120/80" />
                </label>
                <label>
                    Temperature
                    <input type="text" placeholder="Example: 98.6 F" />
                </label>
                <label>
                    Pulse
                    <input type="text" placeholder="Example: 78 bpm" />
                </label>
                <label>
                    Oxygen level
                    <input type="text" placeholder="Example: 98%" />
                </label>
                <label className="form-wide">
                    Symptoms
                    <textarea placeholder="Main symptoms and duration." rows={5} />
                </label>
                <label className="form-wide">
                    Medical history
                    <textarea
                        placeholder="Allergies, current medicines, existing conditions, previous surgeries, or family history."
                        rows={5}
                    />
                </label>

                <div className="form-section form-wide">
                    <strong>Emergency contact</strong>
                </div>
                <label>
                    Contact name
                    <input type="text" placeholder="Emergency contact name" />
                </label>
                <label>
                    Contact phone
                    <input type="tel" placeholder="Emergency phone number" />
                </label>
                <label className="form-wide">
                    Doctor notes
                    <textarea
                        placeholder="Diagnosis notes, prescriptions, tests, or follow-up instructions."
                        rows={5}
                    />
                </label>
                <div className="form-actions form-wide">
                    <button className="btn-primary" type="button">
                        Save Patient Info
                    </button>
                    <button className="btn-secondary" type="reset">
                        Clear
                    </button>
                </div>
            </form>
        </section>
    );
}

function PatientsView({ onPatientDetails }) {
    return (
        <section className="panel patient-panel page-panel">
            <div className="section-heading">
                <div>
                    <p className="eyebrow">Queue</p>
                    <h2>Patients</h2>
                </div>
                <button className="btn-primary" type="button" onClick={onPatientDetails}>
                    Take Patient Details
                </button>
            </div>
            <div className="patient-table">
                {patients.map((patient) => (
                    <article className="patient-row" key={patient.name}>
                        <strong>{patient.name}</strong>
                        <span>{patient.status}</span>
                        <span>{patient.time}</span>
                        <span className={`risk risk-${patient.risk.toLowerCase()}`}>{patient.risk}</span>
                    </article>
                ))}
            </div>
        </section>
    );
}

function RecordsView() {
    return (
        <section className="panel page-panel">
            <div className="section-heading">
                <div>
                    <p className="eyebrow">Clinical files</p>
                    <h2>Records</h2>
                </div>
                <span className="summary-pill">3 recent</span>
            </div>
            <div className="record-grid">
                {patients.map((patient) => (
                    <article className="record-card" key={patient.name}>
                        <strong>{patient.name}</strong>
                        <span>Last visit: Today at {patient.time}</span>
                        <span>Status: {patient.status}</span>
                    </article>
                ))}
            </div>
        </section>
    );
}

function SettingsView() {
    return (
        <section className="panel page-panel">
            <div className="section-heading">
                <div>
                    <p className="eyebrow">Preferences</p>
                    <h2>Settings</h2>
                </div>
            </div>
            <div className="settings-list">
                <label>
                    Clinic name
                    <input type="text" defaultValue="PulsePanel Clinic" />
                </label>
                <label>
                    Default language
                    <select defaultValue="English">
                        <option>English</option>
                        <option>Hindi</option>
                        <option>Gujarati</option>
                    </select>
                </label>
                <label className="toggle-row">
                    <input type="checkbox" defaultChecked />
                    Voice intake enabled
                </label>
            </div>
        </section>
    );
}

function AnalysisResults({ analysis }) {
    if (!analysis) {
        return (
            <section className="panel review-panel">
                <div className="section-heading">
                    <div>
                        <p className="eyebrow">RAG output</p>
                        <h2>Analysis results</h2>
                    </div>
                </div>
                <div className="empty-state">
                    <strong>No analysis yet</strong>
                    <p>Submit a patient record to see labels, ranked results, and backend errors here.</p>
                </div>
            </section>
        );
    }

    return (
        <section className="panel review-panel">
            <div className="section-heading">
                <div>
                    <p className="eyebrow">RAG output</p>
                    <h2>Analysis results</h2>
                </div>
                <span className="summary-pill">Record {analysis.record_id}</span>
            </div>

            <div className="analysis-meta">
                <div>
                    <span>Patient ID</span>
                    <strong>{formatValue(analysis.patient_id)}</strong>
                </div>
                <div>
                    <span>Embedding text</span>
                    <strong>{formatValue(analysis.embedding_text)}</strong>
                </div>
            </div>

            <div className="result-group">
                <h3>Labels</h3>
                {analysis.labels?.length ? (
                    <div className="result-list">
                        {analysis.labels.map((label, index) => (
                            <article className="result-card" key={`${label.label}-${index}`}>
                                <strong>{formatValue(label.label)}</strong>
                                <span>{formatValue(label.fact)}</span>
                                <small>{formatValue(label.risk_concept)}</small>
                                <p>{formatValue(label.evidence)}</p>
                            </article>
                        ))}
                    </div>
                ) : (
                    <div className="empty-state compact">
                        <strong>No labels returned</strong>
                    </div>
                )}
            </div>

            <div className="result-group">
                <h3>Top results</h3>
                {analysis.results?.length ? (
                    <div className="result-list">
                        {analysis.results.map((result) => (
                            <article className="result-card" key={`${result.rank}-${result.title}`}>
                                <div className="result-head">
                                    <strong>
                                        {result.rank}. {formatValue(result.title)}
                                    </strong>
                                    <span>{formatValue(result.score)}</span>
                                </div>
                                <span>{formatValue(result.condition)}</span>
                                <p>{formatValue(result.explanation)}</p>
                                <small>{formatValue(result.retrieval_sources)}</small>
                            </article>
                        ))}
                    </div>
                ) : (
                    <div className="empty-state compact">
                        <strong>No ranked results returned</strong>
                    </div>
                )}
            </div>

            <div className="result-group">
                <h3>Errors</h3>
                {analysis.errors?.length ? (
                    <ul className="error-list">
                        {analysis.errors.map((error, index) => (
                            <li key={`${error}-${index}`}>{formatValue(error)}</li>
                        ))}
                    </ul>
                ) : (
                    <div className="empty-state compact">
                        <strong>No backend errors reported</strong>
                    </div>
                )}
            </div>
        </section>
    );
}

function IntakeView({
    analysis,
    bp,
    conditions,
    error,
    heartRate,
    listening,
    onAddSymptom,
    onAddQuickSymptom,
    onAnalyze,
    onBpChange,
    onHeartRateChange,
    onPatientIdChange,
    onQueryChange,
    onRecordIdChange,
    onSymptomsChange,
    onRemoveSymptom,
    onShowOutputToggle,
    onSourceChange,
    onSpo2Change,
    onStopVoice,
    onTemperatureChange,
    onToggleVoice,
    onVisitIdChange,
    query,
    recordId,
    patientId,
    showAnalysisOutput,
    source,
    spo2,
    submitting,
    temperature,
    visitId,
    voiceSupported,
}) {
    return (
        <section className="panel intake-panel page-panel">
            <div className="section-heading">
                <div>
                    <p className="eyebrow">Intake</p>
                    <h2>Send patient data to the orchestrator</h2>
                </div>
                <span className="summary-pill">{conditions.length} saved</span>
            </div>

            <div className="analysis-form">
                <label>
                    Record ID
                    <input
                        value={recordId}
                        onChange={(event) => onRecordIdChange(event.target.value)}
                        placeholder="Example: R001"
                    />
                </label>
                <label>
                    Patient ID
                    <input
                        value={patientId}
                        onChange={(event) => onPatientIdChange(event.target.value)}
                        placeholder="Example: P001"
                    />
                </label>
                <label className="form-wide">
                    Visit ID
                    <input
                        value={visitId}
                        onChange={(event) => onVisitIdChange(event.target.value)}
                        placeholder="Optional visit identifier"
                    />
                </label>
                <label className="form-wide">
                    Clinical query
                    <textarea
                        value={query}
                        onChange={(event) => onQueryChange(event.target.value)}
                        placeholder="Example: Patient has chest pain and dizziness."
                        rows={5}
                    />
                </label>
                <label className="form-wide">
                    Symptoms
                    <textarea
                        value={conditions.join('\n')}
                        onChange={(event) => onSymptomsChange(event.target.value)}
                        placeholder="Add one symptom per line or separate with commas."
                        rows={5}
                    />
                </label>
                <div className="quick-list form-wide" aria-label="Quick symptoms">
                    {quickSymptoms.map((symptom) => (
                        <button key={symptom} type="button" onClick={() => onAddQuickSymptom(symptom)}>
                            {symptom}
                        </button>
                    ))}
                </div>
                <label>
                    SpO2
                    <input value={spo2} onChange={(event) => onSpo2Change(event.target.value)} placeholder="90" inputMode="decimal" />
                </label>
                <label>
                    Heart rate
                    <input
                        value={heartRate}
                        onChange={(event) => onHeartRateChange(event.target.value)}
                        placeholder="112"
                        inputMode="decimal"
                    />
                </label>
                <label>
                    Temperature
                    <input
                        value={temperature}
                        onChange={(event) => onTemperatureChange(event.target.value)}
                        placeholder="38.2"
                        inputMode="decimal"
                    />
                </label>
                <label>
                    Blood pressure
                    <input value={bp} onChange={(event) => onBpChange(event.target.value)} placeholder="150/95" />
                </label>
                <label className="form-wide">
                    Source
                    <input value={source} onChange={(event) => onSourceChange(event.target.value)} placeholder="frontend" />
                </label>
            </div>

            <div className="input-actions">
                <button className="btn-primary" type="button" onClick={onAnalyze} disabled={submitting}>
                    {submitting ? 'Sending...' : 'Analyze patient'}
                </button>
                <button className="btn-secondary" type="button" onClick={onShowOutputToggle}>
                    {showAnalysisOutput ? 'Hide RAG output' : 'Show RAG output'}
                </button>
                <button className="btn-secondary" type="button" onClick={onAddSymptom}>
                    Add symptom
                </button>
                <button className="btn-secondary" type="button" onClick={listening ? onStopVoice : onToggleVoice}>
                    {listening ? 'Stop voice' : 'Voice input'}
                </button>
            </div>

            {error && <p className="error">{error}</p>}
            {!voiceSupported && <p className="hint">Voice input works best in Chrome or Edge.</p>}

            {showAnalysisOutput && <AnalysisResults analysis={analysis} />}

            <div className="section-heading section-heading-spaced">
                <div>
                    <p className="eyebrow">Review</p>
                    <h2>Recorded symptoms</h2>
                </div>
            </div>

            <div className="doctor-summary">
                <strong>Dr. Health</strong>
                <span>{conditions.length ? `${conditions.length} symptom${conditions.length === 1 ? '' : 's'} captured for clinical review.` : 'No symptoms recorded yet. Add a concern to prepare the visit note.'}</span>
            </div>

            {conditions.length ? (
                <ul className="conditions-list">
                    {conditions.map((condition, index) => (
                        <li key={`${condition}-${index}`}>
                            <span>{condition}</span>
                            <button type="button" onClick={() => onRemoveSymptom(index)} aria-label={`Remove ${condition}`}>
                                Remove
                            </button>
                        </li>
                    ))}
                </ul>
            ) : (
                <div className="empty-state">
                    <strong>Ready for the first note</strong>
                    <p>Add a typed or voice concern to begin the patient summary.</p>
                </div>
            )}
        </section>
    );
}

function App() {
    const [activePage, setActivePage] = useState('Dashboard');
    const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
    const [showAnalysisOutput, setShowAnalysisOutput] = useState(false);
    const [query, setQuery] = useState('');
    const [conditions, setConditions] = useState([]);
    const [recordId, setRecordId] = useState('');
    const [patientId, setPatientId] = useState('');
    const [visitId, setVisitId] = useState('');
    const [spo2, setSpo2] = useState('');
    const [heartRate, setHeartRate] = useState('');
    const [temperature, setTemperature] = useState('');
    const [bp, setBp] = useState('');
    const [source, setSource] = useState('frontend');
    const [analysis, setAnalysis] = useState(null);
    const [backendStatus, setBackendStatus] = useState('loading');
    const [backendMessage, setBackendMessage] = useState('Checking backend...');
    const [error, setError] = useState('');
    const [submitting, setSubmitting] = useState(false);
    const [listening, setListening] = useState(false);
    const recognitionRef = useRef(null);

    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    const voiceSupported = Boolean(SpeechRecognition);

    const summary = useMemo(() => {
        if (!conditions.length) {
            return 'No symptoms recorded yet. Add a concern to prepare the visit note.';
        }

        return `${conditions.length} symptom${conditions.length === 1 ? '' : 's'} captured for clinical review.`;
    }, [conditions.length]);

    useEffect(() => {
        let ignore = false;

        async function checkHealth() {
            try {
                const response = await fetch(`${API_BASE}/health`);
                if (!response.ok) {
                    throw new Error(`Health check failed (${response.status})`);
                }

                const data = await response.json();
                if (ignore) return;

                setBackendStatus('ready');
                setBackendMessage(`${data.service || 'backend'} ready`);
            } catch (healthError) {
                if (ignore) return;

                setBackendStatus('error');
                setBackendMessage('Backend offline');
                setError((current) => current || healthError.message);
            }
        }

        checkHealth();

        return () => {
            ignore = true;
        };
    }, []);

    const addCondition = (value = query) => {
        const trimmed = value.trim();
        if (!trimmed) return;

        setConditions((current) => compact([trimmed, ...current]));
        setError('');
    };

    const addQuickSymptom = (symptom) => {
        setConditions((current) => compact([symptom, ...current]));
    };

    const removeCondition = (indexToRemove) => {
        setConditions((current) => current.filter((_, index) => index !== indexToRemove));
    };

    const startVoice = () => {
        if (!SpeechRecognition) {
            setError('Voice input is not available in this browser.');
            return;
        }

        const recognition = new SpeechRecognition();
        recognition.continuous = false;
        recognition.interimResults = false;
        recognition.lang = 'en-US';

        recognition.onresult = (event) => {
            const transcript = Array.from(event.results)
                .map((result) => result[0].transcript)
                .join(' ');
            setQuery(transcript);
        };

        recognition.onerror = () => {
            setError('Voice recognition failed. Please try typing the concern.');
            setListening(false);
        };

        recognition.onend = () => {
            recognitionRef.current = null;
            setListening(false);
        };

        recognitionRef.current = recognition;
        recognition.start();
        setListening(true);
        setError('');
    };

    const stopVoice = () => {
        recognitionRef.current?.stop();
        recognitionRef.current = null;
        setListening(false);
    };

    const submitAnalysis = async () => {
        const symptoms = conditions.length ? conditions : splitSymptoms(query);
        const trimmedQuery = query.trim();

        if (!recordId.trim() || !patientId.trim() || !trimmedQuery) {
            setError('Please fill record ID, patient ID, and the clinical query before sending.');
            return;
        }

        setSubmitting(true);
        setError('');

        const payload = {
            record_id: recordId.trim(),
            patient_id: patientId.trim(),
            query: trimmedQuery,
            symptoms,
            vitals: {
                ...(spo2 ? { SpO2: Number(spo2) } : {}),
                ...(heartRate ? { HR: Number(heartRate) } : {}),
                ...(temperature ? { temp: Number(temperature) } : {}),
                ...(bp.trim() ? { bp: bp.trim() } : {}),
            },
            source: source.trim() || 'frontend',
            ...(visitId.trim() ? { visit_id: visitId.trim() } : {}),
        };

        try {
            const response = await fetch(`${API_BASE}/analyze`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(payload),
            });

            const data = await response.json();

            if (!response.ok) {
                throw new Error(data?.detail || 'Analysis request failed.');
            }

            setAnalysis(data);
            setShowAnalysisOutput(true);
            setBackendStatus('ready');
            setBackendMessage('Analysis complete');
        } catch (submitError) {
            setError(submitError.message);
            setBackendStatus('error');
            setBackendMessage('Analysis failed');
        } finally {
            setSubmitting(false);
        }
    };

    return (
        <div className={`app-shell ${sidebarCollapsed ? 'sidebar-collapsed' : ''}`}>
            <Sidebar
                activePage={activePage}
                onNavigate={setActivePage}
                collapsed={sidebarCollapsed}
                onToggle={() => setSidebarCollapsed((current) => !current)}
            />

            <main className="main">
                <PageHeader
                    activePage={activePage}
                    backendStatus={backendStatus}
                    backendMessage={backendMessage}
                    onPatientDetails={() => setActivePage('Intake')}
                />

                {activePage === 'Dashboard' && (
                    <>
                        <section className="hero-panel">
                            <div className="hero-copy">
                                <span className="badge">RAG-ready intake</span>
                                <h2>Capture symptoms, review priority, and send the record to analysis.</h2>
                                <p>
                                    Enter the patient identifiers, clinical query, symptoms, and vitals. The
                                    frontend will call the orchestrator and render its ranked response.
                                </p>
                            </div>
                            <div className="doctor-visual" aria-hidden="true">
                                <div className="pulse-ring" />
                                <div className="doctor-avatar">Dr</div>
                            </div>
                        </section>

                        <section className="stats-grid" aria-label="Clinic overview">
                            {stats.map((stat) => (
                                <StatCard {...stat} key={stat.label} />
                            ))}
                        </section>

                        <PatientsView onPatientDetails={() => setActivePage('Intake')} />
                    </>
                )}

                {activePage === 'Intake' && (
                    <IntakeView
                        analysis={analysis}
                        bp={bp}
                        conditions={conditions}
                        error={error}
                        heartRate={heartRate}
                        listening={listening}
                        onAddSymptom={addCondition}
                        onAddQuickSymptom={addQuickSymptom}
                        onAnalyze={submitAnalysis}
                        onBpChange={setBp}
                        onHeartRateChange={setHeartRate}
                        onPatientIdChange={setPatientId}
                        onQueryChange={setQuery}
                        onRecordIdChange={setRecordId}
                        onSymptomsChange={(value) => setConditions(splitSymptoms(value))}
                        onRemoveSymptom={removeCondition}
                        onShowOutputToggle={() => setShowAnalysisOutput((current) => !current)}
                        onSourceChange={setSource}
                        onSpo2Change={setSpo2}
                        onStopVoice={stopVoice}
                        onTemperatureChange={setTemperature}
                        onToggleVoice={startVoice}
                        onVisitIdChange={setVisitId}
                        query={query}
                        recordId={recordId}
                        patientId={patientId}
                        showAnalysisOutput={showAnalysisOutput}
                        source={source}
                        spo2={spo2}
                        submitting={submitting}
                        temperature={temperature}
                        visitId={visitId}
                        voiceSupported={voiceSupported}
                    />
                )}

                {activePage === 'Patients' && <PatientsView onPatientDetails={() => setActivePage('Intake')} />}
                {activePage === 'Records' && <RecordsView />}
                {activePage === 'Add Info' && <AddInfoPage />}
                {activePage === 'Settings' && <SettingsView />}
            </main>
        </div>
    );
}

export default App;
