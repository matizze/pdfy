# pdfy

Motor oficial da Matizze para transformar conteúdo JSON estruturado em PDFs A4 profissionais, consistentes e determinísticos.

O modelo fornece somente conteúdo. O `pdfy` controla capa, identidade visual, tipografia, cores, margens, componentes, paginação, páginas de continuação e encerramento. O resultado mantém texto, tabelas e gráficos como vetores no PDF.

## Estado do projeto

- Schema público: `1`.
- Template visual: um único padrão oficial da Matizze.
- Componentes: 13.
- Renderer do PDF: ReportLab.
- Auditoria: pypdf, pdfplumber e trace geométrico próprio.
- Renderização de previews: PDFium via pypdfium2, sem dependência do Poppler.
- Transporte MCP: STDIO.
- Distribuição Python e comando executável: `pdfyy`.
- Pacote para import em Python: `pdfy`.
- Repositório público: [github.com/matizze/pdfy](https://github.com/matizze/pdfy).

O nome diferente da distribuição é intencional: `pdfy` já está ocupado no índice público de pacotes Python, enquanto o código continua sendo importado como `pdfy`.

## O que é automático

- A capa é criada a partir de `title`, `subtitle`, `recipient` e `date`.
- Cada item de `sections` começa em uma página nova.
- Componentes longos continuam em páginas adicionais sem reduzir o corpo para um tamanho ilegível.
- A última página é fixa e obrigatória.
- O encerramento usa o slogan `Tecnologia como meio, resultado como foco.`.
- O rodapé `DOCUMENTO CONFIDENCIAL` não é usado.
- Fontes e ativos oficiais são carregados do próprio pacote; a execução não depende de pastas pessoais.
- A mesma entrada produz o mesmo PDF byte a byte dentro da mesma versão do `pdfy` e das dependências fixadas.

O JSON não aceita `kind`, `template`, fontes, cores, tamanhos, margens, coordenadas ou outras propriedades visuais.

## Início rápido no repositório

Requisitos de desenvolvimento:

- Python 3.11 ou superior;
- [uv](https://docs.astral.sh/uv/);
- nenhuma dependência de sistema para renderizar os previews.

Instale o ambiente fixado:

```bash
uv sync
```

Gere o exemplo completo:

```bash
uv run python scripts/generate_pdf.py \
  --input examples/complete-document.json \
  --output outputs/complete-document.pdf
```

Faça a auditoria técnica, renderize todas as páginas e crie a contact sheet:

```bash
uv run python scripts/validate_pdf.py \
  --input examples/complete-document.json \
  --pdf outputs/complete-document.pdf \
  --render-dir outputs/complete-document-render \
  --report outputs/complete-document-validation.json
```

O comando de geração também grava `outputs/complete-document.layout.json`, com o trace das áreas ocupadas em cada página.

## Servidor MCP via STDIO

O executável `pdfyy` inicia um servidor MCP local. Ele não abre porta, não envia documentos para um serviço externo e usa `stdin`/`stdout` exclusivamente para o protocolo.

Durante o desenvolvimento:

```bash
uv run pdfyy
```

O processo ficar silencioso e não encerrar é o comportamento esperado: ele está aguardando um cliente MCP. Logs devem sempre ir para `stderr`, porque qualquer texto comum em `stdout` corrompe o transporte STDIO.

### Uso com `uvx`

Depois que `pdfyy` for publicado em um índice acessível ao computador cliente:

```bash
uvx pdfyy@0.1.0
```

O `uvx` baixa o pacote, cria um ambiente isolado em cache e executa o comando. Na primeira execução, o computador precisa de acesso ao índice; depois disso, o cache pode evitar novos downloads. O pacote não fica embutido no `uvx`.

Como o repositório é público, qualquer computador com Git e acesso à internet pode instalar diretamente do GitHub:

```bash
uvx --from "git+https://github.com/matizze/pdfy.git@<tag-ou-commit>" pdfyy
```

Para distribuição previsível, prefira uma versão publicada ou um tag/commit imutável. Evite apontar clientes de produção para `main`.

### Configuração genérica de um cliente MCP

Após publicação no índice:

```json
{
  "mcpServers": {
    "pdfy": {
      "command": "uvx",
      "args": ["pdfyy@0.1.0"]
    }
  }
}
```

Usando o repositório público, sem credenciais do GitHub:

```json
{
  "mcpServers": {
    "pdfy": {
      "command": "uvx",
      "args": [
        "--from",
        "git+https://github.com/matizze/pdfy.git@<tag-ou-commit>",
        "pdfyy"
      ]
    }
  }
}
```

Se o aplicativo não encontrar `uvx`, use o caminho absoluto retornado por `which uvx` no macOS/Linux ou `where uvx` no Windows. Reinicie o cliente MCP depois de alterar sua configuração.

### Fluxo recomendado para um agente

1. Chamar `pdfy_get_creation_options` com `topic: "overview"`.
2. Consultar os componentes necessários com `topic: "component"`.
3. Montar o JSON apenas com conteúdo.
4. Chamar `pdfy_validate_document`.
5. Corrigir todos os erros retornados.
6. Chamar `pdfy_generate_document` com um caminho local terminado em `.pdf`.
7. Conferir `ok`, `issues`, `warnings` e, quando houver revisão humana, abrir a contact sheet retornada.

## Tools MCP

O servidor expõe exatamente três tools públicas.

### `pdfy_get_creation_options`

Permite que o agente descubra o contrato sem depender de conhecimento prévio nem reconstruir o layout.

Entradas:

| Campo | Tipo | Padrão | Uso |
|---|---|---|---|
| `topic` | `overview`, `component`, `schema` ou `example` | `overview` | Define o nível de descoberta. |
| `component_type` | string ou `null` | `null` | Obrigatório somente com `topic: "component"`. |
| `example` | `minimal`, `complete` ou `null` | `null` | Seleciona o exemplo; o padrão para `topic: "example"` é `minimal`. |

Comportamento por tópico:

- `overview`: retorna campos obrigatórios e opcionais, regras automáticas, os 13 componentes e um guia de escolha.
- `component`: retorna finalidade, campos, limites do schema, definições referenciadas e um exemplo daquele componente.
- `schema`: retorna o JSON Schema Draft 2020-12 completo.
- `example`: retorna o documento mínimo ou completo distribuído com o pacote.

Exemplos de argumentos:

```json
{"topic": "overview"}
```

```json
{"topic": "component", "component_type": "timeline"}
```

```json
{"topic": "example", "example": "complete"}
```

Essa tool nunca oferece escolhas de fonte, cor, margem, coordenada ou template.

### `pdfy_validate_document`

Valida o objeto antes de criar arquivos.

Entrada:

```json
{
  "document": {
    "schema": "1",
    "title": "Título do documento",
    "sections": [
      {
        "title": "Resumo",
        "components": [
          {"type": "text", "content": "Conteúdo objetivo."}
        ]
      }
    ]
  }
}
```

Em caso de sucesso, retorna `ok`, versão do schema, título, quantidade de seções e quantidade de componentes. Em caso de erro, retorna todos os problemas encontrados, cada um com:

- `path`: localização exata, como `$.sections[0].components[0].color`;
- `code`: código estável, como `unexpected_property`;
- `message`: descrição legível;
- `hint`: correção recomendada quando aplicável.

Erros de validação são respostas estruturadas com `ok: false`, o que permite ao agente corrigir vários campos em uma única rodada.

### `pdfy_generate_document`

Valida o JSON, gera o PDF de forma atômica, audita o arquivo, renderiza todas as páginas a 144 DPI e cria a contact sheet.

Entradas:

| Campo | Tipo | Regra |
|---|---|---|
| `document` | objeto JSON | Mesmo contrato aceito pela validação. |
| `output_path` | string | Caminho local terminado em `.pdf`; relativo ou absoluto. |

Exemplo:

```json
{
  "document": {
    "schema": "1",
    "title": "Plano de implantação",
    "sections": [
      {
        "title": "Objetivo",
        "components": [
          {"type": "callout", "content": "Implantar o processo com segurança."}
        ]
      }
    ]
  },
  "output_path": "outputs/plano-de-implantacao.pdf"
}
```

Saída principal:

- `ok`: sucesso conjunto da geração, auditoria e renderização;
- `pdf`: caminho absoluto do PDF;
- `layout_trace`: caminho do trace geométrico;
- `pages`: número de páginas;
- `rendered_pages`: caminhos dos PNGs;
- `contact_sheet`: caminho da visão geral;
- `renderer`: versões do pypdfium2 e PDFium;
- `issues` e `warnings`: achados técnicos.

O diretório dos previews usa o nome `<arquivo>-render` ao lado do PDF. Um destino existente é substituído atomicamente somente depois que o novo PDF termina de ser construído. O processo precisa de permissão de escrita no destino.

## Contrato JSON

Documento mínimo:

```json
{
  "schema": "1",
  "title": "Título do documento",
  "sections": [
    {
      "title": "Resumo executivo",
      "components": [
        {
          "type": "text",
          "content": "Conteúdo objetivo."
        }
      ]
    }
  ]
}
```

Campos da raiz:

| Campo | Obrigatório | Limite |
|---|---:|---:|
| `schema` | sim | valor fixo `1` |
| `title` | sim | 90 caracteres |
| `subtitle` | não | 180 caracteres |
| `recipient` | não | 120 caracteres |
| `date` | não | data real em `YYYY-MM-DD` |
| `sections` | sim | 1 a 20 seções |

Cada seção aceita `title`, `subtitle` opcional e de 1 a 30 `components`. Propriedades desconhecidas são rejeitadas em todos os níveis.

O contrato completo está em [`schemas/document.schema.json`](schemas/document.schema.json). Os documentos de referência estão em [`examples/minimal-document.json`](examples/minimal-document.json) e [`examples/complete-document.json`](examples/complete-document.json).

## Componentes disponíveis

| Tipo | Usar para | Estrutura principal |
|---|---|---|
| `text` | Parágrafos e explicações | `content`; `title` opcional |
| `metrics` | Indicadores curtos | `items` com `label`, `value`, `note` opcional |
| `highlights` | Mensagens breves em destaque | `items` de texto |
| `cards` | Conceitos ou entregas | `items` com `title`, `description`, `tag` opcional |
| `callout` | Decisão ou conclusão dominante | `content`; `title` opcional |
| `comparison` | Dois cenários lado a lado | `left_label`, `right_label`, `rows` |
| `chart` | Valores numéricos comparáveis | `items` com `label`, `value`, `note`; `unit` opcional |
| `steps` | Sequência ordenada | `items` com `title`, `description` opcional |
| `timeline` | Marcos por período | `items` com `period`, `title`, `description` opcional |
| `table` | Dados tabulares | `columns` e `rows`, de 2 a 6 colunas |
| `investment` | Itens, total e observações | `items`; `total` e `notes` opcionais |
| `list` | Itens simples | `items` de texto |
| `signature` | Assinaturas | `signers`; `intro` e `title` opcionais |

Consulte [`references/components.md`](references/components.md) para a orientação editorial e [`references/content-limits.md`](references/content-limits.md) para todos os limites. O renderer pagina blocos extensos de forma segura, mas não consegue melhorar conteúdo semanticamente denso; quando um único item for grande demais, divida-o no JSON.

## Uso como biblioteca Python

```python
from pdfy import generate_pdf, validate_document

document = validate_document("examples/minimal-document.json")
result = generate_pdf(
    document,
    "outputs/minimal-document.pdf",
    trace_path="outputs/minimal-document.layout.json",
)

print(result.path)
print(len(result.trace.pages))
```

`validate_document` aceita um mapping, texto JSON ou caminho UTF-8. `generate_pdf` também aceita esses formatos e substitui o destino de forma atômica.

## Validação técnica

A validação combina verificações independentes:

- JSON Schema Draft 2020-12 e regras semânticas;
- chaves duplicadas e números não finitos;
- data de calendário real;
- largura consistente das linhas de tabela;
- capa, encerramento e começo de cada seção;
- quantidade de páginas e metadados;
- MediaBox A4, rotação e CropBox;
- fontes Montserrat incorporadas;
- caracteres e objetos fora da página;
- tamanho mínimo do texto;
- caracteres de substituição ou NUL;
- trace interno de colisões e overflow;
- renderização de todas as páginas;
- comparação opcional com imagens golden.

O PDFium não substitui o ReportLab. O ReportLab produz o PDF vetorial; o PDFium apenas rasteriza páginas para inspeção e regressão visual. A troca de Poppler por PDFium elimina uma instalação de sistema e mantém boa qualidade, mas altera antialiasing e pixels dos PNGs. Por isso, imagens golden devem ser criadas e comparadas com a mesma família e versão de renderer.

Comparação visual opcional:

```bash
uv run python scripts/validate_pdf.py \
  --input examples/complete-document.json \
  --pdf outputs/complete-document.pdf \
  --render-dir outputs/complete-document-render \
  --golden tests/golden/approved-example
```

Tolerâncias atuais:

- borda ignorada: 2 px;
- MAE máximo: 1,5 em canais de 0 a 255;
- delta relevante por pixel: 32;
- fração máxima de pixels alterados: 0,5%.

Essas tolerâncias absorvem pequenas diferenças de rasterização; não substituem auditoria geométrica, extração de texto nem inspeção humana da contact sheet.

## Desenvolvimento e testes

Execute toda a suíte:

```bash
uv run pytest
```

Os testes cobrem:

- schema mínimo e completo;
- campos inválidos e componentes desconhecidos;
- todos os componentes;
- acentuação e normalização Unicode;
- tabelas e textos longos;
- paginação e continuação;
- começo de cada seção em nova página;
- capa e encerramento automáticos;
- determinismo byte a byte;
- metadados, fontes, geometria, cortes e overflow;
- renderização e regressão visual;
- descoberta, validação e geração pelas tools MCP;
- exposição de exatamente três tools via cliente MCP em memória.

Valide a Skill depois de alterá-la:

```bash
uv run python <caminho-da-skill-creator>/scripts/quick_validate.py .
```

Antes de aceitar uma mudança visual:

1. gerar os três exemplos;
2. executar a validação técnica;
3. abrir a contact sheet do documento completo;
4. inspecionar páginas individuais quando necessário;
5. comparar com o golden usando a versão fixada do PDFium;
6. atualizar o golden somente quando a mudança visual for intencional e aprovada.

## Build e teste do pacote isolado

Crie wheel e source distribution:

```bash
uv build
```

Teste o wheel como ferramenta isolada:

```bash
uvx --from dist/pdfyy-0.1.0-py3-none-any.whl pdfyy
```

O wheel inclui schema, exemplos mínimo e completo, fontes, logos, backgrounds e gráficos necessários em runtime. Sempre teste fora do checkout antes de publicar, porque um ambiente editável pode mascarar arquivos ausentes no pacote.

Para testar o protocolo interativamente, use o MCP Inspector conforme a documentação do SDK MCP. O Inspector requer Node.js/npx; a suíte normal não requer.

## Publicação

Este repositório estar público no GitHub não torna `uvx pdfyy` globalmente disponível. Para esse comando curto funcionar em qualquer computador, publique `pdfyy` em um índice Python acessível. Até lá, use a instalação via URL Git pública documentada acima.

Fluxo recomendado para uma versão:

1. escolher a política de distribuição: índice privado da Matizze ou PyPI;
2. definir licença e metadados legais antes de uma publicação pública;
3. atualizar `version` em `pyproject.toml` e `src/pdfy/__init__.py`;
4. executar testes, validação visual e teste do wheel;
5. criar um tag imutável;
6. publicar o artefato no índice escolhido;
7. configurar clientes com uma versão exata, como `pdfyy@0.1.0`.

O projeto não publica, cria tags nem altera remotos automaticamente.

## Estrutura principal

```text
pdfy/
├── README.md                  # documentação humana
├── SKILL.md                   # instrução canônica para agentes
├── pyproject.toml             # pacote pdfyy e comando MCP
├── schemas/                   # contrato JSON oficial
├── examples/                  # documentos mínimo, completo e longo
├── scripts/                   # geração e validação por CLI
├── src/pdfy/
│   ├── mcp_server.py          # três tools e transporte STDIO
│   ├── creation_options.py    # descoberta do contrato
│   ├── engine.py              # geração determinística e atômica
│   ├── parser.py              # leitura e normalização
│   ├── registry.py            # type -> renderer
│   ├── components/            # renderers dos 13 componentes
│   ├── design/                # tokens visuais centralizados
│   ├── template/              # capa, seção, paginação e encerramento
│   ├── validation/            # conteúdo, layout, PDF e golden
│   └── assets/                # ativos oficiais autocontidos
├── references/                # regras editoriais e visuais
└── tests/                     # testes funcionais, MCP e golden
```

## Segurança, privacidade e operação

- O servidor MCP roda localmente e não possui chamadas de rede próprias.
- A primeira instalação pelo `uvx` pode acessar o índice ou o Git remoto.
- Documentos e previews são gravados somente no caminho local solicitado.
- O servidor não executa conteúdo do JSON como código.
- O schema rejeita propriedades desconhecidas.
- O cliente que inicia o servidor herda as permissões do usuário do sistema; limite os diretórios permitidos no ambiente do cliente quando necessário.
- Não inclua segredos no JSON ou em logs de validação.
- Em STDIO, nunca adicione `print()` ou subprocessos que escrevam em `stdout` fora do protocolo.

## Limitações atuais

- Existe somente o schema `1` e um template Matizze.
- O gráfico oficial é de barras horizontais; não há escolha de tipo.
- `investment` não soma valores nem formata moeda.
- O renderer não interpreta HTML ou Markdown.
- A tool de geração escreve no filesystem do computador onde o servidor MCP está rodando, não no computador remoto do modelo.
- A contact sheet ajuda a revisão, mas a aprovação visual final continua humana.
- A regressão visual depende da versão fixada do PDFium e pode exigir novo golden após uma atualização deliberada.
- O pacote ainda precisa ser publicado em um índice para que o comando curto `uvx pdfyy@versão` funcione; via URL Git pública ele já pode ser executado sem autenticação.
- Não há licença pública definida neste repositório; resolva isso antes de qualquer distribuição pública.

## Próximas versões recomendadas

1. Publicar `pdfyy` em um índice privado da Matizze e automatizar releases assinados.
2. Adicionar CI para testes, build do wheel, auditoria completa e comparação golden na versão fixada do PDFium.
3. Testar explicitamente os wheels em macOS, Linux e Windows.
4. Definir uma política de retenção para PDFs e previews gerados por clientes MCP.
5. Versionar mudanças futuras do contrato sem alterar o comportamento do schema `1`.

Referências técnicas: [uv tools](https://docs.astral.sh/uv/guides/tools/), [MCP Python SDK](https://py.sdk.modelcontextprotocol.io/) e [pypdfium2](https://github.com/pypdfium2-team/pypdfium2).
