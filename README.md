# TV Globo — Ad Inventory & Audience REST API

> REST API desenvolvida como desafio técnico de Engenharia de Dados da TV Globo.  
> Fornece audiência prevista e segundos disponíveis para anúncios por programa ou período, alimentando um algoritmo de otimização da grade de anúncios.

---

## Contexto do problema

O time de algoritmos da TV Globo precisa otimizar a grade de anúncios: dado um objetivo de audiência, o algoritmo escolhe em quais programas e horários veicular os anúncios para atingir esse objetivo com eficiência.

Para funcionar, esse algoritmo precisa de dois dados por programa:

- **Quantos segundos** estão disponíveis para anúncios naquele programa
- **Qual audiência** aquele programa deve ter numa exibição futura

Esta API é o componente responsável por fornecer esses dados. Ela pré-processa arquivos históricos de audiência e inventário, calcula a audiência prevista e os expõe via endpoints REST.

---

## Decisões técnicas

### Por que FastAPI e não Flask?

FastAPI foi escolhido por três razões principais:

1. **Validação automática** via Pydantic — parâmetros com tipo errado são rejeitados antes de chegar à lógica de negócio, com mensagens de erro claras em JSON
2. **Documentação Swagger gerada automaticamente** em `/docs` — sem esforço extra
3. **Performance** — assíncrono nativo, mais adequado para APIs de alto volume

### Por que mediana e não média para prever audiência?

A média é sensível a outliers. Um evento atípico como um jogo da Copa do Mundo ou uma notícia de grande impacto pode triplicar a audiência de um programa num dia específico. Se usássemos a média, esse evento distorceria todas as previsões futuras. A mediana ignora esses extremos e representa o comportamento típico do programa.

### Por que as últimas 4 exibições?

4 semanas equivalem a aproximadamente 1 mês de histórico recente. Esse número captura a sazonalidade semanal sem diluir o comportamento atual com dados muito antigos. Com 20 semanas de histórico, por exemplo, uma mudança recente no programa demoraria meses para refletir na previsão.

### Por que LEFT JOIN e não INNER JOIN?

Com INNER JOIN, perderíamos todos os programas que têm inventário disponível mas ainda não têm histórico de audiência — programas novos seriam silenciosamente excluídos. O LEFT JOIN preserva todos os registros de inventário e preenche `predicted_audience` com `null` quando não há histórico, mantendo a integridade dos dados.

### Por que Pandas e não Spark?

O volume de dados do desafio (≈ 9.000 registros de audiência e ≈ 2.300 de inventário) é pequeno e bem adequado para Pandas. PySpark introduziria complexidade operacional desnecessária para esse contexto. Em produção com volumes maiores, a migração para Spark seria natural sem alterar a lógica de negócio.

### Carregamento em memória (singleton)

O dataframe mestre é carregado uma única vez na inicialização da API. Todas as requisições reutilizam o mesmo objeto em memória, evitando leituras repetidas de disco. Em produção, esse padrão seria substituído por consultas ao banco de dados — conforme previsto na arquitetura de nuvem.

---

## Arquitetura

```
CSVs (audiência + inventário)
        ↓
preprocessing.py   ← pipeline Pandas: normalização, extração de weekday,
        ↓             cálculo de mediana, LEFT JOIN
  dataframe mestre (em memória)
        ↓
   main.py (FastAPI)
        ↓
  /health   /program   /period
        ↓
  Algoritmo de otimização de grade
```

---

## Estrutura do projeto

```
globo-ad-inventory-api-case/
├── app/
│   ├── __init__.py
│   ├── main.py            # Endpoints FastAPI
│   ├── preprocessing.py   # Pipeline de dados com Pandas
│   └── schemas.py         # Modelos Pydantic (validação de entrada e saída)
├── tests/
│   ├── test_api.py        # 10 testes dos endpoints
│   └── test_preprocessing.py  # 5 testes do pipeline de dados
├── rest_client.py         # Cliente de demonstração
├── requirements.txt
└── README.md
```

> **Nota:** A pasta `data/` com os CSVs não está versionada por conter dados fictícios do processo seletivo.

---

## Stack

| Tecnologia | Versão | Uso |
|-----------|--------|-----|
| Python | 3.11+ | Linguagem principal |
| FastAPI | 0.110+ | Framework da API REST |
| Pandas | 2.0+ | Pipeline de dados |
| Pydantic | 2.0+ | Validação de schemas |
| Uvicorn | 0.29+ | Servidor ASGI |
| pytest | 8.0+ | Testes unitários |
| httpx | 0.27+ | Cliente HTTP nos testes |

---

## Instalação

```bash
# Clonar o repositório
git clone https://github.com/Bianca3489/globo-ad-inventory-api-case.git
cd globo-ad-inventory-api-case

# Criar e ativar o ambiente virtual
python -m venv .venv
source .venv/bin/activate

# Instalar dependências
pip install -r requirements.txt
```

---

## Rodando a API

```bash
uvicorn app.main:app --reload
```

Acesse a documentação interativa (Swagger UI) em `http://localhost:8000/docs`

---

## Endpoints

### `GET /health`
Verifica se a API está no ar e quantos registros estão carregados.

```json
{ "status": "ok", "total_records": 2291 }
```

---

### `GET /program`
Retorna segundos disponíveis e audiência prevista para um programa em uma data específica. Busca todos os sinais (localidades) para aquele programa/data.

| Parâmetro | Tipo | Exemplo |
|-----------|------|---------|
| `program_code` | string | `HUCK` |
| `exhibition_date` | date | `2020-08-01` |

```bash
curl "http://localhost:8000/program?program_code=HUCK&exhibition_date=2020-08-01"
```

Erros: `404` se o programa não existir na data informada.

---

### `GET /period`
Retorna todos os programas exibidos num intervalo de datas com seus respectivos segundos disponíveis e audiência prevista.

| Parâmetro | Tipo | Exemplo |
|-----------|------|---------|
| `start_date` | date | `2020-07-25` |
| `end_date` | date | `2020-08-08` |

```bash
curl "http://localhost:8000/period?start_date=2020-07-25&end_date=2020-08-08"
```

Erros: `422` se `end_date` for anterior a `start_date`. `404` se não houver programas no período.

---

## Pipeline de pré-processamento

O script `app/preprocessing.py` executa 4 etapas em sequência:

1. **Carga** — lê os dois CSVs normalizando separadores e formatos de data diferentes
2. **Extração de weekday** — `dt.dayofweek` extrai o dia da semana (0=Seg, 6=Dom), chave para o agrupamento
3. **Cálculo da audiência prevista** — mediana das últimas 4 audiências por `(signal, program_code, weekday)`
4. **JOIN** — LEFT JOIN entre inventário e audiência prevista, preservando todos os registros

**Dataframe resultante:**

| Coluna | Tipo | Descrição |
|--------|------|-----------|
| `signal` | string | Sinal/localização (ex: SP1, BH) |
| `program_code` | string | Código do programa (ex: HUCK) |
| `weekday` | int (0–6) | Dia da semana |
| `date` | date | Data de exibição |
| `available_time` | int | Segundos disponíveis para anúncios |
| `predicted_audience` | float | Mediana das últimas 4 audiências |

---

## Testes

```bash
pytest tests/ -v
```

**Resultado esperado: 15 passed**

| Arquivo | Testes | Cobertura |
|---------|--------|-----------|
| `test_api.py` | 10 | Todos os endpoints: sucesso e erros (404, 422) |
| `test_preprocessing.py` | 5 | Pipeline: mediana, agrupamento, join |

Os testes da API usam `monkeypatch` para substituir o dataframe real por um controlado, tornando os testes determinísticos e independentes dos arquivos CSV.

---

## Cliente de demonstração

```bash
# Terminal 1 — subir a API
uvicorn app.main:app --reload

# Terminal 2 — executar o cliente
python rest_client.py
```

O cliente demonstra todos os cenários: sucesso nos três endpoints, programa inexistente (404) e datas invertidas (422).

---

## Arquitetura de deploy (Google Cloud Platform)

Para produção, a arquitetura proposta é serverless no GCP:

```
Cloud Storage (CSVs)
      ↓
Cloud Scheduler → Cloud Workflows → Cloud Run Job (preprocessing)
                                          ↓
                                      Cloud SQL (PostgreSQL)
                                          ↓
                                    Pub/Sub (confirma gravação)
                                          
Cloud Run (API FastAPI) ← consultas → Cloud SQL
```

| Componente | Serviço GCP | Justificativa |
|-----------|-------------|---------------|
| Armazenamento CSVs | Cloud Storage | Barato, durável, integrado ao GCP |
| Agendamento diário | Cloud Scheduler | Cron gerenciado |
| Orquestração e retry | Cloud Workflows | Persiste estado, retoma de onde parou em caso de falha |
| Job de processamento | Cloud Run Jobs | Serverless, escala a zero |
| Banco de dados | Cloud SQL (PostgreSQL) | SQL relacional com índices para queries por programa/período |
| API REST | Cloud Run | Serverless, escala conforme demanda |
| Confirmação de gravação | Cloud Pub/Sub | Evento publicado ao fim do job confirma sucesso |

---

## Autora

Desenvolvido por **Bianca Rodrigues** como parte do processo seletivo de Engenharia de Dados da TV Globo.
