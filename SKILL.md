---
name: pdfy
description: Gera e valida PDFs A4 profissionais com a identidade oficial da Matizze a partir de JSON estruturado. Use quando Codex precisar criar propostas, relatórios, planos, diagnósticos, documentos executivos ou outros PDFs Matizze consistentes sem decidir fontes, cores, margens ou layout manualmente.
---

# Usar o pdfy

Transformar conteúdo estruturado em PDF Matizze com o renderer deste repositório. Manter o modelo focado no conteúdo; não recriar o layout.

## Fluxo obrigatório

1. Ler `references/components.md` e escolher somente os componentes necessários.
2. Consultar `references/content-limits.md` antes de redigir conteúdo extenso.
3. Criar um JSON UTF-8 compatível com `schemas/document.schema.json`. Não adicionar propriedades visuais.
4. Validar e gerar:

```bash
uv run python scripts/generate_pdf.py --input /caminho/documento.json --output /caminho/documento.pdf
uv run python scripts/validate_pdf.py --input /caminho/documento.json --pdf /caminho/documento.pdf --render-dir /caminho/render
```

5. Inspecionar `contact-sheet.png` e, quando necessário, as páginas individuais.
6. Corrigir primeiro o conteúdo. Alterar o renderer somente para defeitos generalizáveis.
7. Repetir até a validação retornar sucesso e não haver cortes, colisões, páginas pobres ou glifos quebrados.

## JSON mínimo

```json
{
  "schema": "1",
  "title": "Título do documento",
  "sections": [
    {
      "title": "Resumo executivo",
      "components": [
        {"type": "text", "content": "Conteúdo objetivo."}
      ]
    }
  ]
}
```

## Guardrails

- Usar apenas `scripts/generate_pdf.py`; não escrever outro gerador.
- Não inserir `kind`, `template`, layout, fonte, cor, tamanho, margem ou coordenadas no JSON.
- Não inventar valores, datas, métricas, obrigações ou dados jurídicos/comerciais.
- Tratar texto como texto simples; não usar HTML ou Markdown.
- Preferir mais páginas a condensar conteúdo. Manter títulos curtos e respeitar os limites editoriais.
- Preservar a capa automática e o encerramento fixo obrigatório.
- Usar hífen ASCII; evitar travessões Unicode e glifos incomuns.
- Entregar somente após executar a validação e revisar visualmente a renderização.
