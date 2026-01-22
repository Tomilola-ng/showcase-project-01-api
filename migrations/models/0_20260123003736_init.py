from tortoise import BaseDBAsyncClient

RUN_IN_TRANSACTION = True


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        CREATE TABLE IF NOT EXISTS "aerich" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "version" VARCHAR(255) NOT NULL,
    "app" VARCHAR(100) NOT NULL,
    "content" JSONB NOT NULL
);
CREATE TABLE IF NOT EXISTS "fileasset" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "key" VARCHAR(255) NOT NULL,
    "alt_text" VARCHAR(255),
    "content_type" VARCHAR(100),
    "file_size" INT
);
COMMENT ON TABLE "fileasset" IS 'File model';
CREATE TABLE IF NOT EXISTS "accounts" (
    "id" UUID NOT NULL PRIMARY KEY,
    "role" VARCHAR(50) NOT NULL DEFAULT 'regular',
    "first_name" VARCHAR(255) NOT NULL,
    "last_name" VARCHAR(255) NOT NULL,
    "state" VARCHAR(255),
    "country" VARCHAR(255),
    "email" VARCHAR(255) UNIQUE,
    "phone_number" VARCHAR(20),
    "password" VARCHAR(255) NOT NULL,
    "status" VARCHAR(50) NOT NULL DEFAULT 'active',
    "last_login_at" TIMESTAMPTZ,
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "image_id" INT REFERENCES "fileasset" ("id") ON DELETE SET NULL
);
CREATE INDEX IF NOT EXISTS "idx_accounts_email_e90d21" ON "accounts" ("email");
CREATE INDEX IF NOT EXISTS "idx_accounts_role_c24b27" ON "accounts" ("role");
CREATE INDEX IF NOT EXISTS "idx_accounts_status_973bef" ON "accounts" ("status");
CREATE INDEX IF NOT EXISTS "idx_accounts_role_600dd4" ON "accounts" ("role", "status");
COMMENT ON COLUMN "accounts"."role" IS 'REGULAR: regular\nADMIN: admin';
COMMENT ON COLUMN "accounts"."status" IS 'ACTIVE: active\nSUSPENDED: suspended\nPENDING_VERIFICATION: pending_verification\nDEACTIVATED: deactivated';
COMMENT ON TABLE "accounts" IS 'Table: accounts';"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        """


MODELS_STATE = (
    "eJztmVlv2zgQgP+KoKcUyAatG6dFUBRQfLTaJnbhI7toUgi0RCtEJEolqSTewv99Seo+7F"
    "iGndi7fjHs4Qw185HmjIa/VdezoENPNEiQeaeeK79VDFzIvxRGjhUV+H4qFwIGJo5UBanO"
    "hDICTMalU+BQyEUWpCZBPkMe5lIcOI4QeiZXRNhORQFGvwJoMM+G7A4SPnDzk4sRtuATpP"
    "FP/96YIuhYOVeRJZ4t5Qab+VKmY9aViuJpE8P0nMDFqbI/Y3ceTrQRZkJqQwwJYFBMz0gg"
    "3BfeRXHGEYWepiqhixkbC05B4LBMuCsyMD0s+HFvqAzQFk/5o/Hu9MPpx/dnpx+5ivQkkX"
    "yYh+GlsYeGkkBvpM7lOGAg1JAYU24PkFDhUgle6w6QanoZkwJC7ngRYQxsGcNYkEJMN86G"
    "KLrgyXAgtpnY4I1mcwmza23Q+qoNjrjWGxGNxzdzuMd70VAjHBNgU5Dir1EDYqS+nwDfvX"
    "27AkCutRCgHMsD5E9kMPwP5iH+Oez3qiFmTAogx5gHeGMhkx0rDqLs525iXUJRRC2cdin9"
    "5WThHV1pfxe5ti77F5KCR5lN5CxyggvOWByZ0/vMn18IJsC8fwTEMkojXsNbpFsechtuUQ"
    "IwsCUrEbGIL04ipukFmFXml2hoeYIJlehKKUYdCbNzJWuUXY2q8eeTz40KXYAclYtvVOJx"
    "v+Q3ygALaEZ6rCSyWvlqPNbbNRJWECDrRNiss7efz1vqp2mATQFUkU8SH6ef1a1sdrmv35"
    "+9Ke5hGd3yBBYTLx+8HRy4EqfO3QDYhCWsse3LncIqgXbgAFLGqA46X8aX2uBciVRusda+"
    "0nt8k1ouwsUdvMox3VzllG4uPqSbpTN6ighlhvxVI9flrfYz5W2lZnDAGjRzRgeYCUxx5N"
    "YCmRisBTE6L/9bDGU2JLM6FDMmB44xx7BOqEExMdgIw62/lG6foM8pQINn8AkkdUAW7fZz"
    "T66SuBuLE3ejlLh9QOmjRyqKziUoMzaHPJPLMwFdt+RMrV+w6OSvSugBVtScWmukX3fEe5"
    "BQuMXD8fB7p9futM8VGlAf8kmtWyxEeu+Lcd0Z6F29pY30Pi9LxShfCuMBEjRFJhBz3uJ2"
    "R86pjcQcFpQTy3B2on6VtZPj2QgboKLT0OaeMuTCJYVX1riwglZkfRJ/2cmTZgnSkX7VGY"
    "60q++5vkObr6UYaUjprCA9OivgTyZR/tJHXxXxU/nR73WKr3aJ3uiHKnwCAfMM7D0awMqG"
    "HYtjUb5cIVCgXWMt85YbWMjXOOt4DFYfO7NoH+3JykZbfunCBr615sLmLQ8L+6oLGzmf6X"
    "q5wIZGvbuajMnzNzY7ccRu4s6m1LUtQCwT7HoEIht/g7NSBVLgFrVdu8iBGqVwNyHO440Q"
    "S1MvCHhMOqq5/cFj5JFBJqMcdkZKb3x5qc5fp+Gd4q1oeefYL256T7kaSNSe7XqLWRU5Ta"
    "nhnR86XLS++EXrPazVVonUD+9d6QWrwwwGnyoqgiW3rBmb/ewEbKfLJ69NQxQ1aBbt9pLo"
    "Vu6uxTltUPRPBc6FZ2PO5v9c2SxOz5k/f3hRa8hsX9F8uYjsu98G0JGtiMV1T+a6eecAL6"
    "p65puvVOb/Aqh4KfE="
)
