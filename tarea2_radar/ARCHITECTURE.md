                    Usuario
                       │
                       ▼
                    app.py
                       │
                       ▼
                   search.py
                       │
             ┌─────────┴─────────┐
             ▼                   ▼
      Filtros estructurados   Consulta semántica
             │                   │
             ▼                   ▼
          ChromaDB           Embeddings
             │                   │
             └─────────┬─────────┘
                       ▼
                  Resultados
                       │
                       ▼
                radar_engine.py
                       │
                       ▼
                    risk.py
                       │
                       ▼
              Ranking + señales
                       │
                       ▼
                  Resultado
