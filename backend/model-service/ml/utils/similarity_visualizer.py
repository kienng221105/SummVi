import numpy as np
def print_similarity_matrix(
    matrix: np.ndarray,
    doc_ids: list[str],
    threshold: float = 0.65,
):
    short_ids = [d[:8] for d in doc_ids] 
    header = "        " + "  ".join(f"{s:8}" for s in short_ids)
    print(header)
    for i, row_id in enumerate(short_ids):
        row = f"{row_id:8}"
        for j in range(len(short_ids)):
            val = matrix[i, j]
            marker = "▓" if val >= threshold and i != j else " "
            row += f"  {val:.3f}{marker} "
        print(row)

def summarize_routing(groups) -> str:
    lines = []
    for g in groups:
        lines.append(
            f"{g.group_id}: {len(g.doc_ids)} docs → "
            f"{g.route.upper()} (avg_sim={g.avg_similarity:.2f})"
        )
    return "\n".join(lines)
