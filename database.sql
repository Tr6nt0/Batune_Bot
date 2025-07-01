CREATE TABLE submissions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    forecast TEXT UNIQUE,
    source TEXT NOT NULL,
    status TEXT DEFAULT 'pending',
    submitted_by INTEGER,
    submitted_guild INTEGER,
    submitted_time DATETIME DEFAULT CURRENT_TIMESTAMP
)

CREATE TABLE fortunes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    batune_id INTEGER UNIQUE,
    guild_id INTEGER,
    global_id INTEGER,
    forecast TEXT UNIQUE,
    used BOOLEAN DEFAULT 0,
    source TEXT NOT NULL,
    approved_by INTEGER,
    approved_time DATETIME
)

CREATE TABLE queue_state (
    batune_index INTEGER DEFAULT 0
)
