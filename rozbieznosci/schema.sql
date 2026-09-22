PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS clients (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    tax_id TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS projects (
    id INTEGER PRIMARY KEY,
    client_id INTEGER NOT NULL REFERENCES clients(id) ON DELETE RESTRICT,
    name TEXT NOT NULL,
    code TEXT NOT NULL UNIQUE
);
CREATE INDEX IF NOT EXISTS idx_projects_client ON projects(client_id);

CREATE TABLE IF NOT EXISTS estimates (
    id INTEGER PRIMARY KEY,
    project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE RESTRICT,
    version INTEGER NOT NULL CHECK (version > 0),
    approved INTEGER NOT NULL CHECK (approved IN (0, 1)),
    net_cents INTEGER NOT NULL CHECK (typeof(net_cents) = 'integer' AND net_cents >= 0),
    UNIQUE (project_id, version)
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_estimates_one_approved
    ON estimates(project_id) WHERE approved = 1;

CREATE TABLE IF NOT EXISTS stages (
    id INTEGER PRIMARY KEY,
    project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE RESTRICT,
    name TEXT NOT NULL,
    baseline_cents INTEGER NOT NULL CHECK (typeof(baseline_cents) = 'integer' AND baseline_cents >= 0),
    status TEXT NOT NULL CHECK (status IN ('open', 'completed'))
);
CREATE INDEX IF NOT EXISTS idx_stages_project ON stages(project_id);

CREATE TABLE IF NOT EXISTS tranches (
    id INTEGER PRIMARY KEY,
    stage_id INTEGER NOT NULL REFERENCES stages(id) ON DELETE RESTRICT,
    sequence INTEGER NOT NULL CHECK (sequence > 0),
    baseline_cents INTEGER NOT NULL CHECK (typeof(baseline_cents) = 'integer' AND baseline_cents >= 0),
    acceptance_condition TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('planned', 'due', 'paid')),
    UNIQUE (stage_id, sequence)
);
CREATE INDEX IF NOT EXISTS idx_tranches_stage ON tranches(stage_id);

CREATE TABLE IF NOT EXISTS documents (
    id INTEGER PRIMARY KEY,
    project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE RESTRICT,
    kind TEXT NOT NULL CHECK (kind IN ('estimate', 'contract', 'amendment', 'acceptance', 'email')),
    title TEXT NOT NULL,
    path TEXT NOT NULL UNIQUE,
    available INTEGER NOT NULL DEFAULT 1 CHECK (available IN (0, 1))
);
CREATE INDEX IF NOT EXISTS idx_documents_project ON documents(project_id);

CREATE TABLE IF NOT EXISTS document_chunks (
    id INTEGER PRIMARY KEY,
    document_id INTEGER NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    locator TEXT NOT NULL,
    text TEXT NOT NULL,
    embedding_json TEXT,
    UNIQUE (document_id, locator)
);
CREATE INDEX IF NOT EXISTS idx_document_chunks_document ON document_chunks(document_id);
CREATE VIRTUAL TABLE IF NOT EXISTS document_fts USING fts5(
    chunk_id UNINDEXED, text, tokenize = 'unicode61 remove_diacritics 2'
);

CREATE TABLE IF NOT EXISTS changes (
    id INTEGER PRIMARY KEY,
    stage_id INTEGER NOT NULL REFERENCES stages(id) ON DELETE RESTRICT,
    tranche_id INTEGER NOT NULL REFERENCES tranches(id) ON DELETE RESTRICT,
    document_id INTEGER REFERENCES documents(id) ON DELETE RESTRICT,
    kind TEXT NOT NULL CHECK (kind IN ('scope', 'discount', 'extra_work')),
    delta_cents INTEGER NOT NULL CHECK (typeof(delta_cents) = 'integer' AND delta_cents != 0),
    approved INTEGER NOT NULL CHECK (approved IN (0, 1))
);
CREATE INDEX IF NOT EXISTS idx_changes_tranche ON changes(tranche_id);

CREATE VIEW IF NOT EXISTS tranche_references AS
SELECT t.id AS tranche_id,
       t.baseline_cents + COALESCE(SUM(c.delta_cents), 0) AS reference_cents
FROM tranches t
LEFT JOIN changes c ON c.tranche_id = t.id AND c.approved = 1
GROUP BY t.id;

CREATE TABLE IF NOT EXISTS invoices (
    id INTEGER PRIMARY KEY,
    client_id INTEGER NOT NULL REFERENCES clients(id) ON DELETE RESTRICT,
    project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE RESTRICT,
    tranche_id INTEGER REFERENCES tranches(id) ON DELETE RESTRICT,
    issued_on TEXT NOT NULL CHECK (date(issued_on) IS NOT NULL),
    number TEXT NOT NULL UNIQUE,
    net_cents INTEGER NOT NULL CHECK (typeof(net_cents) = 'integer' AND net_cents >= 0),
    vat_cents INTEGER NOT NULL CHECK (typeof(vat_cents) = 'integer' AND vat_cents >= 0),
    retention_cents INTEGER NOT NULL DEFAULT 0
        CHECK (typeof(retention_cents) = 'integer' AND retention_cents >= 0 AND retention_cents <= net_cents)
);
CREATE INDEX IF NOT EXISTS idx_invoices_client_date ON invoices(client_id, issued_on);
CREATE INDEX IF NOT EXISTS idx_invoices_project ON invoices(project_id);
CREATE INDEX IF NOT EXISTS idx_invoices_tranche ON invoices(tranche_id);

CREATE TRIGGER IF NOT EXISTS invoices_match_project_insert
BEFORE INSERT ON invoices
BEGIN
    SELECT RAISE(ABORT, 'Faktura musi wskazywać klienta i transzę swojego projektu')
    WHERE NOT EXISTS (
        SELECT 1 FROM projects p
        WHERE p.id = NEW.project_id
          AND p.client_id = NEW.client_id
          AND (NEW.tranche_id IS NULL OR EXISTS (
              SELECT 1 FROM stages s
              JOIN tranches t ON t.stage_id = s.id
              WHERE s.project_id = p.id AND t.id = NEW.tranche_id
          ))
    );
END;

CREATE TRIGGER IF NOT EXISTS invoices_match_project_update
BEFORE UPDATE OF client_id, project_id, tranche_id ON invoices
BEGIN
    SELECT RAISE(ABORT, 'Faktura musi wskazywać klienta i transzę swojego projektu')
    WHERE NOT EXISTS (
        SELECT 1 FROM projects p
        WHERE p.id = NEW.project_id
          AND p.client_id = NEW.client_id
          AND (NEW.tranche_id IS NULL OR EXISTS (
              SELECT 1 FROM stages s
              JOIN tranches t ON t.stage_id = s.id
              WHERE s.project_id = p.id AND t.id = NEW.tranche_id
          ))
    );
END;

CREATE TABLE IF NOT EXISTS invoice_items (
    id INTEGER PRIMARY KEY,
    invoice_id INTEGER NOT NULL REFERENCES invoices(id) ON DELETE CASCADE,
    description TEXT NOT NULL,
    net_cents INTEGER NOT NULL CHECK (typeof(net_cents) = 'integer' AND net_cents >= 0),
    vat_cents INTEGER NOT NULL CHECK (typeof(vat_cents) = 'integer' AND vat_cents >= 0)
);
CREATE INDEX IF NOT EXISTS idx_invoice_items_invoice ON invoice_items(invoice_id);

CREATE TABLE IF NOT EXISTS analyses (
    id INTEGER PRIMARY KEY,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    result_json TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS followups (
    id INTEGER PRIMARY KEY,
    analysis_id INTEGER NOT NULL REFERENCES analyses(id) ON DELETE CASCADE,
    case_id INTEGER,
    question TEXT NOT NULL,
    answer_json TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_followups_analysis ON followups(analysis_id, id);
