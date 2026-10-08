---
name: pdfy
description: Gera e valida PDFs A4 profissionais com a identidade Matizze a partir de JSON estruturado. Use para propostas, relatórios, planos, diagnósticos e documentos executivos Matizze.
---

# Usar o pdfy

Use as tools MCP do `pdfy` para transformar conteúdo estruturado em um PDF Matizze. O modelo fornece somente conteúdo; o renderer define capa, layout, paginação e encerramento.

1. Chame `pdfy_get_creation_options` com `topic: "overview"`.
2. Consulte `topic: "component"` apenas para os componentes necessários.
3. Monte um JSON do schema `1`, sem propriedades visuais.
4. Chame `pdfy_validate_document` e corrija todos os erros.
5. Chame `pdfy_generate_document` com um caminho local terminado em `.pdf`.
6. Confirme `ok: true` e revise a contact sheet retornada antes de entregar.

## Guardrails

- Não recrie o layout manualmente nem adicione `kind`, `template`, cores, fontes, tamanhos, margens ou coordenadas ao JSON.
- Não invente valores, datas, métricas, obrigações ou dados jurídicos/comerciais.
- Use `sections` com componentes ou `content` com Markdown (relatórios corridos), nunca os dois. Não use HTML.
- Prefira mais páginas a condensar conteúdo; mantenha títulos curtos.
- Preserve a capa automática e o encerramento Matizze obrigatório.
- Entregue somente depois de validar e revisar a renderização.
