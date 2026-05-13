const widgetRenderers = {
    variables(stage) {
        stage.innerHTML = `
            <div class="widget-flow">
                <div class="widget-node">name</div>
                <div>-&gt;</div>
                <div class="widget-node">"Minh"</div>
                <div class="widget-node">age</div>
                <div>-&gt;</div>
                <div class="widget-node">20</div>
            </div>
        `;
    },
    condition(stage) {
        stage.innerHTML = `
            <div class="widget-flow">
                <div class="widget-node">score = 8</div>
                <div>-&gt;</div>
                <div class="widget-node">score &gt;= 5</div>
                <div>-&gt;</div>
                <div class="widget-node">Pass</div>
            </div>
        `;
    },
    loop(stage) {
        stage.innerHTML = `
            <div class="widget-flow">
                <div class="widget-node">range(3)</div>
                <div>-&gt;</div>
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
                <div>-&gt;</div>
                <div class="widget-node">return 5</div>
            </div>
        `;
    },
    logic_gates(stage) {
        stage.innerHTML = `
            <div class="widget-flow">
                <div class="widget-node">A = 1</div>
                <div class="widget-node">B = 0</div>
                <div>AND</div>
                <div class="widget-node">0</div>
                <div>OR</div>
                <div class="widget-node">1</div>
                <div>XOR</div>
                <div class="widget-node">1</div>
            </div>
        `;
    },
    truth_table(stage) {
        stage.innerHTML = `
            <div class="widget-flow">
                <div class="widget-node">00 -&gt; 0</div>
                <div class="widget-node">01 -&gt; 1</div>
                <div class="widget-node">10 -&gt; 1</div>
                <div class="widget-node">11 -&gt; 0</div>
                <div>XOR</div>
            </div>
        `;
    },
    logisim_flow(stage) {
        stage.innerHTML = `
            <div class="widget-flow">
                <div class="widget-node">Pins</div>
                <div>-&gt;</div>
                <div class="widget-node">Gates</div>
                <div>-&gt;</div>
                <div class="widget-node">Wires</div>
                <div>-&gt;</div>
                <div class="widget-node">LED</div>
            </div>
        `;
    },
    adders(stage) {
        stage.innerHTML = `
            <div class="widget-flow">
                <div class="widget-node">X</div>
                <div class="widget-node">Y</div>
                <div>xor</div>
                <div class="widget-node">Sum</div>
                <div>and</div>
                <div class="widget-node">Carry</div>
            </div>
        `;
    },
    data_routing(stage) {
        stage.innerHTML = `
            <div class="widget-flow">
                <div class="widget-node">Select</div>
                <div>controls</div>
                <div class="widget-node">Input 0</div>
                <div class="widget-node">Input 1</div>
                <div>-&gt;</div>
                <div class="widget-node">Output</div>
            </div>
        `;
    }
};

document.querySelectorAll("[data-widget]").forEach((panel) => {
    const stage = panel.querySelector(".widget-stage");
    const type = panel.dataset.widget;
    const renderer = widgetRenderers[type] || widgetRenderers.variables;
    renderer(stage);
    stage.querySelectorAll(".widget-node").forEach((node, index) => {
        node.style.animationDelay = `${index * 60}ms`;
    });
});
