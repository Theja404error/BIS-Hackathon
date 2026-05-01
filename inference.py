"""
MANDATORY entry-point script. Judges run:
    python inference.py --input hidden_private_dataset.json --output team_results.json

DO NOT change the CLI signature or output schema — your automated score depends on it.

Expected input format (one of these — handles both common shapes):
    [{"id": "q1", "query": "53 grade cement"}, ...]
  OR
    {"queries": [{"id": "q1", "query": "..."}]}

Output format (strict):
    [
      {
        "id": "q1",
        "retrieved_standards": ["IS 8112:2013", "IS 269:2015", "IS 12269"],
        "latency_seconds": 1.234
      },
      ...
    ]
"""
import argparse
import json
import sys
from pathlib import Path


def load_input(path: str):
    with open(path) as f:
        data = json.load(f)
    if isinstance(data, dict) and "queries" in data:
        return data["queries"]
    if isinstance(data, list):
        return data
    raise ValueError(f"Unrecognized input shape in {path}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, help="Path to input JSON")
    parser.add_argument("--output", required=True, help="Path to output JSON")
    args = parser.parse_args()

    # Lazy import so --help works without heavy deps loaded
    from src.rag_pipeline import RAGPipeline

    print(f"Loading RAG pipeline...", file=sys.stderr)
    pipe = RAGPipeline()

    items = load_input(args.input)
    print(f"Processing {len(items)} queries...", file=sys.stderr)

    results = []
    for item in items:
        qid = item.get("id") or item.get("query_id") or str(len(results))
        query = item.get("query") or item.get("description") or item.get("text", "")
        out = pipe.query(query, top_k=5)
        results.append({
            "id": qid,
            "retrieved_standards": out["retrieved_standards"],
            "latency_seconds": out["latency_seconds"],
        })
        print(f"  [{qid}] {len(out['retrieved_standards'])} results in {out['latency_seconds']}s", file=sys.stderr)

    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    with open(args.output, "w") as f:
        json.dump(results, f, indent=2)

    print(f"✅ Wrote {len(results)} results to {args.output}", file=sys.stderr)


if __name__ == "__main__":
    main()
