#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from pdfy import PdfyValidationError, generate_pdf


def main() -> int:
    parser = argparse.ArgumentParser(description="Gera um PDF A4 Matizze a partir de JSON.")
    parser.add_argument("--input", required=True, type=Path, help="Arquivo JSON de entrada")
    parser.add_argument("--output", required=True, type=Path, help="Arquivo PDF de saída")
    args = parser.parse_args()
    try:
        trace_path = args.output.with_suffix(".layout.json")
        result = generate_pdf(args.input, args.output, trace_path=trace_path)
    except PdfyValidationError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    except (OSError, RuntimeError, ValueError) as exc:
        print(f"Falha ao gerar PDF: {exc}", file=sys.stderr)
        return 1
    payload = result.as_dict()
    payload.pop("trace", None)
    payload["layout_trace"] = str(trace_path.resolve())
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
