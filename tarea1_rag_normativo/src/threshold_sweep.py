"""
threshold_sweep.py — Fase 3, Task 1: calibración del threshold de abstención

Requisito del enunciado (Phase 3): "Calibrate that threshold with a
sweep over your evaluation set, and show the evidence (a table or a
chart)."

Este script NO llama al LLM (solo retrieval — evaluación sin costo,
tal como exige Phase 4 mas adelante). Para cada pregunta del set de
evaluacion, mide la similitud del mejor fragmento recuperado y, para
cada threshold candidato, calcula:
  - preguntas in-domain que SI se hubieran respondido (bien)
  - preguntas in-domain que se hubieran abstenido por error (mal:
    abstencion incorrecta, el sistema si tenia la respuesta)
  - preguntas out-of-domain que se hubieran abstenido (bien)
  - preguntas out-of-domain que se hubieran respondido por error (mal:
    el sistema alucina con contexto irrelevante)

Uso:
    python src/threshold_sweep.py
"""

import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from engine import load_config, retrieve  # noqa: E402

BASE_DIR = Path(__file__).resolve().parent.parent
EVAL_PATH = BASE_DIR / "eval" / "preguntas.csv"
LOGS_DIR = BASE_DIR / "logs"
LOGS_DIR.mkdir(parents=True, exist_ok=True)

THRESHOLDS = [round(t, 2) for t in [0.50, 0.55, 0.60, 0.65, 0.70, 0.72, 0.74, 0.76, 0.78, 0.80, 0.85, 0.90]]


def load_eval_set():
    with open(EVAL_PATH, "r", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def main():
    config = load_config()
    questions = load_eval_set()

    print(f"Corriendo retrieval para {len(questions)} preguntas (sin llamar al LLM)...\n")
    results = []
    for q in questions:
        sources = retrieve(q["pregunta"], config, top_k=5)
        best_sim = sources[0]["similarity"] if sources else 0.0
        results.append({
            "id": q["id"],
            "tipo": q["tipo"],
            "pregunta": q["pregunta"],
            "best_similarity": round(best_sim, 4),
            "top1_documento": sources[0]["documento"] if sources else "",
            "top1_pagina": sources[0]["pagina"] if sources else "",
        })
        print(f"  {q['id']} ({q['tipo']}): best_sim={best_sim:.4f} | top1={sources[0]['documento']} p.{sources[0]['pagina']}")

    # Guardar similitudes crudas (evidencia base)
    sims_path = LOGS_DIR / "threshold_sweep_similarities.csv"
    with open(sims_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(results[0].keys()))
        writer.writeheader()
        writer.writerows(results)

    # Sweep
    sweep_rows = []
    for threshold in THRESHOLDS:
        correct_answer = 0    # in_domain, contestado
        incorrect_abstain = 0  # in_domain, se abstuvo por error
        correct_abstain = 0   # out_of_domain, se abstuvo (bien)
        incorrect_answer = 0  # out_of_domain, contesto por error

        for r in results:
            would_answer = r["best_similarity"] >= threshold
            if r["tipo"] == "in_domain":
                if would_answer:
                    correct_answer += 1
                else:
                    incorrect_abstain += 1
            else:  # out_of_domain
                if would_answer:
                    incorrect_answer += 1
                else:
                    correct_abstain += 1

        sweep_rows.append({
            "threshold": threshold,
            "in_domain_respondidas_ok": correct_answer,
            "in_domain_abstencion_incorrecta": incorrect_abstain,
            "out_domain_abstencion_correcta": correct_abstain,
            "out_domain_respondidas_por_error": incorrect_answer,
        })

    sweep_path = LOGS_DIR / "threshold_sweep.csv"
    with open(sweep_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(sweep_rows[0].keys()))
        writer.writeheader()
        writer.writerows(sweep_rows)

    print(f"\n=== SWEEP DE THRESHOLD ===\n")
    header = f"{'threshold':<11}{'in_ok':<8}{'in_mal':<9}{'out_ok':<9}{'out_mal':<9}"
    print(header)
    print("-" * len(header))
    for r in sweep_rows:
        print(f"{r['threshold']:<11}{r['in_domain_respondidas_ok']:<8}"
              f"{r['in_domain_abstencion_incorrecta']:<9}"
              f"{r['out_domain_abstencion_correcta']:<9}"
              f"{r['out_domain_respondidas_por_error']:<9}")

    print(f"\nCSVs guardados en:\n  {sims_path}\n  {sweep_path}")
    print("\nElige el threshold mas alto que aun mantenga 'in_mal' en 0 (o cercano a 0)")
    print("mientras 'out_ok' se mantenga alto -- ese es el mejor balance costo/precision.")


if __name__ == "__main__":
    main()
