/* ─── SOKONI WATCH — Dashboard JS ─── */

const API = {
  async get(path) {
    try {
      const r = await fetch(path);
      if (r.status === 401) { location.href = "/login"; return null; }
      if (!r.ok) { console.warn("API error", path, r.status); return null; }
      return r.json();
    } catch(e) { console.error("Fetch error", path, e); return null; }
  },
  async post(path, body={}) {
    try {
      const r = await fetch(path, {
        method:"POST", headers:{"Content-Type":"application/json"},
        body: JSON.stringify(body)
      });
      if (r.status === 401) { location.href = "/login"; return null; }
      return r.json();
    } catch(e) { console.error("Fetch error", path, e); return null; }
  },
  async del(path) {
    try {
      const r = await fetch(path, {method:"DELETE"});
      return r.json();
    } catch(e) { return null; }
  }
};

// ─── State ────────────────────────────────────────────────────────────────
let appState = {
  role: null, user: null,
  hawkers: [], alerts: [], categories: {},
  warehouse: [], dashData: {}, pulse: {}
};
let currentView = "";

// ─── Boot ─────────────────────────────────────────────────────────────────
document.addEventListener("DOMContentLoaded", async () => {
  startClock();
  try {
    const me = await API.get("/api/me");
    if (!me || me.error) { location.replace("/login"); return; }
    
    appState.user = me;
    appState.role = me.role;
    setupUserCard(me);
    buildNav(me.role);
    
    await loadAll();
    
    const startView = me.role === "admin" ? "admin-dashboard" : "hawker-dashboard";
    switchView(startView);
    
    // Hide loading overlay
    if (window.__hideLoader) window.__hideLoader();
    
    setInterval(() => loadAll(), 30000);
  } catch(err) {
    console.error("Boot failed:", err);
    if (window.__hideLoader) window.__hideLoader();
    location.replace("/login");
  }
});

function startClock() {
  const el = document.getElementById("clock");
  setInterval(() => {
    el.textContent = new Date().toLocaleTimeString("en-KE",{hour:"2-digit",minute:"2-digit",second:"2-digit"});
  }, 1000);
}

function setupUserCard(me) {
  document.getElementById("user-avatar").textContent = me.name.charAt(0);
  document.getElementById("user-name").textContent = me.name;
  document.getElementById("user-role-label").textContent = me.role === "admin" ? "System Admin" : "Hawker / Mwuza";
  document.getElementById("role-badge").textContent = me.role === "admin" ? "Admin Portal" : "Hawker Portal";
}

// ─── Navigation ────────────────────────────────────────────────────────────
const ADMIN_NAV = [
  { view:"admin-dashboard", icon:"📊", label:"Dashboard" },
  { view:"admin-hawkers",   icon:"👩‍🌾", label:"Wauza Bidhaa", sep:"MANAGEMENT" },
  { view:"admin-warehouse", icon:"🏭", label:"Hifadhi — Warehouse" },
  { view:"admin-distribute",icon:"🚚", label:"Gawanya Stock" },
  { view:"admin-alerts",    icon:"🚨", label:"Tahadhari", badge:true },
  { view:"admin-market",    icon:"📈", label:"Soko Pulse", sep:"ANALYTICS" },
];

const HAWKER_NAV = [
  { view:"hawker-dashboard",icon:"📊", label:"Dashboard" },
  { view:"hawker-stock",    icon:"📦", label:"Bidhaa Zangu", sep:"MY STORE" },
  { view:"hawker-market",   icon:"🔥", label:"Soko Pulse" },
  { view:"hawker-alerts",   icon:"🔔", label:"Tahadhari", badge:true },
];

function buildNav(role) {
  const navItems = role === "admin" ? ADMIN_NAV : HAWKER_NAV;
  const nav = document.getElementById("nav-menu");
  nav.innerHTML = "";
  navItems.forEach(item => {
    if (item.sep) {
      const sep = document.createElement("div");
      sep.className = "nav-sep";
      sep.textContent = item.sep;
      nav.appendChild(sep);
    }
    const a = document.createElement("div");
    a.className = "nav-item";
    a.dataset.view = item.view;
    a.innerHTML = `<span class="nav-icon">${item.icon}</span> ${item.label}${item.badge ? `<span class="nav-badge" id="nb-${item.view}" style="display:none">0</span>` : ""}`;
    a.addEventListener("click", () => switchView(item.view));
    nav.appendChild(a);
  });
  if (role === "admin") {
    document.getElementById("simulate-btn").style.display = "block";
  }
}

function switchView(view) {
  currentView = view;
  document.querySelectorAll(".view").forEach(v => v.classList.remove("active"));
  const el = document.getElementById(`view-${view}`);
  if (el) el.classList.add("active");
  document.querySelectorAll(".nav-item").forEach(n => {
    n.classList.toggle("active", n.dataset.view === view);
  });
  const titles = {
    "admin-dashboard":"Dashboard","admin-hawkers":"Wauza Bidhaa — Sellers",
    "admin-warehouse":"Hifadhi — Warehouse","admin-distribute":"Gawanya Bidhaa — Distribute",
    "admin-alerts":"Tahadhari — Alerts","admin-market":"Soko Pulse",
    "hawker-dashboard":"Dashboard","hawker-stock":"Bidhaa Zangu — My Stock",
    "hawker-market":"Soko Pulse — Market Trends","hawker-alerts":"Tahadhari Zangu"
  };
  document.getElementById("topbar-title").textContent = titles[view] || view;
  renderView(view);
}

async function loadAll() {
  try {
    const [dash, hawkers, alerts, cats, pulse] = await Promise.all([
      API.get("/api/dashboard"),
      API.get("/api/hawkers"),
      API.get("/api/alerts"),
      API.get("/api/categories"),
      API.get("/api/market_pulse")
    ]);
    appState.dashData  = dash || {};
    appState.hawkers   = Array.isArray(hawkers) ? hawkers : [];
    appState.alerts    = Array.isArray(alerts) ? alerts : [];
    appState.categories= cats || {};
    appState.pulse     = pulse || {};
    if (appState.role === "admin") {
      const wh = await API.get("/api/warehouse");
      appState.warehouse = Array.isArray(wh) ? wh : [];
    }
    updateAlertBadges();
    if (currentView) renderView(currentView);  // re-render current view with fresh data
  } catch(e) {
    console.error("loadAll failed", e);
  }
}

function updateAlertBadges() {
  const unread = appState.alerts.filter(a => !a.read).length;
  const badges = document.querySelectorAll(".nav-badge");
  badges.forEach(b => {
    b.textContent = unread;
    b.style.display = unread ? "inline-block" : "none";
  });
}

// ─── Render Dispatcher ────────────────────────────────────────────────────
function renderView(view) {
  switch(view) {
    case "admin-dashboard":  renderAdminDashboard(); break;
    case "admin-hawkers":    renderAdminHawkers(); break;
    case "admin-warehouse":  renderWarehouse(); break;
    case "admin-distribute": renderDistribute(); break;
    case "admin-alerts":     renderAlerts("admin-alerts-page"); break;
    case "admin-market":     renderMarket("market-grid"); break;
    case "hawker-dashboard": renderHawkerDashboard(); break;
    case "hawker-stock":     renderHawkerStock(); break;
    case "hawker-market":    renderMarket("hawker-market-grid"); break;
    case "hawker-alerts":    renderAlerts("hawker-alerts-page"); break;
  }
}

// ─── ADMIN Dashboard ──────────────────────────────────────────────────────
function renderAdminDashboard() {
  const d = appState.dashData;
  document.getElementById("admin-stats").innerHTML = `
    ${sc("blue","👩‍🌾",d.total_hawkers,"Wauza Bidhaa","Active hawkers")}
    ${sc("gold","📦",d.total_products,"Bidhaa Zote","Total products")}
    ${sc("amber","⚠️",d.low_stock_count,"Hifadhi Ndogo","Low stock items")}
    ${sc("red","🚨",d.critical_count,"Hatari","Critical items")}
    ${sc("green","💰",d.total_sales_today,"Mauzo Leo","Sales today")}
    ${sc("purple","🏭",d.warehouse_items,"Warehouse","Total items in stock")}
  `;
  // Alerts strip
  const unread = appState.alerts.filter(a=>!a.read).slice(0,8);
  const strip = document.getElementById("admin-alerts-strip");
  strip.innerHTML = unread.length
    ? unread.map(a=>`
        <div class="alert-chip ${a.level}" onclick="markAlertRead('${a.id}')">
          <div class="alert-chip-icon">${a.level==="critical"?"🚨":"⚠️"}</div>
          <div class="alert-chip-body">
            <div class="alert-chip-name">${a.hawker_name} — ${a.product}</div>
            <div class="alert-chip-detail">📍 ${a.location} · Stock: ${a.current_stock}/${a.min_threshold}</div>
          </div>
        </div>`).join("")
    : `<div class="empty"><div class="ei">✅</div><p>Hakuna tahadhari — No alerts!</p></div>`;

  // Hot products
  const hot = (appState.pulse.hot_products||[]).slice(0,6);
  const max = hot[0]?.[1]||1;
  document.getElementById("admin-hot-list").innerHTML = hot.map((h,i)=>`
    <div class="hot-item">
      <div class="hot-rank">${i+1}</div>
      <div style="flex:1">
        <div style="font-size:13px;font-weight:600;margin-bottom:4px">${h[0]}</div>
        <div class="hot-bar-wrap"><div class="hot-bar" style="width:${(h[1]/max*100).toFixed(0)}%"></div></div>
      </div>
      <div class="hot-val">${h[1]} sold</div>
    </div>`).join("");

  // Hawker cards
  document.getElementById("admin-hawker-cards").innerHTML = appState.hawkers.map(h=>hawkerCard(h)).join("");
  document.querySelectorAll(".h-card").forEach((c,i)=>{
    c.addEventListener("click",()=>openHawkerDetail(appState.hawkers[i].id));
  });
}

function sc(type, icon, val, label, sub) {
  return `<div class="stat-card sc-${type}">
    <div class="stat-icon">${icon}</div>
    <div class="stat-val">${val??'—'}</div>
    <div class="stat-label">${label}</div>
    <div class="stat-sub">${sub}</div>
  </div>`;
}

function hawkerCard(h) {
  const prods = h.products.slice(0,5);
  const hasAlert = appState.alerts.some(a=>a.hawker_id===h.id&&!a.read);
  return `<div class="h-card">
    <div class="h-card-top">
      <div class="h-avatar">${h.name.charAt(0)}</div>
      <div>
        <div class="h-name">${h.name}${hasAlert?" 🔴":""}</div>
        <div class="h-loc">📍 ${h.location}</div>
      </div>
      <div class="h-cat-badge">${h.category}</div>
    </div>
    <div class="mini-bars">${prods.map(p=>{
      const pct=Math.round(p.current_stock/p.max_stock*100);
      const cls=pct<=20?"crit":pct<=40?"low":"ok";
      return `<div class="mini-row">
        <div class="mini-name">${p.name}</div>
        <div class="mini-bar-wrap"><div class="mini-bar mb-${cls}" style="width:${pct}%"></div></div>
        <div class="mini-pct">${pct}%</div>
      </div>`;
    }).join("")}</div>
  </div>`;
}

// ─── Admin: Hawkers Table ─────────────────────────────────────────────────
function renderAdminHawkers() {
  const search = document.getElementById("hawker-search");
  const render = () => {
    const q = search.value.toLowerCase();
    const filtered = appState.hawkers.filter(h=>
      !q || h.name.toLowerCase().includes(q) || h.location.toLowerCase().includes(q)
    );
    document.getElementById("hawkers-tbody").innerHTML = filtered.map(h=>{
      const low = h.products.filter(p=>p.current_stock<=p.min_threshold).length;
      const crit = h.products.filter(p=>p.current_stock<=p.min_threshold*0.5).length;
      const sales = h.products.reduce((s,p)=>s+p.sales_today,0);
      const st = crit>0?"crit":low>0?"low":"ok";
      const stl = crit>0?"🚨 Critical":low>0?"⚠️ Low Stock":"✅ Sawa";
      return `<tr>
        <td><strong>${h.name}</strong><br><small style="color:var(--text3)">${h.phone}</small></td>
        <td>${h.location}</td>
        <td>${h.category}</td>
        <td>${h.products.length}</td>
        <td>${sales}</td>
        <td class="status-${st}">${stl}</td>
        <td>
          <button class="btn-success" style="margin-right:6px" onclick="openHawkerDetail('${h.id}')">👁 View</button>
          <button class="btn-danger" onclick="deleteHawker('${h.id}','${h.name}')">🗑 Delete</button>
        </td>
      </tr>`;
    }).join("");
  };
  search.oninput = render;
  render();
}

// ─── Admin: Warehouse ─────────────────────────────────────────────────────
function renderWarehouse() {
  const search = document.getElementById("warehouse-search");
  const render = () => {
    const q = search.value.toLowerCase();
    const filtered = appState.warehouse.filter(w=>
      !q || w.name.toLowerCase().includes(q) || w.category.toLowerCase().includes(q)
    );
    document.getElementById("warehouse-grid").innerHTML = filtered.length
      ? filtered.map(w=>`
          <div class="wh-card">
            <div class="wh-name">${w.name}</div>
            <div class="wh-cat">${w.category}</div>
            <div class="wh-qty" style="color:${w.quantity<w.reorder_level?"var(--red)":"var(--cyan)"}">${w.quantity}</div>
            <div class="wh-unit">${w.unit} in stock</div>
            <div class="wh-price">KSh ${w.price_ksh}/${w.unit}</div>
            <div class="wh-actions">
              <button class="btn-success" onclick="openAddStockModal('${w.name}')">+ Restock</button>
              <button class="btn-danger" onclick="deleteWarehouseItem('${encodeURIComponent(w.name)}','${w.name}')">🗑</button>
            </div>
          </div>`).join("")
      : `<div class="empty"><div class="ei">📦</div><p>Hakuna bidhaa — No items found</p></div>`;
  };
  search.oninput = render;
  render();
}

// ─── Admin: Distribute ────────────────────────────────────────────────────
function renderDistribute() {
  // Populate hawker select
  const hawkerSel = document.getElementById("dist-hawker");
  hawkerSel.innerHTML = `<option value="">-- Chagua Mwuza --</option>` +
    appState.hawkers.map(h=>`<option value="${h.id}">${h.name} — ${h.location}</option>`).join("");

  // Populate product select from warehouse
  const prodSel = document.getElementById("dist-product");
  prodSel.innerHTML = `<option value="">-- Chagua Bidhaa --</option>` +
    appState.warehouse.map(w=>`<option value="${w.name}">${w.name} (${w.quantity} ${w.unit} available)</option>`).join("");

  prodSel.onchange = () => {
    const name = prodSel.value;
    const item = appState.warehouse.find(w=>w.name===name);
    const info = document.getElementById("dist-info");
    info.innerHTML = item
      ? `📦 Available: <strong>${item.quantity} ${item.unit}</strong> · KSh ${item.price_ksh}/${item.unit}`
      : "Select a product to see stock info";
  };

  hawkerSel.onchange = () => {
    const hId = hawkerSel.value;
    const hawker = appState.hawkers.find(h=>h.id===hId);
    const summary = document.getElementById("dist-hawker-summary");
    if (!hawker) { summary.innerHTML=""; return; }
    summary.innerHTML = `
      <div style="margin-bottom:12px">
        <strong>${hawker.name}</strong> · ${hawker.location}<br>
        <small style="color:var(--text3)">${hawker.phone}</small>
      </div>
      ${hawker.products.map(p=>{
        const pct=Math.round(p.current_stock/p.max_stock*100);
        const col=pct<=20?"var(--red)":pct<=40?"var(--amber)":"var(--green)";
        return `<div class="mini-row" style="margin-bottom:8px">
          <div class="mini-name" style="width:100px;font-size:12px">${p.name}</div>
          <div class="mini-bar-wrap"><div class="mini-bar" style="width:${pct}%;background:${col}"></div></div>
          <div class="mini-pct">${p.current_stock}/${p.max_stock}</div>
        </div>`;
      }).join("")}`;
  };
}

async function distributeStock() {
  const hawker_id = document.getElementById("dist-hawker").value;
  const product_name = document.getElementById("dist-product").value;
  const quantity = parseInt(document.getElementById("dist-qty").value);
  if (!hawker_id||!product_name||!quantity||quantity<1) {
    showToast("Tafadhali jaza sehemu zote — Fill all fields","error"); return;
  }
  const r = await API.post("/api/distribute",{hawker_id,product_name,quantity});
  if (r?.success) {
    showToast(`✅ ${product_name} imetumwa! Warehouse remaining: ${r.warehouse_remaining}`,"success");
    await loadAll();
    renderDistribute();
  } else {
    showToast("❌ " + (r?.error||"Failed"),"error");
  }
}

// ─── Alerts ───────────────────────────────────────────────────────────────
function renderAlerts(containerId) {
  const container = document.getElementById(containerId);
  const sorted = [...appState.alerts].sort((a,b)=>{
    if(a.read!==b.read) return a.read?1:-1;
    if(a.level!==b.level) return a.level==="critical"?-1:1;
    return new Date(b.timestamp)-new Date(a.timestamp);
  });
  container.innerHTML = sorted.length
    ? sorted.map(a=>`
        <div class="alert-row-full ${a.level} ${a.read?"read":""}">
          <div class="arf-icon">${a.level==="critical"?"🚨":"⚠️"}</div>
          <div class="arf-info">
            <div class="arf-title">${a.hawker_name} — ${a.product}</div>
            <div class="arf-detail">📍 ${a.location} · Stock: ${a.current_stock} (min: ${a.min_threshold})${a.admin_has_stock?` · 🏭 Admin has ${a.admin_qty} in warehouse`:""}</div>
            <div class="arf-time">⏰ ${timeSince(new Date(a.timestamp))}</div>
          </div>
          ${!a.read?`<button class="btn-success" onclick="markAlertRead('${a.id}')">✓ Read</button>`:`<span style="font-size:11px;color:var(--text3)">Read ✓</span>`}
        </div>`).join("")
    : `<div class="empty"><div class="ei">🎉</div><p>Hakuna tahadhari — No alerts!</p></div>`;
}

async function markAlertRead(id) {
  await API.post(`/api/alerts/read/${id}`);
  await loadAll();
}

// ─── Market Pulse ─────────────────────────────────────────────────────────
function renderMarket(containerId) {
  const cats = appState.pulse.categories || {};
  const grid = document.getElementById(containerId);
  grid.innerHTML = Object.entries(cats).map(([cat,d])=>{
    const health = d.total_products>0 ? Math.round((d.total_products-d.low_stock)/d.total_products*100) : 100;
    const hc = health>70?"var(--green)":health>40?"var(--amber)":"var(--red)";
    return `<div class="mkt-card">
      <div class="mkt-title">${cat}</div>
      <div class="mkt-sub">Market Category Overview</div>
      <div class="mkt-row"><span class="mkt-row-label">👩‍🌾 Hawkers</span><span class="mkt-row-val">${d.hawkers}</span></div>
      <div class="mkt-row"><span class="mkt-row-label">📦 Products</span><span class="mkt-row-val">${d.total_products}</span></div>
      <div class="mkt-row"><span class="mkt-row-label">⚠️ Low Stock</span><span class="mkt-row-val" style="color:${d.low_stock>0?"var(--amber)":"var(--green)"}">${d.low_stock}</span></div>
      <div class="mkt-row"><span class="mkt-row-label">💰 Sales Today</span><span class="mkt-row-val">${d.total_sales}</span></div>
      <div class="mkt-row"><span class="mkt-row-label">💪 Health</span><span class="mkt-row-val" style="color:${hc}">${health}%</span></div>
      <div class="mkt-health-bar"><div class="mkt-health-fill" style="width:${health}%"></div></div>
    </div>`;
  }).join("");
}

// ─── HAWKER: Dashboard ────────────────────────────────────────────────────
function renderHawkerDashboard() {
  const d = appState.dashData;
  const hawker = d.hawker;
  if (!hawker) return;
  document.getElementById("hawker-stats").innerHTML = `
    ${sc("blue","📦",d.product_count,"Bidhaa Zangu","My products")}
    ${sc("green","💰",d.total_sales,"Mauzo Leo","My sales today")}
    ${sc("amber","⚠️",d.low_stock,"Hifadhi Ndogo","Low stock items")}
    ${sc("red","🔔",d.active_alerts,"Tahadhari","Active alerts")}
  `;

  // Hot products
  const hot = d.hot_products||[];
  const maxH = hot[0]?.[1]||1;
  document.getElementById("hawker-hot-list").innerHTML = hot.length
    ? hot.map((h,i)=>`
        <div class="hot-item">
          <div class="hot-rank">${i+1}</div>
          <div style="flex:1">
            <div style="font-size:13px;font-weight:600;margin-bottom:4px">${h[0]}</div>
            <div class="hot-bar-wrap"><div class="hot-bar" style="width:${(h[1]/maxH*100).toFixed(0)}%"></div></div>
          </div>
          <div class="hot-val">${h[1]} sold</div>
        </div>`).join("")
    : `<div class="empty"><div class="ei">📊</div><p>No sales data yet</p></div>`;

  // Low stock
  const low = hawker.products.filter(p=>p.current_stock<=p.min_threshold);
  document.getElementById("hawker-low-list").innerHTML = low.length
    ? low.map(p=>{
        const pct=Math.round(p.current_stock/p.max_stock*100);
        const col=pct<=10?"var(--red)":"var(--amber)";
        return `<div class="product-item">
          <div style="flex:1">
            <div class="prod-name">${p.name}</div>
            <div class="prod-cat">${p.category}</div>
          </div>
          <div class="prod-bar-wrap"><div class="prod-bar" style="width:${pct}%;background:${col}"></div></div>
          <div>
            <div class="prod-qty" style="color:${col}">${p.current_stock}</div>
            <div class="prod-unit">/${p.max_stock} ${p.unit}</div>
          </div>
        </div>`;
      }).join("")
    : `<div class="empty"><div class="ei">✅</div><p>Sawa! All stock levels okay</p></div>`;
}

// ─── HAWKER: My Stock ──────────────────────────────────────────────────────
function renderHawkerStock() {
  const hawker = appState.dashData.hawker;
  if (!hawker) return;
  const container = document.getElementById("hawker-products-list");
  container.innerHTML = hawker.products.length
    ? hawker.products.map(p=>{
        const pct=Math.round(p.current_stock/p.max_stock*100);
        const col=pct<=20?"var(--red)":pct<=40?"var(--amber)":"var(--green)";
        return `<div class="product-item" id="pi-${p.id}">
          <div style="min-width:130px">
            <div class="prod-name">${p.name}</div>
            <div class="prod-cat">${p.category} · KSh ${p.price_ksh}/${p.unit}</div>
          </div>
          <div class="prod-bar-wrap">
            <div class="prod-bar" style="width:${pct}%;background:${col}"></div>
          </div>
          <div style="text-align:right;min-width:80px">
            <div class="prod-qty" style="color:${col}">${p.current_stock}</div>
            <div class="prod-unit">/${p.max_stock} ${p.unit}</div>
            <div style="font-size:10px;color:var(--text3)">${pct}% full</div>
          </div>
          <div class="prod-actions">
            <button class="btn-sold" onclick="recordSale('${p.id}','${p.name}')">📉 Uza</button>
            <button class="btn-success" onclick="updateStockModal('${p.id}','${p.name}',${p.current_stock})">✏️ Update</button>
          </div>
        </div>`;
      }).join("")
    : `<div class="empty"><div class="ei">📦</div><p>Huna bidhaa — No products yet.<br>Wait for admin to distribute stock.</p></div>`;
}

async function recordSale(productId, productName) {
  const qty = parseInt(prompt(`Uliuza ngapi ${productName}? (How many ${productName} sold?)`))||0;
  if (!qty||qty<1) return;
  const r = await API.post("/api/hawker/update_stock",{product_id:productId,action:"sold",quantity:qty});
  if (r?.success) {
    showToast(`✅ Recorded ${qty} ${productName} sold!`,"success");
    await loadAll();
    renderHawkerStock();
  }
}

function updateStockModal(pid, name, current) {
  openModal(`
    <div class="modal-title">✏️ Update Stock — ${name}</div>
    <div class="modal-form-group">
      <div class="form-label">Current Stock Level</div>
      <input type="number" class="modal-input" id="new-stock-val" value="${current}" min="0"/>
    </div>
    <button class="btn-primary" onclick="submitStockUpdate('${pid}','${name}')">💾 Save Update</button>
  `);
}

async function submitStockUpdate(pid, name) {
  const qty = parseInt(document.getElementById("new-stock-val").value);
  const r = await API.post("/api/hawker/update_stock",{product_id:pid,action:"set",quantity:qty});
  if (r?.success) {
    closeModalDirect();
    showToast(`✅ ${name} stock updated to ${qty}`,"success");
    await loadAll();
    renderHawkerStock();
  }
}

// ─── Admin: Add Hawker Modal ───────────────────────────────────────────────
function openAddHawkerModal() {
  const cats = Object.keys(appState.categories);
  openModal(`
    <div class="modal-title">👩‍🌾 Ongeza Mwuza — Add Hawker</div>
    <div class="modal-row">
      <div class="modal-form-group">
        <div class="form-label">Jina — Full Name</div>
        <input type="text" class="modal-input" id="ah-name" placeholder="e.g. Mama Wanjiku"/>
      </div>
      <div class="modal-form-group">
        <div class="form-label">Username</div>
        <input type="text" class="modal-input" id="ah-username" placeholder="e.g. mama_wanjiku"/>
      </div>
    </div>
    <div class="modal-row">
      <div class="modal-form-group">
        <div class="form-label">Password</div>
        <input type="text" class="modal-input" id="ah-pass" placeholder="e.g. wanjiku2024"/>
      </div>
      <div class="modal-form-group">
        <div class="form-label">Phone</div>
        <input type="text" class="modal-input" id="ah-phone" placeholder="+254..."/>
      </div>
    </div>
    <div class="modal-row">
      <div class="modal-form-group">
        <div class="form-label">Location</div>
        <input type="text" class="modal-input" id="ah-loc" placeholder="e.g. Gikomba Market"/>
      </div>
      <div class="modal-form-group">
        <div class="form-label">Category</div>
        <select class="modal-input" id="ah-cat">
          ${cats.map(c=>`<option value="${c}">${c}</option>`).join("")}
        </select>
      </div>
    </div>
    <div class="modal-form-group">
      <div class="form-label">M-PESA Till Number</div>
      <input type="text" class="modal-input" id="ah-mpesa" placeholder="e.g. 123456"/>
    </div>
    <button class="btn-primary mt" onclick="submitAddHawker()">✅ Ongeza Mwuza</button>
  `);
}

async function submitAddHawker() {
  const body = {
    name: document.getElementById("ah-name").value,
    username: document.getElementById("ah-username").value,
    password: document.getElementById("ah-pass").value,
    phone: document.getElementById("ah-phone").value,
    location: document.getElementById("ah-loc").value,
    category: document.getElementById("ah-cat").value,
    mpesa_till: document.getElementById("ah-mpesa").value
  };
  if (!body.name||!body.username||!body.password) {
    showToast("Jaza sehemu zote muhimu","error"); return;
  }
  const r = await API.post("/api/hawkers", body);
  if (r?.success) {
    closeModalDirect();
    showToast(`✅ ${body.name} ameongezwa!`,"success");
    await loadAll();
    renderAdminHawkers();
  } else {
    showToast("❌ "+(r?.error||"Failed"),"error");
  }
}

async function deleteHawker(id, name) {
  if (!confirm(`Una uhakika unataka kumfuta ${name}?\nAre you sure you want to delete ${name}?`)) return;
  const r = await API.del(`/api/hawkers/${id}`);
  if (r?.success) {
    showToast(`🗑 ${name} amefutwa`,"gold");
    await loadAll();
    renderAdminHawkers();
  }
}

// ─── Warehouse Modals ─────────────────────────────────────────────────────
function openAddStockModal(prefill="") {
  const cats = Object.keys(appState.categories);
  openModal(`
    <div class="modal-title">📦 ${prefill?"Restock":"Ongeza Bidhaa"} — ${prefill||"New Item"}</div>
    <div class="modal-form-group">
      <div class="form-label">Jina la Bidhaa — Product Name</div>
      <input type="text" class="modal-input" id="ws-name" value="${prefill}" placeholder="e.g. Sukuma Wiki"/>
    </div>
    <div class="modal-row">
      <div class="modal-form-group">
        <div class="form-label">Category</div>
        <select class="modal-input" id="ws-cat">
          ${cats.map(c=>`<option value="${c}">${c}</option>`).join("")}
        </select>
      </div>
      <div class="modal-form-group">
        <div class="form-label">Quantity</div>
        <input type="number" class="modal-input" id="ws-qty" placeholder="e.g. 500" min="1"/>
      </div>
    </div>
    <div class="modal-row">
      <div class="modal-form-group">
        <div class="form-label">Unit</div>
        <select class="modal-input" id="ws-unit">
          <option>kg</option><option>bunch</option><option>piece</option><option>litre</option><option>packet</option>
        </select>
      </div>
      <div class="modal-form-group">
        <div class="form-label">Price (KSh)</div>
        <input type="number" class="modal-input" id="ws-price" placeholder="e.g. 80" min="1"/>
      </div>
    </div>
    <button class="btn-primary mt" onclick="submitAddStock()">💾 Hifadhi</button>
  `);
}

async function submitAddStock() {
  const body = {
    name: document.getElementById("ws-name").value,
    category: document.getElementById("ws-cat").value,
    quantity: parseInt(document.getElementById("ws-qty").value)||0,
    unit: document.getElementById("ws-unit").value,
    price_ksh: parseFloat(document.getElementById("ws-price").value)||0,
    reorder_level: 100
  };
  if (!body.name||!body.quantity) { showToast("Jaza sehemu muhimu","error"); return; }
  const r = await API.post("/api/warehouse", body);
  if (r?.success) {
    closeModalDirect();
    showToast(`✅ ${body.name} imeongezwa!`,"success");
    await loadAll();
    renderWarehouse();
  }
}

async function deleteWarehouseItem(encoded, name) {
  if (!confirm(`Futa ${name} kwenye hifadhi?\nDelete ${name} from warehouse?`)) return;
  const r = await API.del(`/api/warehouse/${encoded}`);
  if (r?.success) {
    showToast(`🗑 ${name} imefutwa`,"gold");
    await loadAll();
    renderWarehouse();
  }
}

// ─── Hawker Detail Modal ──────────────────────────────────────────────────
async function openHawkerDetail(id) {
  const hawker = await API.get(`/api/hawkers/${id}`);
  if (!hawker) return;
  const low = hawker.products.filter(p=>p.current_stock<=p.min_threshold).length;
  openModal(`
    <div style="display:flex;align-items:center;gap:14px;margin-bottom:20px">
      <div class="h-avatar" style="width:52px;height:52px;border-radius:50%;background:linear-gradient(135deg,var(--royal-light),var(--gold-dim));display:flex;align-items:center;justify-content:center;font-size:22px;font-weight:700;color:#fff">${hawker.name.charAt(0)}</div>
      <div>
        <div style="font-family:var(--font-d);font-size:22px;font-weight:700">${hawker.name}</div>
        <div style="font-size:13px;color:var(--text3)">📍 ${hawker.location} · ${hawker.category}</div>
        <div style="font-size:13px;color:var(--green)">📱 ${hawker.phone}</div>
        <div style="font-size:12px;color:var(--text3)">M-PESA: ${hawker.mpesa_till||"—"}</div>
      </div>
    </div>
    <div style="display:flex;gap:20px;padding:14px 0;border-top:1px solid var(--border);border-bottom:1px solid var(--border);margin-bottom:18px">
      <div style="text-align:center"><div style="font-family:var(--font-d);font-size:24px;font-weight:700">${hawker.products.length}</div><div style="font-size:11px;color:var(--text3)">Products</div></div>
      <div style="text-align:center"><div style="font-family:var(--font-d);font-size:24px;font-weight:700;color:var(--amber)">${low}</div><div style="font-size:11px;color:var(--text3)">Low Stock</div></div>
      <div style="text-align:center"><div style="font-family:var(--font-d);font-size:24px;font-weight:700;color:var(--gold)">${hawker.products.reduce((s,p)=>s+p.sales_today,0)}</div><div style="font-size:11px;color:var(--text3)">Sales Today</div></div>
    </div>
    <div style="font-family:var(--font-d);font-size:16px;font-weight:700;margin-bottom:12px">📦 Stock Levels</div>
    ${hawker.products.map(p=>{
      const pct=Math.round(p.current_stock/p.max_stock*100);
      const col=pct<=20?"var(--red)":pct<=40?"var(--amber)":"var(--green)";
      return `<div style="background:var(--bg3);border-radius:10px;padding:12px 14px;margin-bottom:8px;display:flex;align-items:center;gap:12px">
        <div style="flex:1">
          <div style="font-size:14px;font-weight:600">${p.name}</div>
          <div style="font-size:11px;color:var(--text3)">KSh ${p.price_ksh}/${p.unit}</div>
          <div style="height:5px;background:var(--bg);border-radius:3px;overflow:hidden;margin-top:6px">
            <div style="height:100%;width:${pct}%;background:${col};border-radius:3px;transition:width 0.5s"></div>
          </div>
        </div>
        <div style="text-align:right">
          <div style="font-family:var(--font-d);font-size:20px;font-weight:700;color:${col}">${p.current_stock}</div>
          <div style="font-size:10px;color:var(--text3)">/${p.max_stock} ${p.unit}</div>
        </div>
      </div>`;
    }).join("")}
  `);
}

// ─── Simulate sales (admin only) ──────────────────────────────────────────
async function simulateSales() {
  const btn = document.getElementById("simulate-btn");
  btn.textContent = "⏳...";
  btn.disabled = true;
  await API.post("/api/simulate_sales");
  await loadAll();
  btn.textContent = "⚡ Simulate Sales";
  btn.disabled = false;
  showToast("Sales simulated across all hawkers! 📉","gold");
}

// ─── Modal Helpers ─────────────────────────────────────────────────────────
function openModal(html) {
  document.getElementById("modal-body").innerHTML = html;
  document.getElementById("modal-overlay").classList.add("open");
}

function closeModal(e) {
  if (e.target === document.getElementById("modal-overlay")) closeModalDirect();
}

function closeModalDirect() {
  document.getElementById("modal-overlay").classList.remove("open");
}

// ─── Toast ─────────────────────────────────────────────────────────────────
let toastT;
function showToast(msg, type="info") {
  const t = document.getElementById("toast");
  t.textContent = msg;
  t.className = `toast ${type} show`;
  clearTimeout(toastT);
  toastT = setTimeout(()=>{ t.className="toast"; }, 3500);
}

// ─── Time Helper ──────────────────────────────────────────────────────────
function timeSince(date) {
  const s = Math.floor((new Date()-date)/1000);
  if(s<60) return `${s}s ago`;
  if(s<3600) return `${Math.floor(s/60)}m ago`;
  if(s<86400) return `${Math.floor(s/3600)}h ago`;
  return `${Math.floor(s/86400)}d ago`;
}
