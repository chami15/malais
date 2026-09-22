-- Esquema do Malais. Vive em .sql, não em string Python, pra ficar legível
-- como SQL de verdade (syntax highlight, diff limpo) e não como texto solto
-- dentro de um arquivo .py.
--
-- IMPORTANTE: isso roda toda subida (`preparar()` chama isto via
-- `executescript`). Alteração em coluna de tabela já existente NÃO passa por
-- aqui — `CREATE TABLE IF NOT EXISTS` não mexe em tabela que já existe. Coluna
-- nova é `_acrescentar_colunas()`, tabela renomeada é `_renomear_tabelas()`,
-- os dois em `app/banco/__init__.py`.

CREATE TABLE IF NOT EXISTS lembretes (
    id       INTEGER PRIMARY KEY AUTOINCREMENT,
    texto    TEXT NOT NULL,
    criada_em TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
);

CREATE TABLE IF NOT EXISTS historico (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    comando   TEXT NOT NULL,
    resposta  TEXT,
    criada_em TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
);
