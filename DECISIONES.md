# DECISIONES.md

Registro de decisiones tomadas durante el proyecto y su justificación.

## Fase 1 — Fuentes (Task 1)

### Documentos obligatorios
- **Ley N.° 32069** — Ley General de Contrataciones Públicas
  Fuente: https://www.gob.pe/institucion/osce/colecciones/45029-ley-n-32069-ley-general-de-contrataciones-publicas
  Fecha de descarga: <completar>
- **Decreto Supremo N.° 001-2026-EF** — modifica el Reglamento de la Ley 32069
  Fuente: https://busquedas.elperuano.pe/dispositivo/NL/2474920-3
  Fecha de descarga: <completar>
  Fecha de publicación (verificada): 08/01/2026

### Hallazgo de accesibilidad de fuentes (evidencia para el README)
Tanto gob.pe como busquedas.elperuano.pe implementan protección anti-bot que
bloquea la descarga automatizada de PDFs (error 418 / solo permiten
navegación humana con JS). Esto se documenta como hallazgo legítimo: la
descarga de ambos PDFs se hizo manualmente desde el navegador, con fecha
registrada arriba. Ver "Risk controls" del enunciado: es un hallazgo
válido sobre el estado del open data peruano, no una falla del proyecto.

### Documento opcional
- Pendiente de decidir (recomendado por el enunciado para enriquecer las
  preguntas de versiones de Fase 3/Phase 3).

## Fase 2+ (pendiente)
- Modelo de embeddings local: <por decidir — candidato: multilingual-e5-base>
- Modelo generador: <por decidir>
- Vector store: <por decidir — candidato: ChromaDB>
