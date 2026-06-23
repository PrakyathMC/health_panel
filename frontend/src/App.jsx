import { useMemo, useRef, useState } from 'react';

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

const navItems = ['Dashboard', 'Patients', 'Records', 'Add Info', 'Settings'];

function Sidebar({ activePage, onNavigate }) {
    return (
        <aside className="sidebar">
            <div className="brand">
                <span className="brand-mark">P</span>
                <span>PulsePanel</span>
            </div>
            <nav className="nav-list" aria-label="Primary navigation">
                {navItems.map((item) => (
                    <button
                        className={`nav-item ${item === activePage ? 'active' : ''}`}
                        key={item}
                        type="button"
                        onClick={() => onNavigate(item)}
                    >
                        {item}
                    </button>
                ))}
            </nav>
        </aside>
    );
}

function PageHeader({ activePage, onPatientDetails }) {
    return (
        <header className="topbar">
            <div>
                <p className="eyebrow">Clinical workspace</p>
                <h1>{activePage === 'Dashboard' ? 'Health Panel' : activePage}</h1>
            </div>
            <div className="topbar-actions">
                <button className="btn-primary" type="button" onClick={onPatientDetails}>
                    Take Patient Details
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
                        <option value="" disabled>Select gender</option>
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
                    <textarea placeholder="Allergies, current medicines, existing conditions, previous surgeries, or family history." rows={5} />
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
                    <textarea placeholder="Diagnosis notes, prescriptions, tests, or follow-up instructions." rows={5} />
                </label>
                <div className="form-actions form-wide">
                    <button className="btn-primary" type="button">Save Patient Info</button>
                    <button className="btn-secondary" type="reset">Clear</button>
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

function App() {
    const [activePage, setActivePage] = useState('Dashboard');
    const [text, setText] = useState('');
    const [conditions, setConditions] = useState([]);
    const [listening, setListening] = useState(false);
    const [error, setError] = useState('');
    const recognitionRef = useRef(null);

    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    const voiceSupported = Boolean(SpeechRecognition);

    const summary = useMemo(() => {
        if (!conditions.length) {
            return 'No symptoms recorded yet. Add a concern to prepare the visit note.';
        }

        return `${conditions.length} symptom${conditions.length === 1 ? '' : 's'} captured for clinical review.`;
    }, [conditions.length]);

    const addCondition = (value = text) => {
        const trimmed = value.trim();
        if (!trimmed) return;

        setConditions((current) => [trimmed, ...current]);
        setText('');
        setError('');
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
            setText(transcript);
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

    return (
        <div className="app-shell">
            <Sidebar activePage={activePage} onNavigate={setActivePage} />

            <main className="main">
                <PageHeader activePage={activePage} onPatientDetails={() => setActivePage('Add Info')} />

                {activePage === 'Dashboard' && (
                    <>
                        <section className="hero-panel">
                            <div className="hero-copy">
                                <span className="badge">RAG-ready intake</span>
                                <h2>Capture symptoms, review priority, and prepare patient context.</h2>
                                <p>
                                    A clean front desk for recording patient concerns before consultation.
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

                        <div className="workspace-grid">
                            <section className="panel intake-panel">
                                <div className="section-heading">
                                    <div>
                                        <p className="eyebrow">Intake</p>
                                        <h2>Describe the concern</h2>
                                    </div>
                                    <span className="summary-pill">{conditions.length} saved</span>
                                </div>

                                <textarea
                                    value={text}
                                    onChange={(event) => setText(event.target.value)}
                                    placeholder="Example: Mild fever since yesterday with body ache and sore throat."
                                    rows={6}
                                />

                                <div className="quick-list" aria-label="Quick symptoms">
                                    {quickSymptoms.map((symptom) => (
                                        <button key={symptom} type="button" onClick={() => addCondition(symptom)}>
                                            {symptom}
                                        </button>
                                    ))}
                                </div>

                                <div className="input-actions">
                                    <button className="btn-primary" type="button" onClick={() => addCondition()}>
                                        Add concern
                                    </button>
                                    <button className="btn-secondary" type="button" onClick={listening ? stopVoice : startVoice}>
                                        {listening ? 'Stop voice' : 'Voice input'}
                                    </button>
                                </div>

                                {error && <p className="error">{error}</p>}
                                {!voiceSupported && <p className="hint">Voice input works best in Chrome or Edge.</p>}
                            </section>

                            <section className="panel review-panel">
                                <div className="section-heading">
                                    <div>
                                        <p className="eyebrow">Review</p>
                                        <h2>Recorded symptoms</h2>
                                    </div>
                                </div>

                                <div className="doctor-summary">
                                    <strong>Dr. Health</strong>
                                    <span>{summary}</span>
                                </div>

                                {conditions.length ? (
                                    <ul className="conditions-list">
                                        {conditions.map((condition, index) => (
                                            <li key={`${condition}-${index}`}>
                                                <span>{condition}</span>
                                                <button type="button" onClick={() => removeCondition(index)} aria-label={`Remove ${condition}`}>
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
                        </div>

                        <PatientsView onPatientDetails={() => setActivePage('Add Info')} />
                    </>
                )}

                {activePage === 'Patients' && <PatientsView onPatientDetails={() => setActivePage('Add Info')} />}
                {activePage === 'Records' && <RecordsView />}
                {activePage === 'Add Info' && <AddInfoPage />}
                {activePage === 'Settings' && <SettingsView />}
            </main>
        </div>
    );
}

export default App;
