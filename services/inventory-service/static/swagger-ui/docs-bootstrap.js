window.addEventListener("load", () => {
  const root = document.getElementById("swagger-ui");
  const swagger = window.SwaggerUIBundle;
  if (!root || !swagger) {
    return;
  }

  const ui = swagger({
    url: root.dataset.openapiUrl,
    dom_id: "#swagger-ui",
    layout: "BaseLayout",
    deepLinking: true,
    showExtensions: true,
    showCommonExtensions: true,
    persistAuthorization: true,
    displayRequestDuration: true,
    tryItOutEnabled: true,
    defaultModelsExpandDepth: 1,
    docExpansion: "list",
    oauth2RedirectUrl: root.dataset.oauth2RedirectUrl,
    presets: [swagger.presets.apis, swagger.SwaggerUIStandalonePreset].filter(Boolean),
  });

  const defaultApiKey = root.dataset.defaultApiKey;
  if (defaultApiKey && typeof ui.preauthorizeApiKey === "function") {
    ui.preauthorizeApiKey("APIKeyHeader", defaultApiKey);
  }
});
