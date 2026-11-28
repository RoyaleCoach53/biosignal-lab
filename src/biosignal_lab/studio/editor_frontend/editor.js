/* Local data-only editor. Python owns scientific validation and execution. */
(() => {
  "use strict";
  const $ = id => document.getElementById(id);
  const clone = value => JSON.parse(JSON.stringify(value));
  const same = (left, right) => JSON.stringify(left) === JSON.stringify(right);
  const ns = "http://www.w3.org/2000/svg";
  const width = 238, portStart = 66, portStep = 34;
  const state = {workflow: null, catalog: {}, positions: {}, groups: [], digest: "", disabled: false,
    selected: null, selection: new Set(), clipboard: null, pasteCount: 0,
    pending: null, undo: [], redo: [], outbound: null, view: {x: 30, y: 30, zoom: 1}};
  let counter = 0, gesture = null, parameterNode = null, preserveFocusSelection = false;
  function message(type, extra = {}) {
    window.parent.postMessage({isStreamlitMessage: true, type, ...extra}, "*");
  }
  function announce(text) { $("status").textContent = text; }
  function frameHeight() { message("streamlit:setFrameHeight", {height: Math.ceil(document.documentElement.scrollHeight)}); }
  function snapshot() { return clone({workflow: state.workflow, positions: state.positions, groups: state.groups}); }
  function remember() {
    state.undo.push(snapshot());
    if (state.undo.length > 50) state.undo.shift();
    state.redo = [];
  }
  function emit(text) {
    // Only one mutation may use a server revision. Buffer fast local edits until
    // the parent acknowledges it, then send the latest graph with the new digest.
    if (!state.outbound) sendGraph();
    if (text) announce(text);
    renderGraph();
  }
  function sendGraph() {
    const eventId = `${Date.now()}-${++counter}`;
    state.outbound = {id: eventId, ...snapshot()};
    message("streamlit:setComponentValue", {dataType: "json", value: {
      event_id: eventId, graph_digest: state.digest,
      workflow: clone(state.workflow), positions: clone(state.positions), groups: clone(state.groups),
    }});
  }
  function validateWorkflow(raw) {
    if (raw && typeof raw === "object" && !Array.isArray(raw)) {
      if (Object.keys(raw).some(key => !["schema_version", "name", "nodes"].includes(key))) throw new Error("Unknown workflow fields.");
      raw = clone(raw);
      if (!Object.hasOwn(raw, "schema_version")) raw.schema_version = 1;
      if (!Object.hasOwn(raw, "name")) raw.name = "Untitled experiment";
      if (Array.isArray(raw.nodes)) raw.nodes.forEach(node => {
        if (!node || typeof node !== "object" || Array.isArray(node)) return;
        if (Object.keys(node).some(key => !["id", "kind", "parameters", "inputs"].includes(key))) throw new Error("Unknown node fields.");
        if (!Object.hasOwn(node, "parameters")) node.parameters = {};
        if (!Object.hasOwn(node, "inputs")) node.inputs = {};
        if (node.inputs && typeof node.inputs === "object") Object.values(node.inputs).forEach(source => {
          if (!source || typeof source !== "object" || Array.isArray(source)) return;
          if (Object.keys(source).some(key => !["node", "port"].includes(key))) throw new Error("Unknown connection fields.");
          if (!Object.hasOwn(source, "port")) source.port = "out";
        });
      });
    }
    if (!raw || typeof raw !== "object" || Array.isArray(raw) || raw.schema_version !== 1 ||
        typeof raw.name !== "string" || raw.name.length > 200 ||
        !Array.isArray(raw.nodes) || raw.nodes.length < 1 || raw.nodes.length > 128) {
      throw new Error("Use a schema_version 1 workflow with a name and 1–128 nodes.");
    }
    const ids = new Set();
    for (const node of raw.nodes) {
      if (!node || typeof node !== "object" || !/^[A-Za-z][A-Za-z0-9_-]{0,63}$/.test(node.id) || ids.has(node.id)) {
        throw new Error("Node IDs must be unique, start with a letter, and contain at most 64 letters, digits, underscores or hyphens.");
      }
      ids.add(node.id);
      if (!Object.hasOwn(state.catalog, node.kind)) throw new Error(`Unavailable node type: ${String(node.kind).slice(0, 100)}`);
      if (!node.parameters || typeof node.parameters !== "object" || Array.isArray(node.parameters) ||
          !node.inputs || typeof node.inputs !== "object" || Array.isArray(node.inputs)) throw new Error("Node parameters and inputs must be JSON objects.");
      for (const [port, source] of Object.entries(node.inputs)) {
        if (!Object.hasOwn(state.catalog[node.kind].inputs, port) || !source || typeof source.node !== "string" || typeof source.port !== "string") {
          throw new Error(`Invalid input connection on ${node.id}.`);
        }
      }
    }
    for (const node of raw.nodes) for (const source of Object.values(node.inputs)) {
      const parent = raw.nodes.find(candidate => candidate.id === source.node);
      if (!parent || !Object.hasOwn(state.catalog[parent.kind].outputs, source.port)) throw new Error(`Connection on ${node.id} refers to an unavailable source port.`);
    }
    return clone(raw);
  }
  function strictJSON(text) {
    const parsed = JSON.parse(text, (_key, value) => {
      if (typeof value === "number" && !Number.isFinite(value)) throw new Error("Numbers must be finite.");
      return value;
    });
    // JSON.parse validates grammar first. Scan valid tokens to catch duplicate
    // object keys before JavaScript's parser can silently discard their values.
    const tokens = text.match(/"(?:\\.|[^"\\])*"|[{}\[\]:,]|true|false|null|-?(?:0|[1-9]\d*)(?:\.\d+)?(?:[eE][+-]?\d+)?/g) || [];
    const stack = [];
    for (const token of tokens) {
      const current = stack.at(-1);
      if (token === "{") stack.push({object: true, key: true, keys: new Set()});
      else if (token === "[") stack.push({object: false});
      else if (token === "}" || token === "]") stack.pop();
      else if (token === "," && current?.object) current.key = true;
      else if (token.startsWith('"') && current?.object && current.key) {
        const name = JSON.parse(token);
        if (current.keys.has(name)) throw new Error(`Duplicate JSON field: ${name.slice(0, 80)}`);
        current.keys.add(name); current.key = false;
      }
    }
    return parsed;
  }
  function ensurePositions(proposed = {}) {
    const positions = Object.create(null);
    state.workflow.nodes.forEach((node, index) => {
      const p = Object.hasOwn(proposed, node.id) ? proposed[node.id] : null;
      positions[node.id] = p && Number.isFinite(p.x) && Number.isFinite(p.y)
        ? {x: Math.max(-10000, Math.min(10000, p.x)), y: Math.max(-10000, Math.min(10000, p.y))}
        : {x: (index % 3) * 300, y: Math.floor(index / 3) * 220};
    });
    state.positions = positions;
  }
  function svg(tag, attributes = {}) {
    const el = document.createElementNS(ns, tag);
    Object.entries(attributes).forEach(([key, value]) => el.setAttribute(key, String(value)));
    return el;
  }
  function element(tag, className, text) {
    const el = document.createElement(tag);
    if (className) el.className = className;
    if (text !== undefined) el.textContent = text;
    return el;
  }
  function control(text, action, options = {}) {
    const button = element("button", options.className, text);
    button.type = "button";
    button.disabled = state.disabled;
    if (options.label) button.setAttribute("aria-label", options.label);
    button.addEventListener("click", action);
    return button;
  }
  function ports(node, side) { return Object.entries(state.catalog[node.kind]?.[side] || {}); }
  function anchor(node, port, side) {
    const index = ports(node, side).findIndex(([name]) => name === port);
    const position = state.positions[node.id];
    return {x: position.x + (side === "outputs" ? width : 0), y: position.y + portStart + index * portStep + portStep / 2};
  }
  function nodeHeight(node) { return portStart + Math.max(1, ports(node, "inputs").length, ports(node, "outputs").length) * portStep + 43; }
  function cleanGroups(groups) {
    if (!Array.isArray(groups)) return [];
    const available = new Set(state.workflow.nodes.map(node => node.id)), ids = new Set(), members = new Set(), result = [];
    for (const group of groups.slice(0, 128)) {
      if (!group || typeof group !== "object" || !/^[A-Za-z][A-Za-z0-9_-]{0,63}$/.test(group.id) || ids.has(group.id) ||
          typeof group.name !== "string" || !group.name.trim() || group.name.length > 100 || !Array.isArray(group.nodes)) continue;
      const nodes = group.nodes.filter(id => available.has(id) && !members.has(id));
      const unique = [...new Set(nodes)].slice(0, 128);
      if (!unique.length) continue;
      ids.add(group.id); unique.forEach(id => members.add(id)); result.push({id: group.id, name: group.name, nodes: unique});
    }
    return result;
  }
  function groupBounds(group) {
    const nodes = group.nodes.map(id => state.workflow.nodes.find(node => node.id === id)).filter(Boolean);
    if (!nodes.length) return null;
    const x = Math.min(...nodes.map(node => state.positions[node.id].x)) - 18;
    const y = Math.min(...nodes.map(node => state.positions[node.id].y)) - 45;
    return {x, y, width: Math.max(...nodes.map(node => state.positions[node.id].x + width)) - x + 18,
      height: Math.max(...nodes.map(node => state.positions[node.id].y + nodeHeight(node))) - y + 18};
  }
  function selectionUI() {
    document.querySelectorAll(".node").forEach(item => {
      const selected = state.selection.has(item.dataset.id);
      item.classList.toggle("selected", selected); item.querySelector(".node-title").setAttribute("aria-pressed", String(selected));
    });
    $("selection-count").textContent = `${state.selection.size} node${state.selection.size === 1 ? "" : "s"} selected`;
    $("copy").disabled = state.disabled || !state.selection.size;
    $("paste").disabled = state.disabled || !state.clipboard;
    $("group").disabled = state.disabled || state.selection.size < 2;
    $("ungroup").disabled = state.disabled || !state.groups.some(group => group.nodes.some(id => state.selection.has(id)));
    $("select-all").disabled = state.disabled || !state.workflow;
  }
  function choose(id, toggle = false) {
    if (toggle) {if (state.selection.has(id)) state.selection.delete(id); else state.selection.add(id);}
    else state.selection = new Set([id]);
    state.selected = state.selection.has(id) ? id : state.selection.values().next().value || null;
    selectionUI();
  }
  function selectAll() {
    if (!state.workflow || state.disabled) return;
    state.selection = new Set(state.workflow.nodes.map(node => node.id));
    state.selected = state.workflow.nodes[0].id; selectionUI(); announce(`Selected ${state.selection.size} nodes.`);
  }
  function beginDrag(event, active, ids) {
    if (state.disabled || event.button !== 0) return;
    event.stopPropagation();
    gesture = {kind: "nodes", id: active, ids: [...ids], x: event.clientX, y: event.clientY,
      originals: Object.fromEntries([...ids].map(id => [id, clone(state.positions[id])])), before: snapshot(), moved: false};
    $("viewport").setPointerCapture(event.pointerId);
  }
  function copySelected() {
    if (state.disabled || !state.selection.size) return;
    const ids = state.selection;
    state.clipboard = {nodes: state.workflow.nodes.filter(node => ids.has(node.id)).map(node => ({...clone(node),
      inputs: Object.fromEntries(Object.entries(node.inputs).filter(([, source]) => ids.has(source.node)))})),
      positions: Object.fromEntries([...ids].map(id => [id, clone(state.positions[id])])),
      groups: state.groups.map(group => ({...clone(group), nodes: group.nodes.filter(id => ids.has(id))})).filter(group => group.nodes.length > 1)};
    state.pasteCount = 0; selectionUI(); announce(`Copied ${ids.size} nodes inside this editor. External input connections are excluded.`);
  }
  function freshId(stem, used) {
    const base = stem.slice(0, 52); let id = `${base}_copy`, index = 1;
    while (used.has(id)) id = `${base}_copy${++index}`;
    used.add(id); return id;
  }
  function pasteSelected() {
    if (state.disabled || !state.clipboard) return;
    if (state.clipboard.nodes.some(node => !Object.hasOwn(state.catalog, node.kind))) {announce("The clipboard contains algorithms unavailable in this registry."); return;}
    if (state.workflow.nodes.length + state.clipboard.nodes.length > 128) {announce("Pasting would exceed the 128-node limit."); return;}
    const used = new Set(state.workflow.nodes.map(node => node.id)), mapping = new Map();
    state.clipboard.nodes.forEach(node => mapping.set(node.id, freshId(node.id, used)));
    const copied = state.clipboard.nodes.map(node => ({...clone(node), id: mapping.get(node.id),
      inputs: Object.fromEntries(Object.entries(node.inputs).map(([port, source]) => [port, {...source, node: mapping.get(source.node)}]))}));
    remember(); state.pasteCount++;
    const offset = 45 * state.pasteCount;
    state.clipboard.nodes.forEach(node => {const p = state.clipboard.positions[node.id]; state.positions[mapping.get(node.id)] = {x: p.x + offset, y: p.y + offset};});
    state.workflow.nodes.push(...copied);
    const groupIds = new Set(state.groups.map(group => group.id));
    state.clipboard.groups.forEach(group => state.groups.push({id: freshId(group.id, groupIds), name: `${group.name.slice(0, 93)} (copy)`, nodes: group.nodes.map(id => mapping.get(id))}));
    state.selection = new Set(copied.map(node => node.id)); state.selected = copied[0].id;
    emit(`Pasted ${copied.length} nodes with fresh IDs and internal connections. Configure any missing external inputs before execution.`);
  }
  function groupSelected() {
    if (state.disabled || state.selection.size < 2) return;
    if (state.groups.length >= 128) {announce("The editor supports at most 128 visual groups."); return;}
    remember();
    const used = new Set(state.groups.map(group => group.id)); let id = "group", index = 1;
    while (used.has(id)) id = `group_${++index}`;
    const name = $("group-name").value.trim() || `Group ${index}`;
    state.groups = state.groups.map(group => ({...group, nodes: group.nodes.filter(node => !state.selection.has(node))})).filter(group => group.nodes.length);
    state.groups.push({id, name, nodes: [...state.selection]});
    emit(`Created visual group ${name}. Scientific connections are unchanged.`);
    fit();
  }
  function ungroupSelected() {
    if (state.disabled || !state.groups.some(group => group.nodes.some(id => state.selection.has(id)))) return;
    remember(); state.groups = state.groups.map(group => ({...group, nodes: group.nodes.filter(id => !state.selection.has(id))})).filter(group => group.nodes.length);
    emit("Removed selected nodes from visual groups. Scientific connections are unchanged.");
  }
  function renderGroups() {
    $("groups").replaceChildren();
    state.groups.forEach(group => {
      const bounds = groupBounds(group); if (!bounds) return;
      const box = element("div", "visual-group"); box.dataset.group = group.id;
      Object.entries(bounds).forEach(([key, value]) => {box.style[key === "x" ? "left" : key === "y" ? "top" : key] = `${value}px`;});
      const title = control(group.name, () => {state.selection = new Set(group.nodes); state.selected = group.nodes[0]; selectionUI(); announce(`Selected visual group ${group.name}.`);}, {className: "group-title", label: `Select group ${group.name}`});
      title.addEventListener("pointerdown", event => {state.selection = new Set(group.nodes); state.selected = group.nodes[0]; selectionUI(); beginDrag(event, group.nodes[0], group.nodes);});
      box.append(title); $("groups").append(box);
    });
  }
  function graphEdges() {
    return state.workflow.nodes.flatMap(node => Object.entries(node.inputs).map(([input, source]) => ({node, input, source})));
  }
  function removeEdge(nodeId, input) {
    if (state.disabled) return;
    const node = state.workflow.nodes.find(item => item.id === nodeId);
    if (!node || !Object.hasOwn(node.inputs, input)) return;
    remember(); delete node.inputs[input]; emit(`Removed connection into ${nodeId}.${input}.`);
  }
  function compatible(source, destination) {
    return ["kind", "unit", "sfreq", "modality"].every(key => source[key] == null || destination[key] == null || source[key] === destination[key]);
  }
  function createsCycle(sourceId, targetId) {
    const edges = graphEdges();
    const seen = new Set(), stack = [targetId];
    while (stack.length) {
      const id = stack.pop();
      if (id === sourceId) return true;
      if (seen.has(id)) continue;
      seen.add(id);
      edges.filter(edge => edge.source.node === id).forEach(edge => stack.push(edge.node.id));
    }
    return false;
  }
  function connect(target, input) {
    if (!state.pending) { announce("Choose an output port first, then this input."); return; }
    const source = state.workflow.nodes.find(node => node.id === state.pending.node);
    const sourcePort = state.catalog[source.kind].outputs[state.pending.port];
    const targetPort = state.catalog[target.kind].inputs[input];
    if (!compatible(sourcePort, targetPort)) { announce("Incompatible port types, units, sampling frequency or modality. Connection was not changed."); return; }
    if (createsCycle(source.id, target.id)) { announce("This connection would create a cycle. Connection was not changed."); return; }
    const value = {node: source.id, port: state.pending.port};
    if (same(target.inputs[input], value)) { state.pending = null; renderGraph(); announce("These ports are already connected."); return; }
    remember(); target.inputs[input] = value; state.pending = null; emit(`Connected ${source.id}.${value.port} to ${target.id}.${input}. Python will validate runtime metadata.`);
  }
  function portButton(node, name, descriptor, side) {
    const output = side === "outputs";
    const button = control("", () => {
      if (output) {
        state.pending = state.pending?.node === node.id && state.pending.port === name ? null : {node: node.id, port: name};
        renderGraph(); announce(state.pending ? `Output ${node.id}.${name} selected. Choose an input port.` : "Connection cancelled.");
      } else connect(node, name);
    }, {className: `port ${output ? "output" : "input"}`, label: `${output ? "Output" : "Input"} ${name} ${descriptor.kind}, ${node.id}.${name}${descriptor.unit ? `, ${descriptor.unit}` : ""}`});
    button.dataset.node = node.id; button.dataset.port = name; button.dataset.direction = side;
    const dot = element("span", "port-dot"); dot.setAttribute("aria-hidden", "true");
    const text = element("span", "port-text"); text.append(element("span", "", name), document.createTextNode(" "), element("span", "port-type", descriptor.kind));
    if (output) {
      button.setAttribute("aria-pressed", String(state.pending?.node === node.id && state.pending.port === name));
      button.append(text, dot);
    } else button.append(dot, text);
    return button;
  }
  function deleteNode(id) { deleteNodes([id]); }
  function deleteNodes(ids) {
    if (state.disabled) return;
    const removed = new Set(ids);
    if (state.workflow.nodes.every(node => removed.has(node.id))) { announce("Keep at least one node in a workflow."); return; }
    remember();
    state.workflow.nodes = state.workflow.nodes.filter(node => !removed.has(node.id));
    for (const node of state.workflow.nodes) for (const [input, source] of Object.entries(node.inputs)) if (removed.has(source.node)) delete node.inputs[input];
    removed.forEach(id => {delete state.positions[id]; state.selection.delete(id);});
    state.groups = cleanGroups(state.groups);
    state.selected = state.selection.values().next().value || null; state.pending = null; emit(`Deleted ${removed.size} nodes and their connections.`);
  }
  function editParameters(node) {
    parameterNode = node.id;
    $("parameters-heading").textContent = `Parameters: ${node.id} (${node.kind})`;
    $("parameter-json").value = JSON.stringify(node.parameters, null, 2);
    $("parameter-error").textContent = "";
    $("parameters").showModal(); $("parameter-json").focus();
  }
  function renderGraph() {
    if (!state.workflow) return;
    $("empty").hidden = true;
    $("nodes").replaceChildren(); $("edges").replaceChildren(); $("connection-list").replaceChildren(); renderGroups();
    state.workflow.nodes.forEach(node => {
      const box = element("article", `node${state.selection.has(node.id) ? " selected" : ""}`);
      box.dataset.id = node.id;
      box.style.left = `${state.positions[node.id].x}px`; box.style.top = `${state.positions[node.id].y}px`;
      box.setAttribute("aria-label", `Node ${node.id}, ${node.kind}`);
      const title = control(node.id, event => {if (event.detail === 0) choose(node.id, event.shiftKey || event.ctrlKey || event.metaKey); focusTitle(node.id, true);}, {className: "node-title", label: `Move node ${node.id}`});
      title.addEventListener("focus", () => {
        if (preserveFocusSelection) return;
        state.selected = node.id;
        if (!state.selection.has(node.id)) state.selection = new Set([node.id]);
        selectionUI();
      });
      title.addEventListener("pointerdown", event => {
        if (state.disabled || event.button !== 0) return;
        event.preventDefault(); event.stopPropagation();
        if (event.shiftKey || event.ctrlKey || event.metaKey) choose(node.id, true);
        else if (!state.selection.has(node.id)) choose(node.id);
        focusTitle(node.id, true);
        if (state.selection.has(node.id)) beginDrag(event, node.id, state.selection);
      });
      title.addEventListener("keydown", event => {
        const vectors = {ArrowLeft: [-1, 0], ArrowRight: [1, 0], ArrowUp: [0, -1], ArrowDown: [0, 1]};
        if (!vectors[event.key] || state.disabled) return;
        event.preventDefault(); event.stopPropagation(); remember();
        const step = event.shiftKey ? 40 : 10, vector = vectors[event.key];
        const selected = state.selection.has(node.id) ? state.selection : new Set([node.id]);
        selected.forEach(id => {state.positions[id].x += vector[0] * step; state.positions[id].y += vector[1] * step;});
        emit(`Moved ${selected.size} selected nodes.`); focusTitle(node.id);
      });
      box.append(title, element("div", "node-subtitle", node.kind));
      const inputs = ports(node, "inputs"), outputs = ports(node, "outputs");
      for (let index = 0; index < Math.max(1, inputs.length, outputs.length); index++) {
        const row = element("div", "port-row");
        row.append(inputs[index] ? portButton(node, ...inputs[index], "inputs") : element("span"), outputs[index] ? portButton(node, ...outputs[index], "outputs") : element("span"));
        box.append(row);
      }
      const actions = element("div", "node-actions");
      actions.append(control("Parameters", () => editParameters(node), {label: `Edit parameters for ${node.id}`}), control("Delete", () => deleteNode(node.id), {label: `Delete node ${node.id}`}));
      box.append(actions); $("nodes").append(box);
    });
    graphEdges().forEach(({node, input, source}) => {
      const parent = state.workflow.nodes.find(item => item.id === source.node);
      if (!parent) return;
      const start = anchor(parent, source.port, "outputs"), end = anchor(node, input, "inputs");
      const bend = Math.max(60, Math.abs(end.x - start.x) * .45);
      const d = `M ${start.x} ${start.y} C ${start.x + bend} ${start.y}, ${end.x - bend} ${end.y}, ${end.x} ${end.y}`;
      const text = `${source.node}.${source.port} → ${node.id}.${input}`;
      const path = svg("path", {d, class: "edge"});
      const target = svg("path", {d, class: "edge-target", tabindex: state.disabled ? -1 : 0, role: "button", "aria-label": `Delete connection ${text}`});
      const title = svg("title"); title.textContent = text; target.append(title);
      target.addEventListener("click", () => removeEdge(node.id, input));
      target.addEventListener("keydown", event => {if (["Enter", " ", "Delete", "Backspace"].includes(event.key)) {event.preventDefault(); removeEdge(node.id, input);}});
      $("edges").append(path, target);
      const item = element("li", "", text); item.append(control("Disconnect", () => removeEdge(node.id, input), {label: `Disconnect ${text}`})); $("connection-list").append(item);
    });
    $("undo").disabled = state.disabled || !state.undo.length; $("redo").disabled = state.disabled || !state.redo.length;
    ["add", "layout", "import"].forEach(id => {$(id).disabled = state.disabled;});
    selectionUI(); applyView(); frameHeight();
  }
  function focusTitle(id, preserve = false) {
    preserveFocusSelection = preserve;
    [...document.querySelectorAll(".node")].find(node => node.dataset.id === id)?.querySelector(".node-title").focus({preventScroll: true});
    preserveFocusSelection = false;
  }
  function applyView() {
    const {x, y, zoom} = state.view;
    $("stage").style.transform = `translate(${x}px,${y}px) scale(${zoom})`;
    $("zoom-level").value = `${Math.round(zoom * 100)}%`;
    $("viewport").style.backgroundPosition = `${x}px ${y}px`;
    $("viewport").style.backgroundSize = `${22 * zoom}px ${22 * zoom}px`;
    renderMinimap();
  }
  function renderMinimap() {
    $("minimap").replaceChildren();
    if (!state.workflow) return;
    const points = state.workflow.nodes.map(node => ({...state.positions[node.id], width, height: nodeHeight(node), id: node.id}));
    const minX = Math.min(...points.map(p => p.x)), minY = Math.min(...points.map(p => p.y));
    const graphW = Math.max(...points.map(p => p.x + p.width)) - minX, graphH = Math.max(...points.map(p => p.y + p.height)) - minY;
    const scale = Math.min(164 / Math.max(graphW, 1), 94 / Math.max(graphH, 1));
    state.groups.forEach(group => {const b = groupBounds(group); if (b) $("minimap").append(svg("rect", {x: 8 + (b.x - minX) * scale, y: 8 + (b.y - minY) * scale, width: b.width * scale, height: b.height * scale, fill: "none", stroke: "#b8a8ec", "stroke-width": .6}));});
    points.forEach(p => $("minimap").append(svg("rect", {x: 8 + (p.x - minX) * scale, y: 8 + (p.y - minY) * scale, width: p.width * scale, height: p.height * scale, rx: 2, fill: state.selection.has(p.id) ? "#80dfdb" : "#6b84b5"})));
    const v = state.view, area = $("viewport");
    $("minimap").append(svg("rect", {x: 8 + (-v.x / v.zoom - minX) * scale, y: 8 + (-v.y / v.zoom - minY) * scale, width: area.clientWidth / v.zoom * scale, height: area.clientHeight / v.zoom * scale, fill: "none", stroke: "#f0d6a0", "stroke-width": 1}));
  }
  function zoom(next, clientX, clientY) {
    const bounds = $("viewport").getBoundingClientRect();
    const x = clientX == null ? bounds.width / 2 : clientX - bounds.left;
    const y = clientY == null ? bounds.height / 2 : clientY - bounds.top;
    const value = Math.max(.25, Math.min(2, next));
    const factor = value / state.view.zoom;
    state.view.x = x - (x - state.view.x) * factor; state.view.y = y - (y - state.view.y) * factor; state.view.zoom = value; applyView();
  }
  function fit() {
    if (!state.workflow) return;
    const xs = state.workflow.nodes.map(node => state.positions[node.id].x), ys = state.workflow.nodes.map(node => state.positions[node.id].y);
    const groups = state.groups.map(groupBounds).filter(Boolean);
    const left = Math.min(...xs, ...groups.map(group => group.x)), top = Math.min(...ys, ...groups.map(group => group.y));
    const right = Math.max(...state.workflow.nodes.map(node => state.positions[node.id].x + width), ...groups.map(group => group.x + group.width));
    const bottom = Math.max(...state.workflow.nodes.map(node => state.positions[node.id].y + nodeHeight(node)), ...groups.map(group => group.y + group.height));
    state.view.zoom = Math.max(.25, Math.min(1.2, ($("viewport").clientWidth - 60) / (right - left), ($("viewport").clientHeight - 60) / (bottom - top)));
    state.view.x = 30 - left * state.view.zoom; state.view.y = 30 - top * state.view.zoom; applyView();
  }
  function catalogue() {
    const search = $("search").value.toLowerCase(), previous = $("node-kind").value;
    $("node-kind").replaceChildren();
    Object.entries(state.catalog).filter(([kind, definition]) => `${kind} ${definition.description || ""}`.toLowerCase().includes(search)).forEach(([kind]) => {
      const option = element("option", "", kind); option.value = kind; $("node-kind").append(option);
    });
    if ([...$("node-kind").options].some(option => option.value === previous)) $("node-kind").value = previous;
    describe();
  }
  function describe() { $("node-description").textContent = state.catalog[$("node-kind").value]?.description || "No matching node types."; }
  $("search").addEventListener("input", catalogue); $("node-kind").addEventListener("change", describe);
  $("select-all").addEventListener("click", selectAll); $("copy").addEventListener("click", copySelected); $("paste").addEventListener("click", pasteSelected);
  $("group").addEventListener("click", groupSelected); $("ungroup").addEventListener("click", ungroupSelected);
  $("add").addEventListener("click", () => {
    const kind = $("node-kind").value;
    if (!state.workflow || state.disabled || !Object.hasOwn(state.catalog, kind)) return;
    if (state.workflow.nodes.length >= 128) {announce("The editor supports at most 128 nodes."); return;}
    const stem = kind.replace(/[^A-Za-z0-9_-]/g, "_").replace(/^[^A-Za-z]+/, "").slice(0, 45) || "node";
    let id = stem, index = 1;
    while (state.workflow.nodes.some(node => node.id === id)) id = `${stem}_${++index}`;
    remember(); state.workflow.nodes.push({id, kind, parameters: {}, inputs: {}});
    state.positions[id] = {x: (80 - state.view.x) / state.view.zoom, y: (80 - state.view.y) / state.view.zoom};
    state.selected = id; state.selection = new Set([id]); emit(`Added ${id}. Configure its parameters and required inputs before execution.`); focusTitle(id);
  });
  function history(direction) {
    const from = direction === "undo" ? state.undo : state.redo, to = direction === "undo" ? state.redo : state.undo;
    if (state.disabled || !from.length) return;
    to.push(snapshot()); const previous = from.pop();
    state.workflow = previous.workflow; state.positions = previous.positions; state.groups = previous.groups || []; state.pending = null;
    state.selection = new Set([...state.selection].filter(id => state.workflow.nodes.some(node => node.id === id)));
    if (!state.workflow.nodes.some(node => node.id === state.selected)) state.selected = null;
    emit(direction === "undo" ? "Graph edit undone." : "Graph edit redone.");
  }
  $("undo").addEventListener("click", () => history("undo")); $("redo").addEventListener("click", () => history("redo"));
  $("layout").addEventListener("click", () => {
    if (!state.workflow || state.disabled) return;
    remember();
    const levels = new Map(), unresolved = [...state.workflow.nodes];
    for (let iteration = 0; iteration < state.workflow.nodes.length && unresolved.length; iteration++) {
      for (let index = unresolved.length - 1; index >= 0; index--) {
        const node = unresolved[index], parents = Object.values(node.inputs).map(value => value.node);
        if (parents.every(id => levels.has(id))) {levels.set(node.id, parents.length ? 1 + Math.max(...parents.map(id => levels.get(id))) : 0); unresolved.splice(index, 1);}
      }
    }
    const rows = new Map();
    state.workflow.nodes.forEach(node => {
      const level = levels.get(node.id) ?? 0, row = rows.get(level) || 0;
      state.positions[node.id] = {x: level * 310, y: row}; rows.set(level, row + nodeHeight(node) + 40);
    });
    emit("Arranged nodes by dependency depth."); fit();
  });
  $("parameters-form").addEventListener("submit", event => {
    event.preventDefault();
    try {
      if (state.disabled) return;
      if ($("parameter-json").value.length > 100000) throw new Error("Parameter JSON must be below 100 kB.");
      const value = strictJSON($("parameter-json").value);
      if (!value || typeof value !== "object" || Array.isArray(value)) throw new Error("Parameters must be a JSON object.");
      const node = state.workflow.nodes.find(item => item.id === parameterNode);
      if (!node) throw new Error("This node no longer exists.");
      remember(); node.parameters = value; $("parameters").close(); emit(`Updated ${node.id} parameters. Python will validate fields and ranges.`);
    } catch (error) {$("parameter-error").textContent = error.message;}
  });
  $("cancel-parameters").addEventListener("click", () => $("parameters").close());
  $("import").addEventListener("click", () => {$("file").value = ""; $("file").click();});
  $("file").addEventListener("change", async () => {
    try {
      const file = $("file").files[0]; if (!file || state.disabled) return;
      if (file.size > 1000000) throw new Error("Workflow import must be below 1 MB.");
      const workflow = validateWorkflow(strictJSON(await file.text()));
      remember(); state.workflow = workflow; ensurePositions(); state.groups = []; state.pending = null; state.selected = null; state.selection.clear();
      emit("Imported workflow data. Nothing has been executed."); fit();
    } catch (error) {announce(`Import rejected: ${error.message}`);}
  });
  $("export").addEventListener("click", () => {
    if (!state.workflow) return;
    const url = URL.createObjectURL(new Blob([JSON.stringify(state.workflow, null, 2) + "\n"], {type: "application/json"}));
    const link = element("a"); link.href = url; link.download = "biosignal-workflow.json"; link.click();
    setTimeout(() => URL.revokeObjectURL(url), 1000); announce("Exported workflow definition as JSON. Signals and results are not included.");
  });
  $("zoom-in").addEventListener("click", () => zoom(state.view.zoom * 1.2)); $("zoom-out").addEventListener("click", () => zoom(state.view.zoom / 1.2));
  $("fit").addEventListener("click", fit); $("reset-view").addEventListener("click", () => {state.view = {x: 30, y: 30, zoom: 1}; applyView();});
  $("viewport").addEventListener("wheel", event => {if (event.ctrlKey || event.metaKey) {event.preventDefault(); zoom(state.view.zoom * Math.exp(-event.deltaY * .003), event.clientX, event.clientY);}}, {passive: false});
  $("viewport").addEventListener("pointerdown", event => {
    if (event.button !== 0 || event.target.closest(".node,.edge-target,.group-title")) return;
    gesture = {kind: "pan", x: event.clientX, y: event.clientY, original: {...state.view}};
    $("viewport").classList.add("panning"); $("viewport").setPointerCapture(event.pointerId);
  });
  $("viewport").addEventListener("pointermove", event => {
    if (!gesture) return;
    const dx = event.clientX - gesture.x, dy = event.clientY - gesture.y;
    if (gesture.kind === "pan") {state.view.x = gesture.original.x + dx; state.view.y = gesture.original.y + dy; applyView(); return;}
    if (Math.abs(dx) + Math.abs(dy) < 3 && !gesture.moved) return;
    gesture.moved = true;
    gesture.ids.forEach(id => {const original = gesture.originals[id]; state.positions[id] = {x: Math.max(-10000, Math.min(10000, original.x + dx / state.view.zoom)), y: Math.max(-10000, Math.min(10000, original.y + dy / state.view.zoom))};});
    renderGraph();
  });
  function endGesture(event) {
    const finished = gesture; gesture = null; $("viewport").classList.remove("panning");
    if ($("viewport").hasPointerCapture(event.pointerId)) $("viewport").releasePointerCapture(event.pointerId);
    if (finished?.kind === "nodes" && finished.moved) {
      state.undo.push(finished.before); if (state.undo.length > 50) state.undo.shift(); state.redo = [];
      emit(`Moved ${finished.ids.length} selected nodes.`); focusTitle(finished.id);
    }
  }
  $("viewport").addEventListener("pointerup", endGesture); $("viewport").addEventListener("pointercancel", endGesture);
  document.addEventListener("keydown", event => {
    if (event.target.matches("input,textarea,select") || $("parameters").open) return;
    if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "z") {event.preventDefault(); history(event.shiftKey ? "redo" : "undo"); return;}
    if (event.ctrlKey || event.metaKey) {
      const key = event.key.toLowerCase();
      if (key === "a") {event.preventDefault(); selectAll(); return;}
      if (key === "c" && state.selection.size) {event.preventDefault(); copySelected(); return;}
      if (key === "v" && state.clipboard) {event.preventDefault(); pasteSelected(); return;}
      if (key === "g") {event.preventDefault(); if (event.shiftKey) ungroupSelected(); else groupSelected(); return;}
    }
    if (event.key === "Escape") {state.pending = null; state.selection.clear(); state.selected = null; renderGraph(); announce("Connection cancelled and selection cleared.");}
    if (["Delete", "Backspace"].includes(event.key) && state.selection.size && !event.target.matches(".edge-target")) {event.preventDefault(); deleteNodes([...state.selection]);}
    if (event.target === $("viewport")) {
      const vectors = {ArrowLeft: [40, 0], ArrowRight: [-40, 0], ArrowUp: [0, 40], ArrowDown: [0, -40]};
      if (vectors[event.key]) {event.preventDefault(); state.view.x += vectors[event.key][0]; state.view.y += vectors[event.key][1]; applyView();}
      if (["+", "="].includes(event.key)) {event.preventDefault(); zoom(state.view.zoom * 1.2);}
      if (event.key === "-") {event.preventDefault(); zoom(state.view.zoom / 1.2);}
    }
  });
  window.addEventListener("message", event => {
    if (event.source !== window.parent || event.data?.type !== "streamlit:render") return;
    const args = event.data.args;
    if (!args || typeof args !== "object" || !args.workflow || !args.catalog) return;
    try {
      state.catalog = args.catalog;
      const next = validateWorkflow(args.workflow);
      const digest = typeof args.graph_digest === "string" ? args.graph_digest : "";
      const acknowledged = state.outbound && (Object.hasOwn(args, "event_ack")
        ? args.event_ack === state.outbound.id : same(next, state.outbound.workflow));
      let changed = false, resend = false;
      if (acknowledged) {
        if (same(next, state.outbound.workflow)) {
          // Keep edits made locally while the accepted graph was in flight.
          resend = !same(next, state.workflow) || !same(state.positions, state.outbound.positions) || !same(state.groups, state.outbound.groups);
          if (!resend) announce("Draft synchronized with Python. Scientific validation messages appear below.");
        } else {
          // A rejected structural draft must not be replayed indefinitely.
          changed = true;
          announce("The application rejected the last draft. Review its validation messages.");
        }
        state.outbound = null;
      } else if (!state.outbound || digest !== state.digest) {
        changed = !state.workflow || !same(next, state.workflow);
        if (changed) state.outbound = null;
      }
      state.digest = digest;
      state.disabled = !!args.disabled;
      if (changed) {state.workflow = next; ensurePositions(args.positions || {}); state.groups = cleanGroups(args.groups || []); state.undo = []; state.redo = []; state.pending = null; state.selected = null; state.selection.clear();}
      else if (!state.outbound && !resend && Array.isArray(args.groups)) state.groups = cleanGroups(args.groups);
      $("errors").replaceChildren();
      if (Array.isArray(args.errors)) args.errors.slice(0, 20).forEach(error => $("errors").append(element("p", "", String(error))));
      catalogue(); renderGraph();
      if (changed) {fit(); announce("Workflow loaded. Graph editing does not execute algorithms.");}
      if (resend) sendGraph();
    } catch (error) {announce(`Workflow could not be loaded: ${error.message}`);}
  });
  new ResizeObserver(() => {applyView(); frameHeight();}).observe(document.body);
  message("streamlit:componentReady", {apiVersion: 1}); frameHeight();
})();
