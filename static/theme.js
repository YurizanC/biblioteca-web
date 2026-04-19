document.addEventListener("DOMContentLoaded", () => {
    const botonTema = document.getElementById("toggle-tema");
    const temaGuardado = localStorage.getItem("tema");

    if (temaGuardado === "claro") {
        document.body.classList.add("tema-claro");
    }

    if (botonTema) {
        botonTema.addEventListener("click", () => {
            document.body.classList.toggle("tema-claro");

            if (document.body.classList.contains("tema-claro")) {
                localStorage.setItem("tema", "claro");
            } else {
                localStorage.setItem("tema", "oscuro");
            }
        });
    }
});