// Pede confirmação em formulários com data-confirmar, como a exclusão de treino.
document.addEventListener("submit", (evento) => {
  const mensagem = evento.target.dataset.confirmar;
  if (mensagem && !window.confirm(mensagem)) {
    evento.preventDefault();
  }
});

// Adiciona e remove linhas de exercício no formulário de treino.
document.addEventListener("click", (evento) => {
  if (evento.target.closest("#adicionar-linha")) {
    const modelo = document.getElementById("modelo-linha");
    document.getElementById("linhas").append(modelo.content.cloneNode(true));
    return;
  }

  const remover = evento.target.closest(".remover-linha");
  if (remover) {
    remover.closest(".linha-exercicio").remove();
  }
});
