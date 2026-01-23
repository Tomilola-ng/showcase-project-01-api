from tortoise import BaseDBAsyncClient

RUN_IN_TRANSACTION = True


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        CREATE TABLE IF NOT EXISTS "messages" (
    "id" UUID NOT NULL PRIMARY KEY,
    "status" VARCHAR(20) NOT NULL DEFAULT 'open',
    "name" VARCHAR(255) DEFAULT 'Message Name',
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS "idx_messages_created_c3e88b" ON "messages" ("created_at");
COMMENT ON COLUMN "messages"."status" IS 'OPEN: open\nCLOSED: closed';
COMMENT ON TABLE "messages" IS 'Table: messages';
        CREATE TABLE IF NOT EXISTS "chats" (
    "id" UUID NOT NULL PRIMARY KEY,
    "value" TEXT NOT NULL,
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "file_id" INT REFERENCES "fileasset" ("id") ON DELETE SET NULL,
    "message_id" UUID NOT NULL REFERENCES "messages" ("id") ON DELETE CASCADE,
    "sender_id" UUID NOT NULL REFERENCES "accounts" ("id") ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS "idx_chats_message_f5e04b" ON "chats" ("message_id");
CREATE INDEX IF NOT EXISTS "idx_chats_sender__b2dda8" ON "chats" ("sender_id");
CREATE INDEX IF NOT EXISTS "idx_chats_created_fa4464" ON "chats" ("created_at");
COMMENT ON TABLE "chats" IS 'Table: chats';
        CREATE TABLE "message_participants" (
    "messages_id" UUID NOT NULL REFERENCES "messages" ("id") ON DELETE CASCADE,
    "account_id" UUID NOT NULL REFERENCES "accounts" ("id") ON DELETE CASCADE
);"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        DROP TABLE IF EXISTS "message_participants";
        DROP TABLE IF EXISTS "message_participants";
        DROP TABLE IF EXISTS "messages";
        DROP TABLE IF EXISTS "chats";"""


MODELS_STATE = (
    "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"
    "+Z3iKl90ClO6RSDVSbapEK7sacKGH+P+BdZjg="
)
