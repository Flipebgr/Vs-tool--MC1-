/*
 * Centraliza a câmera do Cytoscape.js no nó buscado.
 *
 * dash-cytoscape (via react-cytoscapejs) guarda a instância viva do
 * Cytoscape.js no próprio elemento DOM do grafo, em `_cyreg.cy`. Não é uma
 * API pública documentada, mas é a técnica padrão usada pela comunidade
 * dash-cytoscape para interações que a biblioteca não expõe como prop
 * declarativa (como "centralizar em um nó específico").
 *
 * Se essa referência interna mudar em uma atualização futura da lib, este
 * arquivo é o único lugar que precisa ser ajustado.
 */
window.dash_clientside = window.dash_clientside || {};

window.dash_clientside.graph_interactions = {
    center_on_node: function (nodeId) {
        const container = document.getElementById("graph");
        if (!container || !nodeId) {
            return window.dash_clientside.no_update;
        }

        const cy = container._cyreg && container._cyreg.cy;
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
