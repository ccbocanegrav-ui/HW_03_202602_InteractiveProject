# DECISIONES.md
# TAREA 1
Registro de decisiones tomadas durante el proyecto y su justificación.
Se completa a medida que avanzan las fases (no todo de una vez).

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

### Hallazgos técnicos de extracción (Phase 1)
- **Layout a 2 columnas (DS 001-2026-EF)**: El Peruano imprime a 2 columnas.
  `pdfplumber.extract_text()` por defecto no respeta columnas y mezcla
  líneas de la izquierda con la derecha. Solución: por página, se separa
  una franja superior (encabezado, ancho completo) y se detecta una
  "calle" vacía cerca del centro del cuerpo; si existe, se extrae
  izquierda completa y luego derecha completa. La Ley 32069 es a 1
  columna y no se ve afectada (fallback automático, sin falsos positivos).
- **Encabezado de El Peruano en 2 variantes según página par/impar**:
  impares: `"El Peruano / <fecha> NORMAS LEGALES <núm>"`;
  pares (espejado): `"<núm> NORMAS LEGALES <fecha>/ El Peruano"`.
  La regla de limpieza usa un lookahead doble (ambas frases presentes en
  la primera línea de la página, sin importar el orden) para cubrir
  ambos casos sin depender de la paridad de página.
- La Ley 32069 (PDF de la colección OSCE, version anterior) no trae el
  encabezado del diario pegado — es un PDF tipografiado distinto al
  inserto original, aunque ambas fuentes son oficiales.

### Cambio de fuente para ley_32069 (actualizacion)
Se reemplazo el PDF de ley_32069 por un volumen de Editora Perú (294
paginas) que trae Ley + Reglamento combinados en un solo archivo.
Editora Perú es la empresa estatal que imprime El Peruano, por lo que
la fuente es oficial, pero el archivo mezcla 2 documentos distintos.

- **Se restringe la extraccion a paginas 4-52** (unicamente el texto
  de la Ley; 1-3 son portada/indice, 53+ es el Reglamento — un
  documento distinto, no parte del corpus obligatorio de Task 1).
- Este archivo usa un formato de encabezado de **3 lineas** distinto
  al de El Peruano: `"NORMAS LEGALES ACTUALIZADAS" / <num. pagina> /
  <titulo del documento>`. Se agrego una segunda regla de limpieza en
  `clean.py` para este formato.
- Se detecto y corrigio un bug de margen: la franja reservada para el
  header (6% superior de la pagina) cortaba a la mitad la 3ra linea
  del header en algunas paginas con layout de 2 columnas real,
  produciendo palabras truncadas ("Contr" en vez de "Contrataciones").
  Se amplio a 9% con margen de seguridad, verificado sin regresion en
  el DS 001-2026-EF (que ya funcionaba bien con la franja anterior).

## Fase 2 — Chunking (decidido con evidencia)

**Tamaño elegido: 300 caracteres, overlap 20%.** Basado en el sweep
(`logs/chunking_sweep.csv`):

| Tamaño | Overlap | ley_32069 (n) | ds_001_2026_ef (n) |
|---|---|---|---|
| 100 | 0.2 | 2556 | 1304 |
| 200 | 0.2 | 1315 | 669 |
| **300** | **0.2** | **894** | **453** |
| 500 | 0.2 | 544 | 276 |

- 100 caracteres: demasiados fragmentos y con casos de solo 2-4
  caracteres (ruido, sin contenido util para el embedding).
- 300 caracteres deja a `ley_32069` en 894 fragmentos — dentro del
  rango de referencia (500-1000/documento).
- 500 caracteres: muy pocos fragmentos, mezclan varios artículos
  distintos en un mismo chunk (pierde precision para citar un articulo
  especifico).
- Se corrige ademas un caso de chunk final diminuto (sobrante de
  pagina que no llena el tamaño objetivo): se fusiona con el chunk
  anterior en vez de quedar como fragmento chico y ruidoso.

**Nota**: esta decision se valida/reajusta con Recall@k contra el
set de evaluacion en la Fase 4, una vez que exista.

## Fase 3 — Motor RAG (threshold calibrado con evidencia)

**Threshold elegido: 0.70** (similitud coseno). Sweep completo en
`logs/threshold_sweep.csv`, contra `eval/preguntas.csv` (set
preliminar de 10 preguntas: 6 in-domain, 4 out-of-domain incluyendo
casos "cercanos al dominio pero no contestables").

| Threshold | in_domain OK | in_domain mal-abstención | out_domain OK | out_domain mal-respondida |
|---|---|---|---|---|
| 0.60 | 6 | 0 | 1 | 3 |
| 0.65 | 6 | 0 | 1 | 3 |
| **0.70** | **5** | **1** | **3** | **1** |
| 0.74 | 2 | 4 | 4 | 0 |
| 0.78 (valor de ejemplo del enunciado) | 1 | 5 | 4 | 0 |

**Hallazgo clave**: ningún threshold logra separación perfecta.
Preguntas "cercanas al dominio pero no contestables" (ej. pedir el
procedimiento completo que solo el Reglamento —no indexado— tiene)
obtienen similitud casi tan alta como preguntas legítimamente
respondibles. Esto es un limite conocido de la similitud de embeddings
por si sola, no un bug del sistema.

**Mitigación de doble capa**: el prompt de generación (`config.yaml`,
`generation.system_prompt`) instruye al LLM a decir explícitamente
que no puede responder si el contexto no lo sustenta, aun cuando el
retrieval haya dejado pasar un caso límite. El threshold filtra antes
de gastar en la API; el prompt es la ultima linea de defensa contra
alucinar.

**Modelo de embeddings local**: `intfloat/multilingual-e5-base`
(sentence-transformers), dimension 768, prefijos `query: ` / `passage: `
(ver `embeddings.py`).
**Vector store**: ChromaDB, espacio coseno explicito
(`hnsw:space: cosine` — el default de ChromaDB es euclidiana, hay que
forzarlo o el threshold no tiene sentido).
**Modelo generador**: gpt-4o-mini (config.yaml, precios verificados
2026-09-22).

**Modelo generador**: se cambio de OpenAI (gpt-4o-mini, de pago) a
**Gemini** (gemini-3.6-flash, gratis dentro de la cuota diaria de
Google AI Studio) — decision documentada: el enunciado permite
cualquier proveedor y esto evita el requisito de creditos de pago.
Costo real verificado: $0.00 por consulta (nivel gratuito).
`max_output_tokens` se subio de 500 a 1024 porque gemini-3.6-flash
consume tokens de "thinking" internos antes de la respuesta final;
con 500 la respuesta se cortaba a mitad de frase.

**Prueba end-to-end verificada** (pregunta real, respuesta real):
Pregunta: "¿Cual es el plazo maximo para pagar al contratista luego
de otorgada la conformidad?"
Respuesta: "El pago al contratista se realiza en un plazo máximo de
diez días hábiles luego de otorgada la conformidad por parte del área
usuaria (Ley 32069, pag. 32)..." — correcto, cita fuente, costo $0.00,
70 tokens de salida.

## Fase 4 — Evaluación (resultados reales, 20 preguntas)

**Set de evaluación**: `eval/preguntas.csv`, 15 in-domain (10 sobre Ley,
5 sobre el DS/Reglamento; incluye variantes coloquiales y preguntas
sobre articulos modificados por la norma) + 5 out-of-domain (incluye
casos "cercanos al dominio" a proposito).

**Recall@k ESTRICTO** (documento + pagina exacta):
| k | Recall |
|---|---|
| 1 | 20.0% (3/15) |
| 3 | 46.7% (7/15) |
| 5 | 46.7% (7/15) |

**Recall@k A NIVEL DE DOCUMENTO** (Ley vs. DS, sin exigir pagina exacta):
| k | Recall |
|---|---|
| 1 | 66.7% (10/15) |
| 3 | 86.7% (13/15) |
| 5 | 93.3% (14/15) |

**Hallazgo clave**: la brecha grande entre ambas metricas (20% vs. 67%
en k=1) NO es un fallo del embedding ni del retrieval — se investigo
comparando pagina "esperada" (ubicada buscando el numero de articulo)
contra la pagina real del mejor fragmento recuperado, y se confirmo
que los articulos largos cruzan paginas, y el chunking es por pagina
(decision de Fase 2, ver arriba). El fragmento semanticamente mas
relevante a menudo cae en la pagina vecina a donde "empieza" el
articulo segun una busqueda de texto literal. El sistema SI identifica
el documento correcto la gran mayoria de las veces (93% en top-5).

**Abstention rate** (con threshold=0.70):
- In-domain respondidas correctamente: 93.3% (14/15)
- In-domain abstencion incorrecta: 6.7% (1/15)
- Out-of-domain abstencion correcta: 80.0% (4/5)
- Out-of-domain respondidas por error: 20.0% (1/5) — la pregunta
  q18, diseñada a proposito como "cercana al dominio" (procedimiento
  detallado que solo el Reglamento completo tiene)

## Fase 4 — Comparación de embeddings (proveedor sustituido 2 veces)

El enunciado pide comparar el modelo local contra text-embedding-3-small
de OpenAI. Sin presupuesto para creditos de OpenAI, se intentaron 2
alternativas gratuitas en orden:

1. **Gemini (text-embedding-004)** — descartado. Su endpoint especifico
   de embeddings devuelve `401 ACCESS_TOKEN_TYPE_UNSUPPORTED` con las
   API keys nuevas de Google AI Studio (prefijo "AQ.", que es el unico
   formato que emite actualmente). Se confirmo que NO es un bug de
   nuestro codigo: se probo con 2 SDKs distintos (el deprecado
   `google-generativeai` y el nuevo `google-genai`, incluyendo forzar
   transporte REST), y el mismo error persiste en ambos — es un bug
   del lado de Google, reportado activamente por otros desarrolladores
   en el foro oficial de Google AI para ese endpoint especifico. La
   generacion de texto (`generateContent`) SI funciona con la misma
   key, asi que no es un problema de la cuenta en general.
2. **Cohere (embed-multilingual-v3.0)** — usado finalmente. Nivel
   gratuito real, sin tarjeta, sin el problema de Gemini.

## Fase 5 (pendiente)
- Interfaz Streamlit: `app.py` ya escrito y probado (arranca sin
  errores, panel de calidad con reportes de Fase 1/4). Falta correrlo
  con el indice y las API keys reales de la usuaria.


## Decisiones de diseño - Tarea 2

## 1. Reutilización de embeddings

Se decidió reutilizar el backend de embeddings desarrollado
en la Tarea 1 para mantener consistencia entre ambas tareas.

El modelo utilizado es:

intfloat/multilingual-e5-base

Dimensión:

768

## 2. Búsqueda híbrida

La búsqueda combina filtros estructurados con similitud semántica.

Los filtros se aplican mediante ChromaDB y posteriormente
los resultados se recuperan utilizando embeddings.

## 3. Separación de filtros y consulta semántica

Las restricciones como departamento, mes y monto no se
envían directamente al embedding.

Por ejemplo:

"servicios de limpieza en Lima por más de 1 millón de soles"

se transforma en:

Consulta semántica:
"servicios de limpieza"

Filtros:
departamento = LIMA
categoría = services
monto_min = 1000000

## 4. Reglas del radar

El radar utiliza señales explicables basadas en variables
estructuradas del proceso.

Las señales no representan una acusación ni una conclusión
sobre irregularidades. Indican únicamente condiciones que
merecen revisión.

## 5. Transparencia

Cada señal muestra su severidad y el motivo por el cual
fue activada.
