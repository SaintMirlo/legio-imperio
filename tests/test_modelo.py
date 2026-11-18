"""Pruebas del modelo de Legio Imperium: reglas del enunciado y decisiones de diseño.

Cada prueba dice en su docstring qué regla comprueba. Los escenarios se arman a mano para
que las cifras esperadas se puedan verificar con lápiz y papel (en los comentarios va la
cuenta). Catálogo (HP/ATK/DEF/costo): legionario 20/25/35/5, caballería 50/45/15/12,
ballesta 15/60/5/20, ingeniero 2/5/20/10, esclavo 5/2/5/1.
"""
import math
import random
import unittest
from fractions import Fraction
from types import SimpleNamespace

from modelo.bitacora import Bitacora
from modelo.campana import Campana
from modelo.catalogos import INTEGRANTES_MAXIMOS, TIPOS_EVENTO, TURNOS_MAXIMOS, UNIDAD, UNIDADES
from modelo.combate import (ABANDONADA, CERRADO, ETAPA_1, ETAPA_2, FINALIZADA, PREPARACION, AtaqueTipo,
                            ConsolaDesactualizada, EtapaCombate, MotorCombate, repartir_proporcional)
from modelo.errores import ReglaInvalida
from modelo.estrategias import obtener_estrategia
from modelo.legatus import Legatus
from modelo.legion import Legion
from modelo.unidades import CLASES, Ballesta, Caballeria, EsclavoAuxiliar, Ingeniero, Legionario

TRIPLEX = obtener_estrategia("triplex")
CUNEUS = obtener_estrategia("cuneus")
ORBIS = obtener_estrategia("orbis")

INSTANTES = {"creada", "actualizada", "creado", "actualizado", "instante"}


# --- Fábricas de escenarios ----------------------------------------------------------------

def legion_con(bono_atk=0, bono_def=0, presupuesto=1_000_000, **tropas):
    """Legión suelta (sin campaña) con un Legatus y las tropas indicadas, todas con HP completo."""
    legion = Legion("Legio de prueba", 1, Legatus("Legatus de prueba", bono_atk, bono_def), presupuesto, id=1)
    if any(tropas.values()):
        legion.contratar(tropas)
    return legion


def nueva_campana():
    return Campana.iniciar("Campaña de prueba", "Julio César", "Pompeyo Magno")


def agregar_legion(campana, nombre, tropas, restante=100_000, bono_atk=0, bono_def=0, consul=1):
    """Crea la legión y contrata sus tropas; le quedan `restante` denarios tras el contrato."""
    legion = campana.crear_legion(nombre, consul, f"Legatus de {nombre}", bono_atk, bono_def,
                                  Legion.costo_contrato(tropas) + restante)
    campana.contratar_tropas(legion.id, tropas)
    return legion


def campana_en_batalla(tropas_a, tropas_b, restante_a=100_000, restante_b=100_000, semilla=7):
    """Campaña con Legio A (atacante en la etapa 1) contra Legio B, con el enfrentamiento ya iniciado."""
    campana = nueva_campana()
    a = agregar_legion(campana, "Legio A", tropas_a, restante_a)
    b = agregar_legion(campana, "Legio B", tropas_b, restante_b, consul=2)
    campana.iniciar_enfrentamiento("Batalla de prueba", a.id, b.id, semilla=semilla)
    return campana, a, b


def jugar_hasta_el_final(campana, maximo=400):
    """Avanza el enfrentamiento en curso hasta que termine; devuelve cuántos pasos dio."""
    enfrentamiento = campana.enfrentamiento_activo()
    for paso in range(1, maximo + 1):
        campana.avanzar_combate()
        if not enfrentamiento.en_curso:
            return paso
    raise AssertionError(f"El enfrentamiento no terminó en {maximo} pasos.")


def sin_instantes(valor):
    """a_dict() sin fechas y horas, que dependen del reloj y no del juego."""
    if isinstance(valor, dict):
        return {clave: sin_instantes(v) for clave, v in valor.items() if clave not in INSTANTES}
    if isinstance(valor, list):
        return [sin_instantes(v) for v in valor]
    return valor


def campana_pareja():
    """Dos legiones parejas que se hacen daño en ambas etapas (escenario para el azar)."""
    campana = nueva_campana()
    agregar_legion(campana, "Legio A", {"legionario": 100, "caballeria": 60, "ballesta": 40, "esclavo": 60},
                   bono_atk=25)
    agregar_legion(campana, "Legio B", {"legionario": 100, "caballeria": 60, "ballesta": 40, "ingeniero": 20},
                   bono_atk=25, consul=2)
    return campana


# Composiciones sin daño en ninguna etapa (la defensa siempre resiste), para probar el flujo:
# Legio A en Triplex: ATK (2.500 + 100) × 1,10 = 2.860; DEF (3.500 + 250) × 1,45 = 5.437,5.
# Legio B en Triplex: ATK (45 + 750) × 1,10 = 874,5; DEF (15 + 3.000) × 1,25 = 3.768,75.
SIN_CABALLERIA = {"legionario": 100, "esclavo": 50}
SIN_LEGIONARIOS = {"caballeria": 1, "ingeniero": 150}


# --- Regla 1: Legatus ----------------------------------------------------------------------

class LegatusTests(unittest.TestCase):
    def test_bonos_dentro_del_rango(self):
        """Regla 1: los bonos de %ATK y %DEF admiten de −25 a +25, extremos incluidos."""
        for atk, defensa in ((-25, 25), (25, -25), (0, 0), (25, 25), (-25, -25)):
            legatus = Legatus("Marco Antonio", atk, defensa)
            self.assertEqual((legatus.bono_atk, legatus.bono_def), (atk, defensa))

    def test_bonos_fuera_del_rango(self):
        """Regla 1: un bono fuera de [−25, +25] lanza ReglaInvalida."""
        for atk, defensa in ((26, 0), (-26, 0), (0, 26), (0, -26), (99, 0)):
            with self.subTest(atk=atk, defensa=defensa), self.assertRaises(ReglaInvalida):
                Legatus("Marco Antonio", atk, defensa)

    def test_costo_es_la_suma_de_los_bonos(self):
        """Regla 1: %Costo = %ATK + %DEF (+10/+5 → +15; −20/+20 → 0)."""
        self.assertEqual(Legatus("Marco Antonio", 10, 5).bono_costo, 15)
        self.assertEqual(Legatus("Marco Antonio", -20, 20).bono_costo, 0)
        self.assertEqual(Legatus("Marco Antonio", -25, -25).bono_costo, -50)


# --- Regla 2: contratos --------------------------------------------------------------------

class ContratoTests(unittest.TestCase):
    def test_catalogo_del_enunciado(self):
        """Tabla 2: HP/ATK/DEF/costo de cada tipo de unidad."""
        esperado = {"legionario": (20, 25, 35, 5), "caballeria": (50, 45, 15, 12), "ballesta": (15, 60, 5, 20),
                    "ingeniero": (2, 5, 20, 10), "esclavo": (5, 2, 5, 1)}
        for tipo, valores in esperado.items():
            clase = CLASES[tipo]
            self.assertEqual((clase.hp_base, clase.atk_base, clase.def_base, clase.costo), valores, tipo)

    def test_costo_segun_el_catalogo(self):
        """Regla 2: costo = Σ cantidad × costo del catálogo."""
        cantidades = {"legionario": 10, "caballeria": 2, "ballesta": 3, "ingeniero": 4, "esclavo": 7}
        self.assertEqual(Legion.costo_contrato(cantidades), 10 * 5 + 2 * 12 + 3 * 20 + 4 * 10 + 7 * 1)

    def test_el_legatus_no_cambia_el_precio(self):
        """Regla 2: el %Costo del Legatus no modifica el precio de los contratos."""
        for atk, defensa in ((25, 25), (-25, -25), (0, 0)):
            legion = legion_con(atk, defensa, presupuesto=1000)
            _, costo = legion.contratar({"legionario": 10, "caballeria": 5})
            self.assertEqual(costo, 110)
            self.assertEqual(legion.presupuesto, 890)

    def test_unidades_llegan_con_hp_completo(self):
        """Regla 2: cada unidad contratada llega con el HP completo de su tipo."""
        legion = legion_con(legionario=3, caballeria=2, ballesta=1, ingeniero=4, esclavo=5)
        self.assertEqual(legion.contar(), {"legionario": 3, "caballeria": 2, "ballesta": 1, "ingeniero": 4, "esclavo": 5})
        for tipo in UNIDADES:
            self.assertTrue(all(unidad.hp == UNIDAD[tipo]["hp"] for unidad in legion.unidades[tipo]), tipo)

    def test_contrato_vacio(self):
        """Regla 2: un contrato sin unidades se rechaza y no cobra nada."""
        legion = legion_con(presupuesto=100)
        for vacio in ({}, {"legionario": 0, "esclavo": 0}):
            with self.subTest(contrato=vacio), self.assertRaises(ReglaInvalida):
                legion.contratar(vacio)
        self.assertEqual((legion.presupuesto, legion.integrantes()), (100, 0))

    def test_presupuesto_insuficiente(self):
        """Regla 2: si el contrato cuesta más que el presupuesto se rechaza y el presupuesto no cambia."""
        legion = legion_con(presupuesto=49)
        with self.assertRaises(ReglaInvalida):
            legion.contratar({"legionario": 10})  # 50 denarios
        self.assertEqual((legion.presupuesto, legion.integrantes()), (49, 0))
        legion.contratar({"legionario": 9})  # 45: alcanza
        self.assertEqual((legion.presupuesto, legion.integrantes()), (4, 9))

    def test_maximo_de_integrantes_por_legion(self):
        """Regla 2: una legión admite hasta 10.000 integrantes."""
        self.assertEqual(INTEGRANTES_MAXIMOS, 10_000)
        legion = legion_con(esclavo=9_990)
        with self.assertRaises(ReglaInvalida):
            legion.contratar({"legionario": 11})
        self.assertEqual(legion.integrantes(), 9_990)
        legion.contratar({"legionario": 10})
        self.assertEqual(legion.integrantes(), 10_000)
        with self.assertRaises(ReglaInvalida):
            legion.contratar({"esclavo": 1})
        with self.assertRaises(ReglaInvalida):
            legion_con(legionario=10_001)


# --- Regla 3: mantenimiento ----------------------------------------------------------------

class MantenimientoTests(unittest.TestCase):
    def test_descuento_por_esclavos(self):
        """Regla 3: 15% por cada bloque completo de 50 esclavos, con tope de 90% (decisión de diseño)."""
        casos = {0: 0, 49: 0, 50: 15, 99: 15, 100: 30, 299: 75, 300: 90, 400: 90, 10_000: 90}
        for esclavos, pct in casos.items():
            self.assertEqual(EsclavoAuxiliar.descuento_mantenimiento(esclavos), pct, esclavos)

    def test_formula_de_sueldos(self):
        """Regla 3: base × (100 + %Costo) × (100 − descuento) / 10.000.

        100 legionarios + 100 esclavos: base 500 + 100 = 600; Legatus +10/+5 → +15%; descuento 30%.
        600 × 115 × 70 / 10.000 = 483.
        """
        legion = legion_con(10, 5, legionario=100, esclavo=100)
        m = legion.calcular_mantenimiento()
        self.assertEqual((m.base, m.pct_legatus, m.pct_descuento, m.total), (600, 15, 30, 483))

    def test_sueldos_redondean_mitades_hacia_arriba(self):
        """Regla 3: 1 legionario con %Costo −50: 5 × 50 × 100 / 10.000 = 2,5 → 3 (no 2)."""
        self.assertEqual(legion_con(-25, -25, legionario=1).calcular_mantenimiento().total, 3)

    def test_sueldos_con_descuento_maximo(self):
        """Regla 3: con 400 esclavos el descuento se queda en 90%: (500 + 400) × 10% = 90."""
        m = legion_con(legionario=100, esclavo=400).calcular_mantenimiento()
        self.assertEqual((m.base, m.pct_descuento, m.total), (900, 90, 90))

    def test_pagar_sueldos(self):
        """Reglas 3 y 11: si alcanza, paga y descuenta; si no alcanza, no paga nada."""
        legion = legion_con(presupuesto=9, legionario=1)  # quedan 4 denarios; los sueldos son 5
        mantenimiento, pagado = legion.pagar_mantenimiento()
        self.assertEqual((mantenimiento.total, pagado, legion.presupuesto), (5, False, 4))
        legion.presupuesto = 5
        mantenimiento, pagado = legion.pagar_mantenimiento()
        self.assertEqual((pagado, legion.presupuesto), (True, 0))


# --- Regla 4: estrategias ------------------------------------------------------------------

class EstrategiaTests(unittest.TestCase):
    def test_modificadores_de_cada_formacion(self):
        """Regla 4 (tabla 3): Triplex +10/+10, Cuneus +45/−25 y Orbis −35/+60."""
        self.assertEqual((TRIPLEX.mod_atk, TRIPLEX.mod_def), (10, 10))
        self.assertEqual((CUNEUS.mod_atk, CUNEUS.mod_def), (45, -25))
        self.assertEqual((ORBIS.mod_atk, ORBIS.mod_def), (-35, 60))
        with self.assertRaises(ReglaInvalida):
            obtener_estrategia("testudo")

    def test_sinergia_triplex_con_la_mitad_de_legionarios(self):
        """Regla 4: con ≥50% de legionarios vivos: +35% DEF global y +15% de daño de ballestas."""
        atr = legion_con(legionario=50, ballesta=20, esclavo=30).calcular_atributos(TRIPLEX)  # justo 50%
        self.assertEqual((atr.pct_atk, atr.pct_def), (10, 10 + 35))
        self.assertEqual(atr.dano_tipo, {"ballesta": 15})

    def test_sin_sinergia_bajo_la_mitad(self):
        """Regla 4: con 49% de legionarios (los esclavos cuentan como unidades vivas) no hay sinergia."""
        atr = legion_con(legionario=49, ballesta=20, esclavo=31).calcular_atributos(TRIPLEX)
        self.assertEqual((atr.pct_atk, atr.pct_def), (10, 10))
        self.assertEqual(atr.dano_tipo, {})

    def test_cuneus(self):
        """Regla 4: Cuneus +45/−25; su caballería reparte +50% de daño y la legión recibe +50%."""
        atr = legion_con(legionario=10, caballeria=10).calcular_atributos(CUNEUS)
        self.assertEqual((atr.pct_atk, atr.pct_def), (45, -25))
        self.assertEqual(atr.dano_tipo, {"caballeria": 50})
        self.assertEqual(atr.dano_recibido, 50)

    def test_orbis(self):
        """Regla 4: Orbis −35/+60; su caballería no ataca ni suma ATK; ballestas e ingenieros son inmunes.

        ATK = (10×25 + 10×60 + 5×5) × 0,65 = 568,75 (sin la caballería).
        DEF = (10×35 + 10×15 + 10×5 + 5×20) × 1,60 = 1.040 (todas las unidades vivas).
        """
        atr = legion_con(legionario=10, caballeria=10, ballesta=10, ingeniero=5).calcular_atributos(ORBIS)
        self.assertEqual((atr.pct_atk, atr.pct_def), (-35, 60))
        self.assertEqual(atr.atk_x100, 56_875)
        self.assertEqual(atr.def_x100, 104_000)
        self.assertFalse(atr.ataca("caballeria"))
        self.assertEqual(atr.atk_tipo("caballeria"), 0)
        self.assertEqual(atr.inmunes, {"ballesta", "ingeniero"})

    def test_requisitos_de_composicion(self):
        """Regla 4: Cuneus requiere caballería y Orbis requiere legionarios; Triplex no exige nada."""
        sin_caballeria = {"legionario": 10, "caballeria": 0, "ballesta": 5, "ingeniero": 0, "esclavo": 0}
        sin_legionarios = {"legionario": 0, "caballeria": 10, "ballesta": 5, "ingeniero": 0, "esclavo": 0}
        self.assertIsNotNone(CUNEUS.validar_composicion(sin_caballeria))
        self.assertIsNone(CUNEUS.validar_composicion(sin_legionarios))
        self.assertIsNotNone(ORBIS.validar_composicion(sin_legionarios))
        self.assertIsNone(ORBIS.validar_composicion(sin_caballeria))
        self.assertIsNone(TRIPLEX.validar_composicion(sin_caballeria))

    def test_bono_de_ingenieros(self):
        """Regla 4: +1% DEF y +2% de daño de ballestas por cada 10 ingenieros completos."""
        for cantidad, bonos in {0: (0, 0), 9: (0, 0), 10: (1, 2), 25: (2, 4), 100: (10, 20)}.items():
            self.assertEqual(Ingeniero.aplicar_bono(cantidad), bonos, cantidad)

    def test_los_porcentajes_se_suman(self):
        """Regla 4: %ATK = Legatus + formación; %DEF = Legatus + formación + sinergia + ingenieros.

        Legatus +10/+5, Triplex con sinergia (60 de 90 son legionarios) y 20 ingenieros:
        %ATK = 10 + 10 = 20; %DEF = 5 + 10 + 35 + 2 = 52; ballestas: 15 + 4 = +19% de daño.
        """
        atr = legion_con(10, 5, legionario=60, ballesta=10, ingeniero=20).calcular_atributos(TRIPLEX)
        self.assertEqual((atr.pct_atk, atr.pct_def), (20, 52))
        self.assertEqual(atr.dano_tipo, {"ballesta": 19})


# --- Regla 5: ATK y DEF totales, daño de la etapa ------------------------------------------

class DanoTotalTests(unittest.TestCase):
    def test_totales_en_centesimas(self):
        """Regla 5: ATK_TOTAL = Σ vivos × ATK × (100 + %ATK)/100, guardado en centésimas.

        100 legionarios, Legatus +10/+5, Triplex con sinergia: %ATK 20 y %DEF 50.
        ATK = 100 × 25 × 1,20 = 3.000; DEF = 100 × 35 × 1,50 = 5.250.
        """
        atr = legion_con(10, 5, legionario=100).calcular_atributos(TRIPLEX)
        self.assertEqual((atr.atk_x100, atr.def_x100), (300_000, 525_000))
        self.assertEqual((atr.atk_total, atr.def_total), (3000.0, 5250.0))

    def test_todas_las_unidades_vivas_suman(self):
        """Regla 5: ingenieros y esclavos también suman su ATK y su DEF.

        10 legionarios, 10 ingenieros y 10 esclavos, sin formación (10 ingenieros → +1% DEF):
        ATK = 250 + 50 + 20 = 320; DEF = (350 + 200 + 50) × 1,01 = 606.
        """
        atr = legion_con(legionario=10, ingeniero=10, esclavo=10).calcular_atributos()
        self.assertEqual((atr.atk_x100, atr.def_x100), (32_000, 60_600))

    def test_dano_redondea_mitades_hacia_arriba(self):
        """Regla 5: daño = ATK_TOTAL − DEF_TOTAL redondeado: 180 − 31,5 = 148,5 → 149."""
        atacante = legion_con(ballesta=3).calcular_atributos()               # 3 × 60 = 180
        defensor = legion_con(bono_def=-10, legionario=1).calcular_atributos()  # 35 × 0,90 = 31,5
        self.assertEqual(MotorCombate.dano_total(atacante, defensor), (149, 149))

    def test_la_defensa_resiste(self):
        """Regla 5: si ATK_TOTAL ≤ DEF_TOTAL no hay daño (también con empate exacto)."""
        uno = legion_con(legionario=1).calcular_atributos(TRIPLEX)  # ATK 27,5 contra DEF 50,75
        self.assertEqual(MotorCombate.dano_total(uno, uno), (0, 0))
        siete_ballestas = legion_con(ballesta=7).calcular_atributos()      # ATK 420
        doce_legionarios = legion_con(legionario=12).calcular_atributos()  # DEF 420
        self.assertEqual(MotorCombate.dano_total(siete_ballestas, doce_legionarios), (0, 0))

    def test_cuneus_recibe_cincuenta_por_ciento_mas(self):
        """Regla 5: si el defensor forma en Cuneus, el daño × 1,5: 180 − 11,25 = 168,75 → 169 → 253,5 → 254."""
        atacante = legion_con(ballesta=3).calcular_atributos()
        defensor = legion_con(caballeria=1).calcular_atributos(CUNEUS)  # 15 × 0,75 = 11,25
        self.assertEqual(MotorCombate.dano_total(atacante, defensor), (169, 254))

    def test_bitacora_anota_que_la_defensa_resiste(self):
        """Regla 5: sin daño, la bitácora dice que «la defensa resiste» y no hay bajas."""
        campana, _, _ = campana_en_batalla({"legionario": 1}, {"legionario": 1})
        enfrentamiento = campana.avanzar_combate()
        etapa = enfrentamiento.turno_actual.etapas[0]
        self.assertEqual((etapa.dano, etapa.ataques, etapa.bajas), (0, [], {}))
        textos = [e.texto for e in campana.bitacora.obtener_historial(tipo="combate")]
        self.assertTrue(any("la defensa resiste" in texto for texto in textos), textos)


# --- Regla 6: reparto del daño -------------------------------------------------------------

class RepartoTests(unittest.TestCase):
    def test_ejemplo_del_enunciado(self):
        """Regla 6: 600 de daño con pesos 700/200/100 → 420/120/60."""
        self.assertEqual(repartir_proporcional(600, {"legionario": 700, "caballeria": 200, "ballesta": 100}),
                         {"legionario": 420, "caballeria": 120, "ballesta": 60})

    def test_resto_mayor(self):
        """Regla 6: 100 con pesos 1/2/4 → cuotas 14,29/28,57/57,14; el punto sobrante va al resto mayor."""
        self.assertEqual(repartir_proporcional(100, {"a": 1, "b": 2, "c": 4}), {"a": 14, "b": 29, "c": 57})

    def test_la_suma_siempre_es_exacta(self):
        """Regla 6: la suma de las partes es el total y cada parte es la cuota truncada o redondeada hacia arriba."""
        rng = random.Random(2026)
        for _ in range(300):
            total = rng.randrange(0, 5000)
            tipos = ("ballesta", "caballeria", "legionario")[:rng.randrange(1, 4)]
            pesos = {tipo: rng.randrange(1, 900) for tipo in tipos}
            partes = repartir_proporcional(total, pesos)
            self.assertEqual(sum(partes.values()), total, (total, pesos))
            suma = sum(pesos.values())
            for tipo, parte in partes.items():
                cuota = Fraction(total * pesos[tipo], suma)
                self.assertIn(parte, (math.floor(cuota), math.ceil(cuota)), (total, pesos))

    def test_reparto_en_combate(self):
        """Regla 6: en una etapa el daño se reparte según cuántos legionarios, jinetes y ballestas hay;
        los esclavos no cuentan (700/200/100 + 100 esclavos, 600 de daño → 420/120/60)."""
        atacante = legion_con(legionario=700, caballeria=200, ballesta=100, esclavo=100)
        defensora = legion_con(legionario=10)
        ataques = MotorCombate.repartir(600, atacante.calcular_atributos(), defensora, defensora.calcular_atributos())
        self.assertEqual({a.tipo: a.asignado for a in ataques}, {"legionario": 420, "caballeria": 120, "ballesta": 60})
        self.assertEqual({a.tipo: a.presupuesto for a in ataques}, {"legionario": 420, "caballeria": 120, "ballesta": 60})

    def test_bonos_de_dano_por_tipo(self):
        """Reglas 4 y 6: la sinergia de Triplex (+15%) y los ingenieros (+2% por cada 10) aumentan la parte
        de las ballestas; Cuneus aumenta 50% la de la caballería."""
        defensora = legion_con(legionario=10)
        atr_def = defensora.calcular_atributos()
        triplex = legion_con(legionario=700, caballeria=200, ballesta=100, esclavo=100).calcular_atributos(TRIPLEX)
        ataques = {a.tipo: a for a in MotorCombate.repartir(600, triplex, defensora, atr_def)}
        self.assertEqual((ataques["ballesta"].bono, ataques["ballesta"].presupuesto), (15, 69))  # 60 × 1,15
        con_ingenieros = legion_con(legionario=700, caballeria=200, ballesta=100, ingeniero=20).calcular_atributos(TRIPLEX)
        ataques = {a.tipo: a for a in MotorCombate.repartir(600, con_ingenieros, defensora, atr_def)}
        self.assertEqual((ataques["ballesta"].bono, ataques["ballesta"].presupuesto), (19, 71))  # 60 × 1,19 = 71,4
        cuneus = legion_con(legionario=700, caballeria=200, ballesta=100).calcular_atributos(CUNEUS)
        ataques = {a.tipo: a for a in MotorCombate.repartir(600, cuneus, defensora, atr_def)}
        self.assertEqual((ataques["caballeria"].bono, ataques["caballeria"].presupuesto), (50, 180))  # 120 × 1,5
        self.assertEqual(ataques["ballesta"].presupuesto, 60)

    def test_caballeria_en_orbis_no_recibe_parte(self):
        """Regla 4: en Orbis la caballería no ataca, así que el daño se reparte solo entre los demás."""
        orbis = legion_con(legionario=300, caballeria=200).calcular_atributos(ORBIS)
        defensora = legion_con(legionario=10)
        ataques = MotorCombate.repartir(600, orbis, defensora, defensora.calcular_atributos())
        self.assertEqual({a.tipo: a.asignado for a in ataques}, {"legionario": 600})


# --- Regla 7: el golpe de cada unidad ------------------------------------------------------

class GolpeTests(unittest.TestCase):
    def test_ejemplo_del_enunciado(self):
        """Regla 7: legionario con ATK 43 contra legionario con DEF 37 y 20 HP → golpe de 6 y quedan 14 HP.

        (El enunciado escribe 8 y 12, pero 43 − 37 = 6: decisión documentada del proyecto.)
        ATK 43 = 25 × 1,72; DEF 37 = 35 × (1 + 40/700), un bono no entero que solo se usa aquí
        para reproducir las cifras exactas del enunciado.
        """
        atacante = SimpleNamespace(pct_atk=72)
        defensor = SimpleNamespace(pct_def=Fraction(40, 7))
        self.assertEqual(Legionario.calcular_ataque(72), 43)
        self.assertEqual(Legionario.calcular_defensa(Fraction(40, 7)), 37)
        golpe = MotorCombate.golpe("legionario", "legionario", atacante, defensor)
        self.assertEqual(golpe, 6)
        legionario = Legionario()
        self.assertEqual(legionario.recibir_dano(golpe), 6)
        self.assertEqual(legionario.hp, 14)

    def test_golpe_con_bonos_de_legiones_reales(self):
        """Regla 7: el golpe usa ATK y DEF por unidad con todos los bonos: 25 × 1,29 − 35 × 0,75 = 6."""
        atacante = legion_con(bono_atk=19, legionario=1).calcular_atributos(TRIPLEX)          # 32,25
        defensor = legion_con(legionario=1, caballeria=1).calcular_atributos(CUNEUS)         # 26,25
        self.assertEqual(MotorCombate.golpe("legionario", "legionario", atacante, defensor), 6)

    def test_golpe_redondeado_y_minimo_de_uno(self):
        """Regla 7: el golpe se redondea (1,5 → 2) y vale 1 si la diferencia es ≤ 0 o redondea a 0."""
        ingeniero = legion_con(ingeniero=1).calcular_atributos()  # DEF 20
        uno_y_medio = legion_con(bono_atk=-14, legionario=1).calcular_atributos()  # ATK 21,5
        self.assertEqual(MotorCombate.golpe("legionario", "ingeniero", uno_y_medio, ingeniero), 2)
        un_cuarto = legion_con(bono_atk=-19, legionario=1).calcular_atributos()  # ATK 20,25
        self.assertEqual(MotorCombate.golpe("legionario", "ingeniero", un_cuarto, ingeniero), 1)
        legionarios = legion_con(legionario=1).calcular_atributos()  # ATK 25 contra DEF 35
        self.assertEqual(MotorCombate.golpe("legionario", "legionario", legionarios, legionarios), 1)

    def test_habilidades_de_ataque(self):
        """Regla 7: carga de caballería +20% contra legionarios; ballesta +50% contra caballería; nada más."""
        self.assertEqual(Caballeria.ataque(10, "legionario"), 12)
        self.assertEqual(Caballeria.ataque(3, "legionario"), 4)   # 3,6 → 4
        self.assertEqual(Ballesta.ataque(10, "caballeria"), 15)
        self.assertEqual(Ballesta.ataque(3, "caballeria"), 5)     # 4,5 → 5
        for clase, objetivo in ((Caballeria, "ballesta"), (Caballeria, "caballeria"), (Ballesta, "legionario"),
                                (Legionario, "caballeria"), (Legionario, "legionario")):
            self.assertEqual(clase.ataque(10, objetivo), 10, (clase.__name__, objetivo))

    def test_legionario_en_formacion_cerrada(self):
        """Regla 7: el legionario recibe 20% menos daño en Triplex y Orbis, pero no en Cuneus ni fuera de formación."""
        for estrategia, esperado in ((TRIPLEX, 8), (ORBIS, 8), (CUNEUS, 10), (None, 10)):
            legionario = Legionario()
            self.assertEqual(legionario.recibir_dano(10, estrategia), esperado, estrategia)
            self.assertEqual(legionario.hp, 20 - esperado)
        jinete = Caballeria()
        self.assertEqual(jinete.recibir_dano(10, TRIPLEX), 10)

    def test_minimo_uno_y_tope_del_hp(self):
        """Regla 7: cada golpe quita al menos 1 HP y nunca más del HP que le queda a la unidad."""
        legionario = Legionario()
        self.assertEqual(legionario.recibir_dano(1, TRIPLEX), 1)  # 0,8 → 1
        self.assertEqual(legionario.recibir_dano(0), 1)
        herido = Legionario(hp=3)
        self.assertEqual(herido.recibir_dano(10), 3)
        self.assertEqual(herido.hp, 0)
        self.assertFalse(herido.esta_viva())

    def test_descarga_de_un_golpe_completo(self):
        """Regla 7 en el motor: caballería (ATK 45) contra un legionario en Cuneus (DEF 26,25):
        golpe 19 (18,75), con la carga 23, tope de 20 HP → muere; el daño que sobra se pierde."""
        atr_atacante = legion_con(caballeria=1).calcular_atributos()
        defensora = legion_con(legionario=1)
        atr_defensor = defensora.calcular_atributos(CUNEUS)
        ataque = AtaqueTipo("caballeria", 1, 30, 0, 30)
        MotorCombate.descargar(ataque, atr_atacante, defensora, atr_defensor, random.Random(0))
        self.assertEqual((ataque.golpes, ataque.hp_quitado, ataque.bajas, ataque.sobrante),
                         (1, 20, {"legionario": 1}, 11))
        self.assertEqual(defensora.integrantes(), 0)

    def test_descarga_contra_legionario_en_triplex(self):
        """Regla 7 en el motor: ballesta (ATK 60) contra legionario en Triplex con sinergia (DEF 50,75):
        golpe 9 (9,25); la formación cerrada lo baja a 7 (7,2) y el legionario queda con 13 HP."""
        atr_atacante = legion_con(ballesta=1).calcular_atributos()
        defensora = legion_con(legionario=1)
        ataque = AtaqueTipo("ballesta", 1, 9, 0, 9)
        MotorCombate.descargar(ataque, atr_atacante, defensora, defensora.calcular_atributos(TRIPLEX), random.Random(0))
        self.assertEqual((ataque.golpes, ataque.hp_quitado, ataque.sobrante), (1, 7, 0))
        self.assertEqual(defensora.unidades["legionario"][0].hp, 13)


# --- Regla 8: objetivos válidos ------------------------------------------------------------

class ObjetivosTests(unittest.TestCase):
    CON_FRENTE = {"legionario": 1, "caballeria": 0, "ballesta": 5, "ingeniero": 5, "esclavo": 5}
    SIN_FRENTE = {"legionario": 0, "caballeria": 0, "ballesta": 5, "ingeniero": 5, "esclavo": 5}

    def test_cuerpo_a_cuerpo_primero_contra_legionarios_y_caballeria(self):
        """Regla 8: legionarios y caballería solo golpean legionarios o caballería mientras el enemigo tenga."""
        for clase in (Legionario, Caballeria):
            self.assertEqual(set(clase.objetivos(self.CON_FRENTE, TRIPLEX)), {"legionario", "caballeria"})
            self.assertEqual(set(clase.objetivos(self.SIN_FRENTE, TRIPLEX)), {"ballesta", "ingeniero", "esclavo"})

    def test_caballeria_en_cuneus_alcanza_esclavos(self):
        """Regla 8: en Cuneus la caballería también puede golpear esclavos (los legionarios no)."""
        self.assertEqual(set(Caballeria.objetivos(self.CON_FRENTE, CUNEUS)), {"legionario", "caballeria", "esclavo"})
        self.assertNotIn("esclavo", Legionario.objetivos(self.CON_FRENTE, CUNEUS))
        cuneus = legion_con(caballeria=10).calcular_atributos(CUNEUS)
        triplex = legion_con(caballeria=10).calcular_atributos(TRIPLEX)
        defensora = legion_con(legionario=5, esclavo=5)
        atr_def = defensora.calcular_atributos(TRIPLEX)
        self.assertEqual(set(MotorCombate.objetivos("caballeria", cuneus, defensora, atr_def)), {"legionario", "esclavo"})
        self.assertEqual(set(MotorCombate.objetivos("caballeria", triplex, defensora, atr_def)), {"legionario"})

    def test_ballestas_atacan_a_cualquiera(self):
        """Regla 8: las ballestas pueden golpear cualquier tipo de unidad."""
        self.assertEqual(set(Ballesta.objetivos(self.CON_FRENTE)), set(UNIDADES))

    def test_ingenieros_y_esclavos_no_atacan(self):
        """Regla 8: ingenieros y esclavos nunca atacan ni reciben parte del daño."""
        self.assertFalse(Ingeniero.puede_atacar or EsclavoAuxiliar.puede_atacar)
        self.assertEqual((Ingeniero.objetivos(self.CON_FRENTE), EsclavoAuxiliar.objetivos(self.CON_FRENTE)), ((), ()))
        atacante = legion_con(legionario=1, ingeniero=50, esclavo=50).calcular_atributos()
        defensora = legion_con(legionario=10)
        ataques = MotorCombate.repartir(100, atacante, defensora, defensora.calcular_atributos())
        self.assertEqual([(a.tipo, a.asignado) for a in ataques], [("legionario", 100)])

    def test_la_retaguardia_queda_a_salvo_mientras_haya_frente(self):
        """Regla 8 en una etapa: con legionarios enemigos vivos, la infantería no toca las ballestas.

        60 legionarios (Legatus +25 ATK, sin formación): ATK 1.875. Defensa: 50 legionarios y 10
        ballestas con Legatus −25 DEF: (1.750 + 50) × 0,75 = 1.350. Daño 525 en golpes de
        31,25 − 26,25 = 5: los legionarios pierden justo 525 HP y las ballestas, nada.
        """
        atacante = legion_con(bono_atk=25, legionario=60)
        defensora = legion_con(bono_def=-25, legionario=50, ballesta=10)
        etapa = EtapaCombate(1, "a")
        MotorCombate.resolver(etapa, defensora, atacante.calcular_atributos(), defensora.calcular_atributos(),
                              random.Random(5))
        self.assertEqual(etapa.dano, 525)
        self.assertEqual(defensora.hp_actual("legionario"), 1000 - 525)
        self.assertEqual((defensora.contar()["ballesta"], defensora.hp_actual("ballesta")), (10, 150))

    def test_orbis_protege_ballestas_e_ingenieros(self):
        """Reglas 4 y 8: contra Orbis nadie golpea ballestas ni ingenieros; el daño sobrante se pierde."""
        atacante = legion_con(ballesta=200).calcular_atributos(TRIPLEX)
        defensora = legion_con(legionario=5, ballesta=30, ingeniero=30)
        atr_def = defensora.calcular_atributos(ORBIS)
        etapa = EtapaCombate(1, "a")
        MotorCombate.resolver(etapa, defensora, atacante, atr_def, random.Random(1))
        self.assertGreater(etapa.dano, 0)
        self.assertEqual(etapa.bajas, {"legionario": 5})
        self.assertEqual(defensora.contar(), {"legionario": 0, "caballeria": 0, "ballesta": 30, "ingeniero": 30, "esclavo": 0})
        self.assertEqual(defensora.hp_actual(), 30 * 15 + 30 * 2)
        self.assertEqual(MotorCombate.objetivos("ballesta", atacante, defensora, atr_def), ())
        self.assertGreater(etapa.ataques[0].sobrante, 0)


# --- Regla 9: determinismo -----------------------------------------------------------------

class DeterminismoTests(unittest.TestCase):
    def test_misma_semilla_mismo_resultado(self):
        """Regla 9: dos batallas creadas desde la misma campaña y con la misma semilla terminan igual."""
        datos = campana_pareja().a_dict()
        resultados = []
        for _ in range(2):
            campana = Campana.desde_dict(datos)
            campana.iniciar_enfrentamiento("Batalla", 1, 2, semilla=2026)
            jugar_hasta_el_final(campana)
            resultados.append(sin_instantes(campana.a_dict()))
        self.assertEqual(resultados[0], resultados[1])
        self.assertNotEqual(resultados[0]["legiones"], datos["legiones"])  # hubo combate de verdad

    def test_guardar_y_recuperar_a_mitad_no_cambia_el_resultado(self):
        """Regla 9 (y docstring de modelo/combate.py: «una partida guardada y recuperada da el mismo
        resultado»): dos campañas con el mismo a_dict() y la misma semilla deben seguir igual.

        El motor sortea los objetivos por posición en las listas de unidades; por eso cada etapa
        las ordena primero por HP, el mismo orden con que se cargan de la base de datos.
        """
        original = campana_pareja()
        original.iniciar_enfrentamiento("Batalla", 1, 2, semilla=12345)
        for _ in range(3):
            original.avanzar_combate()
        copia = Campana.desde_dict(original.a_dict())
        for campana in (original, copia):
            jugar_hasta_el_final(campana)
        self.assertEqual(sin_instantes(copia.a_dict()), sin_instantes(original.a_dict()))


# --- Regla 10: flujo del enfrentamiento ----------------------------------------------------

class FlujoCombateTests(unittest.TestCase):
    def setUp(self):
        self.campana, self.a, self.b = campana_en_batalla(SIN_CABALLERIA, SIN_LEGIONARIOS)
        self.enfrentamiento = self.campana.enfrentamiento_activo()

    def estado(self):
        e = self.enfrentamiento
        return e.turno_numero, e.turno_actual.fase, e.pasos

    def cerrar_turno_1(self):
        for _ in range(3):
            self.campana.avanzar_combate()
        self.assertEqual(self.estado(), (2, PREPARACION, 3))

    def test_fases_de_un_turno(self):
        """Regla 10: cada llamada resuelve un paso: etapa 1 (a ataca), etapa 2 (b ataca) y cierre con
        sueldos, que abre el turno siguiente en preparación."""
        self.assertEqual(self.estado(), (1, PREPARACION, 0))
        self.campana.avanzar_combate()
        self.assertEqual(self.estado(), (1, ETAPA_1, 1))
        self.assertEqual([e.atacante for e in self.enfrentamiento.turno_actual.etapas], ["a"])
        self.campana.avanzar_combate()
        self.assertEqual(self.estado(), (1, ETAPA_2, 2))
        self.assertEqual([e.atacante for e in self.enfrentamiento.turno_actual.etapas], ["a", "b"])
        presupuestos = (self.a.presupuesto, self.b.presupuesto)
        self.campana.avanzar_combate()
        turno_1 = self.enfrentamiento.turnos[0]
        self.assertEqual(turno_1.fase, CERRADO)
        # Sueldos: A (500 + 50) × 0,85 = 467,5 → 468; B 12 + 1.500 = 1.512.
        self.assertEqual(turno_1.sueldos, {"a": {"total": 468, "pagado": True}, "b": {"total": 1512, "pagado": True}})
        self.assertEqual((self.a.presupuesto, self.b.presupuesto), (presupuestos[0] - 468, presupuestos[1] - 1512))
        self.assertEqual(self.estado(), (2, PREPARACION, 3))

    def test_paso_desactualizado(self):
        """Regla 10: si la consola manda un paso viejo se lanza ConsolaDesactualizada y nada cambia."""
        self.campana.avanzar_combate(paso=0)
        antes = sin_instantes(self.campana.a_dict())
        with self.assertRaises(ConsolaDesactualizada):
            self.campana.avanzar_combate(paso=0)
        self.assertEqual(sin_instantes(self.campana.a_dict()), antes)
        self.campana.avanzar_combate(paso=1)
        self.assertEqual(self.enfrentamiento.pasos, 2)

    def test_primer_turno_solo_triplex(self):
        """Regla 10: en el turno 1 ambas legiones forman en Triplex Acies; otra formación se rechaza."""
        for lado in ("a", "b"):
            for formacion in ("cuneus", "orbis"):
                with self.subTest(lado=lado, formacion=formacion), self.assertRaises(ReglaInvalida):
                    self.campana.avanzar_combate({lado: {"formacion": formacion}})
        self.assertEqual(self.estado(), (1, PREPARACION, 0))
        self.campana.avanzar_combate({"a": {"formacion": "triplex"}, "b": {"formacion": "triplex"}})
        self.assertEqual(self.estado(), (1, ETAPA_1, 1))

    def test_primer_turno_sin_conversiones(self):
        """Regla 10: en el turno 1 no se pueden convertir esclavos."""
        with self.assertRaises(ReglaInvalida):
            self.campana.avanzar_combate({"a": {"convertir": {"legionario": 5}}})
        self.assertEqual((self.a.contar()["esclavo"], self.enfrentamiento.pasos), (50, 0))

    def test_desde_el_turno_2_la_formacion_depende_de_la_composicion(self):
        """Regla 10: desde el turno 2, Cuneus sin caballería u Orbis sin legionarios se rechazan."""
        self.cerrar_turno_1()
        with self.assertRaises(ReglaInvalida):
            self.campana.avanzar_combate({"a": {"formacion": "cuneus"}})
        with self.assertRaises(ReglaInvalida):
            self.campana.avanzar_combate({"b": {"formacion": "orbis"}})
        self.assertEqual(self.estado(), (2, PREPARACION, 3))
        self.campana.avanzar_combate({"a": {"formacion": "orbis"}, "b": {"formacion": "cuneus"}})
        self.assertEqual(self.enfrentamiento.turno_actual.formaciones, {"a": "orbis", "b": "cuneus"})
        self.assertEqual(self.estado(), (2, ETAPA_1, 4))

    def test_decisiones_se_aplican_todas_o_ninguna(self):
        """Regla 10: si la decisión de b es inválida, la de a (válida) tampoco se aplica."""
        self.cerrar_turno_1()
        antes = sin_instantes(self.campana.a_dict())
        with self.assertRaises(ReglaInvalida):
            self.campana.avanzar_combate({"a": {"formacion": "orbis", "convertir": {"legionario": 10}},
                                          "b": {"formacion": "orbis"}})
        self.assertEqual(sin_instantes(self.campana.a_dict()), antes)
        self.assertEqual(self.a.contar()["esclavo"], 50)

    def test_conversion_de_esclavos(self):
        """Regla 10: los esclavos se convierten en legionarios (5) o caballería (12), primero los más
        heridos, y las unidades nuevas llegan con HP completo."""
        self.cerrar_turno_1()
        for esclavo, hp in zip(self.a.unidades["esclavo"], (4, 1, 3, 2, 4, 2, 3)):
            esclavo.hp = hp
        presupuesto = self.a.presupuesto
        self.campana.avanzar_combate({"a": {"convertir": {"legionario": 3, "caballeria": 2}}})
        conteo = self.a.contar()
        self.assertEqual((conteo["legionario"], conteo["caballeria"], conteo["esclavo"]), (103, 2, 45))
        self.assertEqual(self.a.presupuesto, presupuesto - (3 * 5 + 2 * 12))
        # Se fueron los cinco más heridos (1, 2, 2, 3, 3): quedan los dos de 4 HP y el resto sanos.
        self.assertEqual(sorted(e.hp for e in self.a.unidades["esclavo"]), [4, 4] + [5] * 43)
        self.assertTrue(all(u.hp == 20 for u in self.a.unidades["legionario"]))
        self.assertTrue(all(u.hp == 50 for u in self.a.unidades["caballeria"]))
        participante = self.enfrentamiento.participantes["a"]
        self.assertEqual((participante.convertidos, participante.gastos), ({"legionario": 3, "caballeria": 2}, 39))
        self.assertEqual(len(self.campana.bitacora.obtener_historial(tipo="conversion")), 1)

    def test_limites_de_la_conversion(self):
        """Regla 10: no se convierten más esclavos de los que hay, ni se paga más que el presupuesto,
        ni se convierten en ballestas o ingenieros."""
        self.cerrar_turno_1()
        self.a.presupuesto = 11
        invalidas = [{"legionario": 51}, {"legionario": 30, "caballeria": 21}, {"caballeria": 1},
                     {"ballesta": 1}, {"ingeniero": 1}]
        for convertir in invalidas:
            with self.subTest(convertir=convertir), self.assertRaises(ReglaInvalida):
                self.campana.avanzar_combate({"a": {"convertir": convertir}})
        self.assertEqual((self.a.contar()["esclavo"], self.a.presupuesto, self.enfrentamiento.pasos), (50, 11, 3))
        with self.assertRaises(ValueError):
            EsclavoAuxiliar().convertir("ballesta")
        self.campana.avanzar_combate({"a": {"convertir": {"legionario": 2}}})  # 10 denarios: alcanza
        self.assertEqual((self.a.contar()["esclavo"], self.a.presupuesto), (48, 1))

    def test_refuerzos_solo_en_la_preparacion(self):
        """Regla 10: los refuerzos se contratan en la preparación de un turno, no después de una etapa."""
        presupuesto = self.a.presupuesto
        self.campana.contratar_refuerzos("a", {"legionario": 10})
        self.assertEqual((self.a.contar()["legionario"], self.a.presupuesto), (110, presupuesto - 50))
        participante = self.enfrentamiento.participantes["a"]
        self.assertEqual((participante.contratados["legionario"], participante.gastos), (10, 50))
        self.campana.avanzar_combate()
        with self.assertRaises(ReglaInvalida):
            self.campana.contratar_refuerzos("a", {"legionario": 10})
        self.assertEqual((self.a.contar()["legionario"], self.a.presupuesto), (110, presupuesto - 50))
        self.campana.avanzar_combate()
        self.campana.avanzar_combate()
        self.campana.contratar_refuerzos("b", {"caballeria": 1})  # preparación del turno 2
        self.assertEqual(self.b.contar()["caballeria"], 2)
        with self.assertRaises(ReglaInvalida):
            self.campana.contratar_refuerzos("c", {"legionario": 1})


# --- Regla 11: fin del enfrentamiento ------------------------------------------------------

class FinDelCombateTests(unittest.TestCase):
    def test_cae_la_defensora_en_la_etapa_1(self):
        """Regla 11: si a la defensora solo le quedan esclavos tras la etapa 1, pierde sin etapa 2."""
        campana, a, b = campana_en_batalla({"ballesta": 100}, {"legionario": 1, "esclavo": 50})
        enfrentamiento = campana.avanzar_combate()
        self.assertEqual((enfrentamiento.estado, enfrentamiento.ganador), (FINALIZADA, "a"))
        self.assertEqual(len(enfrentamiento.turno_actual.etapas), 1)
        self.assertFalse(b.tiene_combatientes())
        self.assertIsNone(campana.enfrentamiento_activo())
        with self.assertRaises(ReglaInvalida):
            campana.avanzar_combate()

    def test_cae_la_atacante_en_la_etapa_2(self):
        """Regla 11: el fin se revisa también tras la etapa 2 (b arrasa a a)."""
        campana, a, b = campana_en_batalla({"legionario": 1}, {"ballesta": 20})
        campana.avanzar_combate()
        enfrentamiento = campana.avanzar_combate()
        self.assertEqual((enfrentamiento.estado, enfrentamiento.ganador), (FINALIZADA, "b"))
        self.assertEqual(enfrentamiento.turno_actual.fase, ETAPA_2)
        self.assertEqual(a.integrantes(), 0)

    def test_quien_no_paga_los_sueldos_pierde(self):
        """Regla 11: la legión que no alcanza a pagar los sueldos no paga nada y pierde."""
        campana, a, b = campana_en_batalla({"legionario": 1}, {"legionario": 1}, restante_a=4, restante_b=100)
        for _ in range(3):
            enfrentamiento = campana.avanzar_combate()
        self.assertEqual((enfrentamiento.estado, enfrentamiento.ganador), (FINALIZADA, "b"))
        self.assertEqual(enfrentamiento.turno_actual.sueldos,
                         {"a": {"total": 5, "pagado": False}, "b": {"total": 5, "pagado": True}})
        self.assertEqual((a.presupuesto, b.presupuesto), (4, 95))
        self.assertEqual(len(enfrentamiento.turnos), 1)

    def test_si_ninguna_paga_es_empate(self):
        """Regla 11: si ninguna legión puede pagar los sueldos, el enfrentamiento termina sin vencedor."""
        campana, a, b = campana_en_batalla({"legionario": 1}, {"legionario": 1}, restante_a=4, restante_b=3)
        for _ in range(3):
            enfrentamiento = campana.avanzar_combate()
        self.assertEqual((enfrentamiento.estado, enfrentamiento.ganador), (FINALIZADA, None))
        self.assertEqual((a.presupuesto, b.presupuesto), (4, 3))

    def test_empate_al_llegar_al_maximo_de_turnos(self):
        """Regla 11: tras 100 turnos sin que nadie caiga ni quede sin fondos, empate (decisión de diseño)."""
        self.assertEqual(TURNOS_MAXIMOS, 100)
        campana, a, b = campana_en_batalla({"legionario": 1}, {"legionario": 1}, restante_a=1000, restante_b=1000)
        pasos = jugar_hasta_el_final(campana)
        enfrentamiento = campana.ultimo_enfrentamiento()
        self.assertEqual(pasos, 3 * TURNOS_MAXIMOS)
        self.assertEqual((enfrentamiento.estado, enfrentamiento.ganador), (FINALIZADA, None))
        self.assertEqual((enfrentamiento.turno_numero, enfrentamiento.turno_actual.fase), (100, CERRADO))
        self.assertEqual((a.presupuesto, b.presupuesto), (500, 500))

    def test_abandonar(self):
        """Regla 11: abandonar deja el enfrentamiento «abandonada», sin vencedor."""
        campana, a, b = campana_en_batalla(SIN_CABALLERIA, SIN_LEGIONARIOS)
        campana.avanzar_combate()
        enfrentamiento = campana.abandonar_combate()
        self.assertEqual((enfrentamiento.estado, enfrentamiento.ganador), (ABANDONADA, None))
        self.assertIsNone(campana.enfrentamiento_activo())
        with self.assertRaises(ReglaInvalida):
            campana.abandonar_combate()

    def test_un_solo_enfrentamiento_en_curso(self):
        """Regla 11: no se puede iniciar un segundo enfrentamiento mientras otro sigue en curso."""
        campana, a, b = campana_en_batalla(SIN_CABALLERIA, SIN_LEGIONARIOS)
        c = agregar_legion(campana, "Legio C", {"legionario": 10})
        d = agregar_legion(campana, "Legio D", {"legionario": 10}, consul=2)
        with self.assertRaises(ReglaInvalida):
            campana.iniciar_enfrentamiento("Otra batalla", c.id, d.id)
        campana.abandonar_combate()
        campana.iniciar_enfrentamiento("Otra batalla", c.id, d.id)
        self.assertEqual(len(campana.enfrentamientos), 2)

    def test_legion_en_combate_bloqueada(self):
        """Regla 11: una legión en combate no se configura, disuelve ni contrata por el flujo normal."""
        campana, a, b = campana_en_batalla(SIN_CABALLERIA, SIN_LEGIONARIOS)
        c = agregar_legion(campana, "Legio C", {"legionario": 10})
        for legion in (a, b):
            with self.assertRaises(ReglaInvalida):
                campana.configurar_legion(legion.id, "Legio Nueva", 1, "Otro", 0, 0, 10)
            with self.assertRaises(ReglaInvalida):
                campana.eliminar_legion(legion.id)
            with self.assertRaises(ReglaInvalida):
                campana.contratar_tropas(legion.id, {"legionario": 1})
        self.assertEqual(a.nombre, "Legio A")
        # Una legión que no combate sí se puede cambiar.
        campana.contratar_tropas(c.id, {"legionario": 1})
        self.assertTrue(campana.configurar_legion(c.id, "Legio C", 2, "Otro", 5, 5, 50))
        campana.abandonar_combate()
        campana.eliminar_legion(a.id)
        self.assertNotIn(a.id, campana.legiones)


# --- Regla 12: bitácora --------------------------------------------------------------------

class BitacoraTests(unittest.TestCase):
    def test_eventos_numerados_y_con_tipo_valido(self):
        """Regla 12: los sucesos se numeran 1..n y su tipo pertenece a TIPOS_EVENTO."""
        campana = campana_pareja()
        campana.iniciar_enfrentamiento("Batalla", 1, 2, semilla=11)
        jugar_hasta_el_final(campana)
        eventos = campana.bitacora.eventos
        self.assertEqual([e.numero for e in eventos], list(range(1, len(eventos) + 1)))
        self.assertTrue(set(e.tipo for e in eventos) <= set(TIPOS_EVENTO))
        self.assertTrue({"sistema", "legion", "contrato", "estrategia", "combate", "bajas", "economia", "fin"}
                        <= set(e.tipo for e in eventos))
        with self.assertRaises(ValueError):
            campana.bitacora.registrar_suceso("chisme", "Un tipo que no existe.")

    def test_filtros_del_historial(self):
        """Regla 12: obtener_historial filtra por enfrentamiento, turno, tipo y texto (sin distinguir mayúsculas)."""
        bitacora = Bitacora()
        bitacora.registrar_suceso("sistema", "Comienza la campaña.")
        bitacora.registrar_suceso("combate", "Etapa 1: Legio A ataca a Legio B.", turno=1, etapa=1, enfrentamiento=1)
        bitacora.registrar_suceso("bajas", "Legio B pierde 3 unidades.", turno=1, etapa=1, enfrentamiento=1)
        bitacora.registrar_suceso("combate", "Etapa 1: Legio C ataca a Legio A.", turno=1, etapa=1, enfrentamiento=2)
        bitacora.registrar_suceso("economia", "Legio A paga 500 denarios.", turno=2, etapa=3, enfrentamiento=1)

        def numeros(**filtros):
            return [e.numero for e in bitacora.obtener_historial(**filtros)]

        self.assertEqual(numeros(), [1, 2, 3, 4, 5])
        self.assertEqual(numeros(enfrentamiento=1), [2, 3, 5])
        self.assertEqual(numeros(turno=1), [2, 3, 4])
        self.assertEqual(numeros(tipo="combate"), [2, 4])
        self.assertEqual(numeros(texto="LEGIO a"), [2, 4, 5])
        self.assertEqual(numeros(enfrentamiento=1, tipo="combate", texto="ataca"), [2])
        self.assertEqual(numeros(texto="no aparece"), [])
        self.assertEqual(numeros(desde=3), [4, 5])


if __name__ == "__main__":
    unittest.main()
