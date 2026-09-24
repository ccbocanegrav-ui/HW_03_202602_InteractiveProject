"""
eval_recall.py — Fase 4, Task 1: Evaluación (Phase 4)

Calcula Recall@1, Recall@3, Recall@5 y el abstention rate SIN llamar
al modelo generador — solo retrieval. Esto es intencional (pide el
enunciado): la evaluacion debe poder correrse las veces que haga falta
sin gastar dinero en la API.

QUE MIDE CADA METRICA:
- Recall@k: evalua la etapa de RETRIEVAL + EMBEDDINGS (Fase 2). De las
  preguntas in-domain (con pagina esperada conocida), ¿en que
  porcentaje de los casos el fragmento correcto aparece entre los top-k
  resultados? Si Recall@5 es alto pero Recall@1 es bajo, el problema
  no es el modelo de embeddings — es que hace falta mas contexto (top_k
  mas grande) o mejor reranking, no necesariamente peor calidad de
  busqueda.
- Abstention rate: evalua la etapa de THRESHOLD (Fase 3). Mide si el
  engine decide bien CUANDO no responder: abstenciones correctas (el
  sistema no debia responder y no respondio) vs. incorrectas en ambos
  sentidos (se abstuvo debiendo responder, o respondio debiendo
  abstenerse).

Uso:
    python eval/eval_recall.py
"""

import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from engine import load_config, retrieve  # noqa: E402

BASE_DIR = Path(__file__).resolve().parent.parent
EVAL_PATH = BASE_DIR / "eval" / "preguntas.csv"
LOGS_DIR = BASE_DIR / "logs"
LOGS_DIR.mkdir(parents=True, exist_ok=True)


def load_eval_set():
    with open(EVAL_PATH, "r", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def hit_at_k(sources: list[dict], expected_doc: str, expected_page: str, k: int) -> bool:
    """Hit estricto: documento Y pagina exacta."""
    if not expected_doc or not expected_page:
        return False
    try:
        expected_page = int(expected_page)
    except ValueError:
        return False
    for s in sources[:k]:
        if s["documento"] == expected_doc and s["pagina"] == expected_page:
            return True
    return False


def doc_hit_at_k(sources: list[dict], expected_doc: str, k: int) -> bool:
    """Hit a nivel de documento (Ley vs. DS), sin exigir pagina exacta.
    Util porque los articulos cruzan paginas y el chunking es por
    pagina: el fragmento mas relevante semanticamente a veces cae en
    la pagina siguiente/anterior a donde arranca el articulo, aunque
    el documento correcto si se identifica bien."""
    if not expected_doc:
        return False
    return any(s["documento"] == expected_doc for s in sources[:k])


def main():
    config = load_config()
    questions = load_eval_set()
    threshold = config["retrieval"]["similarity_threshold"]

    in_domain = [q for q in questions if q["tipo"] == "in_domain"]
    out_domain = [q for q in questions if q["tipo"] == "out_of_domain"]

    print(f"Evaluando {len(questions)} preguntas ({len(in_domain)} in-domain, "
          f"{len(out_domain)} out-of-domain) | threshold={threshold}\n")

    rows = []
    recall_hits = {1: 0, 3: 0, 5: 0}
    doc_recall_hits = {1: 0, 3: 0, 5: 0}
    correct_answer = 0        # in_domain, hubiera respondido (bien)
    incorrect_abstain = 0     # in_domain, se hubiera abstenido (mal)
    correct_abstain = 0       # out_domain, se hubiera abstenido (bien)
    incorrect_answer = 0      # out_domain, hubiera respondido (mal)

    for q in questions:
        sources = retrieve(q["pregunta"], config, top_k=5)
        best_sim = sources[0]["similarity"] if sources else 0.0
        would_answer = best_sim >= threshold

        row = {
            "id": q["id"], "tipo": q["tipo"], "best_similarity": round(best_sim, 4),
            "would_answer": would_answer,
        }

        if q["tipo"] == "in_domain":
            for k in (1, 3, 5):
                hit = hit_at_k(sources, q["documento_esperado"], q["pagina_esperada"], k)
                doc_hit = doc_hit_at_k(sources, q["documento_esperado"], k)
                row[f"hit@{k}"] = hit
                row[f"doc_hit@{k}"] = doc_hit
                if hit:
                    recall_hits[k] += 1
                if doc_hit:
                    doc_recall_hits[k] += 1
            if would_answer:
                correct_answer += 1
            else:
                incorrect_abstain += 1
        else:
            if would_answer:
                incorrect_answer += 1
            else:
                correct_abstain += 1

        rows.append(row)
        print(f"  {q['id']} ({q['tipo']}): sim={best_sim:.4f} would_answer={would_answer}"
              + (f" hit@1={row.get('hit@1')} hit@3={row.get('hit@3')} hit@5={row.get('hit@5')}"
                 if q["tipo"] == "in_domain" else ""))

    n_in = len(in_domain)
    n_out = len(out_domain)

    print("\n=== RECALL@K ESTRICTO (documento + pagina exacta) ===")
    for k in (1, 3, 5):
        recall = recall_hits[k] / n_in if n_in else 0
        print(f"  Recall@{k}: {recall:.2%} ({recall_hits[k]}/{n_in})")

    print("\n=== RECALL@K A NIVEL DE DOCUMENTO (Ley vs. DS, sin exigir pagina exacta) ===")
    print("  (los articulos cruzan paginas; el chunking es por pagina, asi que el")
    print("   fragmento mas relevante a veces cae en la pagina vecina. Esta metrica")
    print("   aisla si el problema es 'documento equivocado' o 'pagina vecina'.)")
    for k in (1, 3, 5):
        recall = doc_recall_hits[k] / n_in if n_in else 0
        print(f"  Recall@{k} (documento): {recall:.2%} ({doc_recall_hits[k]}/{n_in})")

    print("\n=== ABSTENTION RATE (evalua la decision de threshold, Fase 3) ===")
    print(f"  In-domain respondidas correctamente:  {correct_answer}/{n_in} ({correct_answer/n_in:.1%})" if n_in else "")
    print(f"  In-domain abstencion INCORRECTA:       {incorrect_abstain}/{n_in} ({incorrect_abstain/n_in:.1%})" if n_in else "")
    print(f"  Out-of-domain abstencion CORRECTA:     {correct_abstain}/{n_out} ({correct_abstain/n_out:.1%})" if n_out else "")
    print(f"  Out-of-domain respondidas por ERROR:   {incorrect_answer}/{n_out} ({incorrect_answer/n_out:.1%})" if n_out else "")

    out_path = LOGS_DIR / "eval_recall_results.csv"
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        fieldnames = sorted({k for r in rows for k in r.keys()})
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    print(f"\nResultados detallados guardados en: {out_path}")


if __name__ == "__main__":
    main()
