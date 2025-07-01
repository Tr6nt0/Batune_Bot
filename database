CREATE TABLE fortunes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,   -- Management ID
    global_id INTEGER UNIQUE,               -- Global ID (for Batune/original)
    guild_id INTEGER,                       -- Guild-specific ID
    forecast TEXT UNIQUE,                   -- Fortune text
    used BOOLEAN DEFAULT 0,                 -- Has been posted
    source TEXT NOT NULL,                   -- 'global' or 'guild'
    approved BOOLEAN DEFAULT 0,             -- Approval status (guild only)
    origin_guild INTEGER,                   -- Guild where submitted
    added_time DATETIME DEFAULT CURRENT_TIMESTAMP
)
