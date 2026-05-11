const widgetRenderers = {
    variables(stage) {
        stage.innerHTML = `
            <div class="widget-flow">
                <div class="widget-node">name</div>
                <div>→</div>
                <div class="widget-node">"Minh"</div>
                <div class="widget-node">age</div>
                <div>→</div>
                <div class="widget-node">20</div>
            </div>
        `;
    },
    condition(stage) {
        stage.innerHTML = `
            <div class="widget-flow">
                <div class="widget-node">score = 8</div>
                <div>→</div>
                <div class="widget-node">score >= 5</div>
                <div>→</div>
                <div class="widget-node">Pass</div>
            </div>
        `;
    },
    loop(stage) {
        stage.innerHTML = `
            <div class="widget-flow">
                <div class="widget-node">range(3)</div>
                <div>→</div>
                <div class="widget-node">0</div>
                <div class="widget-node">1</div>
                <div class="widget-node">2</div>
            </div>
        `;
    },
    function(stage) {
        stage.innerHTML = `
            <div class="widget-flow">
                <div class="widget-node">add(2, 3)</div>
                <div>→</div>
                <div class="widget-node">return 5</div>
            </div>
        `;
    }
};

document.querySelectorAll("[data-widget]").forEach((panel) => {
    const stage = panel.querySelector(".widget-stage");
    const type = panel.dataset.widget;
    const renderer = widgetRenderers[type] || widgetRenderers.variables;
    renderer(stage);
});
