---
name: pdfy
description: Gera e valida PDFs A4 profissionais com a identidade oficial da Matizze a partir de JSON estruturado. Use quando Codex precisar criar propostas, relatórios, planos, diagnósticos, documentos executivos ou outros PDFs Matizze consistentes sem decidir fontes, cores, margens ou layout manualmente.
---

# Usar o pdfy

Transformar conteúdo estruturado em PDF Matizze com o renderer deste repositório. Manter o modelo focado no conteúdo; não recriar o layout.

## Fluxo obrigatório

1. Se o MCP `pdfy` estiver conectado, chamar `pdfy_get_creation_options` com `topic: "overview"`; consultar `topic: "component"` somente para os tipos necessários.
2. Criar um JSON compatível com o schema `1`. Não adicionar propriedades visuais.
3. Chamar `pdfy_validate_document` e corrigir todos os erros.
4. Chamar `pdfy_generate_document` com um caminho local terminado em `.pdf`.
5. Confirmar `ok: true` e inspecionar a contact sheet retornada.

Sem MCP, ler `references/components.md`, consultar `references/content-limits.md` e usar:

```bash
uv run python scripts/generate_pdf.py --input /caminho/documento.json --output /caminho/documento.pdf
uv run python scripts/validate_pdf.py --input /caminho/documento.json --pdf /caminho/documento.pdf --render-dir /caminho/render
```

Corrigir primeiro o conteúdo. Alterar o renderer somente para defeitos generalizáveis. Repetir até a validação retornar sucesso e não haver cortes, colisões, páginas pobres ou glifos quebrados.

## JSON mínimo

Modo estruturado, com componentes:

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

Modo corrido, com Markdown (útil para relatórios longos com cara de documento):

```json
{
  "schema": "1",
  "title": "Relatório de andamento",
  "recipient": "Cliente",
  "date": "2026-10-07",
  "content": "## Contexto\n\nTexto em **Markdown** com listas, tabelas e citações."
}
```

Usar `sections` **ou** `content`, nunca os dois.

## Guardrails

- Usar somente `pdfy_generate_document` ou `scripts/generate_pdf.py`; não escrever outro gerador.
- Não inserir `kind`, `template`, layout, fonte, cor, tamanho, margem ou coordenadas no JSON.
- Não inventar valores, datas, métricas, obrigações ou dados jurídicos/comerciais.
- No modo `content`, usar Markdown padrão; não inserir HTML.
- Preferir mais páginas a condensar conteúdo. Manter títulos curtos e respeitar os limites editoriais.
- Preservar a capa automática e o encerramento fixo obrigatório.
- Usar hífen ASCII; evitar travessões Unicode e glifos incomuns.
- Entregar somente após executar a validação e revisar visualmente a renderização.
