# Dashboard de Preços — SINAPI + SEINFRA-CE (Portátil)

> 🇧🇷 Dashboard offline de consulta de preços da construção civil.
> Zero instalação. Funciona em Windows, Linux e Mac.

[![Licença](https://img.shields.io/badge/licença-MIT-blue)](LICENSE)
[![Plataforma](https://img.shields.io/badge/plataforma-Windows%20%7C%20Linux%20%7C%20Mac-lightgrey)]()

---

## O que é?

Ferramenta portátil para consultar **tabelas de preço da construção civil** — SINAPI (CAIXA, nacional) e SEINFRA-CE (Governo do Ceará).

**14.812 composições** de preço, com busca por palavra-chave, decomposição analítica e navegação hierárquica. Tudo offline, sem instalar nada.

### Fontes de dados

| Base | Fonte | Referência | Itens |
|---|---|---|---|
| SINAPI | CAIXA Econômica Federal | Abril/2026 (CE, sem desoneração) | 10.378 |
| SEINFRA-CE | Governo do Estado do Ceará | Versão 028 | 4.434 |

---

## ⚡ Uso rápido

### Windows
```
Duplo-clique em iniciar.bat
```

### Linux / Mac
```bash
./iniciar.sh
```

### Firefox (qualquer SO)
```
Arraste index.html para o Firefox
```

> ⚠️ **Chrome/Edge bloqueiam arquivos locais.** Use o `.bat` ou `.sh` para subir um mini servidor HTTP.

---

## Funcionalidades

| # | Funcionalidade |
|---|---|
| 🔤 | Busca por palavra-chave (código ou descrição) |
| 🔘 | Alternar entre SINAPI, SEINFRA ou AMBOS |
| 📊 | Decomposição analítica com soma/diferença/total |
| 🌳 | Árvore de grupos SINAPI + hierarquia SEINFRA |
| ⚠️ | Flag "SEM PREÇO" para itens sem cotação |
| 📋 | Botão copiar código |
| 📱 | Responsivo (celular e tablet) |
| 🌙 | Tema dark |
| 📴 | Modo offline após primeiro carregamento |

---

## Arquivos

```
precos_portatil/
├── index.html          ← Abra no navegador (1365 linhas)
├── dados.sqlite        ← Banco de dados portátil (19 MB)
├── iniciar.bat         ← Launcher Windows
├── iniciar.sh          ← Launcher Linux/Mac
├── export_to_sqlite.py ← Script para regenerar dados
└── README.md           ← Este arquivo
```

---

## Como funciona

O dashboard é uma **Single Page Application** (HTML + CSS + JS puro) que carrega um banco SQLite diretamente no navegador usando **[sql.js](https://github.com/sql-js/sql.js/)** (SQLite compilado para WebAssembly).

```
index.html  →  fetch('dados.sqlite')  →  sql.js (WASM)  →  consultas SQL
```

**Zero dependências externas** após o primeiro carregamento — o sql.js (~1 MB) é baixado do CDN na primeira execução e cacheado pelo navegador.

---

## Atualizar dados

Quando sair uma nova tabela SINAPI ou SEINFRA, regenere o SQLite:

```bash
# Requer Python 3 + MariaDB local com os bancos originais
python3 export_to_sqlite.py
```

Isso lê os bancos MariaDB (`sinapi_2026_04`, `seinfra_ce_028`) e gera um novo `dados.sqlite`.

> ⚠️ **Atenção:** o nome do banco SINAPI muda a cada mês (ex: `sinapi_2026_04` → `sinapi_2026_05`).
> Antes de executar, edite o arquivo `export_to_sqlite.py` e atualize a variável `DB_SINAPI`:
> ```python
> DB_SINAPI = "sinapi_2026_05"  # ← mude aqui
> ```
> O mesmo vale para o SEINFRA quando sair uma versão nova (ex: `seinfra_ce_029`).

---

## Licença

MIT — use, modifique e distribua livremente.

---

## Créditos

- Dados: [SINAPI/CAIXA](https://www.caixa.gov.br/poder-publico/modernizacao-gestao/sinapi/) e [SEINFRA-CE](https://www.seinfra.ce.gov.br/)
- Motor SQLite: [sql.js](https://github.com/sql-js/sql.js/)
- Desenvolvido com [Hermes Agent](https://hermes-agent.nousresearch.com/)
