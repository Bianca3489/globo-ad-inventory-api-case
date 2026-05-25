# TV Globo – Ad Inventory & Audience REST API

API desenvolvida para o desafio técnico de Engenharia de Dados / Backend da TV Globo.  
Fornece audiência prevista e segundos disponíveis para anúncios por programa ou período.

---

## Estrutura do projeto

```
globo_challenge/
├── app/
│   ├── __init__.py
│   ├── main.py            # Aplicação FastAPI (endpoints)
│   ├── preprocessing.py   # Pipeline de pré-processamento com Pandas
│   └── schemas.py         # Modelos Pydantic (request / response)
├── data/
│   ├── tvaberta_program_audience.csv
│   └── tvaberta_inventory_availability.csv
├── tests/
│   ├── test_preprocessing.py
│   └── test_api.py
├── rest_client.py         # Cliente de demonstração
└── requirements.txt
```

---

## Instalação

```bash
python -m venv .globo_venv && source .globo_venv/bin/activate
pip install -r requirements.txt
```

---

## Rodar a API

```bash
uvicorn app.main:app --reload
```

Acesse a documentação interativa (Swagger UI) em:  
`http://localhost:8000/docs`

---

## Endpoints

### `GET /health`
Verifica se a API está no ar.

### `GET /program`
Retorna segundos disponíveis e audiência prevista para um programa em uma data.

| Parâmetro        | Tipo   | Exemplo       |
|------------------|--------|---------------|
| `program_code`   | string | `HUCK`        |
| `exhibition_date`| date   | `2020-08-01`  |

### `GET /period`
Retorna dados de todos os programas exibidos num intervalo de datas.

| Parâmetro    | Tipo | Exemplo       |
|--------------|------|---------------|
| `start_date` | date | `2020-07-25`  |
| `end_date`   | date | `2020-08-08`  |

---

## Testes unitários

```bash
pytest tests/ -v
```

---

## Cliente de demonstração

```bash
# Em um terminal:
uvicorn app.main:app --reload

# Em outro:
python rest_client.py
```

---

## Pré-processamento (lógica central)

O script `app/preprocessing.py`:

1. **Carrega** os dois CSVs (audiência histórica e inventário disponível).
2. **Extrai** o dia da semana de cada exibição.
3. **Calcula** `predicted_audience` = mediana das últimas 4 audiências por `(signal, program_code, weekday)`.
4. **Realiza o join** entre inventário e audiência prevista.
5. **Retorna** o dataframe mestre mantido em memória para consultas rápidas.
