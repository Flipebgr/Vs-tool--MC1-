/*
 * Interações client-side que o dash-cytoscape não expõe diretamente como
 * propriedades declarativas:
 *
 * 1. centralizar a câmera no nó encontrado pela busca;
 * 2. enquadrar todos os participantes de um evento selecionado na Timeline;
 * 3. detectar clique no fundo vazio do grafo para limpar o destaque.
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

        if (!cy) {
            if (attempt < MAX_ATTACH_ATTEMPTS) {
                window.setTimeout(function () {
                    ensureBackgroundTapHandler(attempt + 1);
                }, ATTACH_RETRY_MS);
            }
            return;
        }

        if (cy.scratch("_tenantThreadBackgroundTapInstalled")) {
            return;
        }

        cy.scratch("_tenantThreadBackgroundTapInstalled", true);
        cy.on("tap", function (event) {
            if (event.target !== cy) {
                return;
            }

            const clearButton = document.getElementById("clear-graph-highlight");
            if (clearButton) {
                clearButton.click();
            }
        });
    }

    function collectionFromIds(cy, targetValue) {
        const ids = Array.isArray(targetValue) ? targetValue : [targetValue];
        let collection = cy.collection();

        ids.forEach(function (nodeId) {
            if (!nodeId) {
                return;
            }
            const node = cy.getElementById(nodeId);
            if (node && node.length > 0) {
                collection = collection.union(node);
            }
        });

        return collection;
    }

    window.dash_clientside.graph_interactions = {
        center_on_node: function (targetValue) {
            ensureBackgroundTapHandler(0);

            if (!targetValue) {
                return window.dash_clientside.no_update;
            }

            const cy = getCyInstance();
            if (!cy) {
                return window.dash_clientside.no_update;
            }

            const targets = collectionFromIds(cy, targetValue);
            if (!targets || targets.length === 0) {
                return window.dash_clientside.no_update;
            }

            if (targets.length === 1) {
                cy.animate(
                    { center: { eles: targets }, zoom: 1.5 },
                    { duration: 500 }
                );
            } else {
                cy.animate(
                    { fit: { eles: targets, padding: 90 } },
                    { duration: 500 }
                );
            }

            return window.dash_clientside.no_update;
        },
    };
})();
