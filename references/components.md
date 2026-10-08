# Componentes de conteúdo

Todo componente exige `type`. `title` é opcional quando indicado. Valores são conteúdo, nunca instruções visuais.

## Dois modos de documento

O documento raiz usa **um** destes modos, nunca os dois:

- `sections`: lista de seções com componentes. Cada seção começa em página nova com o cabeçalho `SEÇÃO`.
- `content`: um único texto em **Markdown**. O pdfy pagina o texto corrido mantendo o cabeçalho oficial (logo) e o rodapé com a paginação, sem o chrome de seção. Ideal para relatórios e documentos longos.

## Markdown (campo `content`)

Escrever o Markdown como texto normal; o pdfy aplica a identidade oficial. Recursos suportados:

- títulos `#`, `##`, `###`, `####`;
- `**negrito**`, `*itálico*`, `~~riscado~~` e `` `código` ``;
- listas com `-`/`*` e numeradas com `1.`, inclusive aninhadas;
- citações com `>`;
- tabelas `| ... |` com alinhamento por coluna (`:---:`, `---:`);
- blocos de código com cercas ``` ``` ```;
- links `[texto](url)`;
- linhas horizontais `---`.

Não há fonte monoespaçada nem itálico verdadeiro: o pdfy usa os pesos oficiais Montserrat. Imagens `![alt](url)` viram legenda com o texto alternativo, porque o renderer não acessa a rede. HTML é tratado como texto simples.

## Texto e ênfase

- `text`: `content` obrigatório; `title` opcional. Separar parágrafos com linha vazia.
- `highlights`: `items` com mensagens curtas; `title` opcional.
- `callout`: `content` e `title` opcional. Usar para uma decisão ou mensagem dominante.
- `list`: `items` de texto e `title` opcional. Para sequência ordenada, usar `steps`.

## Blocos estruturados

- `metrics`: `items` com `label`, `value` e `note` opcional.
- `cards`: `items` com `title`, `description` e `tag` opcional.
- `steps`: `items` com `title` e `description` opcional; a numeração é automática.
- `timeline`: `items` com `period`, `title` e `description` opcional.
- `comparison`: `left_label`, `right_label` e `rows`; cada linha usa `label`, `left` e `right`.

## Dados

- `chart`: `items` com `label`, `value` numérico não negativo e `note` opcional; `unit` é opcional. O gráfico oficial é sempre de barras horizontais.
- `table`: `columns` e `rows`; cada linha deve ter exatamente a quantidade declarada de colunas.
- `investment`: `items` com `label`, `value` e `description` opcional; aceita `total` e `notes` opcionais. O pdfy não soma nem formata moeda.

## Assinatura

- `signature`: `signers` com `name` e campos opcionais `role`, `organization` e `identifier`; `intro` e `title` são opcionais. Usar `[PREENCHER]` somente quando o campo for indispensável e não tiver sido informado.

Consultar `examples/complete-document.json` para combinações funcionais de todos os componentes.
