# Reporte de calidad de datos — Tarea 2, Fase 2

Filas crudas: **14,186**
Filas finales: **14,186**

## Reglas de validación

| Regla | Registros marcados | Acción |
|---|---:|---|
| OCID faltante | 0 | ninguno encontrado |
| OCID duplicado | 0 | ninguno encontrado |
| Monto faltante | 0 | mantenido con advertencia; excluido de agregados monetarios |
| Monto igual a cero | 401 | mantenido con advertencia; excluido de agregados monetarios |
| Descripción faltante | 0 | corregido: se utiliza el título como respaldo; queda marcado descripcion_valida=False |
| Departamento no identificable | 0 | mantenido con advertencia; no se elimina del corpus, pero queda fuera del mapa |
| Inconsistencias de mayúsculas/acentos/espacios | 0 | corregido en columnas normalizadas; se conserva el nombre original para mostrarlo al usuario |
| TOTAL | 14186 -> 14186 | una fila por proceso identificado por OCID |

## Distribución por departamento

| Departamento | Procesos |
|---|---:|
| LIMA | 3,782 |
| CUSCO | 1,122 |
| ANCASH | 885 |
| AYACUCHO | 732 |
| PUNO | 704 |
| APURIMAC | 644 |
| CAJAMARCA | 574 |
| AREQUIPA | 540 |
| JUNIN | 511 |
| HUANCAVELICA | 465 |
| LA LIBERTAD | 459 |
| HUANUCO | 457 |
| PIURA | 442 |
| LORETO | 424 |
| SAN MARTIN | 389 |
| ICA | 310 |
| LAMBAYEQUE | 285 |
| UCAYALI | 272 |
| TACNA | 266 |
| MOQUEGUA | 237 |
| AMAZONAS | 218 |
| PASCO | 167 |
| CALLAO | 167 |
| MADRE DE DIOS | 91 |
| TUMBES | 43 |

## Procesos por mes

| Mes | Procesos |
|---|---:|
| 2026-01 | 1,012 |
| 2026-02 | 4,908 |
| 2026-03 | 8,266 |