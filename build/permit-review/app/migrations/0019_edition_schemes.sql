-- =============================================================================
-- Newcastle Permit Review — 0019_edition_schemes.sql
--
-- Town Meeting adopted CZC v1.0 on September 14, 2026. The app now holds TWO
-- adopted Codes: the one adopted November 3, 2020 (eight articles, article
-- scheme 'adopted', now superseded) and v1.0 (nine articles, article scheme
-- 'adopted-v1.0', current). 0001_init.sql's CHECK only admitted 'adopted' and
-- 'draft', so it could not record the new Code's numbering -- and
-- ingest/worklist.py reads this column into citations, so it has to be right.
--
-- The new CHECK admits 'draft' and any 'adopted…' scheme, so a future adoption
-- adds its scheme in app/citation.py SCHEME_TO_DRAFT without another migration.
-- Which schemes are REAL is enforced there and by app/renum_check.py, against
-- the rulesets themselves -- not by a list frozen into SQL.
--
-- WHY NOT THE 0002/0003 TABLE REBUILD. Seven tables reference rulesets(id), and
-- criteria_sets, field_defs and rules are ON DELETE CASCADE: dropping a
-- populated rulesets table deletes their rows, and foreign keys cannot be
-- switched off inside the migration's transaction. A rebuild would therefore be
-- safe only on an empty database, and a migration must also carry a database
-- that holds real work (tests/test_deadlines.py migrates one forward).
--
-- WHAT INSTEAD. Loosening a CHECK changes no stored byte, which is the case
-- SQLite documents as safe to make by editing the table's schema text in place
-- (https://sqlite.org/lang_altertable.html, "Making Other Kinds Of Table Schema
-- Changes"). writable_schema = RESET makes SQLite re-read the schema before the
-- transaction continues. The guard afterwards fails the migration -- rolling
-- all of it back -- unless the rewrite actually landed, so a CHECK written in
-- different text than 0001's cannot be skipped silently.
-- =============================================================================

PRAGMA writable_schema = ON;
UPDATE sqlite_schema
   SET sql = replace(sql,
                     'CHECK (article_scheme IN (''adopted'',''draft''))',
                     'CHECK (article_scheme = ''draft'' OR article_scheme GLOB ''adopted*'')')
 WHERE type = 'table' AND name = 'rulesets';
PRAGMA writable_schema = RESET;

CREATE TEMP TABLE _0019_rewrite_landed (landed INTEGER NOT NULL CHECK (landed = 1));
INSERT INTO _0019_rewrite_landed (landed)
SELECT (SELECT instr(sql, 'article_scheme GLOB ''adopted*''') > 0
                AND instr(sql, 'article_scheme IN (''adopted'',''draft'')') = 0
          FROM sqlite_schema WHERE type = 'table' AND name = 'rulesets');
DROP TABLE _0019_rewrite_landed;
