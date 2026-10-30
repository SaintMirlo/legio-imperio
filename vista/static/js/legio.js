/* Comportamiento de la vista del prototipo (Hito 2).
   Aquí no hay reglas del juego: solo avisos, diálogos de archivo y navegación. */
(() => {
  const avisos = document.getElementById("avisos");

  function cerrarDespues(aviso) {
    setTimeout(() => aviso.classList.add("saliendo"), 6000);
  }

  function avisar(texto, categoria = "info") {
    const aviso = document.createElement("div");
    aviso.className = `aviso aviso-${categoria}`;
    aviso.setAttribute("role", "status");
    const mensaje = document.createElement("span");
    mensaje.textContent = texto;
    const cerrar = document.createElement("button");
    cerrar.type = "button";
    cerrar.className = "aviso-cerrar";
    cerrar.setAttribute("aria-label", "Cerrar aviso");
    cerrar.textContent = "×";
    aviso.append(mensaje, cerrar);
    avisos.append(aviso);
    cerrarDespues(aviso);
  }

  avisos.querySelectorAll(".aviso").forEach(cerrarDespues);
  avisos.addEventListener("click", (evento) => {
    const boton = evento.target.closest(".aviso-cerrar");
    if (boton) boton.closest(".aviso").remove();
  });
  avisos.addEventListener("animationend", (evento) => {
    if (evento.animationName === "aviso-sale") evento.target.remove();
  });

  // CU013 Guardar campaña: abre el diálogo «Guardar como» del sistema si el navegador
  // lo permite (Chrome y Edge); si no, descarga el archivo.
  document.querySelectorAll("[data-guardar]").forEach((boton) => {
    boton.addEventListener("click", async () => {
      const nombre = boton.dataset.nombre;
      try {
        const respuesta = await fetch(boton.dataset.guardar);
        const contenido = await respuesta.blob();
        if ("showSaveFilePicker" in window) {
          const archivo = await window.showSaveFilePicker({
            suggestedName: nombre,
            types: [{ description: "Campaña de Legio Imperium", accept: { "application/json": [".json"] } }],
          });
          const escritura = await archivo.createWritable();
          await escritura.write(contenido);
          await escritura.close();
          avisar(`Campaña guardada en «${archivo.name}».`, "exito");
        } else {
          const enlace = document.createElement("a");
          enlace.href = URL.createObjectURL(contenido);
          enlace.download = nombre;
          enlace.click();
          URL.revokeObjectURL(enlace.href);
          avisar(`Campaña guardada como «${nombre}».`, "exito");
        }
      } catch (error) {
        if (error.name === "AbortError") avisar("Guardado cancelado.", "info");
        else avisar("No se pudo guardar la campaña.", "error");
      }
    });
  });

  // CU014 Cargar campaña: el selector de archivos del sistema; al elegir uno se envía.
  const cargar = document.querySelector("[data-cargar]");
  cargar?.addEventListener("change", () => {
    if (cargar.files.length) cargar.form.submit();
  });
  document.querySelectorAll("[data-abrir-cargar]").forEach((boton) => {
    boton.addEventListener("click", () => cargar?.click());
  });

  // Deslizadores del Legatus: muestran su valor y el %Costo resultante (%ATK + %DEF).
  const conSigno = (n) => (n > 0 ? `+${n}%` : n < 0 ? `−${-n}%` : "0%");
  const bonos = [...document.querySelectorAll("[data-bono]")];
  const costo = document.getElementById("bono-costo");
  function refrescarBonos() {
    let suma = 0;
    for (const deslizador of bonos) {
      const valor = Number(deslizador.value);
      suma += valor;
      document.querySelector(`output[for="${deslizador.id}"]`).textContent = conSigno(valor);
    }
    if (costo) costo.textContent = conSigno(suma);
  }
  bonos.forEach((deslizador) => deslizador.addEventListener("input", refrescarBonos));

  // Modo automático de la consola de batalla: avanza solo tras una cuenta regresiva.
  const siguiente = document.getElementById("form-siguiente");
  if (siguiente?.dataset.autoSegundos) {
    let quedan = Number(siguiente.dataset.autoSegundos);
    const cuenta = siguiente.querySelector("[data-cuenta]");
    const reloj = setInterval(() => {
      quedan -= 1;
      if (cuenta) cuenta.textContent = quedan;
      if (quedan > 0) return;
      clearInterval(reloj);
      const automatico = siguiente.querySelector('[name="auto"]');
      if (siguiente.requestSubmit) {
        siguiente.requestSubmit(automatico);
      } else {
        siguiente.append(Object.assign(document.createElement("input"), { type: "hidden", name: "auto", value: "1" }));
        siguiente.submit();
      }
    }, 1000);
  }

  // Consolas de eventos: deja a la vista el último suceso.
  document.querySelectorAll("[data-autoscroll]").forEach((lista) => {
    lista.scrollTop = lista.scrollHeight;
  });

  // Visor de bitácora: filtra por turno, tipo y texto (solo oculta filas).
  const filtros = document.querySelector("[data-filtros-bitacora]");
  if (filtros) {
    const filas = [...document.querySelectorAll(".bitacora tbody tr")];
    const cuenta = filtros.querySelector("[data-cuenta-eventos]");
    const sinResultados = document.querySelector("[data-sin-resultados]");
    const filtrar = () => {
      const turno = filtros.elements.turno.value;
      const tipo = filtros.elements.tipo.value;
      const texto = filtros.elements.texto.value.trim().toLowerCase();
      let visibles = 0;
      for (const fila of filas) {
        const visible = (!turno || fila.dataset.turno === turno)
          && (!tipo || fila.dataset.tipo === tipo)
          && (!texto || fila.textContent.toLowerCase().includes(texto));
        fila.hidden = !visible;
        if (visible) visibles += 1;
      }
      cuenta.textContent = visibles;
      sinResultados.hidden = visibles > 0;
    };
    filtros.addEventListener("input", filtrar);
    filtros.addEventListener("submit", (evento) => evento.preventDefault());
  }
})();
