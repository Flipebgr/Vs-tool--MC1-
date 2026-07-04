/*
 * Interações client-side que o dash-cytoscape não expõe diretamente como
 * propriedades declarativas:
 *
 * 1. centralizar a câmera no nó encontrado pela busca;
 * 2. detectar clique no fundo vazio do grafo para limpar o destaque.
 *
 * A instância viva do Cytoscape.js fica em `_cyreg.cy` no elemento DOM do
 * componente. Essa referência já era usada pela centralização de câmera.
 */
window.dash_clientside = window.dash_clientside || {};

(function () {
    const MAX_ATTACH_ATTEMPTS = 20;
    const ATTACH_RETRY_MS = 100;

    function getCyInstance() {
        const container = document.getElementById("graph");
        if (!container) {
            return null;
        }
        return container._cyreg && container._cyreg.cy
            ? container._cyreg.cy
            : null;
    }

    function ensureBackgroundTapHandler(attempt) {
        const cy = getCyInstance();

        // Na carga inicial, o componente React pode existir antes da instância
        // Cytoscape. Fazemos tentativas curtas e limitadas para registrar o
        // listener sem exigir qualquer ação do usuário.
        if (!cy) {
            if (attempt < MAX_ATTACH_ATTEMPTS) {
                window.setTimeout(function () {
                    ensureBackgroundTapHandler(attempt + 1);
                }, ATTACH_RETRY_MS);
            }
            return;
        }

        // Evita registrar o mesmo listener novamente quando a busca centraliza
        // outros nós ou quando callbacks atualizam os elementos do grafo.
        if (cy.scratch("_tenantThreadBackgroundTapInstalled")) {
            return;
        }

        cy.scratch("_tenantThreadBackgroundTapInstalled", true);
        cy.on("tap", function (event) {
            // Quando o alvo do evento é a própria instância `cy`, o clique foi
            // no canvas vazio — não em um nó ou aresta.
            if (event.target !== cy) {
                return;
            }

            const clearButton = document.getElementById("clear-graph-highlight");
            if (clearButton) {
                clearButton.click();
            }
        });
    }

    window.dash_clientside.graph_interactions = {
        center_on_node: function (nodeId) {
            // O callback também roda na inicialização; aproveitamos essa
            // execução para instalar o listener de clique no fundo.
            ensureBackgroundTapHandler(0);

            if (!nodeId) {
                return window.dash_clientside.no_update;
            }

            const cy = getCyInstance();
            if (!cy) {
                return window.dash_clientside.no_update;
            }

            const target = cy.getElementById(nodeId);
            if (target && target.length > 0) {
                cy.animate(
                    { center: { eles: target }, zoom: 1.5 },
                    { duration: 500 }
                );
            }

            return window.dash_clientside.no_update;
        },
    };
})();
