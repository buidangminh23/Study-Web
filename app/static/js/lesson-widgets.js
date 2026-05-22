/* ── Utility helpers ──────────────────────────────────────── */
function el(tag, cls, html) {
  const e = document.createElement(tag);
  if (cls) e.className = cls;
  if (html) e.innerHTML = html;
  return e;
}

const widgetRenderers = {

  /* ── 1. MATRIX MULTIPLIER ─────────────────────────────── */
  matrix_mult(stage) {
    stage.innerHTML = `
      <div class="wg-wrap">
        <h4 class="wg-title">Interactive Matrix Multiplier (2×2)</h4>
        <div class="wg-matmult">
          <div class="wg-mat-box">
            <div class="wg-mat-label">Matrix A</div>
            <div class="mat-grid-2">
              <input class="mval" value="1"><input class="mval" value="2">
              <input class="mval" value="3"><input class="mval" value="4">
            </div>
          </div>
          <div class="wg-op-sym">×</div>
          <div class="wg-mat-box">
            <div class="wg-mat-label">Matrix B</div>
            <div class="mat-grid-2">
              <input class="mval" value="5"><input class="mval" value="6">
              <input class="mval" value="7"><input class="mval" value="8">
            </div>
          </div>
          <div class="wg-op-sym">=</div>
          <div class="wg-mat-box result-box">
            <div class="wg-mat-label">Result C</div>
            <div class="mat-grid-2" id="matResult"></div>
          </div>
        </div>
        <div class="wg-formula" id="matFormula"></div>
      </div>`;
    const compute = () => {
      const boxes = stage.querySelectorAll(".wg-mat-box");
      const a = [...boxes[0].querySelectorAll(".mval")].map(i=>+i.value||0);
      const b = [...boxes[1].querySelectorAll(".mval")].map(i=>+i.value||0);
      const c = [a[0]*b[0]+a[1]*b[2], a[0]*b[1]+a[1]*b[3], a[2]*b[0]+a[3]*b[2], a[2]*b[1]+a[3]*b[3]];
      stage.querySelector("#matResult").innerHTML = c.map(v=>`<span class="pop">${Number.isInteger(v)?v:v.toFixed(2)}</span>`).join("");
      stage.querySelector("#matFormula").innerHTML = `C₁₁=${a[0]}·${b[0]}+${a[1]}·${b[2]}=<b>${c[0]}</b> &nbsp; C₁₂=${a[0]}·${b[1]}+${a[1]}·${b[3]}=<b>${c[1]}</b>`;
    };
    stage.querySelectorAll(".mval").forEach(i=>i.addEventListener("input",compute));
    compute();
  },

  /* ── 2. DETERMINANT ──────────────────────────────────── */
  determinant_calc(stage) {
    stage.innerHTML = `
      <div class="wg-wrap">
        <h4 class="wg-title">2×2 Determinant Calculator</h4>
        <div class="wg-det-layout">
          <div class="wg-det-matrix">
            <span class="mat-bracket">|</span>
            <div class="mat-grid-2">
              <input class="mval" value="3" id="da"><input class="mval" value="1" id="db">
              <input class="mval" value="2" id="dc"><input class="mval" value="4" id="dd">
            </div>
            <span class="mat-bracket">|</span>
          </div>
          <div class="wg-det-steps">
            <div id="detStep1" class="step-row"></div>
            <div id="detFinal" class="step-row step-final"></div>
          </div>
        </div>
      </div>`;
    const compute = () => {
      const [a,b,c,d] = ["da","db","dc","dd"].map(id=>+stage.querySelector(`#${id}`).value||0);
      const det = a*d-b*c;
      stage.querySelector("#detStep1").innerHTML = `det(A) = (${a})(${d}) − (${b})(${c}) = ${a*d} − ${b*c}`;
      stage.querySelector("#detFinal").innerHTML = `= <b style="color:var(--primary);font-size:22px">${det}</b> &nbsp;<span class="det-badge" style="background:${det===0?"#fef2f2;color:#b91c1c":"#f0fdf4;color:#15803d"}">${det===0?"Singular ⚠":"Non-singular ✓"}</span>`;
    };
    stage.querySelectorAll(".mval").forEach(i=>i.addEventListener("input",compute));
    compute();
  },

  /* ── 3. VECTOR 2D ────────────────────────────────────── */
  vector_2d(stage) {
    const W=320, H=240, cx=160, cy=120, sc=36;
    stage.innerHTML = `
      <div class="wg-wrap">
        <h4 class="wg-title">2D Vector Explorer</h4>
        <div class="wg-vec-layout">
          <canvas width="${W}" height="${H}" id="vecCanvas" class="wg-canvas"></canvas>
          <div class="wg-vec-controls">
            <div class="vec-ctrl-group"><b style="color:#e74c3c">u</b> &nbsp;
              x:<input type="range" min="-3" max="3" value="2" step="0.5" id="ux" class="range-sm"><span id="uxv">2</span>
              y:<input type="range" min="-3" max="3" value="1" step="0.5" id="uy" class="range-sm"><span id="uyv">1</span>
            </div>
            <div class="vec-ctrl-group"><b style="color:#3498db">v</b> &nbsp;
              x:<input type="range" min="-3" max="3" value="1" step="0.5" id="vx" class="range-sm"><span id="vxv">1</span>
              y:<input type="range" min="-3" max="3" value="2" step="0.5" id="vy" class="range-sm"><span id="vyv">2</span>
            </div>
            <div class="vec-info" id="vecInfo"></div>
          </div>
        </div>
      </div>`;
    const canvas = stage.querySelector("#vecCanvas");
    const ctx = canvas.getContext("2d");
    const drawArrow = (x1,y1,x2,y2,color,label) => {
      const dx=x2-x1, dy=y2-y1, len=Math.sqrt(dx*dx+dy*dy);
      if(len<1) return;
      ctx.strokeStyle=color; ctx.fillStyle=color; ctx.lineWidth=2.5;
      ctx.beginPath(); ctx.moveTo(x1,y1); ctx.lineTo(x2,y2); ctx.stroke();
      const angle=Math.atan2(dy,dx);
      ctx.beginPath();
      ctx.moveTo(x2,y2);
      ctx.lineTo(x2-10*Math.cos(angle-0.35),y2-10*Math.sin(angle-0.35));
      ctx.lineTo(x2-10*Math.cos(angle+0.35),y2-10*Math.sin(angle+0.35));
      ctx.closePath(); ctx.fill();
      ctx.font="bold 13px sans-serif"; ctx.fillText(label,x2+6,y2-6);
    };
    const draw = () => {
      const ux=+stage.querySelector("#ux").value, uy=+stage.querySelector("#uy").value;
      const vx=+stage.querySelector("#vx").value, vy=+stage.querySelector("#vy").value;
      stage.querySelector("#uxv").textContent=ux; stage.querySelector("#uyv").textContent=uy;
      stage.querySelector("#vxv").textContent=vx; stage.querySelector("#vyv").textContent=vy;
      const dot=ux*vx+uy*vy, mU=Math.sqrt(ux*ux+uy*uy), mV=Math.sqrt(vx*vx+vy*vy);
      const ang=mU&&mV?(Math.acos(Math.max(-1,Math.min(1,dot/(mU*mV))))*180/Math.PI).toFixed(1):"—";
      stage.querySelector("#vecInfo").innerHTML=`u·v = <b>${dot}</b> &nbsp;|&nbsp; |u|=${mU.toFixed(2)} &nbsp;|&nbsp; |v|=${mV.toFixed(2)}<br>θ = ${ang}°${dot===0?" &nbsp;<b style='color:var(--primary)'>Orthogonal!</b>":""}`;
      ctx.clearRect(0,0,W,H);
      ctx.strokeStyle="#f3f4f6"; ctx.lineWidth=1;
      for(let i=-4;i<=4;i++){
        ctx.beginPath(); ctx.moveTo(cx+i*sc,10); ctx.lineTo(cx+i*sc,H-10); ctx.stroke();
        ctx.beginPath(); ctx.moveTo(10,cy+i*sc); ctx.lineTo(W-10,cy+i*sc); ctx.stroke();
      }
      ctx.strokeStyle="#9ca3af"; ctx.lineWidth=1.5;
      ctx.beginPath(); ctx.moveTo(10,cy); ctx.lineTo(W-10,cy); ctx.stroke();
      ctx.beginPath(); ctx.moveTo(cx,10); ctx.lineTo(cx,H-10); ctx.stroke();
      drawArrow(cx,cy,cx+ux*sc,cy-uy*sc,"#e74c3c","u");
      drawArrow(cx,cy,cx+vx*sc,cy-vy*sc,"#3498db","v");
      drawArrow(cx,cy,cx+(ux+vx)*sc,cy-(uy+vy)*sc,"#27ae60","u+v");
    };
    stage.querySelectorAll("input[type=range]").forEach(r=>r.addEventListener("input",draw));
    draw();
  },

  /* ── 4. COMPLEX PLANE ───────────────────────────────── */
  complex_plane(stage) {
    const W=280, H=240, cx=140, cy=120, sc=42;
    stage.innerHTML = `
      <div class="wg-wrap">
        <h4 class="wg-title">Argand Plane</h4>
        <div style="display:flex;gap:16px;align-items:flex-start;flex-wrap:wrap">
          <canvas width="${W}" height="${H}" id="cpCanvas" class="wg-canvas"></canvas>
          <div style="min-width:150px">
            <div class="vec-ctrl-group">Re(a):<input type="range" min="-3" max="3" value="2" step="0.5" id="ca" class="range-sm"><span id="cav">2</span></div>
            <div class="vec-ctrl-group">Im(b):<input type="range" min="-3" max="3" value="1" step="0.5" id="cb" class="range-sm"><span id="cbv">1</span></div>
            <div class="wg-complex-display" id="cDisplay"></div>
            <button class="wg-btn" id="rotBtn" style="margin-top:8px;width:100%">Multiply by i</button>
          </div>
        </div>
      </div>`;
    let a=2, b=1;
    const canvas = stage.querySelector("#cpCanvas");
    const ctx = canvas.getContext("2d");
    const draw = () => {
      const mod=Math.sqrt(a*a+b*b), arg=(Math.atan2(b,a)*180/Math.PI).toFixed(1);
      stage.querySelector("#cav").textContent=a; stage.querySelector("#cbv").textContent=b;
      stage.querySelector("#cDisplay").innerHTML=`<b>z = ${a}${b>=0?"+":""}${b}i</b><br>|z| = ${mod.toFixed(3)}<br>arg(z) = ${arg}°<br>z̄ = ${a}${-b>=0?"+":""}${-b}i`;
      ctx.clearRect(0,0,W,H);
      ctx.strokeStyle="#f3f4f6"; ctx.lineWidth=1;
      for(let i=-3;i<=3;i++){
        ctx.beginPath(); ctx.moveTo(cx+i*sc,10); ctx.lineTo(cx+i*sc,H-10); ctx.stroke();
        ctx.beginPath(); ctx.moveTo(10,cy+i*sc); ctx.lineTo(W-10,cy+i*sc); ctx.stroke();
      }
      ctx.strokeStyle="#9ca3af"; ctx.lineWidth=1.5;
      ctx.beginPath(); ctx.moveTo(10,cy); ctx.lineTo(W-10,cy); ctx.stroke();
      ctx.beginPath(); ctx.moveTo(cx,10); ctx.lineTo(cx,H-10); ctx.stroke();
      ctx.fillStyle="#6b7280"; ctx.font="11px sans-serif";
      ctx.fillText("Re",W-22,cy-6); ctx.fillText("Im",cx+4,15);
      if(mod>0){
        const px=cx+a*sc, py=cy-b*sc;
        ctx.strokeStyle="var(--primary)||#0f766e"; ctx.lineWidth=2.5;
        ctx.beginPath(); ctx.moveTo(cx,cy); ctx.lineTo(px,py); ctx.stroke();
        ctx.fillStyle="#0f766e"; ctx.beginPath(); ctx.arc(px,py,5,0,Math.PI*2); ctx.fill();
        ctx.fillStyle="#0f766e"; ctx.font="bold 13px sans-serif"; ctx.fillText("z",px+6,py-6);
        // Conjugate
        ctx.fillStyle="#c2410c"; ctx.beginPath(); ctx.arc(px,cy+b*sc,4,0,Math.PI*2); ctx.fill();
        ctx.fillText("z̄",px+6,cy+b*sc+4);
        // Dashed lines
        ctx.setLineDash([4,4]); ctx.strokeStyle="#94a3b8"; ctx.lineWidth=1;
        ctx.beginPath(); ctx.moveTo(px,py); ctx.lineTo(px,cy); ctx.stroke();
        ctx.beginPath(); ctx.moveTo(cx,cy); ctx.lineTo(px,cy); ctx.stroke();
        ctx.setLineDash([]);
      }
    };
    stage.querySelector("#ca").addEventListener("input",e=>{a=+e.target.value;draw();});
    stage.querySelector("#cb").addEventListener("input",e=>{b=+e.target.value;draw();});
    stage.querySelector("#rotBtn").addEventListener("click",()=>{
      [a,b]=[-b,a];
      stage.querySelector("#ca").value=a; stage.querySelector("#cb").value=b; draw();
    });
    draw();
  },

  /* ── 5. BINARY CONVERTER ─────────────────────────────── */
  binary_converter(stage) {
    stage.innerHTML = `
      <div class="wg-wrap">
        <h4 class="wg-title">Binary / Hex / Decimal Converter</h4>
        <div class="wg-bin-inputs">
          <label>Decimal<input type="number" id="decIn" class="wg-num-input" value="78" min="0" max="255"></label>
          <label>Hex<input id="hexIn" class="wg-num-input" style="text-transform:uppercase" value="4E" maxlength="2"></label>
        </div>
        <div class="wg-bits" id="bitRow"></div>
        <div class="wg-bit-labels"><span>128</span><span>64</span><span>32</span><span>16</span><span>8</span><span>4</span><span>2</span><span>1</span></div>
        <div class="wg-bin-formula" id="binFormula"></div>
      </div>`;
    let bits = Array(8).fill(0);
    const fromDec = v => { v=Math.max(0,Math.min(255,v)); bits=Array(8).fill(0).map((_,i)=>(v>>(7-i))&1); render(); };
    const render = () => {
      const val = bits.reduce((s,b,i)=>s+b*(128>>i),0);
      stage.querySelector("#decIn").value=val;
      stage.querySelector("#hexIn").value=val.toString(16).toUpperCase().padStart(2,"0");
      const row = stage.querySelector("#bitRow"); row.innerHTML="";
      bits.forEach((b,i)=>{
        const btn=document.createElement("button");
        btn.className=`bit-btn ${b?"bit-on":"bit-off"}`; btn.textContent=b;
        btn.onclick=()=>{bits[i]^=1;render();}; row.appendChild(btn);
      });
      const terms=bits.map((b,i)=>b?`${b}×${128>>i}`:"").filter(Boolean);
      stage.querySelector("#binFormula").innerHTML=(terms.length?terms.join(" + "):`0`)+` = <b>${val}</b>`;
    };
    stage.querySelector("#decIn").addEventListener("change",e=>fromDec(+e.target.value));
    stage.querySelector("#hexIn").addEventListener("input",e=>{const v=parseInt(e.target.value,16);if(!isNaN(v))fromDec(v);});
    fromDec(78);
  },

  /* ── 6. TWO'S COMPLEMENT ─────────────────────────────── */
  twos_complement(stage) {
    stage.innerHTML = `
      <div class="wg-wrap">
        <h4 class="wg-title">Two's Complement (Step by Step)</h4>
        <div class="wg-bin-inputs">
          <label>Decimal (−128 to 127)<input type="number" id="tcIn" class="wg-num-input" value="-5" min="-128" max="127"></label>
        </div>
        <div id="tcSteps" class="tc-steps"></div>
      </div>`;
    const show = () => {
      const n=Math.max(-128,Math.min(127,+stage.querySelector("#tcIn").value||0));
      const pos=Math.abs(n);
      const posBits=pos.toString(2).padStart(8,"0");
      const flipped=posBits.split("").map(b=>b==="0"?"1":"0").join("");
      const tc=n<0?((~pos+1)&0xFF).toString(2).padStart(8,"0"):posBits;
      const unsigned=parseInt(tc,2);
      stage.querySelector("#tcSteps").innerHTML = n>=0
        ? `<div class="tc-step"><span class="tc-num">Positive</span> ${n} → binary directly</div>
           <div class="tc-row"><span class="tc-tag ok">Result</span><span class="tc-bits">${tc}</span></div>`
        : `<div class="tc-step"><span class="tc-num">Step 1</span> Write |${n}| = ${pos} in binary</div>
           <div class="tc-row"><span class="tc-tag">+${pos}</span><span class="tc-bits">${posBits}</span></div>
           <div class="tc-step"><span class="tc-num">Step 2</span> Flip all bits (one's complement)</div>
           <div class="tc-row"><span class="tc-tag">Flip</span><span class="tc-bits">${flipped}</span></div>
           <div class="tc-step"><span class="tc-num">Step 3</span> Add 1</div>
           <div class="tc-row"><span class="tc-tag ok">= ${n}</span><span class="tc-bits pop">${tc}</span></div>
           <div class="tc-verify">Check: 0b${tc} = ${unsigned} (unsigned) = ${unsigned>=128?unsigned-256:unsigned} (signed)</div>`;
    };
    stage.querySelector("#tcIn").addEventListener("input",show);
    show();
  },

  /* ── 7. SQL JOIN ─────────────────────────────────────── */
  sql_join(stage) {
    const joins = {
      INNER:{l:"none",r:"none",m:"rgba(15,118,110,.55)",d:"Returns ONLY rows matching in BOTH tables."},
      LEFT: {l:"rgba(15,118,110,.25)",r:"none",m:"rgba(15,118,110,.55)",d:"ALL rows from left + matched rows from right (NULL if no match)."},
      RIGHT:{l:"none",r:"rgba(194,65,12,.25)",m:"rgba(15,118,110,.55)",d:"ALL rows from right + matched rows from left (NULL if no match)."},
      FULL: {l:"rgba(15,118,110,.25)",r:"rgba(194,65,12,.25)",m:"rgba(15,118,110,.55)",d:"ALL rows from BOTH tables, NULL where no match."},
    };
    stage.innerHTML = `
      <div class="wg-wrap">
        <h4 class="wg-title">SQL JOIN Visualizer</h4>
        <div class="wg-join-btns">
          ${Object.keys(joins).map(j=>`<button class="wg-btn join-btn" data-j="${j}">${j}</button>`).join("")}
        </div>
        <svg width="300" height="150" id="joinSvg" style="display:block;margin:0 auto"></svg>
        <div class="wg-join-desc" id="joinDesc"></div>
        <pre class="wg-join-sql" id="joinSql"></pre>
      </div>`;
    const draw = j => {
      const c=joins[j];
      const s=stage.querySelector("#joinSvg");
      s.innerHTML=`<defs><clipPath id="cl"><circle cx="175" cy="75" r="55"/></clipPath></defs>
        <circle cx="125" cy="75" r="55" fill="${c.l}" stroke="#0f766e" stroke-width="2.5"/>
        <circle cx="175" cy="75" r="55" fill="${c.r}" stroke="#c2410c" stroke-width="2.5"/>
        <circle cx="125" cy="75" r="55" fill="${c.m}" clip-path="url(#cl)"/>
        <text x="90" y="80" text-anchor="middle" font-weight="bold" font-size="14" fill="#1f2937">A</text>
        <text x="210" y="80" text-anchor="middle" font-weight="bold" font-size="14" fill="#1f2937">B</text>
        <text x="150" y="80" text-anchor="middle" font-size="11" fill="white" font-weight="bold">∩</text>`;
      stage.querySelector("#joinDesc").textContent=c.d;
      stage.querySelector("#joinSql").textContent=`SELECT * FROM A\n${j} JOIN B ON A.id = B.id`;
      stage.querySelectorAll(".join-btn").forEach(b=>b.classList.toggle("active",b.dataset.j===j));
    };
    stage.querySelectorAll(".join-btn").forEach(b=>b.addEventListener("click",()=>draw(b.dataset.j)));
    draw("INNER");
  },

  /* ── 8. VARIABLE BOX ─────────────────────────────────── */
  variable_box(stage) {
    stage.innerHTML = `
      <div class="wg-wrap">
        <h4 class="wg-title">Variable Memory Visualizer</h4>
        <div class="wg-var-input">
          <input id="varName" class="wg-text-input" placeholder="Identifier" value="score">
          <input id="varVal" class="wg-text-input" placeholder="Value" value="95">
          <select id="varType" class="wg-select"><option>int</option><option>str</option><option>float</option><option>bool</option></select>
          <button class="wg-btn" id="varAdd">Add</button>
          <button class="wg-btn-ghost" id="varClear">Clear</button>
        </div>
        <div class="wg-mem-grid" id="memGrid"></div>
      </div>`;
    const vars=[{name:"score",val:"95",type:"int"},{name:"attempts",val:"3",type:"int"},{name:"passed",val:"true",type:"bool"}];
    const colors={int:"#3b82f6",str:"#8b5cf6",float:"#f59e0b",bool:"#10b981"};
    const render=()=>{
      stage.querySelector("#memGrid").innerHTML=vars.map(v=>`
        <div class="mem-box pop" style="border-color:${colors[v.type]||"#6b7280"}">
          <div class="mem-type" style="background:${colors[v.type]||"#6b7280"}">${v.type}</div>
          <div class="mem-name">${v.name}</div>
          <div class="mem-val">${v.val}</div>
        </div>`).join("");
    };
    stage.querySelector("#varAdd").onclick=()=>{
      const nm=stage.querySelector("#varName").value.trim(), vl=stage.querySelector("#varVal").value.trim(), tp=stage.querySelector("#varType").value;
      if(nm&&vl){const ex=vars.find(v=>v.name===nm);if(ex)ex.val=vl;else vars.push({name:nm,val:vl,type:tp});render();}
    };
    stage.querySelector("#varClear").onclick=()=>{vars.length=0;render();};
    render();
  },

  /* ── 9. LOOP TRACER ──────────────────────────────────── */
  loop_trace(stage) {
    stage.innerHTML = `
      <div class="wg-wrap">
        <h4 class="wg-title">Loop Execution Tracer</h4>
        <div class="wg-loop-code"><code>for i in range(<input id="loopN" type="number" value="6" min="1" max="12" class="code-inline-input">):<br>&nbsp;&nbsp;&nbsp;&nbsp;print(i * 2)</code></div>
        <div class="wg-loop-track" id="loopTrack"></div>
        <div style="display:flex;gap:8px;margin-top:10px">
          <button class="wg-btn" id="loopStep">Step →</button>
          <button class="wg-btn" id="loopPlay">▶ Auto</button>
          <button class="wg-btn-ghost" id="loopReset">↺</button>
        </div>
        <div class="wg-loop-state" id="loopState"></div>
      </div>`;
    let cur=0, n=6, timer=null;
    const render=()=>{
      const tr=stage.querySelector("#loopTrack");
      tr.innerHTML=Array.from({length:n},(_,i)=>`<div class="loop-cell ${i<cur?"done":i===cur?"current":""}">${i}</div>`).join("");
      stage.querySelector("#loopState").innerHTML=cur<n?`i = <b>${cur}</b> → print(<b>${cur*2}</b>)`:`<b style="color:var(--primary)">Loop finished! ${n} iterations complete.</b>`;
    };
    const stop=()=>{clearInterval(timer);timer=null;stage.querySelector("#loopPlay").textContent="▶ Auto";};
    stage.querySelector("#loopStep").onclick=()=>{if(cur<n)cur++;render();};
    stage.querySelector("#loopPlay").onclick=()=>{
      if(timer){stop();return;}
      if(cur>=n)cur=0;
      timer=setInterval(()=>{if(cur<n){cur++;render();}else stop();},600);
      stage.querySelector("#loopPlay").textContent="⏸ Pause";
    };
    stage.querySelector("#loopReset").onclick=()=>{stop();cur=0;render();};
    stage.querySelector("#loopN").oninput=e=>{stop();n=Math.max(1,Math.min(12,+e.target.value));cur=0;render();};
    render();
  },

  /* ── 10. LINEAR TRANSFORMATION ──────────────────────── */
  transformation_2d(stage) {
    const W=280, H=220, cx=140, cy=110, sc=32;
    stage.innerHTML = `
      <div class="wg-wrap">
        <h4 class="wg-title">2D Linear Transformation</h4>
        <div style="display:flex;gap:14px;flex-wrap:wrap;align-items:flex-start">
          <canvas width="${W}" height="${H}" id="trCanvas" class="wg-canvas"></canvas>
          <div>
            <div class="wg-mat-label">Transform Matrix A</div>
            <div class="mat-grid-2" style="margin-bottom:8px">
              <input class="mval" id="ta" value="2"><input class="mval" id="tb" value="1">
              <input class="mval" id="tc" value="0"><input class="mval" id="td" value="1">
            </div>
            <div class="wg-presets">
              <button class="wg-btn-ghost" data-p="1,0,0,1">Identity</button>
              <button class="wg-btn-ghost" data-p="0,-1,1,0">Rotate 90°</button>
              <button class="wg-btn-ghost" data-p="-1,0,0,1">Reflect Y</button>
              <button class="wg-btn-ghost" data-p="2,0,0,2">Scale 2×</button>
            </div>
            <div id="trInfo" class="wg-info-box" style="margin-top:8px"></div>
          </div>
        </div>
      </div>`;
    const canvas=stage.querySelector("#trCanvas"), ctx=canvas.getContext("2d");
    const draw=()=>{
      const [a,b,c,d]=["ta","tb","tc","td"].map(k=>+stage.querySelector(`#t${k}`).value||0);
      const det=a*d-b*c;
      stage.querySelector("#trInfo").innerHTML=`det = ${det} (area scale ${Math.abs(det)}×)`;
      ctx.clearRect(0,0,W,H);
      const ts=([x,y])=>[cx+x*sc,cy-y*sc];
      ctx.strokeStyle="#f3f4f6"; ctx.lineWidth=1;
      for(let i=-4;i<=4;i++){
        ctx.beginPath();ctx.moveTo(cx+i*sc,10);ctx.lineTo(cx+i*sc,H-10);ctx.stroke();
        ctx.beginPath();ctx.moveTo(10,cy+i*sc);ctx.lineTo(W-10,cy+i*sc);ctx.stroke();
      }
      ctx.strokeStyle="#d1d5db"; ctx.lineWidth=1.5;
      ctx.beginPath();ctx.moveTo(10,cy);ctx.lineTo(W-10,cy);ctx.stroke();
      ctx.beginPath();ctx.moveTo(cx,10);ctx.lineTo(cx,H-10);ctx.stroke();
      // Original unit square (blue dashed)
      const orig=[[0,0],[1,0],[1,1],[0,1]].map(ts);
      ctx.setLineDash([4,4]); ctx.strokeStyle="#3b82f6"; ctx.lineWidth=1.5;
      ctx.beginPath(); orig.forEach(([x,y],i)=>i?ctx.lineTo(x,y):ctx.moveTo(x,y)); ctx.closePath(); ctx.stroke();
      ctx.fillStyle="rgba(59,130,246,.1)"; ctx.fill();
      ctx.setLineDash([]);
      // Transformed (green solid)
      const trans=[[0,0],[1,0],[1,1],[0,1]].map(([x,y])=>ts([a*x+b*y,c*x+d*y]));
      ctx.strokeStyle="#0f766e"; ctx.lineWidth=2.5;
      ctx.beginPath(); trans.forEach(([x,y],i)=>i?ctx.lineTo(x,y):ctx.moveTo(x,y)); ctx.closePath(); ctx.stroke();
      ctx.fillStyle="rgba(15,118,110,.15)"; ctx.fill();
      // Basis vectors
      [[a,c,"#e74c3c","e₁"],[b,d,"#3498db","e₂"]].forEach(([x,y,col,lbl])=>{
        const [px,py]=ts([x,y]);
        ctx.strokeStyle=col; ctx.lineWidth=2.5;
        ctx.beginPath(); ctx.moveTo(cx,cy); ctx.lineTo(px,py); ctx.stroke();
        ctx.fillStyle=col; ctx.beginPath(); ctx.arc(px,py,4,0,Math.PI*2); ctx.fill();
        ctx.font="bold 12px sans-serif"; ctx.fillText(lbl,px+5,py-5);
      });
    };
    stage.querySelectorAll(".mval").forEach(i=>i.addEventListener("input",draw));
    stage.querySelectorAll("[data-p]").forEach(btn=>btn.addEventListener("click",()=>{
      const [a,b,c,d]=btn.dataset.p.split(",").map(Number);
      ["ta","tb","tc","td"].forEach((k,i)=>stage.querySelector(`#t${k}`).value=[a,b,c,d][i]);
      draw();
    }));
    draw();
  },

  /* ── 11. 4Ps MARKETING ───────────────────────────────── */
  "4ps_diagram"(stage) {
    const ps=[
      {name:"🛍 Product",color:"#0f766e",items:["Core benefit","Features & quality","Branding","Packaging","Product lifecycle"]},
      {name:"💰 Price",color:"#7c3aed",items:["Cost-plus pricing","Price skimming","Penetration pricing","Value-based","Psychological ($9.99)"]},
      {name:"📦 Place",color:"#b45309",items:["Direct channels","Wholesalers/Retailers","E-commerce","Intensive distribution","Exclusive distribution"]},
      {name:"📣 Promotion",color:"#be123c",items:["Advertising","Public Relations","Sales promotions","Personal selling","Digital & Social media"]},
    ];
    stage.innerHTML=`<div class="wg-wrap"><h4 class="wg-title">Marketing Mix — 4Ps <span style="font-size:12px;color:var(--muted)">(click to expand)</span></h4><div class="wg-4ps-grid" id="psGrid"></div></div>`;
    const g=stage.querySelector("#psGrid");
    ps.forEach(p=>{
      const card=document.createElement("div");
      card.className="ps-card";
      card.innerHTML=`<div class="ps-head" style="background:${p.color}">${p.name}</div>
        <ul class="ps-list">${p.items.map(i=>`<li>${i}</li>`).join("")}</ul>`;
      card.onclick=()=>card.classList.toggle("ps-open");
      g.appendChild(card);
    });
  },

  /* ── 12. MASLOW PYRAMID ──────────────────────────────── */
  maslow_pyramid(stage) {
    const levels=[
      {label:"Self-actualization",sub:"Creativity, purpose",color:"#7c3aed",w:70},
      {label:"Esteem",sub:"Status, achievement",color:"#0f766e",w:100},
      {label:"Social / Love",sub:"Belonging, relationships",color:"#0369a1",w:150},
      {label:"Safety",sub:"Security, stability",color:"#b45309",w:210},
      {label:"Physiological",sub:"Food, water, shelter",color:"#be123c",w:280},
    ];
    stage.innerHTML=`<div class="wg-wrap"><h4 class="wg-title">Maslow's Hierarchy of Needs <span style="font-size:12px;color:var(--muted)">(hover for detail)</span></h4><div class="wg-maslow" id="maslow"></div></div>`;
    const m=stage.querySelector("#maslow");
    levels.forEach(l=>{
      const row=document.createElement("div");
      row.className="maslow-row";
      row.innerHTML=`<div class="maslow-bar" style="width:${l.w}px;background:${l.color}">
        <span class="maslow-label">${l.label}</span></div>
        <div class="maslow-sub">${l.sub}</div>`;
      m.appendChild(row);
    });
  },

  /* ── 13. NORMALIZATION STEPS ─────────────────────────── */
  normalization(stage) {
    const forms=[
      {name:"Unnormalized (UNF)",badge:"UNF",color:"#be123c",html:`<table class="nf-table"><tr><th>OrderID</th><th>Customer</th><th>Products</th></tr>
        <tr><td>1</td><td>Alice</td><td class="bad">Pen, Book</td></tr>
        <tr><td>2</td><td>Bob</td><td class="bad">Pen</td></tr></table>
        <div class="nf-issue">❌ "Products" is multi-valued — violates atomicity</div>`},
      {name:"1st Normal Form",badge:"1NF",color:"#b45309",html:`<table class="nf-table"><tr><th>OrderID</th><th>Customer</th><th>Product</th></tr>
        <tr><td>1</td><td>Alice</td><td>Pen</td></tr>
        <tr><td>1</td><td>Alice</td><td>Book</td></tr>
        <tr><td>2</td><td>Bob</td><td>Pen</td></tr></table>
        <div class="nf-issue ok">✓ All values atomic. PK = (OrderID, Product)</div>`},
      {name:"2nd Normal Form",badge:"2NF",color:"#0369a1",html:`<div style="display:flex;gap:8px;flex-wrap:wrap">
        <table class="nf-table"><tr><th>OrderID</th><th>CustID</th></tr><tr><td>1</td><td>C1</td></tr><tr><td>2</td><td>C2</td></tr></table>
        <table class="nf-table"><tr><th>CustID</th><th>Name</th></tr><tr><td>C1</td><td>Alice</td></tr><tr><td>C2</td><td>Bob</td></tr></table>
        </div><div class="nf-issue ok">✓ No partial dependencies on composite key</div>`},
      {name:"3rd Normal Form",badge:"3NF",color:"#0f766e",html:`<div style="display:flex;gap:8px;flex-wrap:wrap">
        <table class="nf-table"><tr><th>OrderID</th><th>CustID</th><th>DeptID</th></tr><tr><td>1</td><td>C1</td><td>D1</td></tr></table>
        <table class="nf-table"><tr><th>DeptID</th><th>DeptName</th></tr><tr><td>D1</td><td>Sales</td></tr></table>
        </div><div class="nf-issue ok">✓ No transitive dependencies</div>`},
    ];
    let step=0;
    stage.innerHTML=`<div class="wg-wrap"><h4 class="wg-title">Normalization Steps</h4>
      <div class="nf-header" id="nfHeader"></div>
      <div id="nfTable" style="margin:12px 0"></div>
      <div class="nf-nav">
        <button class="wg-btn-ghost" id="nfPrev">← Prev</button>
        <span id="nfStep" style="color:var(--muted)"></span>
        <button class="wg-btn" id="nfNext">Next →</button>
      </div></div>`;
    const render=()=>{
      const f=forms[step];
      stage.querySelector("#nfHeader").innerHTML=`<span class="nf-badge" style="background:${f.color}">${f.badge}</span> ${f.name}`;
      stage.querySelector("#nfTable").innerHTML=f.html;
      stage.querySelector("#nfStep").textContent=`${step+1} / ${forms.length}`;
      stage.querySelector("#nfPrev").disabled=step===0;
      stage.querySelector("#nfNext").disabled=step===forms.length-1;
    };
    stage.querySelector("#nfNext").onclick=()=>{if(step<forms.length-1){step++;render();}};
    stage.querySelector("#nfPrev").onclick=()=>{if(step>0){step--;render();}};
    render();
  },

  /* ── 14. ER DIAGRAM ──────────────────────────────────── */
  er_diagram(stage) {
    stage.innerHTML=`<div class="wg-wrap"><h4 class="wg-title">Entity-Relationship Diagram</h4>
      <svg width="400" height="230" id="erSvg" style="display:block;margin:0 auto;width:100%;max-width:400px"></svg>
      <div class="er-legend">
        <span><svg width="12" height="12"><rect width="12" height="12" rx="2" fill="#0f766e"/></svg> Entity</span>
        <span><svg width="12" height="12"><ellipse cx="6" cy="6" rx="6" ry="4" fill="none" stroke="#7c3aed" stroke-width="1.5"/></svg> Attribute</span>
        <span><svg width="12" height="12"><polygon points="6,0 12,6 6,12 0,6" fill="none" stroke="#b45309" stroke-width="1.5"/></svg> Relationship</span>
      </div></div>`;
    const s=stage.querySelector("#erSvg");
    const ln=(x1,y1,x2,y2,dash="")=>s.innerHTML+=`<line x1="${x1}" y1="${y1}" x2="${x2}" y2="${y2}" stroke="#d1d5db" stroke-width="1.5" stroke-dasharray="${dash}"/>`;
    const txt=(x,y,t,col="#1f2937",fw="bold",fs=13)=>s.innerHTML+=`<text x="${x}" y="${y}" text-anchor="middle" fill="${col}" font-weight="${fw}" font-size="${fs}">${t}</text>`;
    // Entities
    s.innerHTML+=`<rect x="20" y="90" width="90" height="40" rx="4" fill="rgba(15,118,110,.15)" stroke="#0f766e" stroke-width="2"/>
      <rect x="290" y="90" width="90" height="40" rx="4" fill="rgba(15,118,110,.15)" stroke="#0f766e" stroke-width="2"/>`;
    txt(65,115,"Student"); txt(335,115,"Course");
    // Relationship diamond
    s.innerHTML+=`<polygon points="200,90 230,110 200,130 170,110" fill="rgba(180,83,9,.12)" stroke="#b45309" stroke-width="2"/>`;
    txt(200,115,"enrolls","#b45309","bold",11);
    // Lines with cardinality
    ln(110,110,170,110); ln(230,110,290,110);
    txt(145,106,"N","#6b7280","normal",12); txt(255,106,"M","#6b7280","normal",12);
    // Student attributes
    s.innerHTML+=`<ellipse cx="45" cy="40" rx="35" ry="18" fill="none" stroke="#0f766e" stroke-width="1.5"/>
      <text x="45" y="40" text-anchor="middle" fill="#0f766e" font-size="11" font-weight="bold" text-decoration="underline">StudentID</text>`;
    ln(55,90,50,58);
    s.innerHTML+=`<ellipse cx="50" cy="185" rx="30" ry="16" fill="none" stroke="#6b7280" stroke-width="1.5"/>`;
    txt(50,190,"Name","#6b7280","normal",11); ln(55,130,52,169);
    // Course attributes
    s.innerHTML+=`<ellipse cx="355" cy="40" rx="35" ry="18" fill="none" stroke="#0f766e" stroke-width="1.5"/>
      <text x="355" y="40" text-anchor="middle" fill="#0f766e" font-size="11" font-weight="bold" text-decoration="underline">CourseID</text>`;
    ln(345,90,350,58);
    s.innerHTML+=`<ellipse cx="355" cy="190" rx="30" ry="16" fill="none" stroke="#6b7280" stroke-width="1.5"/>`;
    txt(355,195,"Credits","#6b7280","normal",11); ln(345,130,350,174);
    // Relationship attribute (Grade)
    s.innerHTML+=`<ellipse cx="200" cy="190" rx="28" ry="16" fill="none" stroke="#7c3aed" stroke-width="1.5" stroke-dasharray="4"/>`;
    txt(200,195,"Grade","#7c3aed","normal",11); ln(200,130,200,174);
  },

  /* ── LEGACY ──────────────────────────────────────────── */
  variables(stage){stage.innerHTML=`<div class="wg-wrap"><div class="widget-flow"><div class="widget-node">score</div><div>→</div><div class="widget-node">95</div><div class="widget-node">passed</div><div>→</div><div class="widget-node">true</div></div></div>`;},
  condition(stage){stage.innerHTML=`<div class="wg-wrap"><div class="widget-flow"><div class="widget-node">score=8</div><div>→</div><div class="widget-node">score≥5?</div><div>→</div><div class="widget-node">Pass</div></div></div>`;},
  loop(stage){stage.innerHTML=`<div class="wg-wrap"><div class="widget-flow"><div class="widget-node">range(3)</div><div>→</div><div class="widget-node">0</div><div class="widget-node">1</div><div class="widget-node">2</div></div></div>`;},
  function(stage){stage.innerHTML=`<div class="wg-wrap"><div class="widget-flow"><div class="widget-node">add(2,3)</div><div>→</div><div class="widget-node">return 5</div></div></div>`;},
  logic_gates(stage){stage.innerHTML=`<div class="wg-wrap"><div class="widget-flow"><div class="widget-node">A=1</div><div class="widget-node">B=0</div><div>AND→</div><div class="widget-node">0</div><div>OR→</div><div class="widget-node">1</div></div></div>`;},
  truth_table(stage){stage.innerHTML=`<div class="wg-wrap"><div class="widget-flow"><div class="widget-node">00→0</div><div class="widget-node">01→1</div><div class="widget-node">10→1</div><div class="widget-node">11→0</div><div>XOR</div></div></div>`;},
  logisim_flow(stage){stage.innerHTML=`<div class="wg-wrap"><div class="widget-flow"><div class="widget-node">Pins</div><div>→</div><div class="widget-node">Gates</div><div>→</div><div class="widget-node">LED</div></div></div>`;},
  adders(stage){stage.innerHTML=`<div class="wg-wrap"><div class="widget-flow"><div class="widget-node">X⊕Y=Sum</div><div class="widget-node">X·Y=Carry</div></div></div>`;},
  data_routing(stage){stage.innerHTML=`<div class="wg-wrap"><div class="widget-flow"><div class="widget-node">Select</div><div>→</div><div class="widget-node">In0/In1</div><div>→</div><div class="widget-node">Out</div></div></div>`;},
  default(stage){stage.innerHTML=`<div class="wg-wrap"><div class="widget-flow"><div class="widget-node">Concept</div><div>→</div><div class="widget-node">Application</div></div></div>`;},
};

/* Mount */
document.querySelectorAll("[data-widget]").forEach(panel=>{
  const stage=panel.querySelector(".widget-stage"), type=panel.dataset.widget;
  const renderer=widgetRenderers[type]||widgetRenderers.default;
  try{renderer(stage);}catch(e){console.warn("Widget error:",type,e);}
  stage.querySelectorAll(".widget-node").forEach((n,i)=>{n.style.animationDelay=`${i*60}ms`;});
});

/* Exercise handler */
document.querySelectorAll(".submit-answer").forEach(btn=>{
  btn.addEventListener("click",async function(){
    const ex=this.closest(".exercise"), id=ex.dataset.exerciseId, type=ex.dataset.type;
    let answer="";
    if(type==="multiple_choice"){const c=ex.querySelector("input[type=radio]:checked");if(!c){alert("Please select an answer.");return;}answer=c.value;}
    else{answer=ex.querySelector(".answer-input")?.value?.trim()||"";}
    const res=await fetch(`/exercises/${id}/attempts`,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({answer})});
    const data=await res.json();
    const p=ex.querySelector(".exercise-result");
    p.textContent=data.result==="passed"?"✓ Correct!":"✗ Incorrect. Try again.";
    p.className="exercise-result "+(data.result==="passed"?"result-pass":"result-fail");
    ex.querySelectorAll("label.choice").forEach(lbl=>{const inp=lbl.querySelector("input");lbl.classList.toggle("choice-correct",data.result==="passed"&&inp.checked);lbl.classList.toggle("choice-wrong",data.result!=="passed"&&inp.checked);});
  });
});
