-- ============================================================
-- PulsePanel Clinical Data Platform - PostgreSQL Schema
-- Based on the PulsePanel Clinical Data Architecture document
-- ============================================================

-- Enable UUID generation
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ============================================================
-- Auto-update trigger for updated_at columns
-- ============================================================
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- ============================================================
-- Patients
-- ============================================================
CREATE TABLE patients (
    patient_id      UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    external_id     VARCHAR(255) UNIQUE,       -- ID from EHR/FHIR system
    name            VARCHAR(255),
    date_of_birth   DATE,
    gender          VARCHAR(50),
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- Visit Records
-- ============================================================
CREATE TABLE visits (
    visit_id        UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    patient_id      UUID NOT NULL REFERENCES patients(patient_id) ON DELETE CASCADE,
    visit_date      TIMESTAMPTZ DEFAULT NOW(),
    source          TEXT[],                     -- e.g. {patient, doctor, wearable, ehr, lab}
    notes           TEXT,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_visits_patient_id ON visits(patient_id);
CREATE INDEX idx_visits_visit_date ON visits(visit_date);

-- ============================================================
-- Symptoms (from patient or doctor)
-- ============================================================
CREATE TABLE symptoms (
    symptom_id      UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    visit_id        UUID NOT NULL REFERENCES visits(visit_id) ON DELETE CASCADE,
    patient_id      UUID NOT NULL REFERENCES patients(patient_id) ON DELETE CASCADE,
    name            VARCHAR(255) NOT NULL,      -- e.g. "chest pain"
    duration        VARCHAR(100),               -- e.g. "2 hours"
    severity        VARCHAR(50),                -- e.g. "severe", "moderate", "mild"
    source          VARCHAR(50),                -- patient, doctor
    recorded_at     TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_symptoms_visit_id ON symptoms(visit_id);
CREATE INDEX idx_symptoms_patient_id ON symptoms(patient_id);
CREATE INDEX idx_symptoms_name ON symptoms(name);

-- ============================================================
-- Vitals (raw numerical data)
-- ============================================================
CREATE TABLE vitals (
    vital_id        UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    visit_id        UUID NOT NULL REFERENCES visits(visit_id) ON DELETE CASCADE,
    patient_id      UUID NOT NULL REFERENCES patients(patient_id) ON DELETE CASCADE,
    vital_name      VARCHAR(100) NOT NULL,      -- e.g. SpO2, HR, BP_systolic, BP_diastolic, Temperature
    value_numeric   DECIMAL(10, 2),
    value_text      VARCHAR(255),               -- for values like "140/90"
    unit            VARCHAR(50),
    source          VARCHAR(50),                -- wearable, device, manual, lab
    recorded_at     TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_vitals_visit_id ON vitals(visit_id);
CREATE INDEX idx_vitals_patient_id ON vitals(patient_id);
CREATE INDEX idx_vitals_name ON vitals(vital_name);
CREATE INDEX idx_vitals_recorded_at ON vitals(recorded_at);

-- ============================================================
-- Lab Reports
-- ============================================================
CREATE TABLE lab_reports (
    lab_id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    visit_id        UUID REFERENCES visits(visit_id) ON DELETE SET NULL,
    patient_id      UUID NOT NULL REFERENCES patients(patient_id) ON DELETE CASCADE,
    test_name       VARCHAR(255) NOT NULL,
    test_code       VARCHAR(100),               -- LOINC code if available
    value_numeric   DECIMAL(10, 2),
    value_text      TEXT,
    unit            VARCHAR(50),
    reference_range VARCHAR(255),
    is_abnormal     BOOLEAN,
    source          VARCHAR(50),
    test_date       TIMESTAMPTZ,
    recorded_at     TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_lab_reports_patient_id ON lab_reports(patient_id);
CREATE INDEX idx_lab_reports_test_name ON lab_reports(test_name);

-- ============================================================
-- Clinical Labels (derived from rules)
-- ============================================================
CREATE TABLE clinical_labels (
    label_id        UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    patient_id      UUID NOT NULL REFERENCES patients(patient_id) ON DELETE CASCADE,
    visit_id        UUID REFERENCES visits(visit_id) ON DELETE CASCADE,
    label_name      VARCHAR(255) NOT NULL,      -- e.g. "hypoxia", "tachycardia", "fever"
    source          VARCHAR(100) NOT NULL,       -- "clinical_rule"
    rule_name       VARCHAR(255),               -- e.g. "SpO2 < 92"
    evidence        JSONB,                      -- {SpO2: 90}
    is_active       BOOLEAN DEFAULT TRUE,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_clinical_labels_patient_id ON clinical_labels(patient_id);
CREATE INDEX idx_clinical_labels_visit_id ON clinical_labels(visit_id);
CREATE INDEX idx_clinical_labels_name ON clinical_labels(label_name);

-- ============================================================
-- Clinical Facts (human-readable statements)
-- ============================================================
CREATE TABLE clinical_facts (
    fact_id         UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    patient_id      UUID NOT NULL REFERENCES patients(patient_id) ON DELETE CASCADE,
    visit_id        UUID REFERENCES visits(visit_id) ON DELETE CASCADE,
    fact_text       TEXT NOT NULL,              -- e.g. "oxygen saturation below normal threshold"
    source_label_id UUID REFERENCES clinical_labels(label_id) ON DELETE SET NULL,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_clinical_facts_patient_id ON clinical_facts(patient_id);

-- ============================================================
-- Risk Concepts (higher-level clinical meaning)
-- ============================================================
CREATE TABLE risk_concepts (
    risk_id         UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    patient_id      UUID NOT NULL REFERENCES patients(patient_id) ON DELETE CASCADE,
    visit_id        UUID REFERENCES visits(visit_id) ON DELETE CASCADE,
    concept_name    VARCHAR(255) NOT NULL,      -- e.g. "respiratory distress", "sepsis risk"
    risk_level      VARCHAR(50),                -- low, moderate, high, critical
    recommendation  TEXT,                       -- e.g. "urgent evaluation recommended"
    evidence        JSONB,                       -- supporting evidence
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_risk_concepts_patient_id ON risk_concepts(patient_id);

-- ============================================================
-- FHIR / EHR Records (structured external records)
-- ============================================================
CREATE TABLE fhir_records (
    fhir_id         UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    patient_id      UUID NOT NULL REFERENCES patients(patient_id) ON DELETE CASCADE,
    resource_type   VARCHAR(100) NOT NULL,      -- e.g. Observation, Condition, MedicationRequest
    resource_id     VARCHAR(255),               -- original FHIR resource ID
    resource_body   JSONB NOT NULL,             -- full FHIR resource
    source_system   VARCHAR(255),
    ingested_at     TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_fhir_records_patient_id ON fhir_records(patient_id);
CREATE INDEX idx_fhir_records_resource_type ON fhir_records(resource_type);

-- ============================================================
-- Canonical Clinical Records (normalized view of all sources)
-- ============================================================
CREATE TABLE canonical_records (
    record_id       UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    patient_id      UUID NOT NULL REFERENCES patients(patient_id) ON DELETE CASCADE,
    visit_id        UUID REFERENCES visits(visit_id) ON DELETE CASCADE,
    record_data     JSONB NOT NULL,             -- full canonical record as described in Section 8
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_canonical_records_patient_id ON canonical_records(patient_id);

-- ============================================================
-- Triggers for auto-updating updated_at
-- ============================================================
CREATE TRIGGER trg_patients_updated_at
    BEFORE UPDATE ON patients
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER trg_canonical_records_updated_at
    BEFORE UPDATE ON canonical_records
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER trg_clinical_rules_updated_at
    BEFORE UPDATE ON clinical_rules
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at();

-- ============================================================
-- Audit Log
-- ============================================================
CREATE TABLE audit_log (
    audit_id        UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    action          VARCHAR(50) NOT NULL,        -- INSERT, UPDATE, DELETE, RULE_APPLIED, QUERY
    table_name      VARCHAR(100),
    record_id       UUID,
    patient_id      UUID,
    changed_by      VARCHAR(255),                -- system component or user
    old_values      JSONB,
    new_values      JSONB,
    description     TEXT,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_audit_log_patient_id ON audit_log(patient_id);
CREATE INDEX idx_audit_log_created_at ON audit_log(created_at);

-- ============================================================
-- Clinical Rules Registry
-- ============================================================
CREATE TABLE clinical_rules (
    rule_id         UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    rule_name       VARCHAR(255) NOT NULL UNIQUE,
    rule_description TEXT,
    condition_expr  TEXT NOT NULL,               -- e.g. "SpO2 < 92"
    output_label    VARCHAR(255) NOT NULL,        -- e.g. "hypoxia"
    is_active       BOOLEAN DEFAULT TRUE,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

-- Seed default clinical rules from the architecture document (Section 5)
INSERT INTO clinical_rules (rule_name, rule_description, condition_expr, output_label) VALUES
    ('hypoxia_rule', 'SpO2 below 92 indicates hypoxia', 'SpO2 < 92', 'hypoxia'),
    ('tachycardia_rule', 'Heart rate above 100 indicates tachycardia', 'HR > 100', 'tachycardia'),
    ('fever_rule', 'Temperature above 37.5 indicates fever', 'Temperature > 37.5', 'fever'),
    ('hypertension_rule', 'BP systolic >= 140 or diastolic >= 90 indicates hypertension', 'BP_systolic >= 140 OR BP_diastolic >= 90', 'hypertension'),
    ('bradycardia_rule', 'Heart rate below 60 indicates bradycardia', 'HR < 60', 'bradycardia'),
    ('hypotension_rule', 'BP systolic < 90 indicates hypotension', 'BP_systolic < 90', 'hypotension'),
    ('severe_hypoxia_rule', 'SpO2 below 85 indicates severe hypoxia', 'SpO2 < 85', 'severe_hypoxia');
