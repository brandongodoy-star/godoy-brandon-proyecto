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
const hoy = () => new Date().toLocaleDateString("en-CA"); // AAAA-MM-DD en la hora local
const iniciales = (nombre) =>
  String(nombre ?? "?").split(/\s+/).filter(Boolean).slice(0, 2).map((p) => p[0].toUpperCase()).join("");
const porId = (lista, id) => lista.find((item) => item.id === id);

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

// ===================== Estado de la aplicación =====================
const ESTADOS = [
  { clave: "recibido", nombre: "Recibido", color: "var(--recibido)" },
  { clave: "en reparacion", nombre: "En reparación", color: "var(--reparacion)" },
  { clave: "listo", nombre: "Listo", color: "var(--listo)" },
  { clave: "entregado", nombre: "Entregado", color: "var(--entregado)" },
];
const ESTADOS_EDITABLES = ["recibido", "en reparacion"];
const POCA_EXISTENCIA = 5;

const estado = {
  token: leerGuardado("taller-token"),
  usuario: leerGuardado("taller-usuario"),
  vista: "resumen",
  busqueda: "",
  datos: { clientes: [], vehiculos: [], mecanicos: [], repuestos: [], ordenes: [] },
};

const nombreEstado = (clave) => ESTADOS.find((e) => e.clave === clave)?.nombre ?? clave;
const claseEstado = (clave) => `estado-${clave.replace(" ", "-")}`;
const insigniaEstado = (clave) =>
  `<span class="insignia ${claseEstado(clave)}"><span class="punto" style="background:currentColor"></span>${esc(nombreEstado(clave))}</span>`;

// ===================== Conexión con la API =====================
class ErrorSilencioso extends Error {}

const TRADUCCIONES = [
  [/^Field required$/, "es obligatorio"],
  [/^String should have at least (\d+) characters?$/, "debe tener al menos $1 caracteres"],
  [/^String should have at most (\d+) characters?$/, "debe tener como máximo $1 caracteres"],
  [/^Input should be greater than or equal to (.+)$/, "debe ser mayor o igual que $1"],
  [/^Input should be greater than (.+)$/, "debe ser mayor que $1"],
  [/^String should match pattern .*$/, "solo puede tener letras, números y guion bajo"],
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
  const [clientes, vehiculos, mecanicos, repuestos, ordenes] = await Promise.all(
    ["/clientes", "/vehiculos", "/mecanicos", "/repuestos", "/ordenes"].map((ruta) => api(ruta))
  );
  estado.datos = { clientes, vehiculos, mecanicos, repuestos, ordenes };
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

function confirmar({ titulo, texto, boton = "Eliminar" }) {
  return new Promise((resolver) => {
    confirmacion.innerHTML = `
      <div class="dialogo-encabezado"><div><h2>${esc(titulo)}</h2></div></div>
      <div class="dialogo-cuerpo"><p>${esc(texto)}</p></div>
      <div class="dialogo-pie">
        <button type="button" class="boton boton-secundario" data-respuesta="no">Cancelar</button>
        <button type="button" class="boton boton-peligro-lleno" data-respuesta="si">${esc(boton)}</button>
      </div>`;
    confirmacion.querySelectorAll("[data-respuesta]").forEach((b) =>
      b.addEventListener("click", () => confirmacion.close(b.dataset.respuesta))
    );
    confirmacion.addEventListener("close", () => resolver(confirmacion.returnValue === "si"), { once: true });
    confirmacion.returnValue = "";
    confirmacion.showModal();
  });
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
  ].join(" ");
  const ayuda = campo.ayuda ? `<span class="ayuda">${esc(campo.ayuda)}</span>` : "";

  if (campo.tipo === "checkbox") {
    return `<div class="${clase}"><input id="${id}" name="${campo.nombre}" type="checkbox" ${valor ? "checked" : ""} />
      <label for="${id}">${esc(campo.etiqueta)}</label></div>`;
  }
  if (campo.tipo === "select") {
    const opciones = campo.opciones
      .map((o) => `<option value="${o.valor}" ${o.valor === valor ? "selected" : ""}>${esc(o.texto)}</option>`)
      .join("");
    return `<div class="${clase}"><label for="${id}">${esc(campo.etiqueta)}</label>
      <select id="${id}" name="${campo.nombre}" ${atributos}><option value="">Seleccione…</option>${opciones}</select>${ayuda}</div>`;
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
    const control = formulario.elements[campo.nombre];
    if (campo.tipo === "checkbox") datos[campo.nombre] = control.checked;
    else if (control.value.trim() === "") datos[campo.nombre] = null;
    else if (campo.tipo === "number" || campo.tipo === "select") datos[campo.nombre] = Number(control.value);
    else datos[campo.nombre] = control.value.trim();
  }
  return datos;
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
      if (!formulario.checkValidity()) {
        const invalido = formulario.querySelector(":invalid");
        error.textContent = `${invalido.labels?.[0]?.textContent ?? "Un campo"}: ${invalido.validationMessage}`;
        invalido.focus();
        return;
      }
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

// ===================== Módulos con tabla (CRUD) =====================
const cantidad = (lista, campo, id) => lista.filter((item) => item[campo] === id).length;
const ordenesActivas = () => estado.datos.ordenes.filter((o) => o.estado !== "entregado");

function insigniaExistencia(existencia) {
  if (existencia === 0) return `<span class="insignia insignia-peligro">Agotado</span>`;
  if (existencia <= POCA_EXISTENCIA) return `<span class="insignia insignia-baja">${existencia} · Poca</span>`;
  return `<span class="insignia insignia-ok">${existencia}</span>`;
}

const MODULOS = {
  clientes: {
    ruta: "/clientes", singular: "cliente", articulo: "el",
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
    ruta: "/vehiculos", singular: "vehículo", articulo: "el",
    columnas: [
      { titulo: "Placa", valor: (v) => `<span class="placa">${esc(v.placa)}</span>` },
      { titulo: "Vehículo", valor: (v) => `<div class="celda-doble"><strong>${esc(v.marca)} ${esc(v.modelo)}</strong><span>Año ${v.anio}</span></div>` },
      { titulo: "Dueño", valor: (v) => esc(porId(estado.datos.clientes, v.cliente_id)?.nombre ?? "—") },
      { titulo: "Órdenes", clase: "numero", valor: (v) => cantidad(estado.datos.ordenes, "vehiculo_id", v.id) },
    ],
    texto: (v) => `${v.placa} ${v.marca} ${v.modelo} ${v.anio} ${porId(estado.datos.clientes, v.cliente_id)?.nombre ?? ""}`,
    nombre: (v) => `${v.placa} (${v.marca} ${v.modelo})`,
    campos: () => [
      { nombre: "placa", etiqueta: "Placa", requerido: true, minlength: 3, maxlength: 10, ayuda: "Se guarda en mayúsculas" },
      { nombre: "anio", etiqueta: "Año", tipo: "number", requerido: true, min: 1950, max: new Date().getFullYear() + 1 },
      { nombre: "marca", etiqueta: "Marca", requerido: true, minlength: 2, maxlength: 50 },
      { nombre: "modelo", etiqueta: "Modelo", requerido: true, maxlength: 50 },
      {
        nombre: "cliente_id", etiqueta: "Dueño", tipo: "select", requerido: true, completo: true,
        opciones: estado.datos.clientes.map((c) => ({ valor: c.id, texto: `${c.nombre} · ${c.telefono}` })),
      },
    ],
  },
  mecanicos: {
    ruta: "/mecanicos", singular: "mecánico", articulo: "el",
    columnas: [
      { titulo: "Nombre", valor: (m) => `<div class="mecanico-mini"><span class="avatar">${esc(iniciales(m.nombre))}</span><strong>${esc(m.nombre)}</strong></div>` },
      { titulo: "Especialidad", valor: (m) => esc(m.especialidad || "—") },
      { titulo: "Estado", valor: (m) => (m.activo ? `<span class="insignia insignia-ok">Activo</span>` : `<span class="insignia insignia-neutra">Inactivo</span>`) },
      { titulo: "Órdenes en curso", clase: "numero", valor: (m) => cantidad(ordenesActivas(), "mecanico_id", m.id) },
    ],
    texto: (m) => `${m.nombre} ${m.especialidad ?? ""}`,
    nombre: (m) => m.nombre,
    ayudaEliminar: "Si ya tiene órdenes no se puede eliminar; en ese caso edítelo y desmarque «Activo».",
    campos: () => [
      { nombre: "nombre", etiqueta: "Nombre completo", requerido: true, minlength: 3, maxlength: 100, completo: true },
      { nombre: "especialidad", etiqueta: "Especialidad", maxlength: 60 },
      { nombre: "activo", etiqueta: "Activo (puede recibir órdenes)", tipo: "checkbox", porDefecto: true },
    ],
  },
  repuestos: {
    ruta: "/repuestos", singular: "repuesto", articulo: "el",
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
};

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
              <button type="button" class="boton boton-icono" data-editar="${item.id}" aria-label="Editar">${icono("editar")}</button>
              <button type="button" class="boton boton-icono peligro" data-eliminar="${item.id}" aria-label="Eliminar">${icono("borrar")}</button>
            </td>
          </tr>`).join("")}
        </tbody>
      </table></div>` : `
      <div class="vacio">${icono(clave)}<strong>${termino ? "Sin resultados" : `Todavía no hay ${esc(VISTAS[clave].titulo.toLowerCase())}`}</strong>
        <span>${termino ? "Pruebe con otra búsqueda." : `Use el botón «Nuevo ${esc(modulo.singular)}» para agregar uno.`}</span></div>`}
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
    titulo: registro ? `Editar ${modulo.singular}` : `Nuevo ${modulo.singular}`,
    subtitulo: registro ? modulo.nombre(registro) : "",
    campos: modulo.campos(),
    valores: registro ?? {},
    textoBoton: registro ? "Guardar cambios" : `Crear ${modulo.singular}`,
    enviar: async (datos) => {
      await api(registro ? `${modulo.ruta}/${registro.id}` : modulo.ruta, { metodo: registro ? "PUT" : "POST", datos });
      aviso(registro ? "Cambios guardados" : `${modulo.singular[0].toUpperCase()}${modulo.singular.slice(1)} creado`);
    },
  });
}

async function eliminarRegistro(clave, registro) {
  const modulo = MODULOS[clave];
  const seguro = await confirmar({
    titulo: `¿Eliminar ${modulo.articulo} ${modulo.singular}?`,
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

// ===================== Órdenes =====================
function textoVehiculo(vehiculo) {
  return vehiculo ? `${vehiculo.marca} ${vehiculo.modelo} ${vehiculo.anio}` : "Vehículo eliminado";
}

function tarjetaOrden(orden) {
  const vehiculo = porId(estado.datos.vehiculos, orden.vehiculo_id);
  const mecanico = porId(estado.datos.mecanicos, orden.mecanico_id);
  return `
    <button type="button" class="tarjeta-orden" data-orden="${orden.id}">
      <div class="arriba"><span class="placa">${esc(vehiculo?.placa ?? "—")}</span><span class="numero-orden">#${orden.id}</span></div>
      <div class="vehiculo">${esc(textoVehiculo(vehiculo))}</div>
      <div class="diagnostico">${esc(orden.diagnostico || "Sin diagnóstico")}</div>
      <div class="abajo">
        <span class="mecanico-mini"><span class="avatar">${esc(iniciales(mecanico?.nombre))}</span><span>${esc(mecanico?.nombre ?? "—")}</span></span>
        <span>${fecha(orden.fecha_ingreso)}</span>
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
  const mecanicos = estado.datos.mecanicos.filter((m) => m.activo || m.id === orden?.mecanico_id);
  return [
    {
      nombre: "vehiculo_id", etiqueta: "Vehículo", tipo: "select", requerido: true, completo: true,
      opciones: estado.datos.vehiculos.map((v) => ({
        valor: v.id,
        texto: `${v.placa} · ${v.marca} ${v.modelo} — ${porId(estado.datos.clientes, v.cliente_id)?.nombre ?? ""}`,
      })),
    },
    {
      nombre: "mecanico_id", etiqueta: "Mecánico", tipo: "select", requerido: true,
      opciones: mecanicos.map((m) => ({ valor: m.id, texto: `${m.nombre}${m.especialidad ? ` · ${m.especialidad}` : ""}${m.activo ? "" : " (inactivo)"}` })),
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
      const guardada = await api(orden ? `/ordenes/${orden.id}` : "/ordenes", { metodo: orden ? "PUT" : "POST", datos });
      aviso(orden ? "Orden actualizada" : `Orden #${guardada.id} creada`);
    },
  });
}

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
        <div class="dato"><small>Vehículo</small><strong>${esc(textoVehiculo(vehiculo))}</strong></div>
        <div class="dato"><small>Cliente</small><strong>${esc(cliente?.nombre ?? "—")}</strong><span class="mono">${esc(cliente?.telefono ?? "")}</span></div>
        <div class="dato"><small>Mecánico</small><strong>${esc(mecanico?.nombre ?? "—")}</strong><span>${esc(mecanico?.especialidad ?? "")}</span></div>
        <div class="dato"><small>Mano de obra</small><strong>${dinero(orden.mano_obra)}</strong></div>
        <div class="dato completo"><small>Diagnóstico</small><strong>${esc(orden.diagnostico || "Sin diagnóstico")}</strong></div>
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
      ${siguiente ? `<button type="button" class="boton boton-primario" id="avanzar-orden">Pasar a «${siguiente.nombre}» ${icono("flecha")}</button>` : ""}
    </div>`, (raiz) => {
    $("#avanzar-orden", raiz)?.addEventListener("click", async () => {
      if (await intentar(() => api(`/ordenes/${id}/avanzar`, { metodo: "POST" }))) {
        aviso(`Orden #${id}: ${siguiente.nombre}`);
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

// ===================== Resumen =====================
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
          <ul class="lista">${mecanicos.filter((m) => m.activo).map((m) => {
            const carga = cantidad(activas, "mecanico_id", m.id);
            return `<li><div class="fila-lista"><span class="avatar">${esc(iniciales(m.nombre))}</span>
              <span class="principal"><strong>${esc(m.nombre)}</strong><span>${esc(m.especialidad || "Sin especialidad")}</span></span>
              <span class="insignia ${carga ? "insignia-baja" : "insignia-neutra"}">${carga} en curso</span></div></li>`;
          }).join("") || `<li class="vacio-chico">No hay mecánicos activos.</li>`}</ul>
        </section>
      </div>
    </div>`;

  conectarTarjetasOrden();
}

// ===================== Navegación =====================
const VISTAS = {
  resumen: { titulo: "Resumen", subtitulo: "Así está el taller hoy", icono: "resumen", pintar: pintarResumen },
  ordenes: { titulo: "Órdenes", subtitulo: "Tablero de órdenes de servicio", icono: "ordenes", pintar: pintarOrdenes,
    boton: "Nueva orden", nuevo: () => formularioOrden() },
  clientes: { titulo: "Clientes", subtitulo: "Personas que traen sus vehículos", icono: "clientes" },
  vehiculos: { titulo: "Vehículos", subtitulo: "Vehículos registrados y sus dueños", icono: "vehiculos" },
  mecanicos: { titulo: "Mecánicos", subtitulo: "Equipo de trabajo del taller", icono: "mecanicos" },
  repuestos: { titulo: "Repuestos", subtitulo: "Inventario y precios", icono: "repuestos" },
};
for (const clave of Object.keys(MODULOS)) {
  VISTAS[clave].pintar = () => pintarModulo(clave);
  VISTAS[clave].boton = `Nuevo ${MODULOS[clave].singular}`;
  VISTAS[clave].nuevo = () => formularioModulo(clave);
}

function pintarMenu() {
  $("#menu").innerHTML = Object.entries(VISTAS).map(([clave, vista]) => {
    const cuenta = clave === "ordenes" ? ordenesActivas().length : estado.datos[clave]?.length;
    return `<a href="#/${clave}" class="${clave === estado.vista ? "activo" : ""}" ${clave === estado.vista ? 'aria-current="page"' : ""}>
      ${icono(vista.icono)}<span>${vista.titulo}</span>${cuenta !== undefined ? `<span class="contador">${cuenta}</span>` : ""}</a>`;
  }).join("");
}

function pintarVista() {
  const vista = VISTAS[estado.vista];
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
  const nueva = VISTAS[clave] ? clave : "resumen";
  if (nueva !== estado.vista) estado.busqueda = "";
  estado.vista = nueva;
  if (!$("#vista-app").hidden) {
    pintarVista();
    window.scrollTo(0, 0);
  }
}
window.addEventListener("hashchange", irSegunDireccion);

// ===================== Sesión =====================
let modoAcceso = "entrar";

function cambiarModoAcceso(modo) {
  modoAcceso = modo;
  document.querySelectorAll("[data-modo]").forEach((b) => b.classList.toggle("activa", b.dataset.modo === modo));
  const registrar = modo === "registrar";
  $("#titulo-acceso").textContent = registrar ? "Cree su cuenta" : "Bienvenido de nuevo";
  $("#texto-acceso").textContent = registrar
    ? "Usuario de 3 a 30 caracteres y contraseña de al menos 6."
    : "Ingrese sus datos para continuar.";
  $("#boton-acceso").textContent = registrar ? "Crear cuenta y entrar" : "Iniciar sesión";
  $("#campo-clave").autocomplete = registrar ? "new-password" : "current-password";
  $("#mensaje-acceso").textContent = "";
}

async function entrar(usuario, clave) {
  const respuesta = await api("/auth/login", { metodo: "POST", formulario: { username: usuario, password: clave } });
  estado.token = respuesta.access_token;
  estado.usuario = usuario;
  guardar("taller-token", estado.token);
  guardar("taller-usuario", usuario);
  await mostrarApp();
}

async function mostrarApp() {
  await cargarDatos();
  $("#vista-login").hidden = true;
  $("#vista-app").hidden = false;
  $("#nombre-usuario").textContent = estado.usuario;
  $("#avatar-usuario").textContent = iniciales(estado.usuario);
  irSegunDireccion();
  pintarVista();
}

function cerrarSesion(mensaje = "") {
  estado.token = null;
  estado.usuario = null;
  guardar("taller-token", null);
  guardar("taller-usuario", null);
  if (dialogo.open) dialogo.close();
  $("#vista-app").hidden = true;
  $("#vista-login").hidden = false;
  document.title = "Taller Mecánico";
  $("#mensaje-acceso").textContent = mensaje;
  $("#formulario-acceso").reset();
}

$("#formulario-acceso").addEventListener("submit", async (evento) => {
  evento.preventDefault();
  const usuario = $("#campo-usuario").value.trim();
  const clave = $("#campo-clave").value;
  const boton = $("#boton-acceso");
  const mensaje = $("#mensaje-acceso");
  mensaje.textContent = "";
  boton.disabled = true;
  try {
    if (modoAcceso === "registrar") {
      await api("/auth/registro", { metodo: "POST", datos: { username: usuario, password: clave } });
    }
    await entrar(usuario, clave);
  } catch (error) {
    mensaje.textContent = error.message;
  } finally {
    boton.disabled = false;
  }
});

document.querySelectorAll("[data-modo]").forEach((b) => b.addEventListener("click", () => cambiarModoAcceso(b.dataset.modo)));
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
      cerrarSesion();
      return;
    }
  }
  cerrarSesion();
}

iniciar();
