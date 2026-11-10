"use strict";

// ===================== Utilidades =====================
const $ = (selector, raiz = document) => raiz.querySelector(selector);

/** Escapa el texto antes de meterlo en el HTML, para que nadie pueda inyectar código. */
const esc = (valor) =>
  String(valor ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);

const formatoDinero = new Intl.NumberFormat("es-HN", { style: "currency", currency: "HNL" });
const dinero = (valor) => formatoDinero.format(valor ?? 0);
const fecha = (iso) =>
  new Date(`${iso}T00:00:00`).toLocaleDateString("es-HN", { day: "numeric", month: "short", year: "numeric" });
const fechaHora = (texto) =>
  new Date(String(texto).replace(" ", "T")).toLocaleString("es-HN", { day: "numeric", month: "short", hour: "numeric", minute: "2-digit" });
const hoy = () => new Date().toLocaleDateString("en-CA"); // AAAA-MM-DD en la hora local
const iniciales = (nombre) =>
  String(nombre ?? "?").split(/\s+/).filter(Boolean).slice(0, 2).map((p) => p[0].toUpperCase()).join("");
const porId = (lista, id) => lista.find((item) => item.id === id);
const conSigno = (numero) => (numero > 0 ? `+${numero}` : `${numero}`);

function antiguedad(iso) {
  const anios = Math.floor((Date.now() - new Date(`${iso}T00:00:00`)) / (365.25 * 24 * 3600 * 1000));
  return anios >= 1 ? `${anios} año${anios === 1 ? "" : "s"}` : "menos de un año";
}

function leerGuardado(clave, almacen = sessionStorage) {
  try { return almacen.getItem(clave); } catch { return null; }
}
function guardar(clave, valor, almacen = sessionStorage) {
  try { valor == null ? almacen.removeItem(clave) : almacen.setItem(clave, valor); } catch {}
}

// ===================== Íconos =====================
const ICONOS = {
  resumen: '<rect x="3" y="3" width="7" height="9" rx="1.5"/><rect x="14" y="3" width="7" height="5" rx="1.5"/><rect x="14" y="12" width="7" height="9" rx="1.5"/><rect x="3" y="16" width="7" height="5" rx="1.5"/>',
  ordenes: '<rect x="5" y="4" width="14" height="17" rx="2"/><path d="M9 4.5V3h6v1.5M9 10h6M9 14h6M9 18h3"/>',
  clientes: '<circle cx="9" cy="8" r="3.5"/><path d="M2.5 20c.8-3.6 3.4-5.5 6.5-5.5s5.7 1.9 6.5 5.5M16 4.6a3.5 3.5 0 0 1 0 6.8M18.5 14.8c1.6.8 2.7 2.5 3 5.2"/>',
  vehiculos: '<path d="M4 15.5V12l1.8-4.6A2 2 0 0 1 7.7 6h8.6a2 2 0 0 1 1.9 1.4L20 12v3.5a1 1 0 0 1-1 1h-1M6 16.5H5a1 1 0 0 1-1-1M10 16.5h4M4 12h16"/><circle cx="8" cy="16.5" r="2"/><circle cx="16" cy="16.5" r="2"/>',
  mecanicos: '<path d="M14.7 6.3a4 4 0 0 0-5.4 5.1l-5.7 5.7a1.9 1.9 0 0 0 2.7 2.7l5.7-5.7a4 4 0 0 0 5.1-5.4l-2.6 2.6-2.4-.6-.6-2.4z"/>',
  repuestos: '<path d="M21 8 12 3 3 8v8l9 5 9-5z"/><path d="M3 8l9 5 9-5M12 13v8"/>',
  usuarios: '<circle cx="8" cy="15" r="4"/><path d="M11 12l9-9M16 7l3 3M14 9l2 2"/>',
  perfil: '<circle cx="12" cy="8" r="4"/><path d="M4 21c1-4 4.5-6 8-6s7 2 8 6"/>',
  reporte: '<path d="M5 21V4h11l-1.5 4L16 12H5"/>',
  estrella: '<path d="M12 3l2.7 5.6 6.1.9-4.4 4.3 1 6.1L12 17l-5.4 2.9 1-6.1L3.2 9.5l6.1-.9z"/>',
  candado: '<rect x="5" y="11" width="14" height="10" rx="2"/><path d="M8 11V8a4 4 0 0 1 8 0v3"/>',
  enviar: '<path d="M21 3 10 14M21 3l-7 18-4-7-7-4z"/>',
  salir: '<path d="M15 4h3a2 2 0 0 1 2 2v12a2 2 0 0 1-2 2h-3M10 17l-5-5 5-5M5 12h11"/>',
  luna: '<path d="M20 14.5A8 8 0 1 1 9.5 4a6.5 6.5 0 0 0 10.5 10.5z"/>',
  sol: '<circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M2 12h2M20 12h2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4"/>',
  mas: '<path d="M12 5v14M5 12h14"/>',
  editar: '<path d="M4 20h4L19 9a2.8 2.8 0 0 0-4-4L4 16z"/><path d="M13.5 6.5l4 4"/>',
  borrar: '<path d="M4 7h16M10 11v6M14 11v6M6 7l1 13h10l1-13M9 7V4h6v3"/>',
  cerrar: '<path d="M6 6l12 12M18 6 6 18"/>',
  flecha: '<path d="M5 12h14M13 6l6 6-6 6"/>',
  buscar: '<circle cx="11" cy="11" r="7"/><path d="M20 20l-3.5-3.5"/>',
  alerta: '<path d="M12 9v4M12 17h.01M10.3 3.9 1.8 18a2 2 0 0 0 1.7 3h17a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0z"/>',
  check: '<path d="M5 12.5l4.5 4.5L19 7.5"/>',
};
const icono = (nombre) => `<svg class="icono" viewBox="0 0 24 24" aria-hidden="true">${ICONOS[nombre] ?? ""}</svg>`;

function pintarIconos(raiz = document) {
  raiz.querySelectorAll("[data-icono]").forEach((elemento) => {
    elemento.innerHTML = icono(elemento.dataset.icono);
  });
}

// ===================== Reglas del taller =====================
const ESTADOS = [
  { clave: "recibido", nombre: "Recibido", color: "var(--recibido)" },
  { clave: "en reparacion", nombre: "En reparación", color: "var(--reparacion)" },
  { clave: "listo", nombre: "Listo", color: "var(--listo)" },
  { clave: "entregado", nombre: "Entregado", color: "var(--entregado)" },
];
const ESTADOS_EDITABLES = ["recibido", "en reparacion"];
const POCA_EXISTENCIA = 5;

// Mismas reglas que creditos.py
const CATEGORIAS = {
  estandar: { nombre: "Estándar", clase: "insignia-neutra", multiplicador: 1 },
  premium: { nombre: "Premium", clase: "insignia-premium", multiplicador: 1.5 },
  lujo: { nombre: "Lujo", clase: "insignia-lujo", multiplicador: 2 },
};
const NIVELES = [
  { nombre: "Aprendiz", minimo: 0, categoria: "estandar", clase: "insignia-neutra" },
  { nombre: "Técnico", minimo: 100, categoria: "premium", clase: "insignia-premium" },
  { nombre: "Maestro", minimo: 250, categoria: "lujo", clase: "insignia-lujo" },
];
const CALIFICACIONES = [
  { clave: "excelente", nombre: "Excelente", puntos: 20, texto: "Quedó perfecto y a tiempo" },
  { clave: "bien", nombre: "Bien", puntos: 10, texto: "Cumplió con lo esperado" },
  { clave: "con problemas", nombre: "Con problemas", puntos: -10, texto: "Hubo detalles o retrasos" },
  { clave: "rehacer", nombre: "Hubo que rehacerlo", puntos: -25, texto: "El trabajo salió mal" },
];
const TIPOS_REPORTE = {
  equipo: "Falla de equipo o herramienta",
  repuestos: "Faltan repuestos",
  seguridad: "Seguridad o accidente",
  otro: "Otro",
};
const ROLES = { administrador: "Administración", recepcion: "Recepción", mecanico: "Mecánico" };

const nivelDe = (creditos) => [...NIVELES].reverse().find((n) => creditos >= n.minimo);
const puntosPor = (calificacion, categoria) =>
  Math.trunc(CALIFICACIONES.find((c) => c.clave === calificacion).puntos * CATEGORIAS[categoria].multiplicador);
const nombreCalificacion = (clave) => CALIFICACIONES.find((c) => c.clave === clave)?.nombre ?? clave;

const estado = {
  token: leerGuardado("taller-token"),
  yo: null,
  vistas: {},
  vista: "",
  busqueda: "",
  datos: {},
};
const esMecanico = () => estado.yo?.rol === "mecanico";

const nombreEstado = (clave) => ESTADOS.find((e) => e.clave === clave)?.nombre ?? clave;
const claseEstado = (clave) => `estado-${clave.replace(" ", "-")}`;
const insigniaEstado = (clave) =>
  `<span class="insignia ${claseEstado(clave)}"><span class="punto" style="background:currentColor"></span>${esc(nombreEstado(clave))}</span>`;
const insigniaCategoria = (clave) => `<span class="insignia ${CATEGORIAS[clave].clase}">${CATEGORIAS[clave].nombre}</span>`;
const insigniaNivel = (creditos) => {
  const nivel = nivelDe(creditos);
  return `<span class="insignia ${nivel.clase}">${icono("estrella")}${nivel.nombre}</span>`;
};
const insigniaCalificacion = (clave) => {
  const positiva = CALIFICACIONES.find((c) => c.clave === clave)?.puntos > 0;
  return `<span class="insignia ${positiva ? "insignia-ok" : "insignia-peligro"}">${esc(nombreCalificacion(clave))}</span>`;
};

// ===================== Conexión con la API =====================
class ErrorSilencioso extends Error {}

const TRADUCCIONES = [
  [/^Field required$/, "es obligatorio"],
  [/^String should have at least (\d+) characters?$/, "debe tener al menos $1 caracteres"],
  [/^String should have at most (\d+) characters?$/, "debe tener como máximo $1 caracteres"],
  [/^Input should be greater than or equal to (.+)$/, "debe ser mayor o igual que $1"],
  [/^Input should be greater than (.+)$/, "debe ser mayor que $1"],
  [/^String should match pattern .*$/, "no tiene el formato correcto"],
  [/^Value error, (.*)$/, "$1"],
];

function traducir(mensaje) {
  const [campo, ...resto] = String(mensaje).split(": ");
  const texto = resto.join(": ");
  if (!texto) return mensaje;
  for (const [patron, reemplazo] of TRADUCCIONES) {
    if (patron.test(texto)) return `${campo}: ${texto.replace(patron, reemplazo)}`;
  }
  return mensaje;
}

function mensajeDeError(cuerpo) {
  const detalle = cuerpo?.detail;
  if (Array.isArray(detalle)) return detalle.map(traducir).join(" · ");
  return detalle || "Ocurrió un error inesperado";
}

async function api(ruta, { metodo = "GET", datos, formulario } = {}) {
  const opciones = { method: metodo, headers: {} };
  if (estado.token) opciones.headers.Authorization = `Bearer ${estado.token}`;
  if (datos !== undefined) {
    opciones.headers["Content-Type"] = "application/json";
    opciones.body = JSON.stringify(datos);
  }
  if (formulario) opciones.body = new URLSearchParams(formulario);

  let respuesta;
  try {
    respuesta = await fetch(ruta, opciones);
  } catch {
    throw new Error("No se pudo conectar con la API. Revise que esté encendida.");
  }
  const cuerpo = await respuesta.json().catch(() => null);
  if (respuesta.status === 401 && estado.token) {
    cerrarSesion("Su sesión venció. Vuelva a iniciar sesión.");
    throw new ErrorSilencioso();
  }
  if (!respuesta.ok) throw new Error(mensajeDeError(cuerpo));
  return cuerpo;
}

/** Ejecuta una acción y muestra el error en un aviso si algo falla. */
async function intentar(accion) {
  try {
    return await accion();
  } catch (error) {
    if (!(error instanceof ErrorSilencioso)) aviso(error.message, "error");
    return undefined;
  }
}

async function cargarDatos() {
  const rutas = esMecanico()
    ? { trabajos: "/mecanico/trabajos", perfil: "/mecanico/perfil", reportes: "/mecanico/reportes" }
    : { clientes: "/clientes", vehiculos: "/vehiculos", mecanicos: "/mecanicos", repuestos: "/repuestos", ordenes: "/ordenes" };
  if (estado.yo.rol === "administrador") rutas.usuarios = "/usuarios";
  const respuestas = await Promise.all(Object.values(rutas).map((ruta) => api(ruta)));
  estado.datos = Object.fromEntries(Object.keys(rutas).map((clave, i) => [clave, respuestas[i]]));
}

// ===================== Avisos y diálogos =====================
function aviso(texto, tipo = "ok") {
  const elemento = document.createElement("div");
  elemento.className = `aviso ${tipo}`;
  elemento.innerHTML = `${icono(tipo === "error" ? "alerta" : "check")}<span>${esc(texto)}</span>`;
  const avisos = $("#avisos");
  avisos.append(elemento);
  // Se vuelve a mostrar como popover para quedar encima de cualquier diálogo abierto
  try {
    if (avisos.matches(":popover-open")) avisos.hidePopover();
    avisos.showPopover();
  } catch {}
  setTimeout(() => elemento.remove(), tipo === "error" ? 6000 : 3500);
}

const dialogo = $("#dialogo");
const confirmacion = $("#confirmacion");

function abrirDialogo(html, alPintar) {
  dialogo.innerHTML = html;
  pintarIconos(dialogo);
  dialogo.querySelectorAll("[data-cerrar]").forEach((b) => b.addEventListener("click", () => dialogo.close()));
  if (!dialogo.open) dialogo.showModal();
  alPintar?.(dialogo);
}

// Cerrar al hacer clic fuera del cuadro
for (const d of [dialogo, confirmacion]) {
  d.addEventListener("click", (evento) => { if (evento.target === d) d.close(); });
}

/** Abre el diálogo chico y resuelve con el valor del botón elegido ("" si se cerró). */
function preguntar(html) {
  return new Promise((resolver) => {
    confirmacion.innerHTML = html;
    confirmacion.querySelectorAll("[data-respuesta]").forEach((b) =>
      b.addEventListener("click", () => confirmacion.close(b.dataset.respuesta))
    );
    confirmacion.addEventListener("close", () => resolver(confirmacion.returnValue), { once: true });
    confirmacion.returnValue = "";
    confirmacion.showModal();
  });
}

async function confirmar({ titulo, texto, boton = "Eliminar" }) {
  const respuesta = await preguntar(`
    <div class="dialogo-encabezado"><div><h2>${esc(titulo)}</h2></div></div>
    <div class="dialogo-cuerpo"><p>${esc(texto)}</p></div>
    <div class="dialogo-pie">
      <button type="button" class="boton boton-secundario" data-respuesta="no">Cancelar</button>
      <button type="button" class="boton boton-peligro-lleno" data-respuesta="si">${esc(boton)}</button>
    </div>`);
  return respuesta === "si";
}

const encabezadoDialogo = (titulo, subtitulo = "") => `
  <div class="dialogo-encabezado">
    <div><h2>${titulo}</h2>${subtitulo ? `<p>${subtitulo}</p>` : ""}</div>
    <button type="button" class="boton boton-icono" data-cerrar aria-label="Cerrar">${icono("cerrar")}</button>
  </div>`;

// ===================== Formularios genéricos =====================
function campoHTML(campo, valor) {
  const id = `campo-${campo.nombre}`;
  const clase = `campo${campo.completo ? " completo" : ""}${campo.tipo === "checkbox" ? " campo-check" : ""}`;
  const atributos = [
    campo.requerido ? "required" : "",
    campo.minlength ? `minlength="${campo.minlength}"` : "",
    campo.maxlength ? `maxlength="${campo.maxlength}"` : "",
    campo.min !== undefined ? `min="${campo.min}"` : "",
    campo.max !== undefined ? `max="${campo.max}"` : "",
    campo.paso ? `step="${campo.paso}"` : "",
    campo.patron ? `pattern="${campo.patron}"` : "",
    campo.autocompletar ? `autocomplete="${campo.autocompletar}"` : "",
  ].join(" ");
  const ayuda = campo.ayuda ? `<span class="ayuda">${esc(campo.ayuda)}</span>` : "";

  if (campo.tipo === "checkbox") {
    return `<div class="${clase}"><input id="${id}" name="${campo.nombre}" type="checkbox" ${valor ? "checked" : ""} />
      <label for="${id}">${esc(campo.etiqueta)}</label></div>`;
  }
  if (campo.tipo === "checks") {
    const elegidos = new Set(valor ?? []);
    const opciones = campo.opciones.map((o) => `
      <label class="check"><input type="checkbox" name="${campo.nombre}" value="${esc(o.valor)}" ${elegidos.has(o.valor) ? "checked" : ""} />
        <span>${esc(o.texto)}</span></label>`).join("");
    return `<fieldset class="${clase} campo-checks"><legend>${esc(campo.etiqueta)}</legend>
      <div class="lista-checks">${opciones || `<span class="ayuda">${esc(campo.textoVacio ?? "No hay opciones")}</span>`}</div>${ayuda}</fieldset>`;
  }
  if (campo.tipo === "select") {
    const opciones = campo.opciones
      .map((o) => `<option value="${esc(o.valor)}" ${o.valor === valor ? "selected" : ""}>${esc(o.texto)}</option>`)
      .join("");
    const vacia = campo.textoVacio ?? "Seleccione…";
    return `<div class="${clase}"><label for="${id}">${esc(campo.etiqueta)}</label>
      <select id="${id}" name="${campo.nombre}" ${atributos}>${vacia ? `<option value="">${esc(vacia)}</option>` : ""}${opciones}</select>${ayuda}</div>`;
  }
  if (campo.tipo === "textarea") {
    return `<div class="${clase}"><label for="${id}">${esc(campo.etiqueta)}</label>
      <textarea id="${id}" name="${campo.nombre}" ${atributos}>${esc(valor)}</textarea>${ayuda}</div>`;
  }
  return `<div class="${clase}"><label for="${id}">${esc(campo.etiqueta)}</label>
    <input id="${id}" name="${campo.nombre}" type="${campo.tipo ?? "text"}" value="${esc(valor)}" ${atributos} />${ayuda}</div>`;
}

function leerFormulario(formulario, campos) {
  const datos = {};
  for (const campo of campos) {
    if (campo.tipo === "checks") {
      const marcados = formulario.querySelectorAll(`input[name="${campo.nombre}"]:checked`);
      datos[campo.nombre] = [...marcados].map((casilla) => Number(casilla.value));
      continue;
    }
    const control = formulario.elements[campo.nombre];
    if (campo.tipo === "checkbox") datos[campo.nombre] = control.checked;
    else if (control.value.trim() === "") datos[campo.nombre] = null;
    else if (campo.tipo === "number" || (campo.tipo === "select" && campo.numerico !== false)) datos[campo.nombre] = Number(control.value);
    else datos[campo.nombre] = campo.tipo === "password" ? control.value : control.value.trim();
  }
  return datos;
}

/** Revisa un formulario con las reglas del navegador y muestra el primer error en `error`. */
function formularioValido(formulario, error) {
  if (formulario.checkValidity()) return true;
  const invalido = formulario.querySelector(":invalid");
  error.textContent = `${invalido.labels?.[0]?.textContent ?? "Un campo"}: ${invalido.validationMessage}`;
  invalido.focus();
  return false;
}

/** Abre un formulario en el diálogo; al guardar llama a enviar(datos) y recarga la vista. */
function abrirFormulario({ titulo, subtitulo, campos, valores = {}, textoBoton = "Guardar", enviar }) {
  abrirDialogo(`
    <form id="formulario-dialogo" novalidate>
      ${encabezadoDialogo(esc(titulo), esc(subtitulo ?? ""))}
      <div class="dialogo-cuerpo">
        <div class="rejilla-campos">${campos.map((c) => campoHTML(c, valores[c.nombre] ?? c.porDefecto)).join("")}</div>
        <p class="mensaje-error" id="error-formulario" aria-live="polite"></p>
      </div>
      <div class="dialogo-pie">
        <button type="button" class="boton boton-secundario" data-cerrar>Cancelar</button>
        <button type="submit" class="boton boton-primario">${esc(textoBoton)}</button>
      </div>
    </form>`, (raiz) => {
    const formulario = $("#formulario-dialogo", raiz);
    formulario.querySelector("input, select, textarea")?.focus();
    formulario.addEventListener("submit", async (evento) => {
      evento.preventDefault();
      const error = $("#error-formulario", raiz);
      if (!formularioValido(formulario, error)) return;
      const boton = formulario.querySelector("[type=submit]");
      boton.disabled = true;
      try {
        await enviar(leerFormulario(formulario, campos));
        dialogo.close();
        await refrescar();
      } catch (e) {
        if (!(e instanceof ErrorSilencioso)) error.textContent = e.message;
      } finally {
        boton.disabled = false;
      }
    });
  });
}

// ===================== Personal: módulos con tabla =====================
const cantidad = (lista, campo, id) => lista.filter((item) => item[campo] === id).length;
const ordenesActivas = () => estado.datos.ordenes.filter((o) => o.estado !== "entregado");

function insigniaExistencia(existencia) {
  if (existencia === 0) return `<span class="insignia insignia-peligro">Agotado</span>`;
  if (existencia <= POCA_EXISTENCIA) return `<span class="insignia insignia-baja">${existencia} · Poca</span>`;
  return `<span class="insignia insignia-ok">${existencia}</span>`;
}

const opcionesCategoria = Object.entries(CATEGORIAS).map(([valor, c]) => ({ valor, texto: c.nombre }));

const MODULOS = {
  clientes: {
    ruta: "/clientes", singular: "cliente",
    columnas: [
      { titulo: "Nombre", valor: (c) => `<strong>${esc(c.nombre)}</strong>` },
      { titulo: "Teléfono", valor: (c) => `<span class="mono">${esc(c.telefono)}</span>` },
      { titulo: "Dirección", valor: (c) => esc(c.direccion || "—") },
      { titulo: "Vehículos", clase: "numero", valor: (c) => cantidad(estado.datos.vehiculos, "cliente_id", c.id) },
    ],
    texto: (c) => `${c.nombre} ${c.telefono} ${c.direccion ?? ""}`,
    nombre: (c) => c.nombre,
    campos: () => [
      { nombre: "nombre", etiqueta: "Nombre completo", requerido: true, minlength: 3, maxlength: 100, completo: true },
      { nombre: "telefono", etiqueta: "Teléfono", tipo: "tel", requerido: true, minlength: 8, maxlength: 20, ayuda: "Ejemplo: 9988-1122" },
      { nombre: "direccion", etiqueta: "Dirección", maxlength: 200 },
    ],
  },
  vehiculos: {
    ruta: "/vehiculos", singular: "vehículo",
    columnas: [
      { titulo: "Placa", valor: (v) => `<span class="placa">${esc(v.placa)}</span>` },
      { titulo: "Vehículo", valor: (v) => `<div class="celda-doble"><strong>${esc(v.marca)} ${esc(v.modelo)}</strong><span>Año ${v.anio}</span></div>` },
      { titulo: "Categoría", valor: (v) => insigniaCategoria(v.categoria) },
      { titulo: "Dueño", valor: (v) => esc(porId(estado.datos.clientes, v.cliente_id)?.nombre ?? "—") },
      { titulo: "Órdenes", clase: "numero", valor: (v) => cantidad(estado.datos.ordenes, "vehiculo_id", v.id) },
    ],
    texto: (v) => `${v.placa} ${v.marca} ${v.modelo} ${v.anio} ${CATEGORIAS[v.categoria].nombre} ${porId(estado.datos.clientes, v.cliente_id)?.nombre ?? ""}`,
    nombre: (v) => `${v.placa} (${v.marca} ${v.modelo})`,
    campos: () => [
      { nombre: "placa", etiqueta: "Placa", requerido: true, minlength: 3, maxlength: 10, ayuda: "Se guarda en mayúsculas" },
      { nombre: "anio", etiqueta: "Año", tipo: "number", requerido: true, min: 1950, max: new Date().getFullYear() + 1 },
      { nombre: "marca", etiqueta: "Marca", requerido: true, minlength: 2, maxlength: 50 },
      { nombre: "modelo", etiqueta: "Modelo", requerido: true, maxlength: 50 },
      {
        nombre: "cliente_id", etiqueta: "Dueño", tipo: "select", requerido: true,
        opciones: estado.datos.clientes.map((c) => ({ valor: c.id, texto: `${c.nombre} · ${c.telefono}` })),
      },
      {
        nombre: "categoria", etiqueta: "Categoría", tipo: "select", numerico: false, requerido: true, textoVacio: "",
        opciones: opcionesCategoria, porDefecto: "estandar",
        ayuda: "Premium pide un mecánico Técnico; Lujo, uno Maestro",
      },
    ],
  },
  mecanicos: {
    ruta: "/mecanicos", singular: "mecánico",
    columnas: [
      { titulo: "Nombre", valor: (m) => `<div class="mecanico-mini"><span class="avatar">${esc(iniciales(m.nombre))}</span><div class="celda-doble"><strong>${esc(m.nombre)}</strong><span>${esc(m.especialidad || "Sin especialidad")}</span></div></div>` },
      { titulo: "Nivel", valor: (m) => `${insigniaNivel(m.creditos)} <span class="texto-tenue">${m.creditos} cr.</span>` },
      { titulo: "Estado", valor: (m) => (m.activo ? `<span class="insignia insignia-ok">Activo</span>` : `<span class="insignia insignia-neutra">Inactivo</span>`) },
      { titulo: "Teléfono", valor: (m) => `<span class="mono">${esc(m.telefono || "—")}</span>` },
      { titulo: "En curso", clase: "numero", valor: (m) => cantidad(ordenesActivas(), "mecanico_id", m.id) },
    ],
    texto: (m) => `${m.nombre} ${m.especialidad ?? ""} ${m.nivel} ${m.correo ?? ""}`,
    nombre: (m) => m.nombre,
    ayudaEliminar: "Si ya tiene órdenes no se puede eliminar; en ese caso edítelo y desmarque «Activo».",
    campos: () => [
      { nombre: "nombre", etiqueta: "Nombre completo", requerido: true, minlength: 3, maxlength: 100, completo: true },
      { nombre: "especialidad", etiqueta: "Especialidad", maxlength: 60 },
      { nombre: "telefono", etiqueta: "Teléfono", tipo: "tel", maxlength: 20 },
      { nombre: "correo", etiqueta: "Correo", tipo: "email", maxlength: 100 },
      { nombre: "fecha_contratacion", etiqueta: "Fecha de contratación", tipo: "date", max: hoy() },
      { nombre: "activo", etiqueta: "Activo (puede recibir órdenes)", tipo: "checkbox", porDefecto: true, completo: true },
    ],
    notaFormulario: "Los créditos no se editan: cambian solo con la calificación de cada trabajo entregado.",
  },
  repuestos: {
    ruta: "/repuestos", singular: "repuesto",
    columnas: [
      { titulo: "Repuesto", valor: (r) => `<strong>${esc(r.nombre)}</strong>` },
      { titulo: "Precio", clase: "numero", valor: (r) => dinero(r.precio) },
      { titulo: "Existencia", valor: (r) => insigniaExistencia(r.existencia) },
      { titulo: "Valor en bodega", clase: "numero", valor: (r) => dinero(r.precio * r.existencia) },
    ],
    texto: (r) => r.nombre,
    nombre: (r) => r.nombre,
    campos: () => [
      { nombre: "nombre", etiqueta: "Nombre", requerido: true, minlength: 2, maxlength: 100, completo: true },
      { nombre: "precio", etiqueta: "Precio (L)", tipo: "number", requerido: true, min: 0.01, paso: 0.01 },
      { nombre: "existencia", etiqueta: "Existencia", tipo: "number", requerido: true, min: 0, paso: 1, porDefecto: 0 },
    ],
  },
  usuarios: {
    ruta: "/usuarios", singular: "cuenta", femenino: true, sinEditar: true,
    columnas: [
      { titulo: "Usuario", valor: (u) => `<strong class="mono">${esc(u.username)}</strong>` },
      { titulo: "Nombre", valor: (u) => esc(u.nombre || "—") },
      { titulo: "Rol", valor: (u) => `<span class="insignia ${u.rol === "mecanico" ? "insignia-baja" : u.rol === "administrador" ? "insignia-lujo" : "insignia-premium"}">${esc(ROLES[u.rol])}</span>` },
      { titulo: "Mecánico vinculado", valor: (u) => esc(u.mecanico || "—") },
    ],
    texto: (u) => `${u.username} ${u.nombre ?? ""} ${ROLES[u.rol]} ${u.mecanico ?? ""}`,
    nombre: (u) => u.username,
    campos: () => {
      const conCuenta = new Set(estado.datos.usuarios.map((u) => u.mecanico_id));
      return [
        { nombre: "username", etiqueta: "Usuario", requerido: true, minlength: 3, maxlength: 30, patron: "[A-Za-z0-9_]+", autocompletar: "off", ayuda: "Letras, números y guion bajo" },
        { nombre: "password", etiqueta: "Contraseña inicial", tipo: "password", requerido: true, minlength: 6, maxlength: 72, autocompletar: "new-password" },
        {
          nombre: "rol", etiqueta: "Rol", tipo: "select", numerico: false, requerido: true,
          opciones: Object.entries(ROLES).map(([valor, texto]) => ({ valor, texto })),
        },
        { nombre: "nombre", etiqueta: "Nombre para mostrar", maxlength: 100 },
        {
          nombre: "mecanico_id", etiqueta: "Ficha de mecánico", tipo: "select", completo: true, textoVacio: "Ninguna",
          opciones: estado.datos.mecanicos.filter((m) => !conCuenta.has(m.id)).map((m) => ({ valor: m.id, texto: `${m.nombre} · ${m.nivel}` })),
          ayuda: "Solo para cuentas de mecánico: así ve sus propios trabajos",
        },
      ];
    },
  },
};

const nuevoTexto = (modulo) => `${modulo.femenino ? "Nueva" : "Nuevo"} ${modulo.singular}`;

function pintarModulo(clave) {
  const modulo = MODULOS[clave];
  const termino = estado.busqueda.toLowerCase();
  const filas = estado.datos[clave].filter((item) => modulo.texto(item).toLowerCase().includes(termino));

  $("#vista").innerHTML = `
    <section class="panel">
      <div class="barra-herramientas">
        <label class="buscador">${icono("buscar")}
          <input id="busqueda" type="search" placeholder="Buscar ${esc(modulo.singular)}…" value="${esc(estado.busqueda)}" aria-label="Buscar" />
        </label>
        <span class="conteo">${filas.length} de ${estado.datos[clave].length}</span>
      </div>
      ${filas.length ? `
      <div class="tabla-contenedor"><table>
        <thead><tr>${modulo.columnas.map((c) => `<th class="${c.clase ?? ""}">${c.titulo}</th>`).join("")}<th></th></tr></thead>
        <tbody>${filas.map((item) => `
          <tr>
            ${modulo.columnas.map((c) => `<td class="${c.clase ?? ""}">${c.valor(item)}</td>`).join("")}
            <td class="acciones-fila">
              ${modulo.sinEditar ? "" : `<button type="button" class="boton boton-icono" data-editar="${item.id}" aria-label="Editar">${icono("editar")}</button>`}
              <button type="button" class="boton boton-icono peligro" data-eliminar="${item.id}" aria-label="Eliminar">${icono("borrar")}</button>
            </td>
          </tr>`).join("")}
        </tbody>
      </table></div>` : `
      <div class="vacio">${icono(clave)}<strong>${termino ? "Sin resultados" : `Todavía no hay ${esc(estado.vistas[clave].titulo.toLowerCase())}`}</strong>
        <span>${termino ? "Pruebe con otra búsqueda." : `Use el botón «${esc(nuevoTexto(modulo))}» para agregar.`}</span></div>`}
    </section>`;

  conectarBusqueda();
  $("#vista").querySelectorAll("[data-editar]").forEach((boton) =>
    boton.addEventListener("click", () => formularioModulo(clave, porId(estado.datos[clave], Number(boton.dataset.editar))))
  );
  $("#vista").querySelectorAll("[data-eliminar]").forEach((boton) =>
    boton.addEventListener("click", () => eliminarRegistro(clave, porId(estado.datos[clave], Number(boton.dataset.eliminar))))
  );
}

function formularioModulo(clave, registro) {
  const modulo = MODULOS[clave];
  abrirFormulario({
    titulo: registro ? `Editar ${modulo.singular}` : nuevoTexto(modulo),
    subtitulo: registro ? modulo.nombre(registro) : modulo.notaFormulario ?? "",
    campos: modulo.campos(),
    valores: registro ?? {},
    textoBoton: registro ? "Guardar cambios" : `Crear ${modulo.singular}`,
    enviar: async (datos) => {
      await api(registro ? `${modulo.ruta}/${registro.id}` : modulo.ruta, { metodo: registro ? "PUT" : "POST", datos });
      const creado = `${modulo.singular[0].toUpperCase()}${modulo.singular.slice(1)} ${modulo.femenino ? "creada" : "creado"}`;
      aviso(registro ? "Cambios guardados" : creado);
    },
  });
}

async function eliminarRegistro(clave, registro) {
  const modulo = MODULOS[clave];
  const seguro = await confirmar({
    titulo: `¿Eliminar ${modulo.femenino ? "la" : "el"} ${modulo.singular}?`,
    texto: `Se eliminará «${modulo.nombre(registro)}». Esta acción no se puede deshacer.${modulo.ayudaEliminar ? ` ${modulo.ayudaEliminar}` : ""}`,
  });
  if (!seguro) return;
  const resultado = await intentar(() => api(`${modulo.ruta}/${registro.id}`, { metodo: "DELETE" }));
  if (resultado) {
    aviso(resultado.mensaje);
    await refrescar();
  }
}

function conectarBusqueda() {
  const entrada = $("#busqueda");
  if (!entrada) return;
  entrada.addEventListener("input", () => {
    estado.busqueda = entrada.value;
    const posicion = entrada.selectionStart;
    pintarVista();
    const nueva = $("#busqueda");
    nueva.focus();
    nueva.setSelectionRange(posicion, posicion);
  });
}

// ===================== Personal: órdenes =====================
function textoVehiculo(vehiculo) {
  return vehiculo ? `${vehiculo.marca} ${vehiculo.modelo} ${vehiculo.anio}` : "Vehículo eliminado";
}

function tarjetaOrden(orden) {
  const vehiculo = porId(estado.datos.vehiculos, orden.vehiculo_id);
  const mecanico = porId(estado.datos.mecanicos, orden.mecanico_id);
  const categoria = vehiculo && vehiculo.categoria !== "estandar" ? insigniaCategoria(vehiculo.categoria) : "";
  return `
    <button type="button" class="tarjeta-orden" data-orden="${orden.id}">
      <div class="arriba"><span class="placa">${esc(vehiculo?.placa ?? "—")}</span>${categoria}<span class="numero-orden">#${orden.id}</span></div>
      <div class="vehiculo">${esc(textoVehiculo(vehiculo))}</div>
      <div class="diagnostico">${esc(orden.diagnostico || "Sin diagnóstico")}</div>
      <div class="abajo">
        <span class="mecanico-mini"><span class="avatar">${esc(iniciales(mecanico?.nombre))}</span><span>${esc(mecanico?.nombre ?? "—")}</span>${orden.equipo.length ? `<span class="mas-equipo" title="Equipo de ${orden.equipo.length + 1}">+${orden.equipo.length}</span>` : ""}</span>
        <span>${orden.calificacion ? esc(nombreCalificacion(orden.calificacion)) : fecha(orden.fecha_ingreso)}</span>
      </div>
    </button>`;
}

function textoOrden(orden) {
  const vehiculo = porId(estado.datos.vehiculos, orden.vehiculo_id);
  const cliente = vehiculo && porId(estado.datos.clientes, vehiculo.cliente_id);
  const mecanico = porId(estado.datos.mecanicos, orden.mecanico_id);
  return `#${orden.id} ${vehiculo?.placa} ${textoVehiculo(vehiculo)} ${cliente?.nombre} ${mecanico?.nombre} ${orden.diagnostico}`.toLowerCase();
}

function pintarOrdenes() {
  const termino = estado.busqueda.toLowerCase();
  const ordenes = estado.datos.ordenes
    .filter((o) => textoOrden(o).includes(termino))
    .sort((a, b) => b.fecha_ingreso.localeCompare(a.fecha_ingreso) || b.id - a.id);

  $("#vista").innerHTML = `
    <div class="filtros-ordenes">
      <label class="buscador">${icono("buscar")}
        <input id="busqueda" type="search" placeholder="Buscar por placa, cliente, mecánico…" value="${esc(estado.busqueda)}" aria-label="Buscar orden" />
      </label>
      <span class="conteo">${ordenes.length} órdenes</span>
    </div>
    <div class="tablero">
      ${ESTADOS.map((e) => {
        const columna = ordenes.filter((o) => o.estado === e.clave);
        return `
        <section class="columna-tablero">
          <header><h2><span class="punto" style="background:${e.color}"></span>${e.nombre}</h2><span class="cuenta">${columna.length}</span></header>
          ${columna.map(tarjetaOrden).join("") || `<p class="vacio-chico">Sin órdenes</p>`}
        </section>`;
      }).join("")}
    </div>`;

  conectarBusqueda();
  conectarTarjetasOrden();
}

function conectarTarjetasOrden() {
  $("#vista").querySelectorAll("[data-orden]").forEach((elemento) =>
    elemento.addEventListener("click", () => abrirOrden(Number(elemento.dataset.orden)))
  );
}

function camposOrden(orden) {
  // De más fama a menos: el primero es el líder sugerido
  const porFama = [...estado.datos.mecanicos].sort((a, b) => b.creditos - a.creditos);
  const mecanicos = porFama.filter((m) => m.activo || m.id === orden?.mecanico_id);
  const disponibles = porFama.filter((m) => m.activo || orden?.equipo.includes(m.id));
  return [
    {
      nombre: "vehiculo_id", etiqueta: "Vehículo", tipo: "select", requerido: true, completo: true,
      opciones: estado.datos.vehiculos.map((v) => ({
        valor: v.id,
        texto: `${v.placa} · ${v.marca} ${v.modelo} (${CATEGORIAS[v.categoria].nombre}) — ${porId(estado.datos.clientes, v.cliente_id)?.nombre ?? ""}`,
      })),
    },
    {
      nombre: "mecanico_id", etiqueta: "Líder del trabajo", tipo: "select", requerido: true, completo: true,
      opciones: mecanicos.map((m, i) => ({
        valor: m.id,
        texto: `${m.nombre} · ${m.nivel} (${m.creditos} cr.)${i === 0 && m.activo ? " · más fama" : ""}${m.activo ? "" : " (inactivo)"}`,
      })),
      porDefecto: mecanicos.find((m) => m.activo)?.id,
      ayuda: "Normalmente el de más fama. Debe tener nivel para el auto: Técnico para Premium, Maestro para Lujo",
    },
    {
      nombre: "equipo", etiqueta: "Equipo (además del líder)", tipo: "checks", completo: true,
      opciones: disponibles.map((m) => ({ valor: m.id, texto: `${m.nombre} · ${m.nivel}` })),
      ayuda: "Ven el trabajo; el líder les asigna tareas, los califica y puede reportarlos",
    },
    { nombre: "fecha_ingreso", etiqueta: "Fecha de ingreso", tipo: "date", requerido: true, max: hoy(), porDefecto: hoy() },
    { nombre: "mano_obra", etiqueta: "Mano de obra (L)", tipo: "number", min: 0, paso: 0.01, porDefecto: 0 },
    { nombre: "diagnostico", etiqueta: "Diagnóstico", tipo: "textarea", maxlength: 300, completo: true },
  ];
}

function formularioOrden(orden) {
  if (!estado.datos.vehiculos.length) {
    aviso("Primero registre un vehículo", "error");
    return;
  }
  abrirFormulario({
    titulo: orden ? `Editar orden #${orden.id}` : "Nueva orden de servicio",
    subtitulo: orden ? "" : "La orden empieza en estado «Recibido»",
    campos: camposOrden(orden),
    valores: orden ?? {},
    textoBoton: orden ? "Guardar cambios" : "Crear orden",
    enviar: async (datos) => {
      datos.mano_obra ??= 0;
      // Si el líder quedó marcado también en el equipo, se quita de ahí
      datos.equipo = datos.equipo.filter((id) => id !== datos.mecanico_id);
      const guardada = await api(orden ? `/ordenes/${orden.id}` : "/ordenes", { metodo: orden ? "PUT" : "POST", datos });
      aviso(orden ? "Orden actualizada" : `Orden #${guardada.id} creada`);
    },
  });

  // El líder elegido no se puede marcar también como miembro del equipo
  const lider = $("#campo-mecanico_id", dialogo);
  const sincronizarEquipo = () =>
    dialogo.querySelectorAll('input[name="equipo"]').forEach((casilla) => {
      const esLider = casilla.value === lider.value;
      casilla.disabled = esLider;
      if (esLider) casilla.checked = false;
      casilla.closest(".check").classList.toggle("deshabilitado", esLider);
    });
  lider.addEventListener("change", sincronizarEquipo);
  sincronizarEquipo();
}

/** Pide la calificación del trabajo antes de entregar. Resuelve con la clave elegida o "". */
function pedirCalificacion(orden, vehiculo, mecanico) {
  const categoria = vehiculo?.categoria ?? "estandar";
  return preguntar(`
    <form method="dialog" id="formulario-calificacion">
      <div class="dialogo-encabezado"><div>
        <h2>¿Cómo quedó el trabajo?</h2>
        <p>Al entregar la orden #${orden.id} se califica el trabajo de ${esc(mecanico?.nombre ?? "el mecánico")}, el líder. Eso suma o resta sus créditos (auto ${CATEGORIAS[categoria].nombre.toLowerCase()}).${orden.equipo.length
          ? ` Cada uno de los ${orden.equipo.length} del equipo recibe la mitad de esto y la otra mitad según lo calificó su líder.`
          : ""}</p>
      </div></div>
      <div class="dialogo-cuerpo"><div class="opciones-calificacion">
        ${CALIFICACIONES.map((c, i) => {
          const puntos = puntosPor(c.clave, categoria);
          return `<label class="opcion-calificacion">
            <input type="radio" name="calificacion" value="${esc(c.clave)}" ${i === 0 ? "checked" : ""} />
            <span class="principal"><strong>${esc(c.nombre)}</strong><span>${esc(c.texto)}</span></span>
            <span class="puntos ${puntos > 0 ? "positivo" : "negativo"}">${conSigno(puntos)} cr.</span>
          </label>`;
        }).join("")}
      </div></div>
      <div class="dialogo-pie">
        <button type="button" class="boton boton-secundario" data-respuesta="">Cancelar</button>
        <button type="button" class="boton boton-primario" id="confirmar-entrega">Entregar orden</button>
      </div>
    </form>`);
}

// El botón «Entregar orden» devuelve la opción marcada
confirmacion.addEventListener("click", (evento) => {
  if (evento.target.closest("#confirmar-entrega")) {
    confirmacion.close($("#formulario-calificacion input:checked", confirmacion)?.value ?? "");
  }
});

async function abrirOrden(id) {
  const resultado = await intentar(() =>
    Promise.all([api(`/ordenes/${id}`), api(`/ordenes/${id}/repuestos`), api(`/ordenes/${id}/total`)])
  );
  if (!resultado) return;
  const [orden, lineas, total] = resultado;
  const vehiculo = porId(estado.datos.vehiculos, orden.vehiculo_id);
  const cliente = vehiculo && porId(estado.datos.clientes, vehiculo.cliente_id);
  const mecanico = porId(estado.datos.mecanicos, orden.mecanico_id);
  const editable = ESTADOS_EDITABLES.includes(orden.estado);
  const posicion = ESTADOS.findIndex((e) => e.clave === orden.estado);
  const siguiente = ESTADOS[posicion + 1];
  const disponibles = estado.datos.repuestos.filter((r) => r.existencia > 0);

  abrirDialogo(`
    ${encabezadoDialogo(
      `Orden #${orden.id} <span class="placa">${esc(vehiculo?.placa ?? "—")}</span>`,
      `Ingresó el ${fecha(orden.fecha_ingreso)} · ${insigniaEstado(orden.estado)}`
    )}
    <div class="dialogo-cuerpo">
      <div class="pasos">${ESTADOS.map((e, i) =>
        `<span class="paso ${i < posicion ? "hecho" : ""} ${i === posicion ? "actual" : ""}">${e.nombre}</span>`).join("")}
      </div>

      <div class="datos-orden">
        <div class="dato"><small>Vehículo</small><strong>${esc(textoVehiculo(vehiculo))}</strong>${vehiculo ? insigniaCategoria(vehiculo.categoria) : ""}</div>
        <div class="dato"><small>Cliente</small><strong>${esc(cliente?.nombre ?? "—")}</strong><span class="mono">${esc(cliente?.telefono ?? "")}</span></div>
        <div class="dato"><small>Líder del trabajo</small><strong>${esc(mecanico?.nombre ?? "—")}</strong>${mecanico ? insigniaNivel(mecanico.creditos) : ""}</div>
        <div class="dato"><small>Mano de obra</small><strong>${dinero(orden.mano_obra)}</strong></div>
        <div class="dato completo"><small>Equipo</small>${orden.equipo.length
          ? `<div class="chips-equipo">${orden.equipo.map((mid) => {
              const m = porId(estado.datos.mecanicos, mid);
              return `<span class="chip-equipo"><span class="avatar">${esc(iniciales(m?.nombre))}</span>${esc(m?.nombre ?? "—")}</span>`;
            }).join("")}</div>`
          : `<span>Solo el líder</span>`}</div>
        <div class="dato completo"><small>Diagnóstico</small><strong>${esc(orden.diagnostico || "Sin diagnóstico")}</strong></div>
        ${orden.calificacion ? `<div class="dato completo"><small>Calificación del trabajo</small>${insigniaCalificacion(orden.calificacion)}</div>` : ""}
      </div>

      <h3 class="seccion-titulo">Repuestos usados <span class="conteo">${lineas.length}</span></h3>
      ${lineas.length ? `
      <div class="tabla-repuestos tabla-contenedor"><table>
        <thead><tr><th>Repuesto</th><th class="numero">Cant.</th><th class="numero">Precio</th><th class="numero">Subtotal</th>${editable ? "<th></th>" : ""}</tr></thead>
        <tbody>${lineas.map((l) => `
          <tr><td>${esc(l.repuesto)}</td><td class="numero">${l.cantidad}</td><td class="numero">${dinero(l.precio)}</td><td class="numero">${dinero(l.subtotal)}</td>
          ${editable ? `<td class="acciones-fila"><button type="button" class="boton boton-icono peligro" data-quitar="${l.id}" aria-label="Quitar ${esc(l.repuesto)}">${icono("borrar")}</button></td>` : ""}</tr>`).join("")}
        </tbody></table></div>` : `<p class="vacio-chico" style="padding-left:0">Esta orden todavía no usa repuestos.</p>`}

      ${editable ? `
      <form id="formulario-repuesto" class="agregar-repuesto">
        <div class="campo"><label for="repuesto-orden">Agregar repuesto</label>
          <select id="repuesto-orden" required>
            <option value="">Seleccione…</option>
            ${disponibles.map((r) => `<option value="${r.id}">${esc(r.nombre)} · ${dinero(r.precio)} · quedan ${r.existencia}</option>`).join("")}
          </select></div>
        <div class="campo"><label for="cantidad-orden">Cantidad</label><input id="cantidad-orden" type="number" min="1" value="1" required /></div>
        <button type="submit" class="boton boton-secundario">${icono("mas")} Agregar</button>
      </form>` : ""}

      <div class="totales">
        <div><span>Mano de obra</span><span>${dinero(total.mano_obra)}</span></div>
        <div><span>Repuestos</span><span>${dinero(total.repuestos)}</span></div>
        <div class="total"><span>Total</span><span>${dinero(total.total)}</span></div>
      </div>
    </div>
    <div class="dialogo-pie">
      ${editable ? `
        <button type="button" class="boton boton-peligro separar" id="eliminar-orden">${icono("borrar")} Eliminar</button>
        <button type="button" class="boton boton-secundario" id="editar-orden">${icono("editar")} Editar</button>` : `<span class="texto-tenue separar">${orden.estado === "entregado" ? "Orden cerrada" : "Ya no se puede modificar"}</span>`}
      ${siguiente ? `<button type="button" class="boton boton-primario" id="avanzar-orden">${siguiente.clave === "entregado" ? "Calificar y entregar" : `Pasar a «${siguiente.nombre}»`} ${icono("flecha")}</button>` : ""}
    </div>`, (raiz) => {
    $("#avanzar-orden", raiz)?.addEventListener("click", async () => {
      let datos;
      if (siguiente.clave === "entregado") {
        const calificacion = await pedirCalificacion(orden, vehiculo, mecanico);
        if (!calificacion) return;
        datos = { calificacion };
      }
      if (await intentar(() => api(`/ordenes/${id}/avanzar`, { metodo: "POST", datos }))) {
        aviso(siguiente.clave === "entregado" ? `Orden #${id} entregada y calificada` : `Orden #${id}: ${siguiente.nombre}`);
        await refrescar();
        abrirOrden(id);
      }
    });
    $("#editar-orden", raiz)?.addEventListener("click", () => formularioOrden(orden));
    $("#eliminar-orden", raiz)?.addEventListener("click", async () => {
      const seguro = await confirmar({
        titulo: `¿Eliminar la orden #${id}?`,
        texto: "Los repuestos que usaba vuelven al inventario. Esta acción no se puede deshacer.",
      });
      if (seguro && (await intentar(() => api(`/ordenes/${id}`, { metodo: "DELETE" })))) {
        dialogo.close();
        aviso("Orden eliminada");
        await refrescar();
      }
    });
    raiz.querySelectorAll("[data-quitar]").forEach((boton) =>
      boton.addEventListener("click", async () => {
        if (await intentar(() => api(`/ordenes/${id}/repuestos/${boton.dataset.quitar}`, { metodo: "DELETE" }))) {
          aviso("Repuesto devuelto al inventario");
          await refrescar();
          abrirOrden(id);
        }
      })
    );
    $("#formulario-repuesto", raiz)?.addEventListener("submit", async (evento) => {
      evento.preventDefault();
      const datos = { repuesto_id: Number($("#repuesto-orden", raiz).value), cantidad: Number($("#cantidad-orden", raiz).value) };
      if (!datos.repuesto_id) return aviso("Seleccione un repuesto", "error");
      if (await intentar(() => api(`/ordenes/${id}/repuestos`, { metodo: "POST", datos }))) {
        aviso("Repuesto agregado a la orden");
        await refrescar();
        abrirOrden(id);
      }
    });
  });
}

// ===================== Personal: resumen =====================
function pintarResumen() {
  const { clientes, vehiculos, mecanicos, repuestos, ordenes } = estado.datos;
  const activas = ordenesActivas();
  const listas = ordenes.filter((o) => o.estado === "listo");
  const bajos = repuestos.filter((r) => r.existencia <= POCA_EXISTENCIA).sort((a, b) => a.existencia - b.existencia);
  const enCurso = [...activas].sort((a, b) => ESTADOS.findIndex((e) => e.clave === b.estado) - ESTADOS.findIndex((e) => e.clave === a.estado) || b.id - a.id);
  const total = ordenes.length || 1;

  const filaOrden = (o) => {
    const vehiculo = porId(estado.datos.vehiculos, o.vehiculo_id);
    return `<li><button type="button" class="fila-lista" data-orden="${o.id}">
      <span class="placa">${esc(vehiculo?.placa ?? "—")}</span>
      <span class="principal"><strong>${esc(textoVehiculo(vehiculo))}</strong><span>${esc(o.diagnostico || "Sin diagnóstico")}</span></span>
      ${insigniaEstado(o.estado)}</button></li>`;
  };

  $("#vista").innerHTML = `
    <div class="estadisticas">
      <div class="panel estadistica"><span class="etiqueta">${icono("ordenes")} En el taller</span><span class="valor">${activas.length}</span><span class="detalle">órdenes sin entregar</span></div>
      <div class="panel estadistica"><span class="etiqueta">${icono("check")} Listas</span><span class="valor">${listas.length}</span><span class="detalle">esperan al cliente</span></div>
      <div class="panel estadistica"><span class="etiqueta">${icono("clientes")} Clientes</span><span class="valor">${clientes.length}</span><span class="detalle">${vehiculos.length} vehículos registrados</span></div>
      <div class="panel estadistica ${bajos.length ? "alerta" : ""}"><span class="etiqueta">${icono("repuestos")} Poca existencia</span><span class="valor">${bajos.length}</span><span class="detalle">de ${repuestos.length} repuestos</span></div>
    </div>

    <div class="rejilla-resumen">
      <div class="columna">
        <section class="panel">
          <div class="panel-encabezado"><h2>Órdenes por estado</h2><a href="#/ordenes" class="conteo">Ver tablero →</a></div>
          <div class="panel-cuerpo">
            <div class="barra-estados">${ESTADOS.map((e) => {
              const n = ordenes.filter((o) => o.estado === e.clave).length;
              return n ? `<span style="width:${(n / total) * 100}%;background:${e.color}" title="${e.nombre}: ${n}"></span>` : "";
            }).join("")}</div>
            <div class="leyenda">${ESTADOS.map((e) => `
              <div><strong>${ordenes.filter((o) => o.estado === e.clave).length}</strong><span><span class="punto" style="background:${e.color}"></span>${e.nombre}</span></div>`).join("")}
            </div>
          </div>
        </section>

        <section class="panel">
          <div class="panel-encabezado"><h2>Trabajo en curso</h2><span class="conteo">${enCurso.length}</span></div>
          ${enCurso.length ? `<ul class="lista">${enCurso.slice(0, 8).map(filaOrden).join("")}</ul>` : `<p class="vacio-chico">No hay vehículos en el taller.</p>`}
        </section>
      </div>

      <div class="columna">
        <section class="panel">
          <div class="panel-encabezado"><h2>Inventario bajo</h2><a href="#/repuestos" class="conteo">Repuestos →</a></div>
          ${bajos.length ? `<ul class="lista">${bajos.map((r) => `
            <li><div class="fila-lista"><span class="principal"><strong>${esc(r.nombre)}</strong><span>${dinero(r.precio)} c/u</span></span>${insigniaExistencia(r.existencia)}</div></li>`).join("")}</ul>`
            : `<p class="vacio-chico">Todos los repuestos tienen buena existencia.</p>`}
        </section>

        <section class="panel">
          <div class="panel-encabezado"><h2>Mecánicos</h2><a href="#/mecanicos" class="conteo">Ver todos →</a></div>
          <ul class="lista">${mecanicos.filter((m) => m.activo).sort((a, b) => b.creditos - a.creditos).map((m) => {
            const carga = cantidad(activas, "mecanico_id", m.id);
            return `<li><div class="fila-lista"><span class="avatar">${esc(iniciales(m.nombre))}</span>
              <span class="principal"><strong>${esc(m.nombre)}</strong><span>${m.creditos} créditos · ${carga} en curso</span></span>
              ${insigniaNivel(m.creditos)}</div></li>`;
          }).join("") || `<li class="vacio-chico">No hay mecánicos activos.</li>`}</ul>
        </section>
      </div>
    </div>`;

  conectarTarjetasOrden();
}

// ===================== Área del mecánico: trabajos =====================
const GRUPOS_TRABAJO = [
  { estado: "en reparacion", titulo: "En reparación", vacio: "No tiene vehículos en reparación." },
  { estado: "recibido", titulo: "Por empezar", vacio: "No tiene trabajos nuevos." },
  { estado: "listo", titulo: "Listos, esperando entrega", vacio: "Ninguno espera entrega." },
  { estado: "entregado", titulo: "Entregados", vacio: "Todavía no ha entregado trabajos." },
];

function tarjetaTrabajo(t) {
  const categoria = t.categoria !== "estandar" ? insigniaCategoria(t.categoria) : "";
  return `
    <button type="button" class="tarjeta-orden" data-trabajo="${t.id}">
      <div class="arriba"><span class="placa">${esc(t.placa)}</span>${categoria}<span class="numero-orden">#${t.id}</span></div>
      <div class="vehiculo">${esc(t.marca)} ${esc(t.modelo)} ${t.anio}</div>
      <div class="diagnostico">${esc(t.diagnostico || "Sin diagnóstico")}</div>
      <div class="abajo">${t.soy_lider
        ? `<span class="insignia insignia-lujo">${icono("estrella")}Líder</span>`
        : `<span>Equipo de ${esc(t.lider)}</span>`}
        ${t.calificacion ? insigniaCalificacion(t.calificacion) : `<span>${fecha(t.fecha_ingreso)}</span>`}</div>
    </button>`;
}

function pintarTrabajos() {
  const { trabajos, perfil } = estado.datos;
  const cuantos = (clave) => trabajos.filter((t) => t.estado === clave).length;

  $("#vista").innerHTML = `
    <div class="estadisticas">
      <div class="panel estadistica"><span class="etiqueta">${icono("mecanicos")} En reparación</span><span class="valor">${cuantos("en reparacion")}</span><span class="detalle">trabajando ahora</span></div>
      <div class="panel estadistica"><span class="etiqueta">${icono("ordenes")} Por empezar</span><span class="valor">${cuantos("recibido")}</span><span class="detalle">asignados por recepción</span></div>
      <div class="panel estadistica"><span class="etiqueta">${icono("check")} Listos</span><span class="valor">${cuantos("listo")}</span><span class="detalle">esperan entrega</span></div>
      <a href="#/perfil" class="panel estadistica enlace-estadistica"><span class="etiqueta">${icono("estrella")} Créditos</span><span class="valor">${perfil.creditos}</span><span class="detalle">${insigniaNivel(perfil.creditos)}</span></a>
    </div>
    ${GRUPOS_TRABAJO.map((g) => {
      const grupo = trabajos.filter((t) => t.estado === g.estado);
      return `
      <section class="grupo-trabajos">
        <h2><span>${esc(g.titulo)}</span> <span class="conteo">${grupo.length}</span></h2>
        ${grupo.length ? `<div class="rejilla-trabajos">${grupo.map(tarjetaTrabajo).join("")}</div>` : `<p class="vacio-chico">${esc(g.vacio)}</p>`}
      </section>`;
    }).join("")}`;

  $("#vista").querySelectorAll("[data-trabajo]").forEach((elemento) =>
    elemento.addEventListener("click", () => abrirTrabajo(Number(elemento.dataset.trabajo)))
  );
}

/** Sección «Equipo» del trabajo. El líder, mientras dura el trabajo, asigna tareas, califica y reporta. */
function seccionEquipo(t) {
  const dirige = t.puedo_dirigir;
  const miembros = t.equipo.filter((m) => !m.es_lider);
  let nota = "";
  if (dirige) {
    nota = `<p class="nota-lider">${icono("estrella")}<span>Usted es el <strong>líder de este trabajo</strong>: asigne una tarea a cada miembro, califique su trabajo y repórtelos si hace falta. Estos permisos terminan cuando marque el trabajo como listo.</span></p>`;
  } else if (t.soy_lider) {
    nota = `<p class="nota-neutra">${icono("check")}<span>Usted lideró este trabajo. Sus permisos de líder terminaron al finalizarlo.</span></p>`;
  } else if (ESTADOS_EDITABLES.includes(t.estado)) {
    nota = `<p class="nota-neutra">${icono("perfil")}<span>El líder de este trabajo es <strong>${esc(t.lider)}</strong>. Solo él puede empezarlo o marcarlo como listo.</span></p>`;
  }

  const filas = t.equipo.map((m) => {
    const estadoMiembro = m.es_lider
      ? `<span class="insignia insignia-lujo">${icono("estrella")}Líder</span>`
      : m.calificacion ? insigniaCalificacion(m.calificacion) : `<span class="insignia insignia-neutra">Sin calificar</span>`;
    const cabecera = `<div class="miembro-cabecera"><span class="avatar">${esc(iniciales(m.nombre))}</span>
      <div class="principal"><strong>${esc(m.nombre)}</strong><span>${esc(m.especialidad || "Sin especialidad")} · ${esc(m.nivel)}</span></div>
      ${estadoMiembro}</div>`;
    if (m.es_lider) return `<li class="miembro">${cabecera}</li>`;
    if (!dirige) return `<li class="miembro">${cabecera}<p class="tarea">${m.tarea ? `Tarea: ${esc(m.tarea)}` : "Sin tarea asignada"}</p></li>`;
    return `<li class="miembro">${cabecera}
      <form class="form-miembro" data-miembro="${m.mecanico_id}">
        <input name="tarea" maxlength="200" placeholder="Tarea que le asigna" value="${esc(m.tarea)}" aria-label="Tarea de ${esc(m.nombre)}" />
        <select name="calificacion" aria-label="Calificación de ${esc(m.nombre)}">
          <option value="">Sin calificar</option>
          ${CALIFICACIONES.map((c) => `<option value="${esc(c.clave)}" ${c.clave === m.calificacion ? "selected" : ""}>${esc(c.nombre)}</option>`).join("")}
        </select>
        <button type="submit" class="boton boton-secundario">Guardar</button>
      </form></li>`;
  }).join("");

  let reportes = "";
  if (t.soy_lider) {
    reportes = `
      <h3 class="seccion-titulo">Reportes del equipo <span class="conteo">${t.reportes_equipo.length}</span></h3>
      ${t.reportes_equipo.length
        ? `<ul class="lista-reportes-equipo">${t.reportes_equipo.map((r) => `
            <li><strong>${esc(r.sobre_mecanico)} · ${esc(r.titulo)}</strong><p>${esc(r.descripcion)}</p>
              <span class="texto-tenue">${fechaHora(r.fecha)}</span></li>`).join("")}</ul>`
        : `<p class="vacio-chico" style="padding-left:0">No ha reportado a ningún miembro.</p>`}
      ${dirige && miembros.length ? `
      <form id="formulario-reporte-equipo" class="reporte-equipo" novalidate>
        <div class="rejilla-campos">
          <div class="campo"><label for="reporte-miembro">Miembro</label>
            <select id="reporte-miembro" required><option value="">Seleccione…</option>
              ${miembros.map((m) => `<option value="${m.mecanico_id}">${esc(m.nombre)}</option>`).join("")}</select></div>
          <div class="campo"><label for="reporte-titulo">Título</label><input id="reporte-titulo" required minlength="3" maxlength="100" /></div>
          <div class="campo completo"><label for="reporte-descripcion">¿Qué pasó?</label>
            <textarea id="reporte-descripcion" required minlength="5" maxlength="1000"></textarea></div>
        </div>
        <p class="mensaje-error" id="error-reporte-equipo" aria-live="polite"></p>
        <button type="submit" class="boton boton-secundario">${icono("reporte")} Reportar a recepción</button>
      </form>` : ""}`;
  }

  return `${nota}
    <h3 class="seccion-titulo">Equipo <span class="conteo">${t.equipo.length}</span></h3>
    <ul class="lista-equipo">${filas}</ul>
    ${reportes}`;
}

async function abrirTrabajo(id) {
  const trabajo = await intentar(() => api(`/mecanico/trabajos/${id}`));
  if (!trabajo) return;
  const posicion = ESTADOS.findIndex((e) => e.clave === trabajo.estado);
  const activo = ESTADOS_EDITABLES.includes(trabajo.estado);

  let final = "";
  if (trabajo.estado === "listo") {
    final = `<p class="nota-info">${icono("check")} Recepción ya fue avisada. El vehículo espera que lo entreguen al cliente.</p>`;
  } else if (trabajo.estado === "entregado") {
    final = `<div class="resultado-trabajo">
      <div><small>Calificación de recepción</small>${trabajo.calificacion ? insigniaCalificacion(trabajo.calificacion) : "—"}</div>
      <div><small>Créditos por este trabajo</small><strong class="${trabajo.creditos > 0 ? "positivo" : trabajo.creditos < 0 ? "negativo" : ""}">${trabajo.creditos == null ? "—" : conSigno(trabajo.creditos)}</strong></div>
    </div>`;
  }

  abrirDialogo(`
    ${encabezadoDialogo(
      `Orden #${trabajo.id} <span class="placa">${esc(trabajo.placa)}</span>`,
      `Ingresó el ${fecha(trabajo.fecha_ingreso)} · ${insigniaEstado(trabajo.estado)}`
    )}
    <div class="dialogo-cuerpo">
      <div class="pasos">${ESTADOS.map((e, i) =>
        `<span class="paso ${i < posicion ? "hecho" : ""} ${i === posicion ? "actual" : ""}">${e.nombre}</span>`).join("")}
      </div>
      <div class="datos-orden">
        <div class="dato"><small>Vehículo</small><strong>${esc(trabajo.marca)} ${esc(trabajo.modelo)} ${trabajo.anio}</strong>${insigniaCategoria(trabajo.categoria)}</div>
        <div class="dato"><small>Cliente</small><strong>${esc(trabajo.cliente)}</strong></div>
        <div class="dato completo"><small>Diagnóstico de recepción</small><strong>${esc(trabajo.diagnostico || "Sin diagnóstico")}</strong></div>
      </div>

      <h3 class="seccion-titulo">Repuestos asignados <span class="conteo">${trabajo.repuestos.length}</span></h3>
      ${trabajo.repuestos.length
        ? `<ul class="lista-repuestos">${trabajo.repuestos.map((r) => `<li><span>${esc(r.repuesto)}</span><strong>× ${r.cantidad}</strong></li>`).join("")}</ul>`
        : `<p class="vacio-chico" style="padding-left:0">Recepción todavía no asignó repuestos.</p>`}

      ${seccionEquipo(trabajo)}

      ${activo ? `
      <div class="campo mensaje-recepcion">
        <label for="mensaje-recepcion">Mensaje para recepción</label>
        <textarea id="mensaje-recepcion" maxlength="300" placeholder="Ejemplo: falta la bomba de agua, llega mañana"></textarea>
        <span class="ayuda">Con «Enviar aviso» cuenta cómo va sin terminar. Al marcarlo listo, el mensaje va como nota.</span>
      </div>` : final}
    </div>
    <div class="dialogo-pie">
      ${activo ? `<button type="button" class="boton boton-secundario separar" id="enviar-aviso">${icono("enviar")} Enviar aviso</button>` : `<button type="button" class="boton boton-secundario" data-cerrar>Cerrar</button>`}
      ${trabajo.soy_lider && trabajo.estado === "recibido" ? `<button type="button" class="boton boton-primario" id="empezar-trabajo">${icono("mecanicos")} Empezar reparación</button>` : ""}
      ${trabajo.soy_lider && trabajo.estado === "en reparacion" ? `<button type="button" class="boton boton-primario" id="marcar-listo">${icono("check")} Marcar como listo</button>` : ""}
    </div>`, (raiz) => {
    const mensaje = () => $("#mensaje-recepcion", raiz)?.value.trim() ?? "";
    $("#empezar-trabajo", raiz)?.addEventListener("click", async () => {
      if (await intentar(() => api(`/mecanico/trabajos/${id}/empezar`, { metodo: "POST" }))) {
        aviso(`Orden #${id}: en reparación`);
        await refrescar();
        abrirTrabajo(id);
      }
    });
    $("#marcar-listo", raiz)?.addEventListener("click", async () => {
      const nota = mensaje();
      if (await intentar(() => api(`/mecanico/trabajos/${id}/listo`, { metodo: "POST", datos: { nota: nota || null } }))) {
        aviso("Trabajo listo: recepción fue notificada");
        await refrescar();
        abrirTrabajo(id);
      }
    });
    $("#enviar-aviso", raiz)?.addEventListener("click", async () => {
      const texto = mensaje();
      if (texto.length < 3) {
        aviso("Escriba el mensaje para recepción", "error");
        $("#mensaje-recepcion", raiz).focus();
        return;
      }
      if (await intentar(() => api(`/mecanico/trabajos/${id}/aviso`, { metodo: "POST", datos: { mensaje: texto } }))) {
        aviso("Aviso enviado a recepción");
        $("#mensaje-recepcion", raiz).value = "";
      }
    });

    // Solo aparecen para el líder mientras dura el trabajo
    raiz.querySelectorAll(".form-miembro").forEach((formulario) =>
      formulario.addEventListener("submit", async (evento) => {
        evento.preventDefault();
        const datos = {
          tarea: formulario.elements.tarea.value.trim() || null,
          calificacion: formulario.elements.calificacion.value || null,
        };
        const ruta = `/mecanico/trabajos/${id}/equipo/${formulario.dataset.miembro}`;
        if (await intentar(() => api(ruta, { metodo: "PUT", datos }))) {
          aviso("Equipo actualizado");
          abrirTrabajo(id);
        }
      })
    );
    $("#formulario-reporte-equipo", raiz)?.addEventListener("submit", async (evento) => {
      evento.preventDefault();
      const formulario = evento.currentTarget;
      const error = $("#error-reporte-equipo", raiz);
      error.textContent = "";
      if (!formularioValido(formulario, error)) return;
      const datos = {
        sobre_mecanico_id: Number($("#reporte-miembro", raiz).value),
        titulo: $("#reporte-titulo", raiz).value.trim(),
        descripcion: $("#reporte-descripcion", raiz).value.trim(),
      };
      if (await intentar(() => api(`/mecanico/trabajos/${id}/reportes-equipo`, { metodo: "POST", datos }))) {
        aviso("Reporte enviado a recepción");
        abrirTrabajo(id);
      }
    });
  });
}

// ===================== Área del mecánico: reportes =====================
function camposReporte() {
  const activos = estado.datos.trabajos.filter((t) => t.estado !== "entregado");
  return [
    {
      nombre: "tipo", etiqueta: "Tipo de reporte", tipo: "select", numerico: false, requerido: true,
      opciones: Object.entries(TIPOS_REPORTE).map(([valor, texto]) => ({ valor, texto })),
    },
    {
      nombre: "orden_id", etiqueta: "Orden relacionada", tipo: "select", textoVacio: "Ninguna",
      opciones: activos.map((t) => ({ valor: t.id, texto: `#${t.id} · ${t.placa} ${t.marca} ${t.modelo}` })),
    },
    { nombre: "titulo", etiqueta: "Título", requerido: true, minlength: 3, maxlength: 100, completo: true },
    { nombre: "descripcion", etiqueta: "¿Qué pasó?", tipo: "textarea", requerido: true, minlength: 5, maxlength: 1000, completo: true },
  ];
}

function pintarReportes() {
  const { reportes } = estado.datos;
  const campos = camposReporte();
  $("#vista").innerHTML = `
    <div class="rejilla-dos">
      <section class="panel">
        <div class="panel-encabezado"><h2>Nuevo reporte</h2></div>
        <form id="formulario-reporte" class="panel-cuerpo" novalidate>
          <div class="rejilla-campos">${campos.map((c) => campoHTML(c, c.porDefecto)).join("")}</div>
          <p class="mensaje-error" id="error-reporte" aria-live="polite"></p>
          <button type="submit" class="boton boton-primario">${icono("enviar")} Enviar a recepción</button>
        </form>
      </section>
      <section class="panel">
        <div class="panel-encabezado"><h2>Mis reportes</h2><span class="conteo">${reportes.length}</span></div>
        ${reportes.length ? `<ul class="lista">${reportes.map((r) => `
          <li class="reporte">
            <div class="reporte-arriba">
              <span class="insignia insignia-neutra">${esc(TIPOS_REPORTE[r.tipo])}</span>
              <span class="insignia ${r.estado === "resuelto" ? "insignia-ok" : "insignia-baja"}">${r.estado === "resuelto" ? "Resuelto" : "Abierto"}</span>
            </div>
            <strong>${esc(r.titulo)}</strong>
            <p>${esc(r.descripcion)}</p>
            <span class="texto-tenue">${fechaHora(r.fecha)}${r.orden_id ? ` · Orden #${r.orden_id}` : ""}</span>
          </li>`).join("")}</ul>`
          : `<div class="vacio">${icono("reporte")}<strong>Sin reportes</strong><span>Si algo falla en el taller, avise desde aquí.</span></div>`}
      </section>
    </div>`;

  const formulario = $("#formulario-reporte");
  formulario.addEventListener("submit", async (evento) => {
    evento.preventDefault();
    const error = $("#error-reporte");
    error.textContent = "";
    if (!formularioValido(formulario, error)) return;
    const boton = formulario.querySelector("[type=submit]");
    boton.disabled = true;
    try {
      await api("/mecanico/reportes", { metodo: "POST", datos: leerFormulario(formulario, campos) });
      aviso("Reporte enviado a recepción");
      await refrescar();
    } catch (e) {
      if (!(e instanceof ErrorSilencioso)) error.textContent = e.message;
    } finally {
      boton.disabled = false;
    }
  });
}

// ===================== Área del mecánico: perfil =====================
function pintarPerfil() {
  const p = estado.datos.perfil;
  const nivel = p.nivel;
  const progreso = nivel.siguiente
    ? Math.min(100, ((p.creditos - nivel.minimo) / (nivel.siguiente.minimo - nivel.minimo)) * 100)
    : 100;
  const totalCalificados = Object.values(p.estadisticas.calificaciones).reduce((a, b) => a + b, 0);

  $("#vista").innerHTML = `
    <section class="panel perfil-cabecera">
      <span class="avatar avatar-grande">${esc(iniciales(p.nombre))}</span>
      <div class="principal">
        <h2>${esc(p.nombre)}</h2>
        <span class="texto-tenue">${esc(p.especialidad || "Sin especialidad")} · usuario <span class="mono">${esc(p.usuario)}</span></span>
      </div>
      ${insigniaNivel(p.creditos)}
    </section>

    <div class="rejilla-dos">
      <div class="columna">
        <section class="panel">
          <div class="panel-encabezado"><h2>Créditos y fama</h2></div>
          <div class="panel-cuerpo">
            <div class="creditos-total">${icono("estrella")}<span class="creditos-numero">${p.creditos}</span><span class="texto-tenue">créditos</span></div>
            <div class="progreso" role="progressbar" aria-valuemin="0" aria-valuemax="100" aria-valuenow="${Math.round(progreso)}"><span style="width:${progreso}%"></span></div>
            <p class="texto-tenue progreso-texto">${nivel.siguiente
              ? `Le faltan <strong>${nivel.siguiente.minimo - p.creditos}</strong> créditos para ser <strong>${esc(nivel.siguiente.nombre)}</strong>.`
              : "Llegó al nivel más alto del taller."}</p>

            <h3 class="seccion-titulo">Autos que puede trabajar</h3>
            <div class="chips-categoria">${NIVELES.map((n) => {
              const abierta = nivel.categorias.includes(n.categoria);
              return `<div class="chip-categoria ${abierta ? "" : "bloqueada"}">
                ${icono(abierta ? "check" : "candado")}
                <strong>${CATEGORIAS[n.categoria].nombre}</strong>
                <span>${abierta ? "Disponible" : `Desde ${n.minimo} cr. (${n.nombre})`}</span>
              </div>`;
            }).join("")}</div>

            <h3 class="seccion-titulo">Cómo se ganan</h3>
            <table class="tabla-puntos">
              <thead><tr><th>Calificación</th>${Object.values(CATEGORIAS).map((c) => `<th class="numero">${c.nombre}</th>`).join("")}</tr></thead>
              <tbody>${CALIFICACIONES.map((c) => `<tr><td>${esc(c.nombre)}</td>${Object.keys(CATEGORIAS).map((cat) => {
                const puntos = puntosPor(c.clave, cat);
                return `<td class="numero ${puntos > 0 ? "positivo" : "negativo"}">${conSigno(puntos)}</td>`;
              }).join("")}</tr>`).join("")}</tbody>
            </table>
          </div>
        </section>

        <section class="panel">
          <div class="panel-encabezado"><h2>Cambiar contraseña</h2></div>
          <form id="formulario-password" class="panel-cuerpo" novalidate>
            <div class="rejilla-campos">
              <div class="campo completo"><label for="password-actual">Contraseña actual</label><input id="password-actual" type="password" autocomplete="current-password" required /></div>
              <div class="campo"><label for="password-nueva">Nueva contraseña</label><input id="password-nueva" type="password" autocomplete="new-password" required minlength="6" maxlength="72" /></div>
              <div class="campo"><label for="password-repetida">Repita la nueva</label><input id="password-repetida" type="password" autocomplete="new-password" required minlength="6" maxlength="72" /></div>
            </div>
            <p class="mensaje-error" id="error-password" aria-live="polite"></p>
            <button type="submit" class="boton boton-secundario">Guardar contraseña</button>
          </form>
        </section>
      </div>

      <div class="columna">
        <section class="panel">
          <div class="panel-encabezado"><h2>Datos personales</h2></div>
          <dl class="datos-personales">
            <div><dt>Teléfono</dt><dd class="mono">${esc(p.telefono || "—")}</dd></div>
            <div><dt>Correo</dt><dd>${esc(p.correo || "—")}</dd></div>
            <div><dt>En el taller desde</dt><dd>${p.fecha_contratacion ? `${fecha(p.fecha_contratacion)} · ${antiguedad(p.fecha_contratacion)}` : "—"}</dd></div>
            <div><dt>Especialidad</dt><dd>${esc(p.especialidad || "—")}</dd></div>
          </dl>
          <p class="texto-tenue nota-datos">Si algún dato está mal, pida a recepción que lo corrija.</p>
        </section>

        <section class="panel">
          <div class="panel-encabezado"><h2>Mis números</h2></div>
          <div class="panel-cuerpo">
            <div class="leyenda">
              <div><strong>${p.estadisticas.entregados}</strong><span>Entregados</span></div>
              <div><strong>${p.estadisticas.en_reparacion + p.estadisticas.por_empezar}</strong><span>Pendientes</span></div>
            </div>
            <ul class="barras-calificacion">${CALIFICACIONES.map((c) => {
              const n = p.estadisticas.calificaciones[c.clave] ?? 0;
              return `<li><span>${esc(c.nombre)}</span><span class="barra"><span class="${c.puntos > 0 ? "positivo" : "negativo"}" style="width:${totalCalificados ? (n / totalCalificados) * 100 : 0}%"></span></span><strong>${n}</strong></li>`;
            }).join("")}</ul>
          </div>
        </section>

        <section class="panel">
          <div class="panel-encabezado"><h2>Historial de créditos</h2></div>
          ${p.historial.length ? `<ul class="lista">${p.historial.map((m) => `
            <li><div class="fila-lista"><span class="principal"><strong>${esc(m.motivo)}</strong><span>${fechaHora(m.fecha)}</span></span>
              <strong class="${m.puntos > 0 ? "positivo" : m.puntos < 0 ? "negativo" : "texto-tenue"}">${conSigno(m.puntos)}</strong></div></li>`).join("")}</ul>`
            : `<p class="vacio-chico">Todavía no tiene movimientos.</p>`}
        </section>
      </div>
    </div>`;

  const formulario = $("#formulario-password");
  formulario.addEventListener("submit", async (evento) => {
    evento.preventDefault();
    const error = $("#error-password");
    error.textContent = "";
    if (!formularioValido(formulario, error)) return;
    const nueva = $("#password-nueva").value;
    if (nueva !== $("#password-repetida").value) {
      error.textContent = "Las contraseñas nuevas no coinciden";
      return;
    }
    const datos = { password_actual: $("#password-actual").value, password_nueva: nueva };
    if (await intentar(() => api("/auth/cambiar-password", { metodo: "POST", datos }))) {
      aviso("Contraseña actualizada");
      formulario.reset();
    }
  });
}

// ===================== Navegación =====================
const VISTAS_PERSONAL = {
  resumen: { titulo: "Resumen", subtitulo: "Así está el taller hoy", icono: "resumen", pintar: pintarResumen },
  ordenes: { titulo: "Órdenes", subtitulo: "Tablero de órdenes de servicio", icono: "ordenes", pintar: pintarOrdenes,
    boton: "Nueva orden", nuevo: () => formularioOrden(), cuenta: () => ordenesActivas().length },
  clientes: { titulo: "Clientes", subtitulo: "Personas que traen sus vehículos", icono: "clientes" },
  vehiculos: { titulo: "Vehículos", subtitulo: "Vehículos registrados, su categoría y sus dueños", icono: "vehiculos" },
  mecanicos: { titulo: "Mecánicos", subtitulo: "Equipo de trabajo, niveles y créditos", icono: "mecanicos" },
  repuestos: { titulo: "Repuestos", subtitulo: "Inventario y precios", icono: "repuestos" },
  usuarios: { titulo: "Cuentas", subtitulo: "Accesos que entrega la empresa", icono: "usuarios", soloAdministrador: true },
};
for (const clave of Object.keys(MODULOS)) {
  VISTAS_PERSONAL[clave].pintar = () => pintarModulo(clave);
  VISTAS_PERSONAL[clave].boton = nuevoTexto(MODULOS[clave]);
  VISTAS_PERSONAL[clave].nuevo = () => formularioModulo(clave);
  VISTAS_PERSONAL[clave].cuenta = () => estado.datos[clave].length;
}

const VISTAS_MECANICO = {
  trabajos: { titulo: "Mis trabajos", subtitulo: "Vehículos que le asignó recepción", icono: "ordenes", pintar: pintarTrabajos,
    cuenta: () => estado.datos.trabajos.filter((t) => ESTADOS_EDITABLES.includes(t.estado)).length },
  reportes: { titulo: "Reportes", subtitulo: "Avise a recepción lo que pase con el equipo o el taller", icono: "reporte", pintar: pintarReportes,
    cuenta: () => estado.datos.reportes.filter((r) => r.estado === "abierto").length },
  perfil: { titulo: "Mi perfil", subtitulo: "Sus datos, su nivel y sus créditos", icono: "perfil", pintar: pintarPerfil },
};

function pintarMenu() {
  $("#menu").innerHTML = Object.entries(estado.vistas).map(([clave, vista]) => {
    const cuenta = vista.cuenta?.();
    return `<a href="#/${clave}" class="${clave === estado.vista ? "activo" : ""}" ${clave === estado.vista ? 'aria-current="page"' : ""}>
      ${icono(vista.icono)}<span>${vista.titulo}</span>${cuenta !== undefined ? `<span class="contador">${cuenta}</span>` : ""}</a>`;
  }).join("");
}

function pintarVista() {
  const vista = estado.vistas[estado.vista];
  document.title = `${vista.titulo} · Taller Mecánico`;
  $("#titulo-vista").textContent = vista.titulo;
  $("#subtitulo-vista").textContent = vista.subtitulo;
  $("#acciones-vista").innerHTML = vista.boton
    ? `<button type="button" class="boton boton-primario" id="boton-nuevo">${icono("mas")} ${esc(vista.boton)}</button>`
    : "";
  $("#boton-nuevo")?.addEventListener("click", vista.nuevo);
  pintarMenu();
  vista.pintar();
}

async function refrescar() {
  await intentar(cargarDatos);
  pintarVista();
}

function irSegunDireccion() {
  const clave = location.hash.replace("#/", "");
  const nueva = estado.vistas[clave] ? clave : Object.keys(estado.vistas)[0];
  if (nueva !== estado.vista) estado.busqueda = "";
  estado.vista = nueva;
  if (!$("#vista-app").hidden) {
    pintarVista();
    window.scrollTo(0, 0);
  }
}
window.addEventListener("hashchange", irSegunDireccion);

// ===================== Sesión =====================
async function entrar(usuario, clave) {
  const respuesta = await api("/auth/login", { metodo: "POST", formulario: { username: usuario, password: clave } });
  estado.token = respuesta.access_token;
  guardar("taller-token", estado.token);
  await mostrarApp();
}

async function mostrarApp() {
  estado.yo = await api("/auth/yo");
  if (esMecanico()) {
    estado.vistas = VISTAS_MECANICO;
  } else {
    estado.vistas = Object.fromEntries(
      Object.entries(VISTAS_PERSONAL).filter(([, v]) => !v.soloAdministrador || estado.yo.rol === "administrador")
    );
  }
  await cargarDatos();
  $("#vista-login").hidden = true;
  $("#vista-app").hidden = false;
  const nombre = esMecanico() ? estado.datos.perfil.nombre : estado.yo.nombre || estado.yo.username;
  $("#nombre-usuario").textContent = nombre;
  $("#avatar-usuario").textContent = iniciales(nombre);
  $("#rol-usuario").textContent = esMecanico()
    ? `Mecánico · ${estado.datos.perfil.nivel.nombre}`
    : ROLES[estado.yo.rol];
  estado.vista = "";
  irSegunDireccion();
}

function cerrarSesion(mensaje = "") {
  estado.token = null;
  estado.yo = null;
  estado.datos = {};
  guardar("taller-token", null);
  if (dialogo.open) dialogo.close();
  if (confirmacion.open) confirmacion.close();
  $("#vista-app").hidden = true;
  $("#vista-login").hidden = false;
  document.title = "Taller Mecánico";
  $("#mensaje-acceso").textContent = mensaje;
  $("#formulario-acceso").reset();
  history.replaceState(null, "", location.pathname);
}

$("#formulario-acceso").addEventListener("submit", async (evento) => {
  evento.preventDefault();
  const boton = $("#boton-acceso");
  const mensaje = $("#mensaje-acceso");
  mensaje.textContent = "";
  boton.disabled = true;
  try {
    await entrar($("#campo-usuario").value.trim(), $("#campo-clave").value);
  } catch (error) {
    mensaje.textContent = error.message;
  } finally {
    boton.disabled = false;
  }
});

$("#boton-salir").addEventListener("click", () => cerrarSesion());

// ===================== Tema claro / oscuro =====================
function temaActual() {
  return document.documentElement.dataset.theme
    ?? (matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light");
}

function pintarBotonesTema() {
  const oscuro = temaActual() === "dark";
  document.querySelectorAll("[data-cambiar-tema]").forEach((boton) => {
    boton.innerHTML = `${icono(oscuro ? "sol" : "luna")}<span class="texto-boton">${oscuro ? "Modo claro" : "Modo oscuro"}</span>`;
    boton.setAttribute("aria-label", oscuro ? "Cambiar a modo claro" : "Cambiar a modo oscuro");
  });
}

document.querySelectorAll("[data-cambiar-tema]").forEach((boton) =>
  boton.addEventListener("click", () => {
    const nuevo = temaActual() === "dark" ? "light" : "dark";
    document.documentElement.dataset.theme = nuevo;
    guardar("taller-tema", nuevo, localStorage);
    pintarBotonesTema();
  })
);

// ===================== Inicio =====================
async function iniciar() {
  pintarIconos();
  pintarBotonesTema();
  if (estado.token) {
    try {
      await mostrarApp();
      return;
    } catch {
      // El token guardado ya no sirve: se pide iniciar sesión otra vez
    }
  }
  cerrarSesion();
}

iniciar();
