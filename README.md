# Tenant Thread Visual Analytics

Aplicação Dash para investigar o **VAST Challenge 2026 — Mini Challenge 2**. O projeto combina o organograma da Tenant Thread com os eventos do dataset para explorar relações estruturais, reconstruir a propagação de artefatos e comparar publicações automatizadas no SaidIT.

## Funcionalidades atuais

O workspace preserva o estado da investigação ao navegar entre oito views:

- **Grafo organizacional:** pessoas, agentes, departamentos, equipes, sistemas e relações, com busca, filtros e layouts Cytoscape.
- **Timeline:** densidade temporal com zoom até eventos individuais, localização por ID e seleção do ponto inicial da investigação.
- **Cadeia de Eventos:** reconstrução rastreável da cadeia essencial ou de todos os eventos relacionados ao artefato.
- **Visão geral do caso:** indicadores e composição do caso selecionado.
- **Fluxo da evidência:** percurso entre instruções, artefatos, agentes, sistemas e publicação.
- **Matriz de participação:** papéis das entidades na cadeia essencial.
- **Casos semelhantes:** comparação de escala, sequência operacional, valores exatos e ponto de intervenção.
- **Análise Investigativa:** evidências diretas, inferências suportadas, limitações e recomendações.

As quatro views centrais de comparação compõem o módulo de **Visual Analytics**. A navegação lateral troca a view ativa sem descartar filtros, seleção temporal, cadeia ou caso em análise.

## Casos conhecidos

A análise comparativa cobre três publicações automatizadas alimentadas por arquivo:

- evento **27290** — caso `HiddenOrca.txt`;
- evento **98591** — caso `MellowOtter.txt`;
- evento **373902** — caso anômalo principal, `SwiftWren.txt`, aberto por padrão.

Para o evento 373902, os artefatos atuais produzem uma cadeia essencial de 8 eventos e uma cadeia completa de 191 eventos relacionados.

## Requisitos e instalação

Recomenda-se **Python 3.12** (validação de entrega realizada com Python 3.12.13). No Windows, a partir da raiz do projeto:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
py -m pip install -r requirements.txt
```

As versões em `requirements.txt` são apenas das dependências diretas e foram fixadas após instalação e validação em ambiente virtual limpo.

## Dados necessários

A aplicação consome diretamente estes artefatos versionados em `data/processed/`:

- `entities.json` — entidades normalizadas;
- `events.parquet` — eventos normalizados e timestamps resolvidos;
- `graph.json` — grafo organizacional unificado;
- `unresolved_parties.json` — registro de participantes não resolvidos.

Com esses quatro arquivos presentes, não é necessário executar o ETL para iniciar a aplicação. Para regenerá-los opcionalmente, mantenha também `data/raw/org_chart.json` e `data/raw/MC2_data.json` e execute:

```powershell
py -m services.etl
```

## Execução

Com o ambiente virtual ativado:

```powershell
py app.py
```

Abra o endereço local exibido pelo Dash no terminal.

## Validação

Os testes de preparação para entrega usam somente `unittest` da biblioteca padrão:

```powershell
py -m unittest discover -s tests -v
```

Eles verificam importação da aplicação, endpoints Dash, 16 callbacks, 82 IDs de componentes sem duplicação, contagens das cadeias do caso 373902 e o filtro `led_by`.

## Estrutura

```text
app.py                 inicialização do Dash
assets/                estilos e comportamento no navegador
callbacks/             interação e navegação do workspace
components/            composição das views
data/raw/              fontes originais do desafio
data/processed/        artefatos consumidos pela aplicação
services/              ETL e serviços analíticos
tests/                 validações de preparação para entrega
utils/                 carregamento, estilos e construção do grafo
```

## Limitações do dataset

- O dataset registra operações e metadados, mas não contém o texto de `SwiftWren.txt` nem de `SwiftWren_further_instructions.md`; portanto, a intenção e o significado semântico da mensagem não podem ser afirmados diretamente.
- A causalidade apresentada é limitada a referências explícitas de artefato, transferências observadas, participantes compartilhados e proximidade temporal. A interface separa evidência direta de inferência e não inventa arestas causais.
- A origem inicial de um arquivo pode estar fora do intervalo observado; nesses casos, a primeira evidência disponível já pode ser uma transferência.
- As comparações são restritas aos três casos automatizados identificados neste recorte e não demonstram, por si só, generalização para eventos ausentes do dataset.
