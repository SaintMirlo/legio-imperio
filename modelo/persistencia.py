"""GestorPersistencia: guarda y carga campañas en una base de datos relacional externa (RT002).

Usa SQLite, que viene con Python: la base es un archivo fuera del código
(instance/legio_imperium.db por defecto) y no requiere instalar un servidor. Las tablas
siguen la jerarquía del enunciado: campaña → cónsules → legiones → Legatus y unidades, y
campaña → enfrentamientos → participantes, turnos y etapas, más la bitácora de eventos.

Cada campaña se guarda completa en una sola transacción: si algo falla, queda la versión
anterior. Al cargar, los datos pasan por las mismas validaciones que un archivo importado.
"""
import json
import sqlite3
import threading
from collections import defaultdict
from contextlib import contextmanager

from modelo.campana import Campana
from modelo.catalogos import UNIDADES

ESQUEMA = """
CREATE TABLE IF NOT EXISTS campana (
    id TEXT PRIMARY KEY,
    nombre TEXT NOT NULL,
    creada TEXT NOT NULL,
    actualizada TEXT NOT NULL,
    siguiente_legion INTEGER NOT NULL,
    siguiente_enfrentamiento INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS consul (
    campana_id TEXT NOT NULL REFERENCES campana(id) ON DELETE CASCADE,
    numero INTEGER NOT NULL CHECK (numero IN (1, 2)),
    nombre TEXT NOT NULL,
    PRIMARY KEY (campana_id, numero)
);
CREATE TABLE IF NOT EXISTS legion (
    campana_id TEXT NOT NULL,
    id INTEGER NOT NULL,
    nombre TEXT NOT NULL,
    consul INTEGER NOT NULL,
    presupuesto INTEGER NOT NULL CHECK (presupuesto >= 0),
    asignado INTEGER NOT NULL,
    creada TEXT NOT NULL,
    PRIMARY KEY (campana_id, id),
    FOREIGN KEY (campana_id, consul) REFERENCES consul(campana_id, numero) ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS legatus (
    campana_id TEXT NOT NULL,
    legion_id INTEGER NOT NULL,
    nombre TEXT NOT NULL,
    bono_atk INTEGER NOT NULL CHECK (bono_atk BETWEEN -25 AND 25),
    bono_def INTEGER NOT NULL CHECK (bono_def BETWEEN -25 AND 25),
    PRIMARY KEY (campana_id, legion_id),
    FOREIGN KEY (campana_id, legion_id) REFERENCES legion(campana_id, id) ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS unidad (
    campana_id TEXT NOT NULL,
    legion_id INTEGER NOT NULL,
    tipo TEXT NOT NULL,
    hp INTEGER NOT NULL CHECK (hp > 0),
    cantidad INTEGER NOT NULL CHECK (cantidad > 0),
    PRIMARY KEY (campana_id, legion_id, tipo, hp),
    FOREIGN KEY (campana_id, legion_id) REFERENCES legion(campana_id, id) ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS enfrentamiento (
    campana_id TEXT NOT NULL REFERENCES campana(id) ON DELETE CASCADE,
    id INTEGER NOT NULL,
    nombre TEXT NOT NULL,
    estado TEXT NOT NULL,
    semilla INTEGER NOT NULL,
    pasos INTEGER NOT NULL,
    ganador TEXT,
    motivo TEXT,
    creado TEXT NOT NULL,
    actualizado TEXT NOT NULL,
    PRIMARY KEY (campana_id, id)
);
CREATE TABLE IF NOT EXISTS participante (
    campana_id TEXT NOT NULL,
    enfrentamiento_id INTEGER NOT NULL,
    lado TEXT NOT NULL CHECK (lado IN ('a', 'b')),
    legion_id INTEGER NOT NULL,
    datos TEXT NOT NULL,
    PRIMARY KEY (campana_id, enfrentamiento_id, lado),
    FOREIGN KEY (campana_id, enfrentamiento_id) REFERENCES enfrentamiento(campana_id, id) ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS turno (
    campana_id TEXT NOT NULL,
    enfrentamiento_id INTEGER NOT NULL,
    numero INTEGER NOT NULL,
    fase TEXT NOT NULL,
    formacion_a TEXT NOT NULL,
    formacion_b TEXT NOT NULL,
    sueldos TEXT NOT NULL,
    PRIMARY KEY (campana_id, enfrentamiento_id, numero),
    FOREIGN KEY (campana_id, enfrentamiento_id) REFERENCES enfrentamiento(campana_id, id) ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS etapa (
    campana_id TEXT NOT NULL,
    enfrentamiento_id INTEGER NOT NULL,
    turno INTEGER NOT NULL,
    numero INTEGER NOT NULL CHECK (numero IN (1, 2)),
    atacante TEXT NOT NULL,
    dano INTEGER NOT NULL,
    datos TEXT NOT NULL,
    PRIMARY KEY (campana_id, enfrentamiento_id, turno, numero),
    FOREIGN KEY (campana_id, enfrentamiento_id, turno)
        REFERENCES turno(campana_id, enfrentamiento_id, numero) ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS evento (
    campana_id TEXT NOT NULL REFERENCES campana(id) ON DELETE CASCADE,
    numero INTEGER NOT NULL,
    instante TEXT NOT NULL,
    tipo TEXT NOT NULL,
    texto TEXT NOT NULL,
    turno INTEGER NOT NULL,
    etapa INTEGER,
    enfrentamiento_id INTEGER,
    PRIMARY KEY (campana_id, numero)
);
"""


class CampanaNoEncontrada(LookupError):
    """La campaña pedida no está en la base de datos."""


class GestorPersistencia:
    def __init__(self, ruta):
        self.ruta = str(ruta)
        self._cerrojo = threading.RLock()  # una edición a la vez dentro de este proceso
        with self._conexion() as conexion:
            conexion.executescript(ESQUEMA)

    @contextmanager
    def _conexion(self):
        conexion = sqlite3.connect(self.ruta, timeout=15, isolation_level=None)
        conexion.row_factory = sqlite3.Row
        conexion.execute("PRAGMA foreign_keys = ON")
        try:
            yield conexion
        finally:
            conexion.close()  # en Windows, una conexión abierta bloquea el archivo

    @contextmanager
    def _transaccion(self):
        with self._conexion() as conexion:
            conexion.execute("BEGIN IMMEDIATE")
            try:
                yield conexion
            except BaseException:
                conexion.execute("ROLLBACK")
                raise
            conexion.execute("COMMIT")

    # --- Guardar ------------------------------------------------------------------------

    def guardar_campana(self, campana):
        datos = campana.a_dict()
        id_campana = datos["id"]
        with self._cerrojo, self._transaccion() as c:
            # Borrar la campaña elimina en cascada sus filas; luego se escribe la versión nueva.
            c.execute("DELETE FROM campana WHERE id = ?", (id_campana,))
            c.execute(
                "INSERT INTO campana (id, nombre, creada, actualizada, siguiente_legion, siguiente_enfrentamiento) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (id_campana, datos["nombre"], datos["creada"], datos["actualizada"],
                 datos["siguiente_legion"], datos["siguiente_enfrentamiento"]),
            )
            c.executemany("INSERT INTO consul (campana_id, numero, nombre) VALUES (?, ?, ?)",
                          [(id_campana, numero, nombre) for numero, nombre in enumerate(datos["consules"], 1)])
            for legion in datos["legiones"]:
                c.execute(
                    "INSERT INTO legion (campana_id, id, nombre, consul, presupuesto, asignado, creada) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (id_campana, legion["id"], legion["nombre"], legion["consul"], legion["presupuesto"],
                     legion["asignado"], legion["creada"]),
                )
                legatus = legion["legatus"]
                c.execute("INSERT INTO legatus (campana_id, legion_id, nombre, bono_atk, bono_def) "
                          "VALUES (?, ?, ?, ?, ?)",
                          (id_campana, legion["id"], legatus["nombre"], legatus["atk"], legatus["def"]))
                c.executemany(
                    "INSERT INTO unidad (campana_id, legion_id, tipo, hp, cantidad) VALUES (?, ?, ?, ?, ?)",
                    [(id_campana, legion["id"], tipo, hp, cantidad)
                     for tipo, grupos in legion["unidades"].items() for hp, cantidad in grupos],
                )
            for enf in datos["enfrentamientos"]:
                c.execute(
                    "INSERT INTO enfrentamiento (campana_id, id, nombre, estado, semilla, pasos, ganador, motivo, "
                    "creado, actualizado) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (id_campana, enf["id"], enf["nombre"], enf["estado"], enf["semilla"], enf["pasos"],
                     enf["ganador"], enf["motivo"], enf["creado"], enf["actualizado"]),
                )
                c.executemany(
                    "INSERT INTO participante (campana_id, enfrentamiento_id, lado, legion_id, datos) "
                    "VALUES (?, ?, ?, ?, ?)",
                    [(id_campana, enf["id"], lado, p["legion_id"], _json(p)) for lado, p in enf["participantes"].items()],
                )
                for turno in enf["turnos"]:
                    c.execute(
                        "INSERT INTO turno (campana_id, enfrentamiento_id, numero, fase, formacion_a, formacion_b, "
                        "sueldos) VALUES (?, ?, ?, ?, ?, ?, ?)",
                        (id_campana, enf["id"], turno["numero"], turno["fase"], turno["formaciones"]["a"],
                         turno["formaciones"]["b"], _json(turno["sueldos"])),
                    )
                    c.executemany(
                        "INSERT INTO etapa (campana_id, enfrentamiento_id, turno, numero, atacante, dano, datos) "
                        "VALUES (?, ?, ?, ?, ?, ?, ?)",
                        [(id_campana, enf["id"], turno["numero"], etapa["numero"], etapa["atacante"], etapa["dano"],
                          _json(etapa)) for etapa in turno["etapas"]],
                    )
            c.executemany(
                "INSERT INTO evento (campana_id, numero, instante, tipo, texto, turno, etapa, enfrentamiento_id) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                [(id_campana, e["numero"], e["instante"], e["tipo"], e["texto"], e["turno"], e["etapa"],
                  e["enfrentamiento"]) for e in datos["bitacora"]],
            )

    # --- Cargar -------------------------------------------------------------------------

    def cargar_campana(self, id_campana):
        """Campaña reconstruida desde la base de datos, o None si no existe."""
        with self._conexion() as c:
            fila = c.execute("SELECT * FROM campana WHERE id = ?", (id_campana,)).fetchone()
            if fila is None:
                return None
            datos = self._leer(c, fila)
        return Campana.desde_dict(datos)

    @staticmethod
    def _leer(c, fila):
        id_campana = fila["id"]

        def filas(sql):
            return c.execute(sql, (id_campana,)).fetchall()

        legatus = {f["legion_id"]: {"nombre": f["nombre"], "atk": f["bono_atk"], "def": f["bono_def"]}
                   for f in filas("SELECT * FROM legatus WHERE campana_id = ?")}
        unidades = defaultdict(lambda: {tipo: [] for tipo in UNIDADES})
        for f in filas("SELECT * FROM unidad WHERE campana_id = ? ORDER BY legion_id, tipo, hp DESC"):
            unidades[f["legion_id"]].setdefault(f["tipo"], []).append([f["hp"], f["cantidad"]])
        legiones = [
            {"id": f["id"], "nombre": f["nombre"], "consul": f["consul"], "presupuesto": f["presupuesto"],
             "asignado": f["asignado"], "creada": f["creada"], "legatus": legatus.get(f["id"]),
             "unidades": unidades[f["id"]]}
            for f in filas("SELECT * FROM legion WHERE campana_id = ? ORDER BY id")
        ]

        participantes = defaultdict(dict)
        for f in filas("SELECT * FROM participante WHERE campana_id = ?"):
            participantes[f["enfrentamiento_id"]][f["lado"]] = json.loads(f["datos"])
        etapas = defaultdict(list)
        for f in filas("SELECT * FROM etapa WHERE campana_id = ? ORDER BY enfrentamiento_id, turno, numero"):
            etapas[(f["enfrentamiento_id"], f["turno"])].append(json.loads(f["datos"]))
        turnos = defaultdict(list)
        for f in filas("SELECT * FROM turno WHERE campana_id = ? ORDER BY enfrentamiento_id, numero"):
            turnos[f["enfrentamiento_id"]].append({
                "numero": f["numero"], "fase": f["fase"],
                "formaciones": {"a": f["formacion_a"], "b": f["formacion_b"]},
                "sueldos": json.loads(f["sueldos"]),
                "etapas": etapas[(f["enfrentamiento_id"], f["numero"])],
            })
        enfrentamientos = [
            {"id": f["id"], "nombre": f["nombre"], "estado": f["estado"], "semilla": f["semilla"],
             "pasos": f["pasos"], "ganador": f["ganador"], "motivo": f["motivo"], "creado": f["creado"],
             "actualizado": f["actualizado"], "participantes": participantes[f["id"]], "turnos": turnos[f["id"]]}
            for f in filas("SELECT * FROM enfrentamiento WHERE campana_id = ? ORDER BY id")
        ]
        bitacora = [
            {"numero": f["numero"], "instante": f["instante"], "tipo": f["tipo"], "texto": f["texto"],
             "turno": f["turno"], "etapa": f["etapa"], "enfrentamiento": f["enfrentamiento_id"]}
            for f in filas("SELECT * FROM evento WHERE campana_id = ? ORDER BY numero")
        ]
        return {
            "id": id_campana, "nombre": fila["nombre"], "creada": fila["creada"], "actualizada": fila["actualizada"],
            "siguiente_legion": fila["siguiente_legion"], "siguiente_enfrentamiento": fila["siguiente_enfrentamiento"],
            "consules": [f["nombre"] for f in filas("SELECT nombre FROM consul WHERE campana_id = ? ORDER BY numero")],
            "legiones": legiones, "enfrentamientos": enfrentamientos, "bitacora": bitacora,
        }

    # --- Consultas y edición ------------------------------------------------------------

    def listar_campanas(self):
        """Campañas guardadas, de la más reciente a la más antigua."""
        with self._conexion() as c:
            return [dict(f) for f in c.execute(
                "SELECT c.id, c.nombre, c.creada, c.actualizada, "
                "(SELECT COUNT(*) FROM legion l WHERE l.campana_id = c.id) AS legiones, "
                "EXISTS (SELECT 1 FROM enfrentamiento e WHERE e.campana_id = c.id AND e.estado = 'en_curso') "
                "AS en_combate FROM campana c ORDER BY c.actualizada DESC, c.rowid DESC"
            )]

    def existe(self, id_campana):
        return self.nombre_campana(id_campana) is not None

    def nombre_campana(self, id_campana):
        """Nombre de la campaña, o None si no está en la base de datos."""
        with self._conexion() as c:
            fila = c.execute("SELECT nombre FROM campana WHERE id = ?", (id_campana,)).fetchone()
        return fila["nombre"] if fila else None

    def ultima_campana_id(self):
        with self._conexion() as c:
            fila = c.execute("SELECT id FROM campana ORDER BY actualizada DESC, rowid DESC LIMIT 1").fetchone()
        return fila["id"] if fila else None

    def eliminar_campana(self, id_campana):
        with self._cerrojo, self._transaccion() as c:
            c.execute("DELETE FROM campana WHERE id = ?", (id_campana,))

    @contextmanager
    def editar(self, id_campana):
        """Carga la campaña, entrega el objeto y lo guarda solo si el bloque termina sin errores.

        Si una regla del juego lanza ReglaInvalida, la base queda como estaba.
        """
        with self._cerrojo:
            campana = self.cargar_campana(id_campana)
            if campana is None:
                raise CampanaNoEncontrada(id_campana)
            yield campana
            self.guardar_campana(campana)


def _json(valor):
    return json.dumps(valor, ensure_ascii=False, separators=(",", ":"))
