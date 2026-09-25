-- Runs once, when the database volume is first created.
-- Installing the extension into template1 means Django's test databases get it too.
\connect template1
CREATE EXTENSION IF NOT EXISTS vector;
\connect actorconnect
CREATE EXTENSION IF NOT EXISTS vector;