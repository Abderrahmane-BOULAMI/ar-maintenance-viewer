// 3D / AR maintenance viewer: point cloud of the cell, equipment health from the CMMS,
// step-by-step procedures, distance measurement and a session log for the evaluation protocol.
import * as THREE from "three";
import { OrbitControls } from "three/addons/controls/OrbitControls.js";
import { PLYLoader } from "three/addons/loaders/PLYLoader.js";
import { VRButton } from "three/addons/webxr/VRButton.js";
import { ARButton } from "three/addons/webxr/ARButton.js";

const COLORS = { green: 0x3fbf7f, orange: 0xf0a030, red: 0xe5484d };
const ENERGY = { electrical: "électrique", hydraulic: "hydraulique", pneumatic: "pneumatique" };
const $ = (id) => document.getElementById(id);
const fmt = (v, d = 0) => (v === null || v === undefined ? "n/a" : Number(v).toLocaleString("fr-FR", { maximumFractionDigits: d }));

const state = { scene: null, equipment: new Map(), selected: null, proc: null, step: 0, stepStart: 0,
                measuring: false, measurePts: [], log: [], ready: false };
const log = (event, data = {}) => state.log.push({ t: new Date().toISOString(), event, ...data });

// ------------------------------------------------------------------ renderer and scene
const renderer = new THREE.WebGLRenderer({ antialias: true, preserveDrawingBuffer: true });
renderer.setPixelRatio(Math.min(devicePixelRatio, 2));
renderer.setSize(innerWidth, innerHeight);
renderer.xr.enabled = true;
$("viewer").appendChild(renderer.domElement);

const scene = new THREE.Scene();
scene.background = new THREE.Color(0x0f1418);
const world = new THREE.Group();            // everything that belongs to the cell (scaled in AR)
scene.add(world);
scene.add(new THREE.HemisphereLight(0xffffff, 0x334455, 1.2));

THREE.Object3D.DEFAULT_UP.set(0, 0, 1);
const camera = new THREE.PerspectiveCamera(55, innerWidth / innerHeight, 0.05, 200);
camera.up.set(0, 0, 1);
camera.position.set(-7, -8, 6);
const controls = new OrbitControls(camera, renderer.domElement);
controls.target.set(0, 0, 0.8);
controls.enableDamping = true;
controls.update();

let fly = null;  // camera animation {from, to, tFrom, tTo, start}
function flyTo(center, size) {
  const c = new THREE.Vector3(...center);
  const r = Math.max(...size) * 1.8 + 1.5;
  const dir = camera.position.clone().sub(controls.target).normalize();
  fly = { from: camera.position.clone(), to: c.clone().add(dir.multiplyScalar(r)).setZ(c.z + r * 0.6),
          tFrom: controls.target.clone(), tTo: c, start: performance.now() };
}

// ------------------------------------------------------------------ equipment overlays
function overlay(eq) {
  const color = COLORS[eq.kpis.status] ?? 0x8899aa;
  let geo;
  if (eq.shape === "cyl") {
    geo = new THREE.CylinderGeometry(eq.size[0] / 2 + 0.05, eq.size[0] / 2 + 0.05, eq.size[2] + 0.1, 32, 1, true);
    geo.rotateX(Math.PI / 2);
  } else {
    geo = new THREE.BoxGeometry(eq.size[0] + 0.1, eq.size[1] + 0.1, eq.size[2] + 0.1);
  }
  const mesh = new THREE.Mesh(geo, new THREE.MeshBasicMaterial({ color, transparent: true, opacity: 0.12,
                                                                 depthWrite: false, side: THREE.DoubleSide }));
  mesh.position.set(...eq.center);
  const edges = new THREE.LineSegments(new THREE.EdgesGeometry(geo, 30), new THREE.LineBasicMaterial({ color }));
  mesh.add(edges);
  mesh.userData.tag = eq.tag;
  mesh.add(label(eq.tag, color, eq.size[2] / 2 + 0.35));
  world.add(mesh);
  return mesh;
}

function label(text, color, z) {
  const c = document.createElement("canvas");
  c.width = 256; c.height = 96;
  const g = c.getContext("2d");
  g.fillStyle = "#182128e6"; g.beginPath(); g.roundRect(4, 10, 248, 76, 18); g.fill();
  g.fillStyle = "#" + color.toString(16).padStart(6, "0"); g.beginPath(); g.arc(42, 48, 14, 0, 2 * Math.PI); g.fill();
  g.fillStyle = "#e7edf1"; g.font = "bold 44px system-ui"; g.fillText(text, 70, 64);
  const s = new THREE.Sprite(new THREE.SpriteMaterial({ map: new THREE.CanvasTexture(c), depthTest: false }));
  s.scale.set(0.8, 0.3, 1);
  s.position.set(0, 0, z);
  s.renderOrder = 10;
  return s;
}

// ------------------------------------------------------------------ side panel
function select(tag, source = "click") {
  const eq = state.equipment.get(tag);
  if (!eq) return false;
  if (state.selected) state.selected.mesh.material.opacity = 0.12;
  state.selected = eq;
  eq.mesh.material.opacity = 0.32;
  flyTo(eq.data.center, eq.data.size);
  log("open_equipment", { tag, source });
  const d = eq.data, k = d.kpis;
  const procs = state.scene.procedures.filter((p) => p.equipment === tag);
  $("panel-body").innerHTML = `
    <h2>${d.tag} · ${d.name}</h2>
    <span class="badge ${k.status}">${{ green: "RAS", orange: "À surveiller", red: "Pannes répétitives" }[k.status]}</span>
    <h3>Indicateurs sur 12 mois</h3>
    <div class="kpis">
      <div class="kpi"><b>${fmt(k.failures_12m)}</b><span>pannes</span></div>
      <div class="kpi"><b>${fmt(k.mtbf_h)} h</b><span>MTBF</span></div>
      <div class="kpi"><b>${fmt(k.mttr_h, 1)} h</b><span>MTTR</span></div>
      <div class="kpi"><b>${fmt(k.availability * 100, 2)} %</b><span>disponibilité</span></div>
      <div class="kpi"><b>${fmt(k.open_orders)}</b><span>OT ouverts</span></div>
      <div class="kpi"><b>${k.next_preventive ?? "n/a"}</b><span>prochaine préventive</span></div>
    </div>
    <h3>Modes de défaillance principaux</h3>
    <ul class="hist">${k.top_modes.map((m) => `<li>${m.mode} : ${m.count}</li>`).join("") || "<li>aucun</li>"}</ul>
    <h3>Dernières interventions</h3>
    <ul class="hist">${d.history.map((h) => `<li class="${h.status === "OPEN" ? "open" : ""}">${h.date} · OT ${h.wo} ·
      ${h.status === "OPEN" ? "OUVERT · " : ""}${h.description}</li>`).join("")}</ul>
    <h3>Procédures</h3>
    ${procs.map((p) => `<div class="proc"><span>${p.title} (${p.duration_min} min)</span>
      <button class="primary" data-proc="${p.id}">Démarrer</button></div>`).join("") || "<p>Aucune procédure publiée.</p>"}
    <h3>Énergies à consigner</h3><p>${d.energy.map((x) => ENERGY[x] ?? x).join(", ")}</p>`;
  $("panel").hidden = false;
  $("panel-body").querySelectorAll("[data-proc]").forEach((b) => (b.onclick = () => startProcedure(b.dataset.proc)));
  return true;
}
$("close").onclick = () => { $("panel").hidden = true; if (state.selected) state.selected.mesh.material.opacity = 0.12; };

// ------------------------------------------------------------------ procedures
function startProcedure(id) {
  const p = state.scene.procedures.find((x) => x.id === id);
  if (!p) return false;
  state.proc = p; state.step = 0;
  log("start_procedure", { id });
  $("panel").hidden = true;
  $("steps").hidden = false;
  showStep();
  return true;
}

function showStep() {
  const p = state.proc, s = p.steps[state.step];
  state.stepStart = performance.now();
  $("step-head").textContent = `${p.title} · étape ${state.step + 1} / ${p.steps.length}`;
  $("step-text").textContent = s.text;
  const tr = (l) => l.map((x) => ENERGY[x] ?? x).join(", ");
  const lock = s.lockout ? `<span class="lock">CONSIGNATION : ${tr(s.lockout)}</span> · ` : "";
  const iso = s.isolate ? `équipement consigné (${tr(s.isolate)}) · ` : "";
  $("step-meta").innerHTML = `${lock}${iso}repère ${s.tag} · environ ${s.minutes} min`;
  $("prev").disabled = state.step === 0;
  $("next").textContent = state.step === p.steps.length - 1 ? "Terminer" : "Étape suivante";
  const eq = state.equipment.get(s.tag);
  state.equipment.forEach((e) => (e.mesh.material.opacity = 0.06));
  eq.mesh.material.opacity = 0.4;
  flyTo(eq.data.center, eq.data.size);
}

function stepDone() {
  log("step_done", { id: state.proc.id, step: state.step + 1,
                     seconds: Math.round((performance.now() - state.stepStart) / 100) / 10 });
}
function nextStep() {
  if (!state.proc) return false;
  stepDone();
  if (state.step < state.proc.steps.length - 1) { state.step++; showStep(); return true; }
  log("end_procedure", { id: state.proc.id, completed: true });
  toast("Procédure terminée, durées enregistrées dans le journal.");
  stopProcedure(false);
  return true;
}
function stopProcedure(aborted = true) {
  if (aborted && state.proc) log("end_procedure", { id: state.proc.id, completed: false, at_step: state.step + 1 });
  state.proc = null;
  $("steps").hidden = true;
  state.equipment.forEach((e) => (e.mesh.material.opacity = 0.12));
}
$("next").onclick = nextStep;
$("prev").onclick = () => { if (state.step > 0) { state.step--; showStep(); } };
$("stop").onclick = () => stopProcedure(true);

// ------------------------------------------------------------------ picking, measurement, search
const ray = new THREE.Raycaster();
ray.params.Points.threshold = 0.04;
const mouse = new THREE.Vector2();
let down = null;
renderer.domElement.addEventListener("pointerdown", (e) => (down = [e.clientX, e.clientY]));
renderer.domElement.addEventListener("pointerup", (e) => {
  if (!down || Math.hypot(e.clientX - down[0], e.clientY - down[1]) > 5) return;  // it was a drag
  mouse.set((e.clientX / innerWidth) * 2 - 1, -(e.clientY / innerHeight) * 2 + 1);
  ray.setFromCamera(mouse, camera);
  if (state.measuring && state.cloud) {
    const hit = ray.intersectObject(state.cloud)[0];
    if (hit) addMeasurePoint(hit.point);
    return;
  }
  const hit = ray.intersectObjects([...state.equipment.values()].map((x) => x.mesh), false)[0];
  if (hit) select(hit.object.userData.tag);
});

const mGroup = new THREE.Group();
world.add(mGroup);
function addMeasurePoint(p) {
  if (state.measurePts.length === 2) { state.measurePts = []; mGroup.clear(); }
  state.measurePts.push(p.clone());
  const dot = new THREE.Mesh(new THREE.SphereGeometry(0.04), new THREE.MeshBasicMaterial({ color: 0xf2b33d }));
  dot.position.copy(p); mGroup.add(dot);
  if (state.measurePts.length === 2) {
    const [a, b] = state.measurePts;
    mGroup.add(new THREE.Line(new THREE.BufferGeometry().setFromPoints([a, b]),
                              new THREE.LineBasicMaterial({ color: 0xf2b33d })));
    const d = a.distanceTo(b);
    toast(`Distance : ${d.toFixed(2)} m`);
    log("measure", { metres: Math.round(d * 100) / 100 });
  }
}
$("measure").onclick = () => {
  state.measuring = !state.measuring;
  $("measure").classList.toggle("on", state.measuring);
  toast(state.measuring ? "Cliquez deux points du nuage." : "Mesure désactivée.");
};

$("search").addEventListener("keydown", (e) => {
  if (e.key !== "Enter") return;
  const q = e.target.value.trim().toLowerCase();
  const hit = [...state.equipment.values()].find((x) => x.data.tag.toLowerCase() === q)
           || [...state.equipment.values()].find((x) => x.data.name.toLowerCase().includes(q));
  if (hit) select(hit.data.tag, "search"); else toast("Aucun équipement trouvé.");
});

$("export").onclick = () => {
  const blob = new Blob([JSON.stringify({ exported: new Date().toISOString(), events: state.log }, null, 1)],
                        { type: "application/json" });
  const a = Object.assign(document.createElement("a"), { href: URL.createObjectURL(blob), download: "session_log.json" });
  a.click();
};

let toastTimer;
function toast(msg) {
  $("toast").textContent = msg; $("toast").hidden = false;
  clearTimeout(toastTimer); toastTimer = setTimeout(() => ($("toast").hidden = true), 2500);
}

// ------------------------------------------------------------------ XR (VR headset, or AR table-top 1:10 model)
async function setupXR() {
  if (!navigator.xr) return;
  if (await navigator.xr.isSessionSupported("immersive-vr").catch(() => false)) $("xr").appendChild(VRButton.createButton(renderer));
  if (await navigator.xr.isSessionSupported("immersive-ar").catch(() => false)) $("xr").appendChild(ARButton.createButton(renderer));
  renderer.xr.addEventListener("sessionstart", () => {
    const ar = renderer.xr.getSession().environmentBlendMode !== "opaque";
    world.rotation.x = -Math.PI / 2;                         // z-up cell -> y-up XR space
    world.scale.setScalar(ar ? 0.1 : 1);                     // AR: table-top model at 1:10
    world.position.set(0, ar ? 0.8 : 0, ar ? -1.2 : -2);
    scene.background = ar ? null : new THREE.Color(0x0f1418);
    log("xr_session", { mode: ar ? "ar" : "vr" });
  });
  renderer.xr.addEventListener("sessionend", () => {
    world.rotation.set(0, 0, 0); world.scale.setScalar(1); world.position.set(0, 0, 0);
    scene.background = new THREE.Color(0x0f1418);
  });
}

// ------------------------------------------------------------------ load
async function load() {
  state.scene = await (await fetch("data/scene.json")).json();
  $("title").textContent = state.scene.title;
  state.scene.equipment.forEach((eq) => state.equipment.set(eq.tag, { data: eq, mesh: overlay(eq) }));
  const geo = await new PLYLoader().loadAsync("data/cell.ply");
  const cloud = new THREE.Points(geo, new THREE.PointsMaterial({ size: 0.025, vertexColors: true }));
  world.add(cloud);
  state.cloud = cloud;
  state.points = geo.attributes.position.count;
  $("loading").remove();
  await setupXR();
  state.ready = true;
  log("loaded", { points: state.points });
}

renderer.setAnimationLoop(() => {
  if (fly) {
    const t = Math.min(1, (performance.now() - fly.start) / 700), e = t * t * (3 - 2 * t);
    camera.position.lerpVectors(fly.from, fly.to, e);
    controls.target.lerpVectors(fly.tFrom, fly.tTo, e);
    if (t === 1) fly = null;
  }
  controls.update();
  renderer.render(scene, camera);
});
addEventListener("resize", () => {
  camera.aspect = innerWidth / innerHeight; camera.updateProjectionMatrix(); renderer.setSize(innerWidth, innerHeight);
});

// small API used by the end-to-end test and by trainers to script a demo
window.app = { state, select, startProcedure, nextStep, stopProcedure, addMeasurePoint: (x, y, z) => addMeasurePoint(new THREE.Vector3(x, y, z)) };
load().catch((err) => { $("loading").textContent = "Erreur de chargement : " + err.message; console.error(err); });
