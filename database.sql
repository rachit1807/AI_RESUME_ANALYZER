-- Additive schema reference for the candidate/recruiter platform.
-- Existing legacy tables named `resumes` and `jobs` are intentionally untouched.
-- Flask-SQLAlchemy creates equivalent tables with IF NOT EXISTS at startup.

CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    name VARCHAR(120) NOT NULL,
    email VARCHAR(254) NOT NULL UNIQUE,
    password_hash VARCHAR(256) NOT NULL,
    role VARCHAR(20) NOT NULL DEFAULT 'candidate',
    active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS ix_users_email ON users(email);
CREATE INDEX IF NOT EXISTS ix_users_role ON users(role);

CREATE TABLE IF NOT EXISTS candidate_profiles (
    user_id INTEGER PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    headline VARCHAR(180) DEFAULT '',
    location VARCHAR(120) DEFAULT '',
    phone VARCHAR(40) DEFAULT '',
    skills TEXT DEFAULT '',
    salary_expectation VARCHAR(80) DEFAULT '',
    linkedin_url VARCHAR(300) DEFAULT '',
    github_url VARCHAR(300) DEFAULT ''
);

CREATE TABLE IF NOT EXISTS companies (
    id SERIAL PRIMARY KEY,
    name VARCHAR(180) NOT NULL,
    website VARCHAR(300) DEFAULT '',
    owner_id INTEGER NOT NULL UNIQUE REFERENCES users(id) ON DELETE CASCADE,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS recruiter_jobs (
    id SERIAL PRIMARY KEY,
    company_id INTEGER NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    title VARCHAR(180) NOT NULL,
    location VARCHAR(120) DEFAULT '',
    salary_range VARCHAR(100) DEFAULT '',
    description TEXT NOT NULL,
    active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS ix_recruiter_jobs_company_id ON recruiter_jobs(company_id);
CREATE INDEX IF NOT EXISTS ix_recruiter_jobs_active ON recruiter_jobs(active);

CREATE TABLE IF NOT EXISTS resume_versions (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    filename VARCHAR(255) NOT NULL,
    extracted_text TEXT NOT NULL,
    builder_data TEXT NOT NULL DEFAULT '{}',
    ats_score INTEGER NOT NULL DEFAULT 0,
    template_name VARCHAR(30) NOT NULL DEFAULT 'classic',
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS ix_resume_versions_user_id ON resume_versions(user_id);
CREATE INDEX IF NOT EXISTS ix_resume_versions_created_at ON resume_versions(created_at);

CREATE TABLE IF NOT EXISTS analyses (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    resume_id INTEGER NOT NULL REFERENCES resume_versions(id) ON DELETE CASCADE,
    job_title VARCHAR(180) DEFAULT 'Target role',
    job_description TEXT NOT NULL,
    ats_score INTEGER NOT NULL,
    matched_skills TEXT NOT NULL DEFAULT '[]',
    missing_skills TEXT NOT NULL DEFAULT '[]',
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS ix_analyses_user_id ON analyses(user_id);
CREATE INDEX IF NOT EXISTS ix_analyses_created_at ON analyses(created_at);

CREATE TABLE IF NOT EXISTS saved_jobs (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title VARCHAR(180) NOT NULL,
    description TEXT NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_saved_job_title UNIQUE(user_id, title)
);
CREATE INDEX IF NOT EXISTS ix_saved_jobs_user_id ON saved_jobs(user_id);

CREATE TABLE IF NOT EXISTS applications (
    id SERIAL PRIMARY KEY,
    job_id INTEGER NOT NULL REFERENCES recruiter_jobs(id) ON DELETE CASCADE,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    resume_id INTEGER REFERENCES resume_versions(id) ON DELETE SET NULL,
    ats_score INTEGER NOT NULL DEFAULT 0,
    status VARCHAR(24) NOT NULL DEFAULT 'submitted',
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_application_candidate_job UNIQUE(job_id, user_id)
);
CREATE INDEX IF NOT EXISTS ix_applications_job_id ON applications(job_id);
CREATE INDEX IF NOT EXISTS ix_applications_user_id ON applications(user_id);
CREATE INDEX IF NOT EXISTS ix_applications_status ON applications(status);

CREATE TABLE IF NOT EXISTS cover_letters (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    job_title VARCHAR(180) NOT NULL,
    body TEXT NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS ix_cover_letters_user_id ON cover_letters(user_id);

CREATE TABLE IF NOT EXISTS interview_sessions (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    role_title VARCHAR(180) NOT NULL,
    score INTEGER NOT NULL,
    feedback TEXT NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS ix_interview_sessions_user_id ON interview_sessions(user_id);

CREATE TABLE IF NOT EXISTS resume_ranking_batches (
    id SERIAL PRIMARY KEY,
    recruiter_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    job_title VARCHAR(180) NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS ix_resume_ranking_batches_recruiter_id ON resume_ranking_batches(recruiter_id);

CREATE TABLE IF NOT EXISTS resume_ranking_items (
    id SERIAL PRIMARY KEY,
    batch_id INTEGER NOT NULL REFERENCES resume_ranking_batches(id) ON DELETE CASCADE,
    filename VARCHAR(255) NOT NULL,
    ats_score INTEGER NOT NULL,
    match_score INTEGER NOT NULL,
    matched_skills TEXT NOT NULL DEFAULT '[]',
    missing_skills TEXT NOT NULL DEFAULT '[]'
);
CREATE INDEX IF NOT EXISTS ix_resume_ranking_items_batch_id ON resume_ranking_items(batch_id);

CREATE TABLE IF NOT EXISTS email_reports (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    report_type VARCHAR(50) NOT NULL,
    recipient VARCHAR(254) NOT NULL,
    sent_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS ix_email_reports_user_id ON email_reports(user_id);

CREATE TABLE IF NOT EXISTS audit_events (
    id SERIAL PRIMARY KEY,
    actor_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    action VARCHAR(80) NOT NULL,
    target_type VARCHAR(60) NOT NULL,
    target_id VARCHAR(80),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS ix_audit_events_actor_id ON audit_events(actor_id);
