"""Genera las copias en PDF de los reportes sin librerías externas.

Escribe un PDF 1.4 sencillo a mano: páginas tamaño carta, fuentes Helvetica (que todo lector de PDF
trae incluidas) y texto en WinAnsi, que cubre las tildes y la ñ del español.
"""

from datetime import datetime

ANCHO, ALTO = 612, 792  # carta, en puntos
MARGEN = 56
NARANJA = (0.91, 0.35, 0.05)
GRIS = (0.42, 0.45, 0.49)
NEGRO = (0.11, 0.13, 0.14)

TIPOS_REPORTE = {
    "equipo": "Falla de equipo o herramienta",
    "repuestos": "Faltan repuestos",
    "seguridad": "Seguridad",
    "otro": "Otro",
    "desempeno": "Desempeño de un miembro del equipo (reporte del líder)",
}


def _texto_pdf(texto: str) -> str:
    """Pasa el texto a WinAnsi (cp1252) y escapa los caracteres especiales de PDF."""
    crudo = str(texto).encode("cp1252", errors="replace").decode("latin-1")
    return crudo.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def _partir(texto: str, tamano: float, ancho: float) -> list[str]:
    """Corta el texto en renglones que caben en `ancho` (aproximando el ancho de Helvetica)."""
    maximo = max(10, int(ancho / (tamano * 0.5)))
    renglones = []
    for parrafo in str(texto).splitlines() or [""]:
        actual = ""
        for palabra in parrafo.split(" "):
            while len(palabra) > maximo:  # palabras larguísimas se cortan
                if actual:
                    renglones.append(actual)
                    actual = ""
                renglones.append(palabra[:maximo])
                palabra = palabra[maximo:]
            prueba = f"{actual} {palabra}".strip()
            if len(prueba) > maximo:
                renglones.append(actual)
                actual = palabra
            else:
                actual = prueba
        renglones.append(actual)
    return renglones


class _Documento:
    """Va dibujando páginas; cuando no cabe más, abre una nueva."""

    def __init__(self, pie: str):
        self.pie = pie
        self.paginas: list[list[str]] = []
        self.nueva_pagina()

    def nueva_pagina(self) -> None:
        self.ops: list[str] = []
        self.paginas.append(self.ops)
        self.y = ALTO - MARGEN

    def texto(self, x: float, y: float, contenido: str, tamano: float = 11, negrita: bool = False, color=NEGRO) -> None:
        fuente = "F2" if negrita else "F1"
        self.ops.append(
            f"{color[0]} {color[1]} {color[2]} rg BT /{fuente} {tamano} Tf {x:.1f} {y:.1f} Td ({_texto_pdf(contenido)}) Tj ET"
        )

    def rectangulo(self, x: float, y: float, ancho: float, alto: float, color) -> None:
        self.ops.append(f"{color[0]} {color[1]} {color[2]} rg {x:.1f} {y:.1f} {ancho:.1f} {alto:.1f} re f")

    def linea(self, y: float) -> None:
        self.ops.append(f"0.85 0.84 0.81 RG 0.8 w {MARGEN} {y:.1f} m {ANCHO - MARGEN} {y:.1f} l S")

    def espacio(self, alto: float) -> None:
        """Asegura que quepan `alto` puntos más; si no, sigue en otra página."""
        if self.y - alto < MARGEN + 30:
            self.nueva_pagina()

    def parrafo(self, contenido: str, tamano: float = 11, sangria: float = 0) -> None:
        for renglon in _partir(contenido, tamano, ANCHO - 2 * MARGEN - sangria):
            self.espacio(tamano + 6)
            self.texto(MARGEN + sangria, self.y, renglon, tamano)
            self.y -= tamano + 5

    def bytes(self) -> bytes:
        total = len(self.paginas)
        objetos = [
            "<< /Type /Catalog /Pages 2 0 R >>",
            None,  # páginas: se completa abajo
            "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>",
            "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold /Encoding /WinAnsiEncoding >>",
        ]
        hijos = []
        for numero, ops in enumerate(self.paginas, start=1):
            pie = [
                f"{GRIS[0]} {GRIS[1]} {GRIS[2]} rg BT /F1 8.5 Tf {MARGEN} 30 Td ({_texto_pdf(self.pie)}) Tj ET",
                f"{GRIS[0]} {GRIS[1]} {GRIS[2]} rg BT /F1 8.5 Tf {ANCHO - MARGEN - 60} 30 Td "
                f"({_texto_pdf(f'Página {numero} de {total}')}) Tj ET",
            ]
            contenido = "\n".join(ops + pie).encode("latin-1")
            objetos.append(f"<< /Length {len(contenido)} >>\nstream\n".encode("latin-1") + contenido + b"\nendstream")
            contenido_id = len(objetos)
            objetos.append(
                f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 {ANCHO} {ALTO}] "
                f"/Resources << /Font << /F1 3 0 R /F2 4 0 R >> >> /Contents {contenido_id} 0 R >>"
            )
            hijos.append(f"{len(objetos)} 0 R")
        objetos[1] = f"<< /Type /Pages /Kids [{' '.join(hijos)}] /Count {total} >>"

        salida = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
        posiciones = []
        for numero, objeto in enumerate(objetos, start=1):
            posiciones.append(len(salida))
            cuerpo = objeto if isinstance(objeto, bytes) else objeto.encode("latin-1")
            salida += f"{numero} 0 obj\n".encode() + cuerpo + b"\nendobj\n"
        inicio_xref = len(salida)
        salida += f"xref\n0 {len(objetos) + 1}\n0000000000 65535 f \n".encode()
        for posicion in posiciones:
            salida += f"{posicion:010d} 00000 n \n".encode()
        salida += f"trailer\n<< /Size {len(objetos) + 1} /Root 1 0 R >>\nstartxref\n{inicio_xref}\n%%EOF\n".encode()
        return bytes(salida)


def reporte_pdf(reporte: dict) -> bytes:
    """Copia en PDF de un reporte tal como se envió: datos, a quién se refiere y su descripción."""
    generado = datetime.now().strftime("%d/%m/%Y %H:%M")
    doc = _Documento(f"Taller Mecánico · Copia del reporte #{reporte['id']} generada el {generado}")

    # Banda de color con el nombre del taller
    doc.rectangulo(0, ALTO - 88, ANCHO, 88, NARANJA)
    doc.texto(MARGEN, ALTO - 46, "Taller Mecánico", 20, negrita=True, color=(1, 1, 1))
    doc.texto(MARGEN, ALTO - 66, "Copia oficial de un reporte enviado a recepción", 10.5, color=(1, 0.93, 0.88))
    doc.texto(ANCHO - MARGEN - 110, ALTO - 50, f"Reporte #{reporte['id']}", 15, negrita=True, color=(1, 1, 1))
    doc.y = ALTO - 128

    for renglon in _partir(reporte["titulo"], 17, ANCHO - 2 * MARGEN):
        doc.texto(MARGEN, doc.y, renglon, 17, negrita=True)
        doc.y -= 22
    doc.y -= 4
    doc.linea(doc.y)
    doc.y -= 24

    datos = [
        ("Tipo", TIPOS_REPORTE.get(reporte["tipo"], reporte["tipo"])),
        ("Enviado por", reporte.get("mecanico") or "—"),
        ("Fecha de envío", reporte.get("fecha") or "—"),
        ("Proyecto", f"#{reporte['orden_id']}" + (f" · {reporte['placa']}" if reporte.get("placa") else "")
         if reporte.get("orden_id") else "Sin proyecto"),
    ]
    if reporte.get("sobre_mecanico"):
        datos.append(("Sobre el mecánico", reporte["sobre_mecanico"]))
    datos.append(("Estado al enviarlo", "Abierto: pendiente de que recepción lo resuelva"))
    for etiqueta, valor in datos:
        doc.espacio(20)
        doc.texto(MARGEN, doc.y, etiqueta.upper(), 8.5, negrita=True, color=GRIS)
        renglones = _partir(valor, 11, ANCHO - 2 * MARGEN - 150)
        for i, renglon in enumerate(renglones):
            doc.texto(MARGEN + 150, doc.y - i * 15, renglon, 11)
        doc.y -= 15 * len(renglones) + 6

    doc.y -= 8
    doc.espacio(40)
    doc.linea(doc.y)
    doc.y -= 26
    doc.texto(MARGEN, doc.y, "DESCRIPCIÓN", 8.5, negrita=True, color=GRIS)
    doc.y -= 20
    doc.parrafo(reporte["descripcion"], 11.5)
    return doc.bytes()


def _dinero(valor: float) -> str:
    return f"L {valor:,.2f}"


def comprobante_pdf(c: dict) -> bytes:
    """Comprobante en PDF de un pago, un anticipo o una venta de repuesto.

    `c` trae: tipo («pago», «anticipo» o «venta»), numero, fecha, los datos de quien pagó,
    concepto (lista de (etiqueta, valor)), forma de pago, monto, totales del proyecto si los hay,
    quién lo registró y la nota del sistema (lo que quedó en el historial de movimientos).
    """
    titulos = {"pago": "Comprobante de pago", "anticipo": "Comprobante de pago anticipado", "venta": "Comprobante de venta"}
    generado = datetime.now().strftime("%d/%m/%Y %H:%M")
    doc = _Documento(f"Taller Mecánico · {titulos[c['tipo']]} {c['numero']} generado el {generado}")

    doc.rectangulo(0, ALTO - 88, ANCHO, 88, NARANJA)
    doc.texto(MARGEN, ALTO - 46, "Taller Mecánico", 20, negrita=True, color=(1, 1, 1))
    doc.texto(MARGEN, ALTO - 66, titulos[c["tipo"]], 10.5, color=(1, 0.93, 0.88))
    doc.texto(ANCHO - MARGEN - 120, ALTO - 50, c["numero"], 15, negrita=True, color=(1, 1, 1))
    doc.y = ALTO - 122

    # Monto destacado
    doc.rectangulo(MARGEN, doc.y - 46, ANCHO - 2 * MARGEN, 52, (0.99, 0.94, 0.90))
    doc.texto(MARGEN + 16, doc.y - 14, "MONTO RECIBIDO", 8.5, negrita=True, color=GRIS)
    doc.texto(MARGEN + 16, doc.y - 36, _dinero(c["monto"]), 20, negrita=True, color=NARANJA)
    doc.texto(ANCHO - MARGEN - 190, doc.y - 14, "FECHA", 8.5, negrita=True, color=GRIS)
    doc.texto(ANCHO - MARGEN - 190, doc.y - 32, c["fecha"], 11.5)
    doc.y -= 74

    def seccion(titulo: str, filas: list[tuple[str, str]]) -> None:
        doc.espacio(40)
        doc.texto(MARGEN, doc.y, titulo, 12, negrita=True)
        doc.y -= 8
        doc.linea(doc.y)
        doc.y -= 18
        for etiqueta, valor in filas:
            renglones = _partir(valor, 11, ANCHO - 2 * MARGEN - 160)
            doc.espacio(15 * len(renglones) + 6)
            doc.texto(MARGEN, doc.y, etiqueta.upper(), 8.5, negrita=True, color=GRIS)
            for i, renglon in enumerate(renglones):
                doc.texto(MARGEN + 160, doc.y - i * 15, renglon, 11)
            doc.y -= 15 * len(renglones) + 6
        doc.y -= 10

    pagador = [("Nombre", c["pagador"]), ("Identidad", c.get("identidad") or "—")]
    if c.get("correo"):
        pagador.append(("Correo", c["correo"]))
    seccion("Datos de quien paga", pagador)
    seccion("Concepto", c["concepto"])
    seccion("Forma de pago", c["forma"])
    if c.get("totales"):
        seccion("Estado de la cuenta", c["totales"])
    seccion("Registro", [("Registrado por", c.get("registrado_por") or "—"), ("Nota del sistema", c.get("nota") or "—")])

    doc.espacio(30)
    doc.parrafo("Este comprobante lo generó el sistema del taller al registrar el cobro. "
                "De la tarjeta solo se guardan la marca y los últimos 4 dígitos.", 9)
    return doc.bytes()
