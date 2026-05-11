const steps = [
  {
    title: "Crear una funcion Python",
    goal: "Empieza con una funcion simple que quieras convertir en Flask.",
    template: "function-step-template",
  },
  {
    title: "Entender el analisis",
    goal: "Comprueba que el agente ha detectado la funcion y sus parametros.",
    template: "analysis-step-template",
  },
  {
    title: "Elegir interfaz",
    goal: "Decide si la funcion sera una pagina, una API JSON o ambas.",
    template: "interface-step-template",
  },
  {
    title: "Crear service",
    goal: "Separa la logica Python de la logica web.",
    template: "service-step-template",
  },
  {
    title: "Crear route",
    goal: "Conecta una URL Flask con la funcion del service.",
    template: "route-step-template",
  },
  {
    title: "Crear template o API",
    goal: "Genera la salida visible o JSON segun la interfaz elegida.",
    template: "template-step-template",
  },
  {
    title: "Montar app factory",
    goal: "Registra los blueprints y deja la aplicacion ensamblada.",
    template: "factory-step-template",
  },
  {
    title: "Extender Flask",
    goal: "Anade capacidades Flask de forma incremental.",
    template: "extend-step-template",
  },
];

const examples = {
  hello: 'def hola_mundo():\n    return "Hola mundo"',
  greet: 'def saludar(nombre):\n    return f"Hola {nombre}"',
  sum: "def sumar(a, b):\n    return int(a) + int(b)",
};

const userId = document.querySelector("#user-id").textContent;
const stepTabs = Array.from(document.querySelectorAll(".step-tab"));
const stepKicker = document.querySelector("#step-kicker");
const stepTitle = document.querySelector("#step-title");
const stepGoal = document.querySelector("#step-goal");
const currentStepState = document.querySelector("#current-step-state");
const currentStepActions = document.querySelector("#current-step-actions");
const recommendedNext = document.querySelector("#recommended-next");
const stepBody = document.querySelector("#step-body");
const prevStepButton = document.querySelector("#prev-step-button");
const nextStepButton = document.querySelector("#next-step-button");
const stateButton = document.querySelector("#state-button");
const llmButton = document.querySelector("#llm-button");
const resetButton = document.querySelector("#reset-button");
const clearLogButton = document.querySelector("#clear-log-button");
const processStateButton = document.querySelector("#process-state-button");
const processSteps = document.querySelector("#process-steps");
const processInteractions = document.querySelector("#process-interactions");
const processValues = document.querySelector("#process-values");
const processNext = document.querySelector("#process-next");
const stateSummary = document.querySelector("#state-summary");
const conversationLog = document.querySelector("#conversation-log");
const artifactList = document.querySelector("#artifact-list");

let currentStep = Number(window.localStorage.getItem("flaskTutor.currentStep") || "0");
let maxStepReached = Number(window.localStorage.getItem("flaskTutor.maxStepReached") || "0");
let latestState = null;
let latestNextAction = "";
let interactionHistory = [];
let busy = false;

renderStep();
renderProcessControl();
refreshState();

stepTabs.forEach((tab) => {
  tab.addEventListener("click", () => {
    currentStep = Number(tab.dataset.step);
    rememberStep();
    renderStep();
  });
});

prevStepButton.addEventListener("click", () => {
  currentStep = Math.max(0, currentStep - 1);
  rememberStep();
  renderStep();
});

nextStepButton.addEventListener("click", () => {
  if (!canContinueFromCurrentStep()) {
    return;
  }
  currentStep = Math.min(steps.length - 1, currentStep + 1);
  maxStepReached = Math.max(maxStepReached, currentStep);
  rememberStep();
  renderStep();
});

stateButton.addEventListener("click", () => {
  sendAgentMessage("estado", { silentAdvance: true });
});

processStateButton.addEventListener("click", () => {
  sendAgentMessage("estado", { silentAdvance: true });
});

llmButton.addEventListener("click", showLlmStatus);

resetButton.addEventListener("click", async () => {
  const confirmed = window.confirm("Reiniciar el estado del alumno?");
  if (!confirmed) {
    return;
  }
  await sendAgentMessage("reset", { nextStep: 0, silentAdvance: true });
  currentStep = 0;
  maxStepReached = 0;
  latestState = null;
  window.localStorage.removeItem("flaskTutor.interfaceSelected");
  rememberStep();
  renderStep();
});

clearLogButton.addEventListener("click", () => {
  conversationLog.innerHTML = "";
  keepLatestConversationVisible();
});

function renderStep() {
  const step = steps[currentStep];
  stepKicker.textContent = `Paso ${currentStep + 1}`;
  stepTitle.textContent = step.title;
  stepGoal.textContent = step.goal;

  stepBody.innerHTML = "";
  const template = document.querySelector(`#${step.template}`);
  stepBody.append(template.content.cloneNode(true));

  renderStepOverview();
  prevStepButton.disabled = currentStep === 0;
  nextStepButton.disabled = currentStep === steps.length - 1 || !canContinueFromCurrentStep();
  nextStepButton.hidden = currentStep === steps.length - 1;
  nextStepButton.textContent = nextStepButtonLabel();

  stepTabs.forEach((tab, index) => {
    tab.classList.toggle("active", index === currentStep);
    tab.classList.toggle("done", isStepDone(index));
    tab.classList.toggle("pending", index === recommendedStepIndex());
    tab.title = stepStatusText(index);
  });

  bindStepActions();
}

function renderProcessControl() {
  renderProcessSteps();
  renderProcessInteractions();
  renderProcessValues();
  processNext.textContent = latestNextAction || recommendedNextText(recommendedStepIndex());
}

function renderProcessSteps() {
  processSteps.innerHTML = "";
  steps.forEach((step, index) => {
    const item = document.createElement("button");
    item.type = "button";
    item.className = `process-step ${isStepDone(index) ? "done" : ""} ${
      index === currentStep ? "active" : ""
    } ${index === recommendedStepIndex() ? "recommended" : ""}`;
    item.textContent = `${index + 1}. ${step.title}`;
    item.title = stepStatusText(index);
    item.addEventListener("click", () => {
      currentStep = index;
      rememberStep();
      renderStep();
      renderProcessControl();
    });
    processSteps.append(item);
  });
}

function renderProcessInteractions() {
  processInteractions.innerHTML = "";
  if (interactionHistory.length === 0) {
    const empty = document.createElement("p");
    empty.textContent = "Sin interacciones todavia.";
    processInteractions.append(empty);
    return;
  }

  interactionHistory.slice(-4).forEach((entry) => {
    const item = document.createElement("p");
    item.className = `interaction-line ${entry.role}`;
    item.textContent = `${entry.role === "user" ? "Alumno" : "Tutor"}: ${entry.text}`;
    processInteractions.append(item);
  });
}

function renderProcessValues() {
  processValues.innerHTML = "";
  const fn = currentFunctionState();
  if (!latestState || !fn) {
    const empty = document.createElement("p");
    empty.textContent = "Sin funcion analizada.";
    processValues.append(empty);
    return;
  }

  const values = [
    ["Funcion", fn.name || "sin nombre"],
    ["Interfaz", fn.interface || "pendiente"],
    ["Parametros", parameterNames(fn)],
    ["Capacidades", Array.isArray(fn.features) && fn.features.length ? fn.features.join(", ") : "sin extensiones"],
    ["Paso global", latestState.global_step || "sin definir"],
  ];

  values.forEach(([label, value]) => {
    const row = document.createElement("p");
    row.innerHTML = `<strong>${label}:</strong> ${escapeHtml(value)}`;
    processValues.append(row);
  });
}

function renderStepOverview() {
  currentStepState.innerHTML = "";
  currentStepActions.innerHTML = "";

  stepStatusItems(currentStep).forEach((item) => {
    const pill = document.createElement("span");
    pill.className = `step-pill ${item.status === "done" ? "done" : ""}`;
    pill.textContent = `${item.label}: ${item.value}`;
    currentStepState.append(pill);
  });

  stepActionItems(currentStep).forEach((item) => {
    const pill = document.createElement("span");
    pill.className = `action-pill ${item.primary ? "primary" : ""}`;
    pill.textContent = item.label;
    currentStepActions.append(pill);
  });

  recommendedNext.textContent = recommendedNextText(currentStep);
}

function bindStepActions() {
  stepBody.querySelectorAll("[data-example]").forEach((button) => {
    button.addEventListener("click", () => {
      const textarea = stepBody.querySelector("#function-source");
      textarea.value = examples[button.dataset.example] || examples.hello;
      textarea.focus();
    });
  });

  const textarea = stepBody.querySelector("#function-source");
  if (textarea && !textarea.value) {
    textarea.value = window.localStorage.getItem("flaskTutor.functionSource") || examples.hello;
    textarea.addEventListener("input", () => {
      window.localStorage.setItem("flaskTutor.functionSource", textarea.value);
    });
  }

  stepBody.querySelectorAll("[data-action='send-function']").forEach((button) => {
    button.addEventListener("click", async () => {
      const source = stepBody.querySelector("#function-source").value.trim();
      if (!source) {
        appendMessage("agent", "Pega una funcion Python antes de analizar.", true);
        return;
      }
      window.localStorage.setItem("flaskTutor.functionSource", source);
      window.localStorage.removeItem("flaskTutor.interfaceSelected");
      await sendAgentMessage(source, { nextStep: 1 });
    });
  });

  stepBody.querySelectorAll("[data-action='show-state']").forEach((button) => {
    button.addEventListener("click", () => sendAgentMessage("estado", { silentAdvance: true }));
  });

  stepBody.querySelectorAll("[data-send]").forEach((button) => {
    button.addEventListener("click", () => {
      const nextStep = inferNextStep(button.dataset.send);
      sendAgentMessage(button.dataset.send, {
        nextStep,
        selectedInterface: currentStep === 2,
      });
    });
  });

  stepBody.querySelectorAll("[data-build-step]").forEach((button) => {
    button.addEventListener("click", () => {
      sendAgentMessage("siguiente", {
        nextStep: nextStepAfterBuild(button.dataset.buildStep),
        displayText: button.textContent.trim(),
      });
    });
  });

  stepBody.querySelectorAll("[data-question]").forEach((button) => {
    button.addEventListener("click", () => {
      sendAgentMessage(button.dataset.question, { silentAdvance: true });
    });
  });
}

function inferNextStep(message) {
  if (currentStep === 2 && message) {
    return 3;
  }
  return currentStep;
}

function nextStepAfterBuild(buildStep) {
  const buildStepTargets = {
    service: 4,
    route: 5,
    template: 6,
    app_factory: 7,
  };
  return buildStepTargets[buildStep] ?? currentStep;
}

async function sendAgentMessage(message, options = {}) {
  const text = (message || "").trim();
  if (!text || busy) {
    return;
  }

  const visibleMessage = options.displayText || text;
  rememberInteraction("user", visibleMessage);
  appendMessage("user", visibleMessage, false);
  renderProcessControl();
  setBusy(true);

  try {
    const response = await fetch("/api/message", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        user_id: userId,
        message: text,
      }),
    });
    const data = await response.json();
    renderAgentResponse(data, options);

    if (typeof options.nextStep === "number") {
      currentStep = options.nextStep;
      maxStepReached = Math.max(maxStepReached, currentStep);
      rememberStep();
      renderStep();
    }
  } catch (error) {
    appendMessage("agent", `No se pudo contactar con la app tutora: ${error}`, true);
  } finally {
    setBusy(false);
  }
}

function renderAgentResponse(data, options = {}) {
  let text = data.reply || "(sin respuesta)";
  latestNextAction = data.next_action || "";
  if (data.next_action) {
    text += `\n\nSiguiente accion: ${data.next_action}`;
  }
  if (data.error) {
    text += `\n\nCodigo: ${data.error}`;
  }

  rememberInteraction("agent", compactInteractionText(data.reply || data.error || "(sin respuesta)"));
  appendMessage("agent", text, !data.ok);

  const state = data.data && data.data.state;
  if (state) {
    latestState = state;
    if (options.selectedInterface) {
      window.localStorage.setItem("flaskTutor.interfaceSelected", "true");
    }
    renderState(state);
    syncStepWithState(data.step, state);
  }

  if (Array.isArray(data.artifacts) && data.artifacts.length > 0) {
    renderArtifacts(data.artifacts);
  }

  renderProcessControl();
}

function syncStepWithState(step, state) {
  if (step === "service") {
    maxStepReached = Math.max(maxStepReached, 4);
  } else if (step === "route") {
    maxStepReached = Math.max(maxStepReached, 5);
  } else if (step === "template" || step === "tests") {
    maxStepReached = Math.max(maxStepReached, 6);
  } else if (step === "app_factory") {
    maxStepReached = Math.max(maxStepReached, 7);
  }

  if (state.current_function && currentStep < 1) {
    maxStepReached = Math.max(maxStepReached, 1);
  }

  rememberStep();
  stepTabs.forEach((tab, index) => {
    tab.classList.toggle("done", isStepDone(index));
    tab.classList.toggle("pending", index === recommendedStepIndex());
    tab.title = stepStatusText(index);
  });
  renderStepOverview();
  renderProcessControl();
  nextStepButton.disabled = currentStep === steps.length - 1 || !canContinueFromCurrentStep();
  nextStepButton.hidden = currentStep === steps.length - 1;
  nextStepButton.textContent = nextStepButtonLabel();
}

function canContinueFromCurrentStep() {
  if (currentStep >= steps.length - 1) {
    return false;
  }

  if (currentStep === 0) {
    return hasCurrentFunction();
  }

  if (currentStep === 1) {
    return hasCurrentFunction();
  }

  if (currentStep === 2) {
    return hasInterfaceChoice();
  }

  if (currentStep === 3) {
    return isFunctionStepDone("service");
  }

  if (currentStep === 4) {
    return isFunctionStepDone("route");
  }

  if (currentStep === 5) {
    return isFunctionStepDone("template");
  }

  if (currentStep === 6) {
    return isProjectIntegrated();
  }

  return false;
}

function hasCurrentFunction() {
  return Boolean(latestState && latestState.current_function);
}

function currentFunctionState() {
  if (!latestState || !latestState.current_function) {
    return null;
  }
  return latestState.functions && latestState.functions[latestState.current_function];
}

function hasInterfaceChoice() {
  const fn = currentFunctionState();
  const interfaceSelected = window.localStorage.getItem("flaskTutor.interfaceSelected") === "true";
  return Boolean(
    fn &&
      fn.interface &&
      (interfaceSelected ||
        isFunctionStepDone("service") ||
        isFunctionStepDone("route") ||
        isFunctionStepDone("template") ||
        isProjectIntegrated())
  );
}

function isFunctionStepDone(stepName) {
  const fn = currentFunctionState();
  return Boolean(fn && fn.steps && fn.steps[stepName] === "done");
}

function isProjectIntegrated() {
  return Boolean(latestState && latestState.global_step === "integration_done");
}

function stepStatusItems(index) {
  const fn = currentFunctionState();
  const stepsState = (fn && fn.steps) || {};

  if (index === 0) {
    return [
      {
        label: "funcion",
        value: hasCurrentFunction() ? "detectada" : "sin funcion",
        status: hasCurrentFunction() ? "done" : "pending",
      },
    ];
  }

  if (index === 1) {
    return [
      {
        label: "analysis",
        value: stepsState.analysis || "pending",
        status: stepsState.analysis,
      },
      {
        label: "funcion actual",
        value: latestState && latestState.current_function ? latestState.current_function : "ninguna",
        status: hasCurrentFunction() ? "done" : "pending",
      },
    ];
  }

  if (index === 2) {
    return [
      {
        label: "interface",
        value: hasInterfaceChoice() && fn ? fn.interface : "pendiente de confirmar",
        status: hasInterfaceChoice() ? "done" : "pending",
      },
    ];
  }

  if (index === 3) {
    return [
      {
        label: "service",
        value: stepsState.service || "pending",
        status: stepsState.service,
      },
    ];
  }

  if (index === 4) {
    return [
      {
        label: "route",
        value: stepsState.route || "pending",
        status: stepsState.route,
      },
    ];
  }

  if (index === 5) {
    return [
      {
        label: "template/API",
        value: stepsState.template || "pending",
        status: stepsState.template,
      },
      {
        label: "modo",
        value: fn ? fn.interface : "sin interfaz",
        status: fn && fn.interface ? "done" : "pending",
      },
    ];
  }

  if (index === 6) {
    return [
      {
        label: "registration",
        value: stepsState.registration || "pending",
        status: stepsState.registration,
      },
      {
        label: "global",
        value: latestState ? latestState.global_step : "sin estado",
        status: isProjectIntegrated() ? "done" : "pending",
      },
    ];
  }

  const features = fn && Array.isArray(fn.features) ? fn.features : [];
  return [
    {
      label: "features",
      value: features.length ? features.join(", ") : "sin extensiones",
      status: features.length ? "done" : "pending",
    },
  ];
}

function stepActionItems(index) {
  if (index === 0) {
    return [
      { label: "Pegar funcion", primary: !hasCurrentFunction() },
      { label: "Usar ejemplo" },
      { label: "Analizar funcion", primary: !hasCurrentFunction() },
      { label: "Explicar funcion" },
    ];
  }

  if (index === 1) {
    return [
      { label: "Ver analisis detectado", primary: hasCurrentFunction() },
      { label: "Ver parametros" },
      { label: "Explicar analisis" },
    ];
  }

  if (index === 2) {
    return [
      { label: "Formulario HTML", primary: !hasInterfaceChoice() },
      { label: "API JSON", primary: !hasInterfaceChoice() },
      { label: "Formulario + API", primary: !hasInterfaceChoice() },
      { label: "Comparar interfaces" },
    ];
  }

  if (index === 3) {
    return [
      { label: "Generar service", primary: !isFunctionStepDone("service") },
      { label: "Ver codigo generado" },
      { label: "Explicar service" },
    ];
  }

  if (index === 4) {
    return [
      { label: "Generar route", primary: !isFunctionStepDone("route") },
      { label: "Explicar route" },
      { label: "Explicar blueprint" },
    ];
  }

  if (index === 5) {
    const fn = currentFunctionState();
    const mode = fn && fn.interface;
    const actions = [{ label: "Generar template/API", primary: !isFunctionStepDone("template") }];
    if (mode === "json_api") {
      actions.push({ label: "Explicar request.get_json" }, { label: "Explicar jsonify" });
    } else if (mode === "both") {
      actions.push({ label: "Explicar HTML + JSON" }, { label: "Explicar render_template" }, { label: "Explicar jsonify" });
    } else {
      actions.push({ label: "Explicar render_template" }, { label: "Explicar request.form" });
    }
    return actions;
  }

  if (index === 6) {
    return [
      { label: "Generar app factory", primary: !isProjectIntegrated() },
      { label: "Registrar blueprints" },
      { label: "Explicar create_app" },
      { label: "Explicar register_blueprint" },
    ];
  }

  return [
    { label: "Anadir flash" },
    { label: "Anadir redirect" },
    { label: "Anadir sessions" },
    { label: "Anadir static files" },
    { label: "Anadir base template" },
    { label: "Anadir error handlers" },
    { label: "Anadir tests" },
    { label: "Regenerar pieza afectada", primary: true },
  ];
}

function recommendedStepIndex() {
  const fn = currentFunctionState();
  if (!hasCurrentFunction()) {
    return 0;
  }
  if (!hasInterfaceChoice()) {
    return 2;
  }
  if (!isFunctionStepDone("service")) {
    return 3;
  }
  if (!isFunctionStepDone("route")) {
    return 4;
  }
  if (!isFunctionStepDone("template")) {
    return 5;
  }
  if (fn && fn.steps && fn.steps.registration !== "done") {
    return 6;
  }
  return 7;
}

function recommendedNextText(index) {
  const recommended = recommendedStepIndex();

  if (index !== recommended) {
    return `El agente recomienda trabajar ahora en: ${steps[recommended].title}.`;
  }

  if (index === 0) {
    return hasCurrentFunction() ? "Revisa el analisis de la funcion." : "Pega una funcion Python y pulsa Analizar funcion.";
  }
  if (index === 1) {
    return "Comprueba nombre y parametros; despues elige la interfaz Flask.";
  }
  if (index === 2) {
    return hasInterfaceChoice() ? "La interfaz esta elegida. Genera el service." : "Elige formulario HTML, API JSON o ambas.";
  }
  if (index === 3) {
    return isFunctionStepDone("service") ? "El service ya esta generado. Continua a route." : "Genera el service.";
  }
  if (index === 4) {
    return isFunctionStepDone("route") ? "La route ya esta generada. Continua a template/API." : "Genera la route.";
  }
  if (index === 5) {
    return isFunctionStepDone("template") ? "La salida ya esta generada. Continua a app factory." : "Genera el template o la informacion de API.";
  }
  if (index === 6) {
    return isProjectIntegrated() ? "La app esta integrada. Puedes anadir extensiones." : "Genera el app factory.";
  }
  return "Anade una extension Flask o regenera la siguiente pieza afectada.";
}

function isStepDone(index) {
  if (index === 0 || index === 1) {
    return hasCurrentFunction();
  }
  if (index === 2) {
    return hasInterfaceChoice();
  }
  if (index === 3) {
    return isFunctionStepDone("service");
  }
  if (index === 4) {
    return isFunctionStepDone("route");
  }
  if (index === 5) {
    return isFunctionStepDone("template");
  }
  if (index === 6) {
    return isProjectIntegrated();
  }
  return Boolean(latestState && latestState.global_step === "integration_done");
}

function stepStatusText(index) {
  return stepStatusItems(index)
    .map((item) => `${item.label}: ${item.value}`)
    .join(" | ");
}

function nextStepButtonLabel() {
  const next = Math.min(steps.length - 1, currentStep + 1);
  return `Ir a ${steps[next].title}`;
}

function renderState(state) {
  stateSummary.innerHTML = "";

  const global = document.createElement("p");
  global.textContent = `Paso global: ${state.global_step || "sin definir"}`;
  const current = document.createElement("p");
  current.textContent = `Funcion actual: ${state.current_function || "ninguna"}`;
  stateSummary.append(global, current);

  const functions = state.functions || {};
  const names = Object.keys(functions);
  if (names.length === 0) {
    const empty = document.createElement("p");
    empty.textContent = "No hay funciones detectadas.";
    stateSummary.append(empty);
    return;
  }

  names.forEach((name) => {
    const fn = functions[name];
    const block = document.createElement("section");
    block.className = "state-function";

    const title = document.createElement("strong");
    title.textContent = `${fn.name} - interfaz: ${fn.interface}`;
    block.append(title);

    const params = Array.isArray(fn.parameters)
      ? fn.parameters.map((param) => param.name).join(", ")
      : "";
    if (params) {
      const p = document.createElement("p");
      p.textContent = `Parametros: ${params}`;
      block.append(p);
    }

    if (Array.isArray(fn.features) && fn.features.length > 0) {
      const features = document.createElement("p");
      features.textContent = `Capacidades: ${fn.features.join(", ")}`;
      block.append(features);
    }

    const stepsBox = document.createElement("div");
    stepsBox.className = "steps";
    Object.entries(fn.steps || {}).forEach(([stepName, value]) => {
      if (stepName === "tests" && !(fn.features || []).includes("tests")) {
        return;
      }

      const pill = document.createElement("span");
      pill.className = `step-pill ${value === "done" ? "done" : ""}`;
      pill.textContent = `${stepLabel(stepName)}: ${value}`;
      stepsBox.append(pill);
    });
    block.append(stepsBox);
    stateSummary.append(block);
  });
}

function stepLabel(stepName) {
  const labels = {
    registration: "app factory",
  };
  return labels[stepName] || stepName;
}

function parameterNames(fn) {
  if (!Array.isArray(fn.parameters) || fn.parameters.length === 0) {
    return "sin parametros";
  }
  return fn.parameters.map((param) => param.name).join(", ");
}

function rememberInteraction(role, text) {
  interactionHistory.push({
    role,
    text: compactInteractionText(text),
  });
  interactionHistory = interactionHistory.slice(-8);
}

function compactInteractionText(text) {
  const clean = String(text || "").replace(/\s+/g, " ").trim();
  return clean.length > 120 ? `${clean.slice(0, 117)}...` : clean;
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function renderArtifacts(artifacts) {
  artifactList.innerHTML = "";

  artifacts.forEach((artifact) => {
    const item = document.createElement("article");
    item.className = "artifact";

    const header = document.createElement("div");
    header.className = "artifact-header";

    const path = document.createElement("span");
    path.className = "artifact-path";
    path.textContent = `${artifact.path || "sin_ruta"} [${artifact.language || "text"}]`;

    const copy = document.createElement("button");
    copy.type = "button";
    copy.textContent = "Copiar";
    copy.addEventListener("click", async () => {
      await navigator.clipboard.writeText(artifact.content || "");
      copy.textContent = "Copiado";
      window.setTimeout(() => {
        copy.textContent = "Copiar";
      }, 1200);
    });

    const code = document.createElement("pre");
    code.textContent = artifact.content || "";

    header.append(path, copy);
    item.append(header, code);
    artifactList.append(item);
  });
}

function appendMessage(role, text, isError) {
  const item = document.createElement("article");
  item.className = `message ${role}${isError ? " error" : ""}`;

  const label = document.createElement("strong");
  label.textContent = role === "user" ? "Alumno" : "Tutor";

  const body = document.createElement("pre");
  body.textContent = text;

  item.append(label, body);
  conversationLog.append(item);
  keepLatestConversationVisible(item);
}

function keepLatestConversationVisible(item = conversationLog.lastElementChild) {
  window.requestAnimationFrame(() => {
    if (item) {
      item.scrollIntoView({ block: "end" });
      return;
    }
    conversationLog.scrollTop = conversationLog.scrollHeight;
  });
}

async function showLlmStatus() {
  if (busy) {
    return;
  }
  setBusy(true);
  try {
    const response = await fetch("/api/llm/status");
    const data = await response.json();
    const lines = [
      `Activo: ${data.enabled}`,
      `OK: ${data.ok}`,
    ];
    if (data.provider) {
      lines.push(`Proveedor: ${data.provider}`);
    }
    if (data.model) {
      lines.push(`Modelo: ${data.model}`);
    }
    if (data.error) {
      lines.push(`Error: ${data.error}`);
    }
    appendMessage("agent", lines.join("\n"), !data.ok);
  } catch (error) {
    appendMessage("agent", `No se pudo consultar el LLM: ${error}`, true);
  } finally {
    setBusy(false);
  }
}

async function refreshState() {
  try {
    const response = await fetch("/api/message", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        user_id: userId,
        message: "estado",
      }),
    });
    const data = await response.json();
    const state = data.data && data.data.state;
    if (!state) {
      return;
    }

    latestState = state;
    latestNextAction = data.next_action || latestNextAction;
    renderState(state);
    syncStepWithState(data.step, state);
    currentStep = recommendedStepIndex();
    maxStepReached = Math.max(maxStepReached, currentStep);
    rememberStep();
    renderStep();
    renderProcessControl();
  } catch (error) {
    stateSummary.innerHTML = "<p>No se pudo cargar el estado inicial del agente.</p>";
    renderProcessControl();
  }
}

function setBusy(value) {
  busy = value;
  document.querySelectorAll("button").forEach((button) => {
    button.disabled = value;
  });
  prevStepButton.disabled = value || currentStep === 0;
  nextStepButton.disabled = value || currentStep === steps.length - 1 || !canContinueFromCurrentStep();
  nextStepButton.hidden = currentStep === steps.length - 1;
}

function rememberStep() {
  window.localStorage.setItem("flaskTutor.currentStep", String(currentStep));
  window.localStorage.setItem("flaskTutor.maxStepReached", String(maxStepReached));
}
